"""
Index utilities met metadata-ondersteuning:
- index_<SAFE>.jsonl
- emb_<SAFE>.npy of .json fallback
- veilige cosine similarity (leeg input = lege array)
"""

from pathlib import Path
import json
import re
import hashlib
from typing import Dict, List, Optional, Any, Tuple

try:
    import numpy as np
except Exception:
    np = None

BASE = Path(__file__).parent.resolve()
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def safe_name(client_id: str, project_id: str) -> str:
    s = f"{client_id}_{project_id}"
    return re.sub(r"[^A-Z0-9_]+", "_", s.upper())


def index_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"


def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"


def emb_json_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.json"


def index_exists(client_id: str, project_id: str) -> bool:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)
    return p.exists() and (e.exists() or j.exists())


# -------------------------------------------------------
# Opslag
# -------------------------------------------------------

def save_index(client_id: str, project_id: str, chunks: List[Dict], embeddings: List[List[float]]):
    """
    Sla index en embeddings op.
    Elke chunk mag extra metadata bevatten: doc_type, source_path, chunk_id.
    """
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    with open(p, "w", encoding="utf-8") as fh:
        for c in chunks:
            row = {
                "client_id": client_id,
                "project_id": project_id,
                "text": c.get("text", ""),
                "doc_type": c.get("doc_type"),
                "source_path": str(c.get("source_path", "")),
                "chunk_id": c.get("chunk_id") or hashlib.md5(c.get("text", "").encode()).hexdigest()[:8],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # embeddings
    if np is not None:
        np.save(e, np.array(embeddings, dtype=np.float32))
        if j.exists():
            j.unlink(missing_ok=True)
    else:
        with open(j, "w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        if e.exists():
            e.unlink(missing_ok=True)


# -------------------------------------------------------
# Laden & retrieval
# -------------------------------------------------------

def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[object]]:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    rows = []
    if p.exists():
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue

    emb = None
    if e.exists() and np is not None:
        emb = np.load(e)
    elif j.exists():
        with open(j, "r", encoding="utf-8") as fh:
            emb = json.load(fh)
        if np is not None and isinstance(emb, list):
            emb = np.array(emb, dtype=np.float32)
    return rows, emb


def _cosine_sim(a, b):
    """
    Robuuste cosine similarity.
    Retourneert lege array bij lege input.
    """
    if np is None:
        raise RuntimeError("Numpy ontbreekt.")
    if a is None or b is None:
        return np.array([])

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)

    if a.size == 0 or b.size == 0:
        return np.array([])

    if a.ndim == 1:
        a = a.reshape(1, -1)

    eps = 1e-12
    denom = np.linalg.norm(a, axis=1) * np.linalg.norm(b) + eps
    sims = (a @ b) / denom
    return sims


def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict]:
    rows, emb = load_index(client_id, project_id)
    if not rows or emb is None or np is None:
        return []
    sims = _cosine_sim(emb, q_emb)
    if sims.size == 0:
        return []
    idx = np.argsort(-sims)[:top_k]
    results = []
    for i in idx:
        r = rows[int(i)].copy()
        r["_score"] = float(sims[i])
        results.append(r)
    return results
