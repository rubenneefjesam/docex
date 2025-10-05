import re
from pathlib import Path
from typing import Optional, Tuple, List
from .pdf_io import read_text_from_file


def parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Zoekt patronen zoals C001 P1001 in bestandsnaam. Retourneert (client, project) of (None, None)."""
    if not name:
        return None, None
    s = name.upper()
    m = re.search(r"(C\d{1,5})[^A-Z0-9]{0,4}?(P\d{1,6})", s)
    if m:
        return m.group(1), m.group(2)
    # fallback op expliciete keywords
    m2 = re.search(r"CLIENT[_-]?(\d{1,4}).*?PROJECT[_-]?(\d{1,6})", s)
    if m2:
        return f"C{m2.group(1)}", f"P{m2.group(2)}"
    return None, None


def safe_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", name)


def find_files_in_dir(base: Path, exts: List[str] = None) -> List[Path]:
    if exts is None:
        exts = [".pdf", ".docx", ".txt"]
    files = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return sorted(files)


def read_and_meta(path: Path) -> Tuple[str, dict]:
    text = read_text_from_file(path)
    meta = {
        "filename": path.name,
        "filepath": str(path),
        "size": path.stat().st_size,
    }
    # try parse ids from filename
    cid, pid = parse_ids_from_filename(path.name)
    if cid:
        meta["client_id"] = cid
    if pid:
        meta["project_id"] = pid
    return text, meta
