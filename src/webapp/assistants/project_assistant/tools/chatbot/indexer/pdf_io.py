from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None


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


def read_text_from_file(path: Path) -> str:
    """Return plain text or empty string on failure."""
    if not path.exists():
        return ""
    suf = path.suffix.lower()
    if suf == ".pdf":
        t = _read_pdf_text_pypdf(path)
        return t
    if suf == ".docx":
        return _read_docx(path)
    if suf in (".txt", ".md"):
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    # fallback: try reading as text
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
