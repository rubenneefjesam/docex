# pdf_io.py
from pathlib import Path
from typing import Optional
import os

# primary PDF reader
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

# optional: docx
try:
    import docx
except Exception:
    docx = None

# optional OCR libs
try:
    import pytesseract
    from pdf2image import convert_from_path
except Exception:
    pytesseract = None
    convert_from_path = None

def _read_pdf_text_pypdf(path: Path) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(str(path))
        parts = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ""
            except Exception:
                t = ""
            if t:
                parts.append(t.strip())
        return "\n\n".join(parts)
    except Exception:
        return ""

def _read_docx(path: Path) -> str:
    if docx is None:
        return ""
    try:
        d = docx.Document(str(path))
        parts = [(p.text or "").strip() for p in d.paragraphs if (p.text or "").strip()]
        return "\n".join(parts)
    except Exception:
        return ""

def _ocr_pdf(path: Path) -> str:
    """Try OCR using pdf2image + pytesseract if available."""
    if convert_from_path is None or pytesseract is None:
        return ""
    try:
        pages = convert_from_path(str(path), dpi=200)
        texts = []
        for img in pages:
            txt = pytesseract.image_to_string(img, lang='eng+nld')  # try english + dutch if installed
            if txt:
                texts.append(txt.strip())
        return "\n\n".join(texts)
    except Exception:
        return ""

def read_text_from_file(path: Path) -> str:
    """Return plain text from pdf/docx/txt. Use OCR as fallback for pdfs."""
    if not path.exists():
        return ""
    suf = path.suffix.lower()
    if suf == ".pdf":
        t = _read_pdf_text_pypdf(path)
        if t and t.strip():
            return t
        # fallback to OCR
        o = _ocr_pdf(path)
        return o or ""
    if suf == ".docx":
        return _read_docx(path)
    if suf in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
