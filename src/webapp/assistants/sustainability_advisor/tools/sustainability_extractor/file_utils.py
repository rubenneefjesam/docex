# file_utils.py
from pathlib import Path
import re
from PyPDF2 import PdfReader
import docx

def read_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        _doc = docx.Document(str(path))
        return "\n".join(para.text for para in _doc.paragraphs)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Onbekend bestandstype: {suffix}")

def is_invoice(text: str) -> bool:
    return bool(re.search(r"factuurnummer|factuur\s*nr", text, re.IGNORECASE)) and \
           bool(re.search(r"€\s*\d", text))
