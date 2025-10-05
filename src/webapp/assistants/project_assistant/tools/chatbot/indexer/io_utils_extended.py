# io_utils_extended.py
from pathlib import Path
from typing import List, Tuple, Optional
import re

# reuse pdf/docx readers
from .pdf_io import read_text_from_file
from ..io_utils import parse_ids_from_filename  # if you keep io_utils in root; else duplicate logic

def find_files_in_dir(base: Path, exts=None) -> List[Path]:
    """Recursively find files under base with given extensions."""
    exts = [e.lower() for e in (exts or [".pdf", ".docx", ".txt"])]
    files = []
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files

def parse_ids_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """Try parse ids from filename then parent folders (reuse filename parser)."""
    cid, pid = parse_ids_from_filename(path.name)
    if cid and pid:
        return cid, pid

    for anc in (path.parent, path.parent.parent):
        if not anc:
            continue
        a_cid, a_pid = parse_ids_from_filename(anc.name)
        if a_cid and a_pid:
            return a_cid, a_pid
        m = re.search(r"(P\d{1,6})", anc.name.upper())
        if m:
            p_found = m.group(1)
            m2 = re.search(r"(C\d{1,6})", anc.name.upper())
            c_found = m2.group(1) if m2 else None
            return c_found, p_found
    return cid, pid

def read_and_meta(path: Path) -> Tuple[str, dict]:
    """
    Read a file and return (text, meta).
    meta contains: filepath, filename, optional client_id, project_id.
    """
    txt = read_text_from_file(path)
    meta = {"filepath": str(path), "filename": path.name}
    # parse ids
    cid, pid = parse_ids_from_filename(path.name)
    if not cid or not pid:
        cid2, pid2 = parse_ids_from_path(path)
        cid = cid or cid2
        pid = pid or pid2
    if cid:
        meta["client_id"] = cid
    if pid:
        meta["project_id"] = pid
    return txt or "", meta
