from __future__ import annotations
import re
from typing import Union
from pathlib import Path

import pandas as pd

def read_text_from_file(file: Union[Path, "UploadedFile"]) -> str:
    """
    Leest tekst uit PDF/TXT/PNG/JPG. Voor PDF/beelden: eenvoudige OCR-loze benadering via pymupdf/pytesseract
    is hier niet meegenomen; we doen een best-effort:
    - TXT: direct lezen
    - PDF: via PyMuPDF (fitz) als beschikbaar, anders lege string
    - PNG/JPG: leeg (of je kunt Tesseract toevoegen in jouw omgeving)
    """
    name = getattr(file, "name", str(file))
    suffix = Path(name).suffix.lower()

    if suffix == ".txt":
        return file.read().decode("utf-8", errors="ignore") if hasattr(file, "read") else Path(file).read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        try:
            import fitz  # PyMuPDF
            data = b""
            if hasattr(file, "read"):
                data = file.read()
            doc = fitz.open(stream=data, filetype="pdf") if data else fitz.open(str(file))
            parts = []
            for page in doc:
                parts.append(page.get_text())
            return "\n".join(parts)
        except Exception:
            return ""

    if suffix in {".png", ".jpg", ".jpeg"}:
        # Placeholder: zonder OCR geven we lege string terug.
        # Voeg pytesseract toe in jouw stack voor echte OCR.
        return ""

    # Default
    return ""


def is_invoice(text: str) -> bool:
    """
    Heuristisch checkje of er sprake is van een factuur.
    """
    if not text:
        return False
    text_l = text.lower()
    patterns = ["factuur", "invoice", "vat", "btw", "iban", "kvk", "subtotaal", "subtotal"]
    return any(p in text_l for p in patterns)
