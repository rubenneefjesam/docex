# io_utils.py
"""
I/O helpers: .docx en .txt lezen, bestandsnaam -> client/project parsing, chunking.
Voeg parse_ids_from_path toe om ook parent-folder te scannen.
"""
import os
import tempfile
import re
from typing import Optional, List, Tuple
from pathlib import Path

# optional python-docx
try:
    import docx
except Exception:
    docx = None


def safe_read_docx_text(path: str) -> str:
    """Read plain text from a .docx; return empty string on error."""
    if not docx:
        return ""
    try:
        d = docx.Document(path)
        parts = [(p.text or "").strip() for p in d.paragraphs if (p.text or "").strip()]
        return "\n".join(parts)
    except Exception:
        return ""


def read_uploaded_text(uploaded) -> str:
    """Support .docx and .txt Streamlit uploads (uploaded is Streamlit UploadedFile)."""
    if not uploaded:
        return ""
    name = (uploaded.name or "").lower()
    if name.endswith(".docx") and docx:
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return safe_read_docx_text(p)
    # fallback: .txt
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse client_id and project_id from filename (returns (client, project)).
    Examples handled: C001_P1001, C1-P1001, client001_project1001, explicit C/P patterns.
    """
    if not name:
        return None, None
    s = name.upper()
    m = re.search(r"(C\d{1,6}).*?(P\d{1,6})", s)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(r"CLIENT[_-]?(\d{1,6}).*?PROJECT[_-]?(\d{1,6})", s)
    if m2:
        return f"C{m2.group(1)}", f"P{m2.group(2)}"
    return None, None


def parse_ids_from_path(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Try parse ids from filename first, then check parent and grandparent folder names.
    Returns (client_id, project_id) or (None, None).
    """
    cid, pid = parse_ids_from_filename(path.name)
    if cid and pid:
        return cid, pid

    # check parent and grandparent folder names
    for anc in (path.parent, path.parent.parent):
        if not anc:
            continue
        # direct parse from ancestor folder name
        a_cid, a_pid = parse_ids_from_filename(anc.name)
        if a_cid and a_pid:
            return a_cid, a_pid
        # or detect pattern P\d+ in ancestor name
        m = re.search(r"(P\d{1,6})", anc.name.upper())
        if m:
            p_found = m.group(1)
            # try find C\d+ in same ancestor name
            m2 = re.search(r"(C\d{1,6})", anc.name.upper())
            c_found = m2.group(1) if m2 else None
            return c_found, p_found

    return cid, pid


def chunk_text(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    """Simple sliding-window chunker on characters (keeps words intact at boundaries)."""
    if not text:
        return []
    text = text.strip()
    chunks: List[str] = []
    start = 0
    L = len(text)
    while start < L:
        end = start + size
        if end >= L:
            chunks.append(text[start:L].strip())
            break
        slice_ = text[start:end]
        last_space = slice_.rfind(" ")
        if last_space > int(size * 0.6):
            end = start + last_space
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return [c for c in chunks if c]
