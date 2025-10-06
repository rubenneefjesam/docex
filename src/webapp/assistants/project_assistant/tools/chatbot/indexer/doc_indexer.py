# doc_indexer.py
# Nieuwe, verbeterde versie van de indexer zoals besproken:
# - vroegtijdig ID-extractie uit bestandsnaam/pad
# - richer metadata per chunk (source_filepath, assign_method, assign_confidence, file_checksum)
# - dedupe-key bevat unieke file-identificatie (filepath/checksum)
# - dedupe controle over alle candidate client/project combinaties
# - low-confidence review-queue export + uitgebreide logging/statistieken
#
# Let op: deze file houdt dezelfde externe dependencies aan als voorheen:
#   find_files_in_dir, read_and_meta, parse_ids_from_path, chunk_by_sentences, chunk_text_simple,
#   load_index, save_index, Embedder, CHUNK_SIZE, CHUNK_OVERLAP
#
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
import re
import hashlib
import numpy as _np
import os
import csv
import time

from .io_utils_extended import find_files_in_dir, read_and_meta, parse_ids_from_path
from .chunker import chunk_by_sentences, chunk_text_simple
from ..index_utils import load_index, save_index
from .embedder_modular import Embedder
from ..utils import CHUNK_SIZE, CHUNK_OVERLAP

# Configurables via env
BATCH_SIZE = int(os.getenv("INDEX_EMBED_BATCH", "128"))
MAX_CHUNKS_PER_DOC = int(os.getenv("INDEX_MAX_CHUNKS_PER_DOC", "500"))
DEDUPE_WITH_HASH = os.getenv("INDEX_DEDUPE_WITH_HASH", "1") == "1"
LOW_CONF_THRESHOLD = float(os.getenv("INDEX_LOW_CONF_THRESHOLD", "0.5"))
REVIEW_QUEUE_CSV = os.getenv("INDEX_REVIEW_QUEUE_CSV", "index_review_queue.csv")

# Hints for correspondence detection
_CORR_HINTS = ("klantcommunicatie", "correspondentie", "corresp", "mail", "brief", "orderbevestiging", "klantorders")


# -------------------------
# Helpers
# -------------------------
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
    if len(chunks) > MAX_CHUNKS_PER_DOC:
        return chunks[:MAX_CHUNKS_PER_DOC]
    return chunks


def _file_fingerprint(path: Path) -> str:
    """
    Lightweight file fingerprint: sha1(path + mtime + size).
    Avoids hashing whole file for performance, but still unique-ish per version.
    """
    try:
        stat = path.stat()
        key = f"{str(path)}|{stat.st_mtime_ns}|{stat.st_size}"
    except Exception:
        key = str(path)
    return hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()


