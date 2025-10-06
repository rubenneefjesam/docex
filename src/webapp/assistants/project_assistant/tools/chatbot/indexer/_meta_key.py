# _meta_key.py
from typing import Dict, Any, Tuple, Optional, Set, List
import hashlib

DEDUPE_WITH_HASH = True  # default; kan overschreven door caller

def file_fingerprint_from_meta(meta: Dict[str, Any]) -> str:
    """
    Bepaal een fingerprint voor een meta (kan een filepath of expliciete fingerprint bevatten).
    Als meta['file_fingerprint'] aanwezig is, gebruik die; anders gebruik sha1(filepath).
    """
    if not meta:
        return ""
    if meta.get("file_fingerprint"):
        return str(meta.get("file_fingerprint"))
    fp = str(meta.get("filepath") or meta.get("filename") or "")
    return hashlib.sha1(fp.encode("utf-8", errors="ignore")).hexdigest()

def meta_key(m: Dict[str, Any], dedupe_with_hash: bool = DEDUPE_WITH_HASH) -> Tuple[str, str, str, int, Optional[str]]:
    """
    Unieke sleutel: (client, project, file_fingerprint, chunk_index, optional text_hash)
    text_hash alleen wanneer dedupe_with_hash True.
    """
    t_hash = None
    if dedupe_with_hash:
        try:
            t_hash = hashlib.sha1((m.get("text") or "").encode("utf-8", errors="ignore")).hexdigest()
        except Exception:
            t_hash = None
    client = (m.get("client_id") or "UNKNOWN")
    project = (m.get("project_id") or "UNKNOWN")
    file_fprint = file_fingerprint_from_meta(m)
    chunk_index = int(m.get("chunk_index") or 0)
    return (client.upper(), project.upper(), file_fprint.upper(), chunk_index, t_hash)

def build_existing_keys(rows: Optional[List[Dict[str, Any]]], dedupe_with_hash: bool = DEDUPE_WITH_HASH) -> Set[Tuple[str, str, str, int, Optional[str]]]:
    keys = set()
    for r in (rows or []):
        try:
            keys.add(meta_key(r, dedupe_with_hash))
        except Exception:
            continue
    return keys
