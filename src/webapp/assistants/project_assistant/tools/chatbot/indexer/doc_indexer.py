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

# Instelbaar via env (met veilige defaults)
BATCH_SIZE = int(os.getenv("INDEX_EMBED_BATCH", "128"))
MAX_CHUNKS_PER_DOC = int(os.getenv("INDEX_MAX_CHUNKS_PER_DOC", "500"))  # safety guard
DEDUPE_WITH_HASH = os.getenv("INDEX_DEDUPE_WITH_HASH", "1") == "1"

_CORR_HINTS = ("klantcommunicatie", "correspondentie", "corresp", "mail", "brief", "orderbevestiging", "klantorders")

def _find_pid_from_ancestors(path: Path) -> Optional[str]:
    for anc in (path.parent, path.parent.parent):
        if not anc:
            continue
        m = re.search(r"(P\d{1,6})", anc.name.upper())
        if m:
            return m.group(1)
    return None

def _find_pid_in_text(text: str) -> Optional[str]:
    m = re.search(r"\b(P\d{1,6})\b", (text or "").upper())
    if m:
        return m.group(1)
    return None

def _norm_id(val: Optional[str], kind: str) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    if kind == "client":
        if v.startswith("C"):
            return v
        if v.isdigit():
            return "C" + v
    if kind == "project":
        if v.startswith("P"):
            return v
        if v.isdigit():
            return "P" + v
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
    # Safety cap
    if len(chunks) > MAX_CHUNKS_PER_DOC:
        return chunks[:MAX_CHUNKS_PER_DOC]
    return chunks

def _meta_key(m: dict) -> Tuple[str, str, str, int, Optional[str]]:
    """Unieke sleutel voor dedupe binnen index: (client, project, filename, chunk_index, text_hash?)"""
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
    out_list: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        vecs = embedder.embed(batch)
        out_list.extend(vecs)
    # Consistente float32
    arr = _np.array(out_list, dtype=_np.float32)
    return arr

def _concat_embeddings(old: Optional[_np.ndarray], new: _np.ndarray) -> _np.ndarray:
    if old is None or old.size == 0:
        return new.astype(_np.float32, copy=False)
    if old.shape[1] != new.shape[1]:
        raise ValueError(f"Embedding dimension mismatch: old={old.shape}, new={new.shape}")
    return _np.vstack([old.astype(_np.float32, copy=False), new.astype(_np.float32, copy=False)])

def index_documents(data_dir: Path, proj_to_clients: Dict[str, List[str]], embedder: Embedder) -> int:
    files = find_files_in_dir(data_dir, exts=[".pdf", ".docx", ".txt"])
    total_chunks = 0
    skipped = 0

    # reverse mapping client -> [projects]
    client_to_projects: Dict[str, List[str]] = {}
    for p_id, clist in (proj_to_clients or {}).items():
        for c in clist:
            client_to_projects.setdefault(_norm_id(c, "client"), []).append(_norm_id(p_id, "project"))

    for f in files:
        text, meta = read_and_meta(f)

        if not (text or "").strip():
            print(f"[WARN] geen tekst in {f.name}, skipping (OCR mogelijk vereist).")
            skipped += 1
            continue

        # Normaliseer IDs vroeg
        cid = _norm_id(meta.get("client_id"), "client")
        pid = _norm_id(meta.get("project_id"), "project")

        if not cid or not pid:
            parsed_cid, parsed_pid = parse_ids_from_path(f)
            cid = cid or _norm_id(parsed_cid, "client")
            pid = pid or _norm_id(parsed_pid, "project")

        if not pid:
            pid = _find_pid_from_ancestors(Path(meta.get("filepath", str(f))))
            pid = _norm_id(pid, "project")
            if pid:
                print(f"[INFO] pid from folder for {f.name}: {pid}")

        if not pid:
            pid = _find_pid_in_text(text)
            pid = _norm_id(pid, "project")
            if pid:
                print(f"[INFO] pid in text for {f.name}: {pid}")

        target_pids: List[Optional[str]] = []
        if pid and pid != "UNKNOWN":
            target_pids = [pid]
        else:
            # Vallen terug op client mapping
            if cid:
                mapped = client_to_projects.get(cid)
                if mapped:
                    target_pids = [p for p in mapped if p]
                    print(f"[INFO] resolved project(s) {target_pids} for client {cid} via CSV mapping for file {f.name}")
        if not target_pids:
            target_pids = [pid or "UNKNOWN"]
            if target_pids == ["UNKNOWN"]:
                print(f"[INFO] no PID for {f.name}, indexing under UNKNOWN")

        # Chunking
        chunks = _chunk_text(text)
        if not chunks:
            print(f"[WARN] no chunks produced for {f.name}")
            skipped += 1
            continue

        fname_low = f.name.lower()

        for target_pid in target_pids:
            clients_for_project = proj_to_clients.get(target_pid, []) if target_pid else []
            if not clients_for_project and cid:
                clients_for_project = [cid]
            if not clients_for_project:
                clients_for_project = ["UNKNOWN"]

            # Voor dedupe: laad bestaande index en bouw key-set
            # NB: We dedupen per (client, project) target.
            rows_existing, emb_arr = load_index((clients_for_project[0] or "UNKNOWN"), (target_pid or "UNKNOWN"))
            existing_keys = _build_existing_keys(rows_existing or [])

            metas: List[dict] = []
            for i, c in enumerate(chunks):
                m = {
                    "text": c,
                    "client_id": (clients_for_project[0] or "UNKNOWN"),
                    "project_id": (target_pid or "UNKNOWN"),
                    "filename": f.name,
                    "filepath": str(f),
                    "chunk_index": i,
                    "source": "doc_file",
                    "is_correspondentie": _is_correspondentie(fname_low, c),
                }
                if _meta_key(m) not in existing_keys:
                    metas.append(m)

            if not metas:
                # Niets nieuws voor dit (client, project)
                continue

            # Embed in batches
            try:
                embs_new = _embed_in_batches(embedder, [m["text"] for m in metas])
            except Exception as e:
                print(f"[ERROR] embed failed for {f.name} ({clients_for_project[0]}/{target_pid}): {e}")
                skipped += len(metas)
                continue

            # Dimensie-check en concat
            try:
                if rows_existing and emb_arr is not None and len(rows_existing) == len(emb_arr):
                    emb_concat = _concat_embeddings(_np.array(emb_arr, dtype=_np.float32), embs_new)
                    save_index((clients_for_project[0] or "UNKNOWN"), (target_pid or "UNKNOWN"), (rows_existing + metas), emb_concat.tolist())
                else:
                    # Geen bestaande of mismatch → schrijf nieuw voor deze target
                    save_index((clients_for_project[0] or "UNKNOWN"), (target_pid or "UNKNOWN"), metas, embs_new.tolist())
            except Exception as e:
                print(f"[ERROR] saving index failed for {f.name} ({clients_for_project[0]}/{target_pid}): {e}")
                skipped += len(metas)
                continue

            total_chunks += len(metas)

    print(f"[INFO] documents indexed. chunks: {total_chunks}, skipped files: {skipped}")
    return total_chunks
