# src/.../indexer/headers.py
from typing import List, Optional

def find_header(cols: List[str], candidates: List[str]) -> Optional[str]:
    """
    Permissive header lookup (case-insensitive).
    """
    lower_to_orig = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_to_orig:
            return lower_to_orig[cand.lower()]
    return None
