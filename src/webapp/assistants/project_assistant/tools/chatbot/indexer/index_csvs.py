#!/usr/bin/env python3
"""
Index CSV -> file-based vector index (JSONL + .npy)

Plaats dit bestand in:
src/webapp/assistants/project_assistant/tools/chatbot/index_csvs.py

Run vanaf repo root:
python src/webapp/assistants/project_assistant/tools/chatbot/index_csvs.py
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# optional libs
try:
    import pandas as pd
except Exception as e:
    raise SystemExit("Install pandas: pip install pandas")

try:
    import numpy as np
except Exception as e:
    raise SystemExit("Install numpy: pip install numpy")

# sentence-transformers optional
try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# openai optional fallback
try:
    import openai
except Exception:
    openai = None

# -------------------------
# Config (pas aan als nodig)
# -------------------------
BASE = Path("src/webapp/assistants/project_assistant/tools/chatbot").resolve()
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBED_MODEL = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 600))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))

# -------------------------
# Helpers: chunking
# -------------------------
def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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

# -------------------------
# Embedder
# -------------------------
class Embedder:
    def __init__(self):
        self.model_name = EMBED_MODEL
        self.model = None
        self.use_openai = False
        if SentenceTransformer is not None:
            try:
                print(f"[embed] loading SentenceTransformer '{self.model_name}' ...")
                self.model = SentenceTransformer(self.model_name)
                print("[embed] loaded local model.")
            except Exception as e:
                print("[embed] failed to load SentenceTransformer:", e)
                self.model = None
        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            self.use_openai = True
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            print("[embed] using OpenAI embeddings as fallback.")
        if self.model is None and not self.use_openai:
            raise SystemExit("No embedder available. Install sentence-transformers or set OPENAI_API_KEY.")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.model is not None:
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return [list(map(float, x)) for x in np.array(arr)]
        if self.use_openai:
            resp = openai.Embedding.create(model=OPENAI_EMBED_MODEL, input=texts)
            return [r["embedding"] for r in resp["data"]]
        raise RuntimeError("No embedding method available")

# -------------------------
# Index file helpers
# -------------------------
def safe_name(client_id: str, project_id: str) -> str:
    s = f"{client_id}_{project_id}"
    return re.sub(r"[^A-Z0-9_]+", "_", s.upper())

def index_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"

def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"

def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[np.ndarray]]:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    rows = []
    if p.exists():
        with open(p, "r", encoding="utf-8") as fh:
            for L in fh:
                try:
                    rows.append(json.loads(L))
                except Exception:
                    continue
    emb = None
    if e.exists():
        emb = np.load(e)
    return rows, emb

def save_index(client_id: str, project_id: str, chunks: List[Dict], embeddings: List[List[float]]):
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    # write jsonl
    with open(p, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    # write embeddings
    arr = np.array(embeddings, dtype=np.float32)
    np.save(e, arr)

# -------------------------
# Row -> text helper
# -------------------------
def row_to_text(prefix: str, row: Dict) -> str:
    # build a readable text representation of a row (skippable cols could be added)
    parts = []
    for k, v in row.items():
        parts.append(f"{k}: {v}")
    return f"{prefix}\\n" + "\\n".join(parts)

# -------------------------
# Main: read CSVs and index
# -------------------------
def main():
    print("Data dir:", DATA_DIR)
    if not DATA_DIR.exists():
        raise SystemExit(f"Data dir does not exist: {DATA_DIR}")
    # find csvs
    clients_csv = None
    projects_csv = None
    for f in sorted(DATA_DIR.glob("*.csv")):
        name = f.name.lower()
        if "client" in name or "klant" in name:
            clients_csv = f
        if "project" in name:
            projects_csv = f
    if not clients_csv:
        raise SystemExit("clients csv not found in data dir (name should contain 'client' or 'klant')")
    if not projects_csv:
        raise SystemExit("projects csv not found in data dir (name should contain 'project')")

    print("Clients file:", clients_csv)
    print("Projects file:", projects_csv)

    df_clients = pd.read_csv(clients_csv, dtype=str).fillna("")
    df_projects = pd.read_csv(projects_csv, dtype=str).fillna("")

    # quick sanity checks
    if "KlantID" not in df_clients.columns or "ProjectID" not in df_clients.columns:
        raise SystemExit("clients CSV must contain columns 'KlantID' AND 'ProjectID'")
    if "ProjectID" not in df_projects.columns:
        raise SystemExit("projects CSV must contain column 'ProjectID'")

    # build project->clients map
    proj_to_clients = {}
    for _, r in df_clients.iterrows():
        pid = str(r["ProjectID"]).strip()
        cid = str(r["KlantID"]).strip()
        if not pid or not cid:
            continue
        proj_to_clients.setdefault(pid, []).append(cid)

    embedder = Embedder()

    summary = {"clients_indexed": 0, "projects_indexed": 0}
    # index clients (each row -> client+project)
    for _, row in df_clients.iterrows():
        cid = str(row["KlantID"]).strip()
        pid = str(row["ProjectID"]).strip()
        if not cid or not pid:
            print("Skipping row without KlantID/ProjectID:", row.to_dict())
            continue
        text = row_to_text("Client record", row.to_dict())
        chunks = chunk_text(text)
        metas = []
        for i, c in enumerate(chunks):
            metas.append({
                "text": c,
                "client_id": cid,
                "project_id": pid,
                "source": "clients_csv",
                "chunk_index": i
            })
        embs = embedder.embed([m["text"] for m in metas])
        # merge with existing if present
        rows, emb_arr = load_index(cid, pid)
        if rows and emb_arr is not None:
            new_rows = rows + metas
            new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
            save_index(cid, pid, new_rows, new_emb.tolist())
        else:
            save_index(cid, pid, metas, embs)
        summary["clients_indexed"] += 1

    # index projects: create project-chunks and duplicate per client attached to that project
    for _, row in df_projects.iterrows():
        pid = str(row["ProjectID"]).strip()
        if not pid:
            print("Skipping project row without ProjectID:", row.to_dict())
            continue
        text = row_to_text("Project record", row.to_dict())
        chunks = chunk_text(text)
        clients_for_project = proj_to_clients.get(pid, []) or [""]
        for cid in clients_for_project:
            metas = []
            for i, c in enumerate(chunks):
                metas.append({
                    "text": c,
                    "client_id": cid if cid else "UNKNOWN",
                    "project_id": pid,
                    "source": "projects_csv",
                    "chunk_index": i
                })
            embs = embedder.embed([m["text"] for m in metas])
            # merge
            rows, emb_arr = load_index(cid or "UNKNOWN", pid)
            if rows and emb_arr is not None:
                new_rows = rows + metas
                new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
                save_index(cid or "UNKNOWN", pid, new_rows, new_emb.tolist())
            else:
                save_index(cid or "UNKNOWN", pid, metas, embs)
        summary["projects_indexed"] += 1

    print("Indexing complete. Summary:", summary)
    print("Index files created under:", INDEX_DIR)

if __name__ == "__main__":
    main()
