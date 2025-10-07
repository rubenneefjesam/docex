# scripts/build_index.py
"""
CLI-tool om alle documenten in data/* te indexeren:
- doorloopt submappen in data/
- leest .docx/.txt (en overslaan/belden bij andere extensies)
- parse client_id en project_id
- chunk text, genereer embeddings met lokale SentenceTransformer
- slaat index en embeddings op via save_index
"""
from pathlib import Path
import sys

# project root moet in PYTHONPATH staan zodat imports werken
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from webapp.assistants.project_assistant.tools.chatbot.io_utils import (
    safe_read_docx_text,
    read_uploaded_text,
    parse_ids_from_path,
    chunk_text,
)
from embed_utils import Embedder
from webapp.assistants.project_assistant.tools.chatbot.index_utils import (
    save_index,
)

# basis mappen
BASE = REPO_ROOT / "src" / "webapp" / "assistants" / "project_assistant" / "tools" / "chatbot"
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"

# stel lokale embedder in
embedder = Embedder()

# verzamel alle bestanden in submappen
files = list(DATA_DIR.rglob("*"))
print(f">>> Found {len(files)} files under {DATA_DIR}")

total_chunks = 0
for f in files:
    if not f.is_file():
        continue
    suffix = f.suffix.lower()
    text = ""
    if suffix == ".docx":
        text = safe_read_docx_text(str(f))
    elif suffix == ".txt":
        text = f.read_text(encoding="utf-8", errors="ignore")
    else:
        print(f"Skipping unsupported file type: {f.name}")
        continue

    if not text.strip():
        print(f"No text extracted from {f.name}, skipping.")
        continue

    cid, pid = parse_ids_from_path(f)
    if not cid or not pid:
        print(f"Could not parse client/project from {f.name} => cid={cid}, pid={pid}")
        continue

    chunks = chunk_text(text)
    texts = [chunk for chunk in chunks]
    embeddings = embedder.embed(texts)

    # opslaan (merge met bestaande index indien aanwezig)
    save_index(cid, pid, chunks, embeddings)
    total_chunks += len(chunks)
    print(f"Indexed {len(chunks)} chunks from {f.name} into {cid}/{pid}")

print(f"\nDone: totaal {total_chunks} chunks toegevoegd.")