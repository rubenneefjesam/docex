"""
embed_utils.py
---------------
Bevat embed- en indexhulpfuncties.

Taken:
- Beheren van indexpaden en opslag (JSON/NumPy)
- Dummy Embedder-klasse (placeholder voor echte embeddingmodel)
- Functies voor laden, opslaan en ophalen met cosine-similarity
- Veilige automatische padherkenning (geen dubbele src/webapp-structuur)
"""

from pathlib import Path
import json
import re
import hashlib
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
except ImportError:
    np = None


# ---------------------------------------------------------------------
# Basispad — veilig dynamisch herkend
# ---------------------------------------------------------------------
def _resolve_base_dir() -> Path:
    """
    Bepaalt de juiste basismap van de chatbot-tool zonder cwd aan te passen.
    Voorkomt fouten met dubbele 'src/webapp' in het pad.
    """
    here = Path(__file__).resolve()
    parts = list(here.parts)

    try:
        idx = parts.index("chatbot")
        root = Path(*parts[: idx + 1])
        if root.exists():
            return root
    except ValueError:
        pass

    return here.parent


BASE_DIR = _resolve_base_dir()
INDEX_DIR = BASE_DIR / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Naamgeving en paden
# ---------------------------------------------------------------------
def safe_name(client_id: str, project_id: str) -> str:
    return re.sub(r"[^A-Z0-9_]+", "_", f"{client_id}_{project_id}".upper())


def index_path(client_id: str, project_id: str) -> Path:
    """Hoofdpad voor indexbestand (.json)."""
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.json"


def legacy_index_path(client_id: str, project_id: str) -> Path:
    """Fallback voor oude .jsonl-bestanden."""
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"


def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"


def emb_json_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.json"


def index_exists(client_id: str, project_id: str) -> bool:
    return (
        index_path(client_id, project_id).exists()
        or legacy_index_path(client_id, project_id).exists()
    )


# ---------------------------------------------------------------------
# Index opslaan / laden
# ---------------------------------------------------------------------
def save_index(client_id: str, project_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
    """Sla chunks en embeddings op in JSON + NPY/JSON."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # JSON schrijven
    with p.open("w", encoding="utf-8") as fh:
        json.dump(chunks, fh, ensure_ascii=False, indent=2)

    # Embeddings schrijven
    if np:
        np.save(e, np.array(embeddings, dtype=np.float32))
        j.unlink(missing_ok=True)
    else:
        with j.open("w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        e.unlink(missing_ok=True)


def _load_json_or_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Laadt JSON of JSONL afhankelijk van bestandsstructuur."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as fh:
        first_char = fh.read(1)
        fh.seek(0)
        if first_char == "[":  # standaard JSON-lijst
            try:
                rows = json.load(fh)
            except Exception:
                rows = []
        else:  # JSONL
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


def load_index(client_id: str, project_id: str) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """Laad chunks en embeddings uit index, met padherkenning en fallback."""
    p = index_path(client_id, project_id)
    legacy_p = legacy_index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Fallback naar legacy .jsonl
    if not p.exists() and legacy_p.exists():
        p = legacy_p

    # Alternatieve zoekroute (andere map)
    if not p.exists():
        for parent in BASE_DIR.parents:
            candidate = parent / "index" / p.name
            if candidate.exists():
                p = candidate
                e = candidate.with_name(e.name)
                j = candidate.with_name(j.name)
                break

    rows = _load_json_or_jsonl(p)

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


def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict[str, Any]]:
    rows, embs = load_index(client_id, project_id)
    if not rows or embs is None or q_emb is None:
        return []

    similarities = cosine_sim(embs, q_emb)
    if similarities.size == 0:
        return []

    ranked_idx = similarities.argsort()[::-1][:top_k]
    results = []
    for idx in ranked_idx:
        entry = rows[int(idx)].copy()
        entry["_score"] = float(similarities[idx])
        results.append(entry)
    return results


# ---------------------------------------------------------------------
# Dummy Embedder
# ---------------------------------------------------------------------
class Embedder:
    """Genereert deterministische pseudo-embeddings voor testdoeleinden."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        if np is None:
            raise RuntimeError("Numpy is vereist voor de Embedder-stub.")

    def embed_texts(self, texts: List[str]) -> Any:
        vecs = []
        for t in texts:
            seed = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.random(self.dim, dtype=np.float32)
            vecs.append(vec)
        return np.stack(vecs)
