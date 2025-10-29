"""
embed_utils.py — definitieve stabiele versie
--------------------------------------------
Bevat functies voor:
- Laden & opslaan van indexen (JSON of JSONL)
- Similarity & retrieval
- Deterministische dummy-embeddings (voor lokale test)
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
# Basispad
# ---------------------------------------------------------------------
def _resolve_base_dir() -> Path:
    """Bepaalt de juiste basismap van de chatbot-tool zonder cwd aan te passen."""
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
    """Maakt veilige bestandsnaam (alleen hoofdletters, cijfers en underscores)."""
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


# ---------------------------------------------------------------------
# Bestaan controleren
# ---------------------------------------------------------------------
def index_exists(client_id: str, project_id: str) -> bool:
    """Controleer of indexbestanden bestaan (JSON of JSONL + embeddings)."""
    return (
        index_path(client_id, project_id).exists()
        or legacy_index_path(client_id, project_id).exists()
    )


# ---------------------------------------------------------------------
# Opslaan
# ---------------------------------------------------------------------
def save_index(client_id: str, project_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
    """Sla chunks en embeddings op in JSONL + NPY/JSON."""
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # ✅ Schrijf als JSONL (één object per regel)
    with p.open("w", encoding="utf-8") as fh:
        for row in chunks:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    if np:
        np.save(e, np.array(embeddings, dtype=np.float32))
        j.unlink(missing_ok=True)
    else:
        with j.open("w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        e.unlink(missing_ok=True)


# ---------------------------------------------------------------------
# Laden
# ---------------------------------------------------------------------
def load_index(client_id: str, project_id: str) -> Tuple[List[Dict[str, Any]], Optional[Any]]:
    """Laad alle chunks (JSON of JSONL) en bijbehorende embeddings."""
    p = index_path(client_id, project_id)
    legacy_p = legacy_index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # Fallback
    if not p.exists() and legacy_p.exists():
        p = legacy_p

    # 🧠 Lees alle regels veilig in, of JSON-lijst
    rows: List[Dict[str, Any]] = []
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as fh:
                text = fh.read().strip()
                if text.startswith("["):  # JSON-array
                    rows = json.loads(text)
                else:  # JSONL
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"⚠️  Fout bij laden index {p.name}: {e}")

    # 🧠 Embeddings
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
    """Zoek de meest vergelijkbare chunks."""
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
        """Genereer stabiele pseudo-embeddings uit tekst (deterministisch)."""
        vecs = []
        for t in texts:
            seed = int(hashlib.md5(t.encode("utf-8")).hexdigest(), 16) % (2**32)
            rng = np.random.default_rng(seed)
            vec = rng.random(self.dim, dtype=np.float32)
            vecs.append(vec)
        return np.stack(vecs)
