# io_utils_extended.py
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import re
import hashlib
import time
import os
import logging

# Try to reuse centralized helpers when present
try:
    from .id_utils import parse_ids_from_filename_or_path, find_pid_from_ancestors, find_pid_in_text
except Exception:
    # fallback small local implementations if helper not available
    def parse_ids_from_filename_or_path(path_like: Path) -> Tuple[Optional[str], Optional[str]]:
        s = str(path_like).upper()
        c = re.search(r"(C\d{1,6})", s)
        p = re.search(r"(P\d{1,6})", s)
        return (c.group(1) if c else None, p.group(1) if p else None)

    def find_pid_from_ancestors(path_like: Path) -> Optional[str]:
        p = Path(path_like)
        for anc in (p.parent, p.parent.parent):
            if not anc:
                continue
            m = re.search(r"(P\d{1,6})", anc.name.upper())
            if m:
                return m.group(1)
        return None

    def find_pid_in_text(text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"\b(P\d{1,6})\b", text.upper())
        if m:
            return m.group(1)
        return None

# Optional PDF reader
try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None

# logging
logger = logging.getLogger("io_utils_extended")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s io_utils %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
logger.setLevel(os.environ.get("IO_UTILS_LOG_LEVEL", "INFO"))

# env control: whether to compute full checksum (can be slow for many files)
CALC_CHECKSUM = os.getenv("INDEX_CALC_CHECKSUM", "1") == "1"


# ────────────────────────────────────────────────────────────────
# Bestanden vinden
# ────────────────────────────────────────────────────────────────
def find_files_in_dir(base: Path, exts: List[str] = None) -> List[Path]:
    exts = [e.lower() for e in (exts or [".pdf", ".docx", ".txt"])]
    files = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return sorted(files)


# ────────────────────────────────────────────────────────────────
# Lightweight file fingerprint (mtime+size) and optional checksum
# ────────────────────────────────────────────────────────────────
def _file_fingerprint(path: Path) -> str:
    """
    Lightweight fingerprint: sha1(path + mtime + size). Cheap and version-aware.
    """
    try:
        st = path.stat()
        key = f"{str(path)}|{st.st_mtime_ns}|{st.st_size}"
    except Exception:
        key = str(path)
    return hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()


def _file_checksum(path: Path, algo: str = "sha1") -> str:
    """
    Full file checksum (can be slow). Controlled by CALC_CHECKSUM env var.
    """
    if not CALC_CHECKSUM:
        return ""
    h = hashlib.new(algo)
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.debug(f"Checksum failed for {path}: {e}")
        return ""


# ────────────────────────────────────────────────────────────────
# IDs uit padstructuur halen
# ────────────────────────────────────────────────────────────────
def parse_ids_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Wrapper around helper parse. Returns (client_id, project_id).
    """
    try:
        return parse_ids_from_filename_or_path(path)
    except Exception as e:
        logger.debug(f"parse_ids_from_filename_or_path fallback for {path}: {e}")
        # Fallback simple parse
        s = path.name.upper()
        c = re.search(r"(C\d{1,6})", s)
        p = re.search(r"(P\d{1,6})", s)
        return (c.group(1) if c else None, p.group(1) if p else None)


# ────────────────────────────────────────────────────────────────
# Read text + meta (stable API: always returns (text:str, meta:dict))
# ────────────────────────────────────────────────────────────────
def read_and_meta(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Read text and metadata for a path.
    Always returns a tuple (text, meta). Text may be empty string if extraction failed.
    Meta contains keys: filepath, filename, filesize, modified_time, client_id, project_id,
    checksum, extract_method, page_count, file_fingerprint, read_error (optional).
    """
    meta: Dict[str, Any] = {
        "filepath": str(path),
        "filename": path.name,
        "filesize": None,
        "modified_time": None,
        "client_id": None,
        "project_id": None,
        "checksum": None,
        "extract_method": None,
        "page_count": None,
        "file_fingerprint": None,
        "read_error": None,
    }

    try:
        st = path.stat()
        meta["filesize"] = int(st.st_size)
        meta["modified_time"] = int(st.st_mtime)
    except Exception:
        pass

    # Parse IDs from filename/path early
    try:
        parsed_cid, parsed_pid = parse_ids_from_path(path)
        if parsed_cid:
            meta["client_id"] = parsed_cid
        if parsed_pid:
            meta["project_id"] = parsed_pid
    except Exception as e:
        logger.debug(f"parse_ids_from_path failed for {path}: {e}")

    # Page count for PDFs (best-effort)
    if path.suffix.lower() == ".pdf" and PdfReader is not None:
        try:
            r = PdfReader(str(path))
            if getattr(r, "is_encrypted", False):
                try:
                    r.decrypt("")  # try empty password
                except Exception:
                    pass
            meta["page_count"] = len(r.pages)
        except Exception as e:
            logger.debug(f"PdfReader page_count failed for {path.name}: {e}")
            meta["page_count"] = None

    # Try to import project pdf_io extraction function (backward compatible)
    text = ""
    extract_method = None
    try:
        from .pdf_io import read_text_from_file  # local project-specific pdf reader
    except Exception as e:
        logger.warning(f"[WARN] pdf_io import failed for {path.name}: {e} -- returning empty text and meta. Install/restore pdf_io to enable OCR/text extraction.")
        meta["read_error"] = f"pdf_io_import_failed: {e}"
        # still set fingerprint/checksum and return empty text
        meta["file_fingerprint"] = _file_fingerprint(path)
        meta["checksum"] = _file_checksum(path)
        meta["extract_method"] = None
        return "", meta

    # Try to read text; support both new and legacy signatures
    try:
        try:
            text, extract_method = read_text_from_file(path, return_method=True)  # new API
        except TypeError:
            # older variant: returns only text
            text = read_text_from_file(path)
            extract_method = None
    except Exception as e:
        logger.warning(f"[WARN] read_text_from_file failed for {path.name}: {e}")
        meta["read_error"] = f"read_text_failed: {e}"
        text = ""
        extract_method = None

    meta["extract_method"] = extract_method or None
    meta["file_fingerprint"] = _file_fingerprint(path)
    meta["checksum"] = _file_checksum(path)

    # If parsed IDs still missing, try ancestor folder heuristics and text heuristics
    if not meta.get("project_id"):
        try:
            anc_pid = find_pid_from_ancestors(path)
            if anc_pid:
                meta["project_id"] = anc_pid
        except Exception:
            pass

    if not meta.get("project_id") and text:
        try:
            pid_text = find_pid_in_text(text)
            if pid_text:
                meta["project_id"] = pid_text
        except Exception:
            pass

    # ensure client/project are normalized strings (upper)
    if meta.get("client_id"):
        try:
            meta["client_id"] = str(meta["client_id"]).strip().upper()
        except Exception:
            pass
    if meta.get("project_id"):
        try:
            meta["project_id"] = str(meta["project_id"]).strip().upper()
        except Exception:
            pass

    return (text or "", meta)
