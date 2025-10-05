import os
import json
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    import numpy as np
except Exception:
    np = None

BASE = Path(__file__).parent.resolve()
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)


def safe_name(client_id: str, project_id: str) -> str:
    s = f"{client_id}_{project_id}"
    return re.sub(r"[^A-Z0-9_]+", "_", s.upper())


def index_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"index_{safe_name(client_id, project_id)}.jsonl"


def emb_path(client_id: str, project_id: str) -> Path:
    return INDEX_DIR / f"emb_{safe_name(client_id, project_id)}.npy"


def index_exists(client_id: str, project_id: str) -> bool:
    return index_path(client_id, project_id).exists() and emb_path(client_id, project_id).exists()


def save_index(client_id: str, project_id: str, chunks: List[Dict], embeddings: List[List[float]]):
    p = index_path(client_id, project_id)
    e = emb_path(client_id, project_id)
    with open(p, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    if np is None:
        raise RuntimeError("Numpy ontbreekt; kan embeddings niet saven")
    arr = np.array(embeddings, dtype=np.float32)
    np.save(e, arr)


def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[object]]:
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
    if e.exists() and np is not None:
        emb = np.load(e)
    return rows, emb


def _cosine_sim(a, b):
    # a: (n, d) numpy array, b: (d,) numpy array
    import numpy as _np
    if a is None or b is None:
        return _np.array([])
    a_norm = _np.linalg.norm(a, axis=1)
    b_norm = _np.linalg.norm(b)
    denom = a_norm * (b_norm + 1e-12)
    sims = (a @ b) / denom
    return sims


def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict]:
    rows, emb = load_index(client_id, project_id)
    if not rows or emb is None or len(rows) == 0:
        return []
    if np is None:
        raise RuntimeError("Numpy ontbreekt; retrieval kan niet uitgevoerd worden.")
    q = np.array(q_emb, dtype=np.float32)
    sims = _cosine_sim(emb, q)
    idx = np.argsort(-sims)[:top_k]
    results = []
    for i in idx:
        r = rows[int(i)].copy()
        r["_score"] = float(sims[int(i)])
        results.append(r)
    return results


def download_bytes_json(rows: List[Dict]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


def download_bytes_csv(rows: List[Dict]) -> bytes:
    import csv
    import io
    buf = io.StringIO()
    fieldnames = list(rows[0].keys()) if rows else ["text"]
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    for r in rows:
        w.writerow({k: (v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False)) for k, v in r.items()})
    return buf.getvalue().encode("utf-8")