# io_utils_extended.py
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import re
import hashlib
import time

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


# ────────────────────────────────────────────────────────────────
# Helpers voor ID-parsing en normalisatie
# ────────────────────────────────────────────────────────────────
def _norm_id(val: Optional[str], kind: str) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    if kind == "client":
        return v if v.startswith("C") else ("C" + v if v.isdigit() else v)
    if kind == "project":
        return v if v.startswith("P") else ("P" + v if v.isdigit() else v)
    return v


def _parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    if not name:
        return None, None
    s = name.upper()
    # Probeer C…P… patronen
    m = re.search(r"(C\d{1,6}).*?(P\d{1,6})", s)
    if m:
        return m.group(1), m.group(2)
    # Losse matches
    c = re.search(r"(C\d{1,6})", s)
    p = re.search(r"(P\d{1,6})", s)
    return (c.group(1) if c else None), (p.group(1) if p else None)


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
# IDs uit padstructuur halen
# ────────────────────────────────────────────────────────────────
def parse_ids_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    cid, pid = _parse_ids_from_filename(path.name)
    if cid and pid:
        return cid, pid
    for anc in (path.parent, path.parent.parent, getattr(path.parent.parent, "parent", None)):
        if not anc:
            continue
        a_cid, a_pid = _parse_ids_from_filename(anc.name)
        if a_cid and a_pid:
            return a_cid, a_pid
        m_p = re.search(r"(P\d{1,6})", anc.name.upper())
        m_c = re.search(r"(C\d{1,6})", anc.name.upper())
        if (m_c and not cid) or (m_p and not pid):
            return (m_c.group(1) if m_c else cid), (m_p.group(1) if m_p else pid)
    return cid, pid


# ────────────────────────────────────────────────────────────────
# Checksum + meta uitlezen
# ────────────────────────────────────────────────────────────────
def _file_checksum(path: Path, algo: str = "sha1") -> str:
    h = hashlib.new(algo)
    try:
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()


def read_and_meta(path: Path) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Leest tekst en meta. Compatibel met zowel oude als nieuwe pdf_io.
    Geeft None terug als iets fataal foutgaat.
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
    }

    try:
        st = path.stat()
        meta["filesize"] = int(st.st_size)
        meta["modified_time"] = int(st.st_mtime)
    except Exception:
        pass

    cid, pid = _parse_ids_from_filename(path.name)
    if not cid or not pid:
        c2, p2 = parse_ids_from_path(path)
        cid = cid or c2
        pid = pid or p2
    if cid:
        meta["client_id"] = _norm_id(cid, "client")
    if pid:
        meta["project_id"] = _norm_id(pid, "project")

    # Page count (optioneel)
    if path.suffix.lower() == ".pdf" and PdfReader is not None:
        try:
            r = PdfReader(str(path))
            if getattr(r, "is_encrypted", False):
                try:
                    r.decrypt("")
                except Exception:
                    pass
            meta["page_count"] = len(r.pages)
        except Exception:
            meta["page_count"] = None

    # Tekst ophalen via pdf_io (backward compatibel)
    try:
        from .pdf_io import read_text_from_file
    except Exception as e:
        print(f"[ERROR] pdf_io import failed for {path.name}: {e}")
        return None

    text, method = "", ""
    try:
        text, method = read_text_from_file(path, return_method=True)  # nieuwe variant
    except TypeError:
        # oude variant
        text = read_text_from_file(path)
        method = ""
    except Exception as e:
        print(f"[ERROR] read_text_from_file failed for {path.name}: {e}")
        text, method = "", ""

    meta["extract_method"] = method or None
    meta["checksum"] = _file_checksum(path)
    return (text or "", meta)
