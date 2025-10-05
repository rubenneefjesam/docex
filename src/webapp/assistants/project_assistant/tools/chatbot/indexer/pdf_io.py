# pdf_io.py
from pathlib import Path
from typing import Optional, Tuple
import os

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    import docx
except Exception:
    docx = None

# OCR deps (optioneel)
try:
    import pytesseract
    from pdf2image import convert_from_path
except Exception:
    pytesseract = None
    convert_from_path = None


# ────────────────────────────────────────────────────────────────
# Config via omgevingsvariabelen
# ────────────────────────────────────────────────────────────────
OCR_LANG = os.environ.get("OCR_LANG", "nld+eng")   # NL + EN standaard
OCR_DPI = int(os.environ.get("OCR_DPI", "200"))    # kwaliteit/performantie trade-off
OCR_MAX_PAGES = int(os.environ.get("OCR_MAX_PAGES", "50"))  # safety cap
OCR_PAGE_BATCH = int(os.environ.get("OCR_PAGE_BATCH", "10"))  # batch-grootte per OCR-loop
OCR_ENABLED = os.environ.get("OCR_ENABLED", "1") == "1"       # togglen indien gewenst


# ────────────────────────────────────────────────────────────────
# PDF tekstextractie (pypdf)
# ────────────────────────────────────────────────────────────────
def _read_pdf_text_pypdf(path: Path) -> Tuple[str, str]:
    """
    Return (text, method). method in {"pdf_text", "pdf_text_decrypted", ""}.
    """
    if PdfReader is None:
        return "", ""
    try:
        reader = PdfReader(str(path))
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")  # leeg wachtwoord proberen
                method = "pdf_text_decrypted"
            except Exception:
                return "", ""
        else:
            method = "pdf_text"

        parts = []
        for p in reader.pages:
            try:
                t = p.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(t.strip())
        if not parts:
            return "", ""
        return ("\n\n".join(parts), method)
    except Exception:
        return "", ""


# ────────────────────────────────────────────────────────────────
# DOCX extractie (incl. tabellen)
# ────────────────────────────────────────────────────────────────
def _read_docx(path: Path) -> Tuple[str, str]:
    if docx is None:
        return "", ""
    try:
        d = docx.Document(str(path))
        parts = []
        # paragraphs
        parts.extend([(p.text or "").strip() for p in d.paragraphs if (p.text or "").strip()])
        # tables
        for tbl in getattr(d, "tables", []):
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells if (c.text or "").strip()]
                if cells:
                    parts.append(" | ".join(cells))
        out = "\n".join([p for p in parts if p])
        return out, "docx_text" if out else ("", "")
    except Exception:
        return "", ""


# ────────────────────────────────────────────────────────────────
# OCR (paged & batched) — safety caps en heldere methode-tag
# ────────────────────────────────────────────────────────────────
def _ocr_pdf(path: Path) -> Tuple[str, str]:
    if not OCR_ENABLED or convert_from_path is None or pytesseract is None:
        return "", ""
    try:
        # Bepaal aantal pagina's op voorhand (optioneel)
        total_pages = None
        if PdfReader is not None:
            try:
                r = PdfReader(str(path))
                if getattr(r, "is_encrypted", False):
                    try:
                        r.decrypt("")
                    except Exception:
                        return "", ""
                total_pages = len(r.pages)
            except Exception:
                total_pages = None

        # Safety cap
        if total_pages is not None and total_pages > OCR_MAX_PAGES:
            pages_to_ocr = OCR_MAX_PAGES
        else:
            pages_to_ocr = total_pages or OCR_MAX_PAGES

        texts = []
        # pdf2image ondersteunt first_page/last_page -> batchen
        processed = 0
        while processed < pages_to_ocr:
            first = processed + 1
            last = min(processed + OCR_PAGE_BATCH, pages_to_ocr)
            imgs = convert_from_path(str(path), dpi=OCR_DPI, first_page=first, last_page=last)
            for img in imgs:
                txt = pytesseract.image_to_string(img, lang=OCR_LANG)  # taalconfig
                if txt and txt.strip():
                    texts.append(txt.strip())
            processed = last

        out = "\n\n".join(texts).strip()
        return (out, "ocr_text") if out else ("", "")
    except Exception:
        return "", ""


# ────────────────────────────────────────────────────────────────
# TXT/MD fallback
# ────────────────────────────────────────────────────────────────
def _read_text_like(path: Path) -> Tuple[str, str]:
    try:
        t = path.read_text(encoding="utf-8", errors="ignore")
        t = (t or "").strip()
        return (t, "plain_text") if t else ("", "")
    except Exception:
        return "", ""


# ────────────────────────────────────────────────────────────────
# Publieke API
# ────────────────────────────────────────────────────────────────
def read_text_from_file(path: Path, return_method: bool = False) -> Tuple[str, Optional[str]]:
    """
    Leest tekst uit path. Voor PDF: eerst text-extract, dan OCR (optioneel).
    Return: (text, method) als return_method=True, anders alleen text (achterwaarts compatibel).
    method ∈ {"pdf_text", "pdf_text_decrypted", "ocr_text", "docx_text", "plain_text", ""}.
    """
    if not path.exists():
        return ("", "") if return_method else ""

    suf = path.suffix.lower()

    # PDF
    if suf == ".pdf":
        text, method = _read_pdf_text_pypdf(path)
        if text.strip():
            return (text, method) if return_method else text

        # Alleen OCR proberen als enabled
        ocr_text, ocr_method = _ocr_pdf(path)
        return (ocr_text, ocr_method) if return_method else ocr_text

    # DOCX
    if suf == ".docx":
        text, method = _read_docx(path)
        return (text, method) if return_method else text

    # TXT/MD
    if suf in (".txt", ".md"):
        text, method = _read_text_like(path)
        return (text, method) if return_method else text

    # Fallback: probeer als tekst
    text, method = _read_text_like(path)
    return (text, method) if return_method else text