def _meta_key(m: Dict[str, Any]) -> Tuple[str, str, str, int, Optional[str]]:
    """
    Unieke sleutel voor dedupe binnen index:
      (client, project, file_fingerprint, chunk_index, text_hash?)
    file_fingerprint voorkomt collisions van gelijke bestandsnamen in verschillende mappen.
    """
    t_hash = None
    if DEDUPE_WITH_HASH:
        t_hash = hashlib.sha1((m.get("text") or "").encode("utf-8", errors="ignore")).hexdigest()
    return (
        (m.get("client_id") or "UNKNOWN").upper(),
        (m.get("project_id") or "UNKNOWN").upper(),
        (m.get("file_fingerprint") or "").upper(),
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
    arr = _np.array(out_list, dtype=_np.float32)
    return arr


def _concat_embeddings(old: Optional[_np.ndarray], new: _np.ndarray) -> _np.ndarray:
    if old is None or old.size == 0:
        return new.astype(_np.float32, copy=False)
    if old.shape[1] != new.shape[1]:
        raise ValueError(f"Embedding dimension mismatch: old={old.shape}, new={new.shape}")
    return _np.vstack([old.astype(_np.float32, copy=False), new.astype(_np.float32, copy=False)])


# -------------------------
# Main indexer
# -------------------------
def index_documents(data_dir: Path, proj_to_clients: Dict[str, List[str]], embedder: Embedder) -> int:
    files = find_files_in_dir(data_dir, exts=[".pdf", ".docx", ".txt"])
    total_chunks = 0
    skipped = 0

    # reverse mapping client -> [projects]
    client_to_projects: Dict[str, List[str]] = {}
    for p_id, clist in (proj_to_clients or {}).items():
        for c in clist:
            client_to_projects.setdefault(_norm_id(c, "client"), []).append(_norm_id(p_id, "project"))

    # Stats & review queue
    assign_method_counts: Dict[str, int] = {}
    low_confidence_entries: List[Dict[str, Any]] = []
    gold_reviewed = 0

    start_time = time.time()

    for f in files:
        # read text and metadata (existing behavior)
        text, meta = read_and_meta(f)

        # ALWAYS attempt to parse IDs from filename/path early (fallback before text-based logic)
        parsed_cid, parsed_pid = parse_ids_from_path(f)  # existing helper; should look at path+name
        parsed_cid = _norm_id(parsed_cid, "client")
        parsed_pid = _norm_id(parsed_pid, "project")

        # file fingerprint for dedupe key & auditing
        file_fprint = _file_fingerprint(Path(str(f)))

        # Normaliseer IDs vroeg (from meta)
        cid = _norm_id(meta.get("client_id"), "client")
        pid = _norm_id(meta.get("project_id"), "project")

        # If meta lacks, take from parsed filename/path early
        if not cid and parsed_cid:
            cid = parsed_cid
        if not pid and parsed_pid:
            pid = parsed_pid

        # If still no pid, try ancestors (folder names)
        if not pid:
            pid_anc = _find_pid_from_ancestors(Path(meta.get("filepath", str(f))))
            pid = pid or _norm_id(pid_anc, "project")
            if pid:
                # this is folder-based assign
                pass

        # If still no pid and text is present, try text search (defer until after empty-text check)
        # However, we don't want to lose the benefit of filename-based IDs even if text is empty.

        # If file has no selectable text -> warn & skip (OCR required)
        if not (text or "").strip():
            print(f"[WARN] geen tekst in {f.name}, skipping (OCR mogelijk vereist). Fingerprint: {file_fprint}")
            skipped += 1
            # Even when skipping embedding, include low-confidence entry for review if filename yields IDs
            if cid or pid:
                low_confidence_entries.append({
                    "filepath": str(f),
                    "filename": f.name,
                    "client_id": cid or "UNKNOWN",
                    "project_id": pid or "UNKNOWN",
                    "reason": "no_text_ocr_needed",
                    "file_fingerprint": file_fprint,
                    "assign_method": "filename_or_meta" if (cid or pid) else "unknown",
                    "assign_confidence": 0.2
                })
            continue

        # If pid still missing, try extracting from text
        if not pid:
            pid_text = _find_pid_in_text(text)
            pid = pid or _norm_id(pid_text, "project")
            if pid:
                print(f"[INFO] pid in text for {f.name}: {pid}")

        # Build list of candidate target_pids
        target_pids: List[str] = []
        if pid and pid != "UNKNOWN":
            target_pids = [pid]
        else:
            # Fallback on CSV mapping via client
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

        # For each target project, determine candidate clients (from mapping) or fallback to detected client or UNKNOWN
        for target_pid in target_pids:
            clients_for_project = proj_to_clients.get(target_pid, []) if target_pid else []
            if not clients_for_project and cid:
                clients_for_project = [cid]
            if not clients_for_project:
                clients_for_project = ["UNKNOWN"]

            # --- Dedupe: build union of existing keys across all candidate client/project pairs ---
            existing_keys_union: Set[Tuple[str, str, str, int, Optional[str]]] = set()
            existing_indices_cache: Dict[Tuple[str, str], Tuple[List[dict], Optional[List[List[float]]]]] = {}
            for client_candidate in clients_for_project:
                cli = client_candidate or "UNKNOWN"
                pid_key = target_pid or "UNKNOWN"
                try:
                    rows_existing, emb_arr = load_index(cli, pid_key)
                    existing_keys_union |= _build_existing_keys(rows_existing or [])
                    existing_indices_cache[(cli, pid_key)] = (rows_existing or [], emb_arr)
                except Exception as e:
                    # If load fails for a client/project, continue but log
                    print(f"[WARN] failed to load_index for {cli}/{pid_key}: {e}")
                    continue

            # Build metas for this target_pid/client combination.
            # We'll create metas per chunk with audit fields; later we'll save them per client-project.
            metas_global: List[dict] = []
            for i, c in enumerate(chunks):
                # Decide assign_method and confidence heuristics
                if meta.get("client_id") or meta.get("project_id"):
                    assign_method = "meta"
                    assign_conf = 0.99
                elif parsed_cid or parsed_pid:
                    assign_method = "filename"
                    assign_conf = 0.90
                elif _find_pid_from_ancestors(Path(str(f))):
                    assign_method = "folder"
                    assign_conf = 0.85
                elif _find_pid_in_text(c):
                    assign_method = "text"
                    assign_conf = 0.95
                elif cid and target_pid != "UNKNOWN":
                    assign_method = "csv"
                    assign_conf = 0.70
                else:
                    assign_method = "unknown"
                    assign_conf = 0.1

                m = {
                    "text": c,
                    "client_id": (clients_for_project[0] or "UNKNOWN"),  # placeholder, will be replaced per client when saving
                    "project_id": (target_pid or "UNKNOWN"),
                    "filename": f.name,
                    "filepath": str(f),
                    "file_fingerprint": file_fprint,
                    "chunk_index": i,
                    "source": "doc_file",
                    "is_correspondentie": _is_correspondentie(fname_low, c),
                    "assign_method": assign_method,
                    "assign_confidence": assign_conf,
                }

                # If dedupe key already exists across ANY candidate client/project, skip
                if _meta_key(m) not in existing_keys_union:
                    metas_global.append(m)

            if not metas_global:
                # nothing new for any of the candidate client/project combos
                continue

            # Collect assign_method stats
            for mm in metas_global:
                assign_method_counts[mm["assign_method"]] = assign_method_counts.get(mm["assign_method"], 0) + 1
                if mm["assign_confidence"] < LOW_CONF_THRESHOLD:
                    low_confidence_entries.append({
                        "filepath": mm["filepath"],
                        "filename": mm["filename"],
                        "client_id": mm["client_id"],  # placeholder; real client will be set per save
                        "project_id": mm["project_id"],
                        "chunk_index": mm["chunk_index"],
                        "reason": "low_confidence_assign",
                        "file_fingerprint": mm["file_fingerprint"],
                        "assign_method": mm["assign_method"],
                        "assign_confidence": mm["assign_confidence"]
                    })

            # Embed once for the new metas
            try:
                embs_new = _embed_in_batches(embedder, [m["text"] for m in metas_global])
            except Exception as e:
                print(f"[ERROR] embed failed for {f.name} ({clients_for_project[0]}/{target_pid}): {e}")
                skipped += len(metas_global)
                continue

            # For saving: write/merge per actual client-project pair cached earlier.
            # If cached index exists for a particular (client, target_pid), merge there; otherwise write new.
            for client_candidate in clients_for_project:
                cli = client_candidate or "UNKNOWN"
                pid_key = target_pid or "UNKNOWN"
                rows_existing, emb_arr = existing_indices_cache.get((cli, pid_key), ([], None))

                # Prepare metas tailored to this client
                metas_for_client: List[dict] = []
                for m in metas_global:
                    mm = m.copy()
                    mm["client_id"] = cli  # set per-client
                    metas_for_client.append(mm)

                try:
                    if rows_existing and emb_arr is not None and len(rows_existing) == len(emb_arr):
                        emb_concat = _concat_embeddings(_np.array(emb_arr, dtype=_np.float32), embs_new)
                        save_index(cli, pid_key, (rows_existing + metas_for_client), emb_concat.tolist())
                    else:
                        save_index(cli, pid_key, metas_for_client, embs_new.tolist())
                except Exception as e:
                    print(f"[ERROR] saving index failed for {f.name} ({cli}/{pid_key}): {e}")
                    skipped += len(metas_for_client)
                    continue

                total_chunks += len(metas_for_client)

    # End for files

    # Export review queue (simple CSV) for low-confidence items
    if low_confidence_entries:
        try:
            with open(REVIEW_QUEUE_CSV, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["filepath", "filename", "client_id", "project_id", "chunk_index", "reason", "file_fingerprint", "assign_method", "assign_confidence"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in low_confidence_entries:
                    writer.writerow({k: row.get(k, "") for k in fieldnames})
            print(f"[INFO] review queue exported to {REVIEW_QUEUE_CSV} ({len(low_confidence_entries)} items).")
        except Exception as e:
            print(f"[WARN] failed to write review queue csv: {e}")

    elapsed = time.time() - start_time
    print(f"[INFO] documents indexed. chunks: {total_chunks}, skipped files: {skipped}, time: {elapsed:.1f}s")
    print(f"[INFO] assign_method counts: {assign_method_counts}")

    return total_chunks
