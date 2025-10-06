# src/.../indexer/embeddings.py
from typing import Any, List
import numpy as np

def safe_to_float32_list(embs: Any) -> List[List[float]]:
    """
    Force numpy arrays or lists to list-of-list float32.
    """
    if embs is None:
        return []
    try:
        arr = np.asarray(embs, dtype=np.float32)
        return arr.tolist()
    except Exception:
        # fallback
        return [[float(x) for x in row] for row in embs]

def vstack_defensive(old: np.ndarray, new: np.ndarray) -> np.ndarray:
    """
    vstack maar bij dim-mismatch: alleen `new`.
    """
    try:
        return np.vstack([old, new])
    except ValueError:
        return new
