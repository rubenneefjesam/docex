# io_utils.py

import os
import re
import csv
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

# optionele libs
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    import docx
except Exception:
    docx = None


def read_text_from_file(path: Path) -> str:
    """Leest tekstinhoud uit .pdf, .docx, .txt of .csv."""
    if not path.exists():
        return ""
    ext = path.suffix.lower()
    try:
        if ext == ".pdf":
            return _read_pdf_text(path)
        elif ext == ".docx" and docx:
            return _read_docx_text(path)
        elif ext == ".csv":
            return _read_csv_text(path)
        else:
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _read_pdf_text(path: Path) -> str:
    text = ""
    if fitz:
        try:
            with fitz.open(path) as doc:
                text = "\n".join(page.get_text() for page in doc)
        except Exception:
            pass
    elif pdfplumber:
        try:
            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            pass
    return text.strip()


def _read_docx_text(path: Path) -> str:
    if not docx:
        return ""
    try:
        d = docx.Document(path)
        parts = [p.text.strip() for p in d.paragraphs if p.text.strip()]
        return "\n".join(parts)
    except Exception:
        return ""


def _read_csv_text(path: Path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = [" ".join(r) for r in reader]
        return "\n".join(rows)
    except Exception:
        return ""


def parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Zoekt naar C#### en P#### patronen in bestandsnaam."""
    if not name:
        return None, None
    s = name.upper()
    m = re.search(r"(C\d{1,6}).*?(P\d{1,6})", s)
    if m:
        return m.group(1), m.group(2)
    return None, None


def chunk_text(text: str, size: int = 600, overlap: int = 100) -> List[str]:
    """Splits tekst in overlappende stukken."""
    if not text:
        return []
    text = text.strip()
    chunks: List[str] = []
    start = 0
    L = len(text)
    while start < L:
        end = min(L, start + size)
        slice_ = text[start:end]
        last_space = slice_.rfind(" ")
        if last_space > int(size * 0.6):
            end = start + last_space
        chunks.append(text[start:end].strip())
        start = max(end - overlap, end)
    return [c for c in chunks if c]


def infer_doc_type(path: Path) -> Optional[str]:
    name = path.stem.lower()
    if "technische" in name:
        return "technische omschrijving"
    if "orderbevestiging" in name:
        return "orderbevestiging"
    if "klantcommunicatie" in name:
        return "klantcommunicatie"
    if "klantorder" in name:
        return "klantorder"
    return None


def chunk_to_records(text: str, path: Path) -> List[Dict[str, Any]]:
    """Zet chunks om naar indexrecords met metadata."""
    if not text:
        return []
    cid, pid = parse_ids_from_filename(path.name)
    doc_type = infer_doc_type(path)
    chunks = chunk_text(text)
    records: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks):
        records.append({
            "text": chunk,
            "doc_type": doc_type,
            "client_id": cid,
            "project_id": pid,
            "source_path": str(path),
            "chunk_id": f"{path.stem}_{i}",
        })
    return records


def read_uploaded_text(uploaded) -> str:
    """Compatibiliteitsstub voor oude UI-componenten."""
    try:
        if hasattr(uploaded, "name"):
            suffix = Path(uploaded.name).suffix
            tmpd = tempfile.mkdtemp()
            tmpf = Path(tmpd) / f"uploaded{suffix}"
            with open(tmpf, "wb") as f:
                f.write(uploaded.getbuffer())
            return read_text_from_file(tmpf)
        elif isinstance(uploaded, (str, Path)):
            return read_text_from_file(Path(uploaded))
    except Exception:
        pass
    return ""


def download_bytes_json(results: List[Dict[str, Any]]) -> bytes:
    """Serialiseer resultaten naar JSON-bytes voor download."""
    import json
    return json.dumps(results).encode("utf-8")
