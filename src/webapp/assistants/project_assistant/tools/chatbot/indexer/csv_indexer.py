# doc_indexer.py
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import re
import hashlib
import numpy as _np
import os

from .io_utils_extended import find_files_in_dir, read_and_meta, parse_ids_from_path
from .chunker import chunk_by_sentences, chunk_text_simple
from ..index_utils import load_index, save_index
from .embedder_modular import Embedder
from ..utils import CHUNK_SIZE, CHUNK_OVERLAP

# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────
BATCH_SIZE = int(os.getenv("INDEX_EMBED_BATCH", "128"))
MAX_CHUNKS_PER_DOC = int(os.getenv("INDEX_MAX_CHUNKS_PER_DOC", "500"))
DEDUPE_WITH_HASH = os.getenv("INDEX_DEDUPE_WITH_HASH", "1") == "1"

_CORR_HINTS = ("klantcommunicatie", "correspondentie", "corresp", "mail", "brief", "orderbevestiging", "klantorders")


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def _norm_id(val: Optional[str], kind: str) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    if kind == "client":
        return v if v.startswith("C") else ("C" + v if v.isdigit() else v)
    if kind == "project":
        return v if v.startswith("P") else ("P" + v if v.isdigit() else v)
    return v


def _is_correspondentie(fname_low: str, text: str) -> bool:
    if any(k in fname_low for k in _CORR_HINTS):
        return True
    tl = (text or "").lower()
    return "correspondentie" in tl or "geachte" in tl or "betreft" in tl


def _chunk_text(text: str) -> List[str]:
    chunks = chunk_by_sentences(text, target_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if not chunks:
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if len(chunks) > MAX_CHUNKS_PER_DOC:
        return chunks[:MAX_CHUNKS_PER_DOC]
    return chunks


def _meta_key(m: dict) -> Tuple[str, str, str, int, Optional[str]]:
    t_hash = None
    if DEDUPE_WITH_HASH:
        t_hash = hashlib.sha1((m.get("text") or "").encode("utf-8", errors="ignore")).hexdigest()
    return (
        (m.get("client_id") or "UNKNOWN").upper(),
        (m.get("project_id") or "UNKNOWN").upper(),
        m.get("filename") or "",
        int(m.get("chunk_index") or 0),
        t_hash,
    )


def _build_existing_keys(rows: List[dict]) -> Set[Tuple[str, str, str, int, Optional[str]]]:
    keys: Set[Tuple[str, str, str, int, Optional[str]]] = set()
    for r in rows or []:
        try:
            keys.add(_meta_key(r))
        except Exception:
            continue
    return keys


def _embed_in_batches(embedder: Embedder, texts: List[str]) -> _np.ndarray:
    out = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        vecs = embedder.embed(batch)
        out.extend(vecs)
    return _np.array(out, dtype=_np.float32)


def _concat_embeddings(old: Optional[_np.ndarray], new: _np.ndarray) -> _np.ndarray:
    if old is None or old.size == 0:
        return new.astype(_np.float32, copy=False)
    if old.shape[1] != new.shape[1]:
        raise ValueError(f"Embedding dimension mismatch: old={old.shape}, new={new.shape}")
    return _np.vstack([old.astype(_np.float32, copy=False), new.astype(_np.float32, copy=False)])


# ────────────────────────────────────────────────────────────────
# Main indexfunctie
# ────────────────────────────────────────────────────────────────
def index_documents(data_dir: Path, proj_to_clients: Dict[str, List[str]], embedder: Embedder) -> int:
    files = find_files_in_dir(data_dir, exts=[".pdf", ".docx", ".txt"])
    total_chunks = 0
    skipped = 0

    client_to_projects: Dict[str, List[str]] = {}
    for p_id, clist in (proj_to_clients or {}).items():
        for c in clist:
            client_to_projects.setdefault(_norm_id(c, "client"), []).append(_norm_id(p_id, "project"))

    for f in files:
        # Veilige unpack
        res = read_and_meta(f)
        if not res or not isinstance(res, (list, tuple)) or len(res) != 2:
            print(f"[ERROR] read_and_meta returned invalid result for {f.name}, skipping.")
            skipped += 1
            continue
        text, meta = res

        if not (text or "").strip():
            print(f"[WARN] geen tekst in {f.name}, skipping (OCR mogelijk vereist).")
            skipped += 1
            continue

        cid = _norm_id(meta.get("client_id"), "client")
        pid = _norm_id(meta.get("project_id"), "project")

        # Fallbacks voor ontbrekende PID
        if not pid:
            c2, p2 = parse_ids_from_path(f)
            pid = pid or _norm_id(p2, "project")

        target_pids = [pid] if pid else ["UNKNOWN"]

        # Chunks maken
        chunks = _chunk_text(text)
        if not chunks:
            print(f"[WARN] no chunks for {f.name}")
            skipped += 1
            continue

        fname_low = f.name.lower()

        for target_pid in target_pids:
            clients_for_project = proj_to_clients.get(target_pid, [])
            if not clients_for_project and cid:
                clients_for_project = [cid]
            if not clients_for_project:
                clients_for_project = ["UNKNOWN"]

            rows_existing, emb_arr = load_index(clients_for_project[0], target_pid)
            existing_keys = _build_existing_keys(rows_existing or [])

            metas = []
            for i, c in enumerate(chunks):
                m = {
                    "text": c,
                    "client_id": clients_for_project[0],
                    "project_id": target_pid,
                    "filename": f.name,
                    "filepath": str(f),
                    "chunk_index": i,
                    "source": "doc_file",
                    "is_correspondentie": _is_correspondentie(fname_low, c),
                }
                if _meta_key(m) not in existing_keys:
                    metas.append(m)

            if not metas:
                continue

            try:
                embs_new = _embed_in_batches(embedder, [m["text"] for m in metas])
            except Exception as e:
                print(f"[ERROR] embedding failed for {f.name}: {e}")
                skipped += len(metas)
                continue

            try:
                if rows_existing and emb_arr is not None and len(rows_existing) == len(emb_arr):
                    emb_concat = _concat_embeddings(_np.array(emb_arr, dtype=_np.float32), embs_new)
                    save_index(clients_for_project[0], target_pid, (rows_existing + metas), emb_concat.tolist())
                else:
                    save_index(clients_for_project[0], target_pid, metas, embs_new.tolist())
            except Exception as e:
                print(f"[ERROR] saving index failed for {f.name}: {e}")
                skipped += len(metas)
                continue

            total_chunks += len(metas)

    print(f"[INFO] documents indexed. chunks={total_chunks}, skipped_files={skipped}")
    return total_chunks
