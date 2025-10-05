# io_utils_extended.py
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import re
import hashlib
import time

# Import slechts voor PDF-pagina's als beschikbaar; soft dependency
try:
    from pypdf import PdfReader  # alleen gebruikt voor page_count (optioneel)
except Exception:
    PdfReader = None


# ────────────────────────────────────────────────────────────────
# Helpers voor ID-parsing en normalisatie
# ────────────────────────────────────────────────────────────────
_ID_PATTERNS = [
    r"(C\d{1,6}).*?(P\d{1,6})",                          # C123 ... P456
    r"CLIENT[_-]?(?P<c>\d{1,6}).*?PROJECT[_-]?(?P<p>\d{1,6})",
    r"KLANT[_-]?(?P<c>\d{1,6}).*?PROJECT[_-]?(?P<p>\d{1,6})",
    r"(?P<c>C\d{1,6}).*",                                 # losse client
    r".*(?P<p>P\d{1,6}).*",                               # losse project
]

def _norm_id(val: Optional[str], kind: str) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    # Forceer prefix als het alleen digits zijn
    if kind == "client":
        if v.startswith("C"):
            return v
        return f"C{v}" if v.isdigit() else v
    if kind == "project":
        if v.startswith("P"):
            return v
        return f"P{v}" if v.isdigit() else v
    return v

def _parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    if not name:
        return None, None
    s = name.upper()
    # 1) dubbele match
    m = re.search(r"(C\d{1,6}).*?(P\d{1,6})", s)
    if m:
        return m.group(1), m.group(2)
    # 2) gelabelde varianten
    m2 = re.search(r"CLIENT[_-]?(\d{1,6}).*?PROJECT[_-]?(\d{1,6})", s)
    if m2:
        return f"C{m2.group(1)}", f"P{m2.group(2)}"
    m3 = re.search(r"KLANT[_-]?(\d{1,6}).*?PROJECT[_-]?(\d{1,6})", s)
    if m3:
        return f"C{m3.group(1)}", f"P{m3.group(2)}"
    # 3) losse captures
    c = re.search(r"(C\d{1,6})", s)
    p = re.search(r"(P\d{1,6})", s)
    return (c.group(1) if c else None), (p.group(1) if p else None)


# ────────────────────────────────────────────────────────────────
# Bestandsselectie
# ────────────────────────────────────────────────────────────────
def find_files_in_dir(
    base: Path,
    exts: List[str] = None,
    exclude_dirs: List[str] = None,
    max_files: Optional[int] = None,
    min_size_bytes: int = 0,
    max_size_bytes: Optional[int] = None,
) -> List[Path]:
    """
    Vind bestanden met gegeven extensies, met filters voor (sub)folders en grootte.
    Sorteert deterministisch op pad.
    """
    exts = [e.lower() for e in (exts or [".pdf", ".docx", ".txt", ".md"])]
    exclude_dirs = {d.lower() for d in (exclude_dirs or ["__pycache__", ".git", ".venv", "node_modules"])}
    files: List[Path] = []
    for p in base.rglob("*"):
        if p.is_dir():
            # skippen op foldernaam (alleen directe match, rglob loopt toch recursief)
            if p.name.lower() in exclude_dirs:
                continue
        elif p.is_file() and p.suffix.lower() in exts:
            try:
                sz = p.stat().st_size
                if sz < min_size_bytes:
                    continue
                if max_size_bytes is not None and sz > max_size_bytes:
                    continue
                files.append(p)
            except Exception:
                # stat-fout → overslaan
                continue

    files = sorted(files, key=lambda x: str(x).lower())
    if max_files is not None:
        return files[:max_files]
    return files


# ────────────────────────────────────────────────────────────────
# ID’s uit padstructuur halen (tot 3 niveaus omhoog)
# ────────────────────────────────────────────────────────────────
def parse_ids_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    cid, pid = _parse_ids_from_filename(path.name)
    if cid and pid:
        return cid, pid
    # check ouders t/m 3 niveaus
    ancestors = [path.parent, path.parent.parent, getattr(path.parent.parent, "parent", None)]
    for anc in ancestors:
        if not anc:
            continue
        a_cid, a_pid = _parse_ids_from_filename(anc.name)
        if a_cid and a_pid:
            return a_cid, a_pid
        # fallback: solo P/C in mapnaam
        m_p = re.search(r"(P\d{1,6})", anc.name.upper())
        m_c = re.search(r"(C\d{1,6})", anc.name.upper())
        if (m_c and not cid) or (m_p and not pid):
            return (m_c.group(1) if m_c else cid), (m_p.group(1) if m_p else pid)
    return cid, pid


# ────────────────────────────────────────────────────────────────
# Tekst + metadata uit bestand (pdf/docx/txt/md) — pdf-tekst via pdf_io
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

def _pdf_page_count(path: Path) -> Optional[int]:
    if PdfReader is None:
        return None
    try:
        r = PdfReader(str(path))
        if getattr(r, "is_encrypted", False):
            try:
                r.decrypt("")  # probeer lege wachtwoord
            except Exception:
                return None
        return len(r.pages)
    except Exception:
        return None

def read_and_meta(path: Path) -> Tuple[str, Dict[str, Any]]:
    """
    Leest tekst via pdf_io.read_text_from_file (voor PDF ook OCR fallback).
    Geeft uitgebreidere metadata terug voor traceability.
    """
    from .pdf_io import read_text_from_file  # lokale import om circular te vermijden

    meta: Dict[str, Any] = {
        "filepath": str(path),
        "filename": path.name,
        "filesize": None,
        "modified_time": None,
        "client_id": None,
        "project_id": None,
        "checksum": None,
        "page_count": None,
        "extract_method": None,     # wordt door pdf_io gezet via return-aux
    }

    try:
        st = path.stat()
        meta["filesize"] = int(st.st_size)
        meta["modified_time"] = int(st.st_mtime)
    except Exception:
        pass

    # Snelle ID-parsing
    cid, pid = _parse_ids_from_filename(path.name)
    if not cid or not pid:
        c2, p2 = parse_ids_from_path(path)
        cid = cid or c2
        pid = pid or p2
    if cid:
        meta["client_id"] = _norm_id(cid, "client")
    if pid:
        meta["project_id"] = _norm_id(pid, "project")

    # Optioneel: page count voor PD
