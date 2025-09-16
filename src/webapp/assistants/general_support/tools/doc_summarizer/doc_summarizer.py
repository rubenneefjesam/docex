# src/webapp/assistants/general_support/tools/doc_structured_summary/readers.py
from __future__ import annotations
from pathlib import Path
from typing import Tuple

from webapp.core.utils.docx_utils import read_docx  # jij hebt deze al
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


def read_any(path: Path) -> Tuple[str, str]:
    """
    Lees een bestand naar platte tekst.
    Returns: (extensie, tekst)
    """
    ext = path.suffix.lower()
    if ext == ".docx":
        return ext, read_docx(str(path))
    if ext == ".pdf":
        if PdfReader is None:
            raise RuntimeError("pypdf ontbreekt (voeg 'pypdf' toe aan requirements.txt).")
        text = _read_pdf_text(path)
        return ext, text
    if ext in {".txt", ".md"}:
        return ext, path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Niet-ondersteund bestandstype: {ext}")


def _read_pdf_text(path: Path) -> str:
    out = []
    reader = PdfReader(str(path))
    for page in reader.pages:
        txt = page.extract_text() or ""
        out.append(txt.strip())
    return "\n".join(out)
