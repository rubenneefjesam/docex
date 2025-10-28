"""
embed_utils.py
---------------
Bevat embed- en indexhulpfuncties.

Taken:
- Beheren van indexpaden en opslag (JSON/NumPy)
- Dummy Embedder-klasse (placeholder voor echte embeddingmodel)
- Functies voor laden, opslaan en ophalen met cosine-similarity
- Automatische padcorrectie bij verkeerde working directory
"""

import os
from pathlib import Path
import json
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None  # fallback naar JSON-opslag

# ---------------------------------------------------------------------
# Dynamisch padbeheer (voorkomt dubbele src/webapp/... problemen)
# ---------------------------------------------------------------------
def _resolve_base_dir() -> Path:
    """Zoekt automatisch de juiste chatbot-basisdirectory."""
    this_file = Path(__file__).resolve()
    base = this_file.parent

    # Corrigeer als er dubbel 'src/webapp' in het pad voorkomt
    parts = list(base.parts)
    if parts.count("src") > 1 and parts.count("webapp") > 1:
        # neem het eerste voorkomen van 'src/webapp'
        i = parts.index("src")
        j = parts.index("webapp")
        fixed = Path("/").joinpath(*parts[: j + 2]) / "assistants/project_assistant/tools/chatbot"
        if fixed.exists():
            return fixed

    return base


BASE_DIR = _resolve_base_dir()
INDEX_DIR = BASE_DIR / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Hulpfuncties voor naamgeving en paden
# ---------------------------------------------------------------------
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
    """Controleer of een indexbestand en embeddings bestaan."""
    p = index_path(client_id, project_id)
    return p.exists() and (
        emb_path(client_id, project_id).exists() or emb_json_path(client_id, project_id).exists()
    )


# ---------------------------------------------------------------------
# Opslaan & laden van indexen
# ---------------------------------------------------------------------
def save_index(
    client_id: str,
    project_id: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
) -> None:
    """Sla tekstchunks + embeddings op in JSONL + NPY/JSON."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Schrijf chunks als JSONL
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

    # Schrijf embeddings (NumPy of JSON fallback)
    if np:
        np.save(e, np.array(embeddings, dtype=np.float32))
        if j.exists():
            j.unlink(missing_ok=True)
    else:
        with j.open("w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        if e.exists():
            e.unlink(missing_ok=True)


def load_index(client_id: str, project_id: str) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """Laad chunks en embeddings uit index. Automatisch padherstel bij mismatch."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Fallback als pad niet klopt (Streamlit gestart vanuit ander pad)
    if not p.exists():
        alt_path = None
        # Zoek in parent directories
        for parent in BASE_DIR.parents:
            candidate = parent / "index" / p.name
            if candidate.exists():
                alt_path = candidate
                break
        if alt_path:
            p = alt_path
            e = alt_path.with_name(emb_path(client_id, project_id).name)
            j = alt_path.with_name(emb_json_path(client_id, project_id).name)

    rows: List[Dict[str, Any]] = []
    if p.exists():
        with p.open("r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    emb_data = None
    if np and e.exists():
        emb_data = np.load(e)
    elif j.exists():
        with j.open("r", encoding="utf-8") as fh:
            emb_data = json.load(fh)
        if np and isinstance(emb_data, list):
            emb_data = np.array(emb_data, dtype=np.float32)

    return rows, emb_data


# ---------------------------------------------------------------------
# Similarity & retrieval
# ---------------------------------------------------------------------
def cosine_sim(a: Any, b: Any) -> Any:
    """Bereken cosine similarity tussen twee embeddingverzamelingen."""
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
    top_k: int = 6,
) -> List[Dict[str, Any]]:
    """Haal de top K meest vergelijkbare documenten op."""
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
        entry["_score"] = float(similarities[idx])
        results.append(entry)
    return results


# ---------------------------------------------------------------------
# Dummy Embedder (voor testomgeving)
# ---------------------------------------------------------------------
class Embedder:
    """Tijdelijke embedder – genereert pseudo-embeddings voor tests."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        if np is None:
            raise RuntimeError("Numpy is vereist voor de Embedder-stub.")

    def embed_texts(self, texts: List[str]) -> Any:
        """Genereer willekeurige dummy-embeddings (deterministisch op hash)."""
        vecs = []
        for t in texts:
            seed = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.random(self.dim, dtype=np.float32)
            vecs.append(vec)
        return np.stack(vecs)
