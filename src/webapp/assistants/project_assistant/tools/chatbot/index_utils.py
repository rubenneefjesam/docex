# src/webapp/assistants/project_assistant/tools/chatbot/index_utils.py
"""
Index utilities for local per-client/project indices.

- index files: index_<SAFE>.jsonl
- embeddings: emb_<SAFE>.npy  (fallback: emb_<SAFE>.json when numpy missing)
- robust cosine similarity implementation
"""
from pathlib import Path
import json
import re
from typing import List, Dict, Optional, Tuple

try:
    import numpy as np
except Exception:
    np = None

BASE = Path(__file__).parent.resolve()
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(client_id: str, project_id: str) -> str:
    """
    Create a safe uppercase name from client & project IDs.
    Example: C001, P1001 -> C001_P1001 -> INDEX_C001_P1001
    """
    s = f"{client_id}_{project_id}"
    return re.sub(r"[^A-Z0-9_]+", "_", s.upper())


def index_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"


def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"


def emb_json_path(client_id: str, project_id: str) -> Path:
    """Fallback path for embeddings when numpy isn't available."""
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.json"


def index_exists(client_id: str, project_id: str) -> bool:
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)
    return p.exists() and (e.exists() or j.exists())


def save_index(client_id: str, project_id: str, chunks: List[Dict], embeddings: List[List[float]]):
    """
    Save index rows (jsonl) and embeddings.
    If numpy is available, save .npy for speed. Otherwise save embeddings as JSON fallback.
    """
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    # write jsonl index
    with open(p, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    # save embeddings
    if np is not None:
        arr = np.array(embeddings, dtype=np.float32)
        # ensure we write a .npy file
        np.save(e, arr)
        # remove fallback JSON if present
        if j.exists():
            try:
                j.unlink()
            except Exception:
                pass
    else:
        # fallback: write embeddings as readable JSON (slower, larger)
        with open(j, "w", encoding="utf-8") as fh:
            json.dump(embeddings, fh, ensure_ascii=False)
        # remove any stale .npy
        if e.exists():
            try:
                e.unlink()
            except Exception:
                pass


def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[object]]:
    """
    Load rows and embeddings.

    Returns:
      rows: List[dict]
      emb: numpy.ndarray if numpy available and .npy exists, otherwise a Python list if .json used,
           or None if no embeddings found.
    """
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    j = emb_json_path(client_id, project_id)

    rows: List[Dict] = []
    if p.exists():
        with open(p, "r", encoding="utf-8") as fh:
            for L in fh:
                try:
                    rows.append(json.loads(L))
                except Exception:
                    continue

    emb = None
    if e.exists() and np is not None:
        try:
            emb = np.load(e)
        except Exception:
            emb = None
    elif j.exists():
        # load JSON fallback
        try:
            with open(j, "r", encoding="utf-8") as fh:
                emb = json.load(fh)
            # if numpy is available, convert to array for faster math
            if np is not None and isinstance(emb, list):
                emb = np.array(emb, dtype=np.float32)
        except Exception:
            emb = None

    return rows, emb


def _cosine_sim(a, b):
    """
    Robuuste cosine similarity:
      - accepteert numpy-arrays of array-like
      - voorkomt deling door nul met kleine epsilon
      - returned numpy array van similarities (len(a),)

    Voor gebruik in retrieval: a is (n, d) of array-like, b is (d,) array-like.
    Als input None of lege array -> return lege numpy array.
    """
    # lokaal import voor duidelijk foutbericht wanneer numpy ontbreekt
    if np is None:
        # we willen een numpy-array teruggeven voor compatibiliteit met rest van code
        try:
            import numpy as _np
            _np_available = True
        except Exception:
            # fallback: raise informative error
            raise RuntimeError("Numpy ontbreekt; cosine similarity kan niet worden berekend.")
    # nu zeker dat np bestaat (we importeerden boven) — maar be safe:
    import numpy as _np

    if a is None or b is None:
        return _np.array([])

    a = _np.asarray(a, dtype=_np.float32)
    b = _np.asarray(b, dtype=_np.float32)

    if a.size == 0 or b.size == 0:
        return _np.array([])

    if a.ndim == 1:
        a = a.reshape(1, -1)

    # norms with small epsilon to avoid division by zero
    eps = 1e-12
    a_norm = _np.linalg.norm(a, axis=1)
    b_norm = _np.linalg.norm(b)
    denom = (a_norm * (b_norm + eps)) + eps
    sims = (a @ b) / denom
    return sims


def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict]:
    """
    Retrieve top-k rows for a client/project given query embedding q_emb.
    Returns list of rows each annotated with '_score' float.
    """
    rows, emb = load_index(client_id, project_id)
    if not rows or emb is None:
        return []

    if np is None:
        # retrieval requires numeric operations — give a clear error
        raise RuntimeError("Numpy ontbreekt; retrieval kan niet uitgevoerd worden. Installeer numpy of herbouw indices met numpy aanwezig.")

    q = np.array(q_emb, dtype=np.float32)
    sims = _cosine_sim(emb, q)
    if sims.size == 0:
        return []

    # argsort descending
    idx = np.argsort(-sims)[:top_k]
    results = []
    for i in idx:
        i = int(i)
        r = rows[i].copy()
        r["_score"] = float(sims[i])
        results.append(r)
    return results


def download_bytes_json(rows: List[Dict]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


def download_bytes_csv(rows: List[Dict]) -> bytes:
    import csv
    import io

    buf = io.StringIO()
    if not rows:
        buf.write("text\n")
        return buf.getvalue().encode("utf-8")

    # flatten complex types into JSON strings for CSV cells
    fieldnames = list(rows[0].keys())
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow(
            {
                k: (v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False))
                for k, v in r.items()
            }
        )
    return buf.getvalue().encode("utf-8")
