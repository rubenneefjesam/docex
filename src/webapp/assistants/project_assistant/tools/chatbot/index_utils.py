"""
index_utils.py
---------------
Beheert indexering van embeddings en metadata-bestanden.

Kenmerken:
- Automatische padherkenning (voorkomt dubbele 'src/webapp' niveaus)
- Ondersteunt JSONL + NPY of JSON fallback
- Robuuste cosine similarity
"""

from pathlib import Path
import json
import re
import hashlib
from typing import Dict, List, Optional, Any, Tuple

try:
    import numpy as np
except ImportError:
    np = None


# -------------------------------------------------------
# Basismapherkenning
# -------------------------------------------------------
def _resolve_base_dir() -> Path:
    """Bepaalt de juiste chatbot-rootmap, ongeacht werkdirectory."""
    here = Path(__file__).resolve()
    parts = list(here.parts)

    try:
        idx = parts.index("chatbot")
        root = Path(*parts[: idx + 1])
        if root.exists():
            return root
    except ValueError:
        pass

    # fallback — parentmap
    return here.parent


BASE = _resolve_base_dir()
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
    """Controleert of index en embeddings bestaan."""
    p = index_path(client_id, project_id)
    return p.exists() and (
        emb_path(client_id, project_id).exists()
        or emb_json_path(client_id, project_id).exists()
    )


# -------------------------------------------------------
# Opslag
# -------------------------------------------------------
def save_index(client_id: str, project_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
    """Slaat tekstchunks en embeddings op in JSONL + NPY/JSON."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    with p.open("w", encoding="utf-8") as fh:
        for c in chunks:
            row = {
                "client_id": client_id,
                "project_id": project_id,
                "text": c.get("text", ""),
                "doc_type": c.get("doc_type"),
                "source_path": str(c.get("source_path", "")),
                "chunk_id": c.get("chunk_id")
                or hashlib.md5(c.get("text", "").encode()).hexdigest()[:8],
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # embeddings
    if np:
        np.save(e, np.array(embeddings, dtype=np.float32))
        j.unlink(missing_ok=True)
    else:
        with j.open("w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        e.unlink(missing_ok=True)


# -------------------------------------------------------
# Laden & retrieval
# -------------------------------------------------------
def load_index(client_id: str, project_id: str) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """Laadt indexgegevens met automatische fallback bij foutieve paden."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Fallback voor verkeerde padstructuur
    if not p.exists():
        for parent in BASE.parents:
            candidate = parent / "index" / p.name
            if candidate.exists():
                p = candidate
                e = candidate.with_name(e.name)
                j = candidate.with_name(j.name)
                break

    rows: List[Dict[str, Any]] = []
    if p.exists():
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    emb = None
    if np and e.exists():
        emb = np.load(e)
    elif j.exists():
        with j.open("r", encoding="utf-8") as fh:
            emb = json.load(fh)
        if np and isinstance(emb, list):
            emb = np.array(emb, dtype=np.float32)

    return rows, emb


# -------------------------------------------------------
# Cosine similarity
# -------------------------------------------------------
def _cosine_sim(a: Any, b: Any) -> Any:
    """Veilige cosine similarity."""
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


def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict[str, Any]]:
    """Zoekt de meest vergelijkbare chunks in de index."""
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


# -------------------------------------------------------
# Stub (legacy compatibiliteit)
# -------------------------------------------------------
def build_index(client_id: str, project_id: str) -> int:
    """Stubfunctie om legacy imports te behouden."""
    fake_chunks = [{"text": "Demo", "doc_type": "txt", "source_path": "demo.txt"}]
    fake_embs = [[0.1, 0.2, 0.3]]
    save_index(client_id, project_id, fake_chunks, fake_embs)
    return len(fake_chunks)
