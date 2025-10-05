# === FILE: io_utils.py ===
import os
import tempfile
import re
from typing import Optional, List
from pathlib import Path


try:
import docx
except Exception:
docx = None




def safe_read_docx_text(path: str) -> str:
if not docx:
return ""
try:
d = docx.Document(path)
parts = [ (p.text or "").strip() for p in d.paragraphs if (p.text or "").strip() ]
return "\n".join(parts)
except Exception:
return ""




def read_uploaded_text(uploaded) -> str:
if not uploaded:
return ""
name = (uploaded.name or "").lower()
if name.endswith(".docx") and docx:
tmpd = tempfile.mkdtemp()
p = os.path.join(tmpd, "input.docx")
with open(p, "wb") as f:
f.write(uploaded.getbuffer())
return safe_read_docx_text(p)
try:
return uploaded.read().decode("utf-8", errors="ignore")
except Exception:
return ""




def parse_ids_from_filename(name: str) -> (Optional[str], Optional[str]):
if not name:
return None, None
s = name.upper()
m = re.search(r"(C\d{1,4}).*?(P\d{1,5})", s)
if m:
return m.group(1), m.group(2)
m2 = re.search(r"CLIENT[_-]?(\d{1,4}).*?PROJECT[_-]?(\d{1,5})", s)
if m2:
return f"C{m2.group(1)}", f"P{m2.group(2)}"
return None, None




def chunk_text(text: str, size: int = 600, overlap: int = 100) -> List[str]:
if not text:
return []
text = text.strip()
chunks = []
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

