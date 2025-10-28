from pathlib import Path
import json
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None  # fallback naar JSON-opslag

BASE_DIR = Path(__file__).parent
INDEX_DIR = BASE_DIR / "index"
INDEX_DIR.mkdir(exist_ok=True)


def safe_name(client_id: str, project_id: str) -> str:
    combined = f"{client_id}_{project_id}".upper()
    return re.sub(r"[^A-Z0-9_]+", "_", combined)


def index_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"


def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"


def emb_json_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.json"


def index_exists(client_id: str, project_id: str) -> bool:
    p = index_path(client_id, project_id)
    return p.exists() and (
        emb_path(client_id, project_id).exists() or emb_json_path(client_id, project_id).exists()
    )


def save_index(
    client_id: str,
    project_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]]
) -> None:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Schrijf chunks als JSONL
    with p.open('w', encoding='utf-8') as fh:
        for c in chunks:
            row = {
                "client_id": client_id,
                "project_id": project_id,
                "text": c.get("text", ""),
                "doc_type": c.get("doc_type"),
                "source_path": str(c.get("source_path", "")),
                "chunk_id": c.get("chunk_id") or hashlib.md5(c.get("text", "").encode()).hexdigest()[:8]
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Schrijf embeddings (NumPy of JSON fallback)
    if np:
        np.save(e, np.array(embeddings, dtype=np.float32))
        if j.exists(): j.unlink()
    else:
        with j.open('w', encoding='utf-8') as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        if e.exists(): e.unlink()


def load_index(
    client_id: str,
    project_id: str
) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    rows: List[Dict[str, Any]] = []
    if p.exists():
        with p.open('r', encoding='utf-8') as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    emb_data = None
    if np and e.exists():
        emb_data = np.load(e)
    elif j.exists():
        with j.open('r', encoding='utf-8') as fh:
            emb_data = json.load(fh)
        if np and isinstance(emb_data, list):
            emb_data = np.array(emb_data, dtype=np.float32)

    return rows, emb_data


def cosine_sim(a: Any, b: Any) -> Any:
    if np is None:
        raise RuntimeError("Numpy is required for similarity calculations.")
    arr_a = np.atleast_2d(np.array(a, dtype=np.float32))
    arr_b = np.atleast_2d(np.array(b, dtype=np.float32))
    if arr_a.size == 0 or arr_b.size == 0:
        return np.array([])
    norm = lambda x: np.linalg.norm(x, axis=1)
    denom = norm(arr_a)[:, None] * norm(arr_b)[None, :] + 1e-12
    sims = arr_a @ arr_b.T / denom
    return sims.flatten()


def retrieve(
    client_id: str,
    project_id: str,
    q_emb: List[float],
    top_k: int = 6
) -> List[Dict[str, Any]]:
    rows, embs = load_index(client_id, project_id)
    if not rows or embs is None or q_emb is None:
        return []
    similarities = cosine_sim(embs, q_emb)
    if similarities.size == 0:
        return []

    ranked_idx = similarities.argsort()[::-1][:top_k]
    results: List[Dict[str, Any]] = []
    for idx in ranked_idx:
        entry = rows[int(idx)].copy()
        entry['_score'] = float(similarities[idx])
        results.append(entry)
    return results

class Embedder:
    """Tijdelijke stub, voorkomt importfouten."""
    def __init__(self):
        pass

    def embed(self, text: str):
        # TODO: vervang dit later door echte embed-logica (bijv. OpenAI, HuggingFace)
        return [0.1, 0.2, 0.3]