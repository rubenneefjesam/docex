# index_csvs_modular.py
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# relative/local imports (indexer package)
from .io_utils_extended import find_files_in_dir, read_and_meta
from .chunker import chunk_text_simple, chunk_by_sentences
from .embedder_modular import Embedder
from ..index_utils import load_index, save_index

# helpers we just created
from .id_utils import parse_ids_from_filename_or_path, find_pid_from_ancestors, find_pid_in_text
from ._meta_key import meta_key, build_existing_keys, file_fingerprint_from_meta

# common libs
import pandas as pd
try:
    import numpy as np
except Exception:
    np = None

BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 600))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))
REVIEW_QUEUE_CSV = os.environ.get("INDEX_REVIEW_QUEUE_CSV", "index_csvs_review_queue.csv")
DEDUPE_WITH_HASH = os.environ.get("INDEX_DEDUPE_WITH_HASH", "1") == "1"

# permissive header names
CLIENT_ID_HEADER_CANDIDATES = ["klantid", "klant_id", "clientid", "client_id", "klant", "client"]
PROJECT_ID_HEADER_CANDIDATES = ["projectid", "project_id", "projectid", "project", "project_id"]


def _find_header(cols: List[str], candidates: List[str]) -> Optional[str]:
    lower_to_orig = {c.lower(): c for c in cols}
    for cand in candidates:
        if cand.lower() in lower_to_orig:
            return lower_to_orig[cand.lower()]
    return None


def row_to_text(prefix: str, row: Dict) -> str:
    parts = [f"{k}: {v}" for k, v in row.items()]
    return f"{prefix}\n" + "\n".join(parts)


def _safe_to_float32_list(embs: Any) -> List[List[float]]:
    """
    Zorg dat embeddings een list-of-lists float32 zijn.
    Accepteer numpy arrays of lists.
    """
    if embs is None:
        return []
    if np is not None:
        try:
            arr = np.asarray(embs, dtype=np.float32)
            return arr.tolist()
        except Exception:
            pass
    # fallback: coerce
    out = []
    for row in embs:
        out.append([float(x) for x in row])
    return out


def index_clients_projects_from_csv(clients_csv: Path, projects_csv: Path, embedder: Embedder) -> Dict[str, List[str]]:
    """
    Index client rows and project rows from CSVs.
    Returns mapping: project_id -> list of client_ids.
    Idempotent (probeert doublures te voorkomen via meta-key dedupe).
    """
    df_clients = pd.read_csv(clients_csv, dtype=str).fillna("")
    df_projects = pd.read_csv(projects_csv, dtype=str).fillna("")

    # permissive header discovery
    clients_cols = list(df_clients.columns)
    projects_cols = list(df_projects.columns)
    client_id_col = _find_header(clients_cols, CLIENT_ID_HEADER_CANDIDATES)
    project_id_col_clients = _find_header(clients_cols, PROJECT_ID_HEADER_CANDIDATES)
    project_id_col_projects = _find_header(projects_cols, PROJECT_ID_HEADER_CANDIDATES)

    if not client_id_col:
        raise SystemExit(f"clients CSV mist een client-id kolom. Gevonden kolommen: {clients_cols}")
    if not (project_id_col_clients or project_id_col_projects):
        raise SystemExit(f"projects CSV mist een project-id kolom. Gevonden kolommen: {projects_cols}")

    proj_to_clients: Dict[str, List[str]] = {}
    clients_indexed = 0
    low_conf_entries = []

    # index client rows
    for idx, r in df_clients.iterrows():
        raw_cid = str(r.get(client_id_col) or "").strip()
        raw_pid = str(r.get(project_id_col_clients or project_id_col_projects) or "").strip()
        if not raw_cid or not raw_pid:
            continue
        # normaliseer
        cid = parse_ids_from_filename_or_path(raw_cid)[0] or raw_cid.upper()
        pid = parse_ids_from_filename_or_path(raw_pid)[1] or raw_pid.upper()

        # build text & chunks
        text = row_to_text("Client record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        # build metas with audit fields
        metas = []
        for i, c in enumerate(chunks):
            m = {
                "text": c,
                "client_id": cid,
                "project_id": pid,
                "source": "clients_csv",
                "chunk_index": i,
                "assign_method": "clients_csv",
                "assign_confidence": 0.99,
                "file_fingerprint": f"clients_csv_row_{cid}_{pid}_{idx}"
            }
            metas.append(m)

        # dedupe against existing index (if any)
        existing_rows, existing_emb = load_index(cid, pid)
        existing_keys = build_existing_keys(existing_rows, dedupe_with_hash=DEDUPE_WITH_HASH)

        metas_to_add = [m for m in metas if meta_key(m, dedupe_with_hash=DEDUPE_WITH_HASH) not in existing_keys]
        if not metas_to_add:
            continue

        # embed defensively
        try:
            embs = embedder.embed([m["text"] for m in metas_to_add])
            embs = _safe_to_float32_list(embs)
        except Exception as e:
            print(f"[ERROR] embedding clients CSV row {cid}/{pid}: {e}")
            low_conf_entries.append({"type": "embed_error", "cid": cid, "pid": pid, "reason": str(e)})
            continue

        # merge/save
        if existing_rows and existing_emb is not None:
            if np is None:
                raise RuntimeError("Numpy vereist voor embeddings opslaan")
            old_arr = np.asarray(existing_emb, dtype=np.float32)
            new_arr = np.asarray(embs, dtype=np.float32)
            merged = np.vstack([old_arr, new_arr])
            save_index(cid, pid, (existing_rows + metas_to_add), merged.tolist())
        else:
            save_index(cid, pid, metas_to_add, embs)

        proj_to_clients.setdefault(pid, []).append(cid)
        clients_indexed += 1

    # index projects, duplicate per client
    projects_indexed = 0
    for idx, r in df_projects.iterrows():
        raw_pid = str(r.get(project_id_col_projects) or "").strip()
        if not raw_pid:
            continue
        pid = parse_ids_from_filename_or_path(raw_pid)[1] or raw_pid.upper()
        text = row_to_text("Project record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        clients = proj_to_clients.get(pid, []) or ["UNKNOWN"]
        metas_base = []
        for i, c in enumerate(chunks):
            metas_base.append({
                "text": c,
                "project_id": pid,
                "source": "projects_csv",
                "chunk_index": i,
                "assign_method": "projects_csv",
                "assign_confidence": 0.99,
                "file_fingerprint": f"projects_csv_row_{pid}_{idx}"
            })

        for cid in clients:
            # set client on copy
            metas_for_client = []
            for m in metas_base:
                mm = dict(m)
                mm["client_id"] = cid or "UNKNOWN"
                metas_for_client.append(mm)

            # dedupe
            existing_rows, existing_emb = load_index(cid or "UNKNOWN", pid)
            existing_keys = build_existing_keys(existing_rows, dedupe_with_hash=DEDUPE_WITH_HASH)
            metas_to_add = [m for m in metas_for_client if meta_key(m, dedupe_with_hash=DEDUPE_WITH_HASH) not in existing_keys]
            if not metas_to_add:
                continue

            try:
                embs = embedder.embed([m["text"] for m in metas_to_add])
                embs = _safe_to_float32_list(embs)
            except Exception as e:
                print(f"[ERROR] embedding project {pid} for client {cid}: {e}")
                low_conf_entries.append({"type": "embed_error", "cid": cid, "pid": pid, "reason": str(e)})
                continue

            if existing_rows and existing_emb is not None:
                if np is None:
                    raise RuntimeError("Numpy vereist voor embeddings opslaan")
                old_arr = np.asarray(existing_emb, dtype=np.float32)
                new_arr = np.asarray(embs, dtype=np.float32)
                merged = np.vstack([old_arr, new_arr])
                save_index(cid or "UNKNOWN", pid, (existing_rows + metas_to_add), merged.tolist())
            else:
                save_index(cid or "UNKNOWN", pid, metas_to_add, embs)

        projects_indexed += 1

    # export review queue if any low_conf_entries
    if low_conf_entries:
        try:
            import csv
            with open(REVIEW_QUEUE_CSV, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["type", "cid", "pid", "reason"])
                writer.writeheader()
                for r in low_conf_entries:
                    writer.writerow(r)
            print(f"[INFO] review queue exported to {REVIEW_QUEUE_CSV} ({len(low_conf_entries)} items).")
        except Exception as e:
            print(f"[WARN] failed to write review queue csv: {e}")

    print(f"[INFO] clients indexed: {clients_indexed}, projects indexed: {projects_indexed}")
    return proj_to_clients


def index_documents(data_dir: Path, proj_to_clients: Dict[str, List[str]], embedder: Embedder):
    """
    Index documents in data_dir (recursive). Attach documents to clients via proj_to_clients
    mapping where possible. If no project id can be found, index under project_id='UNKNOWN'.
    """
    files = find_files_in_dir(data_dir, exts=[".pdf", ".docx", ".txt"])
    total_chunks = 0
    skipped = []

    for f in files:
        try:
            text, meta = read_and_meta(f)
        except Exception as e:
            print(f"[WARN] Kon bestand niet lezen {f}: {e}")
            skipped.append((str(f), "read_fail", str(e)))
            continue

        if not (text or "").strip():
            print(f"[WARN] Geen tekst gevonden in {f}; skipping")
            skipped.append((str(f), "no_text"))
            continue

        cid = meta.get("client_id")
        pid = meta.get("project_id")

        # fallback 1: try to find project id from path/filename or ancestors
        if not pid:
            parsed_cid, parsed_pid = parse_ids_from_filename_or_path(f)
            pid = pid or parsed_pid
            cid = cid or parsed_cid

        if not pid:
            pid = find_pid_from_ancestors(Path(meta.get("filepath", str(f))))
            if pid:
                meta["project_id"] = pid
                print(f"[INFO] PID gevonden via folder voor {f.name}: {pid}")

        # fallback 2: try to find in text
        if not pid:
            pid_text = find_pid_in_text(text)
            if pid_text:
                pid = pid_text
                meta["project_id"] = pid
                print(f"[INFO] PID gevonden in tekst voor {f.name}: {pid}")

        # final fallback: UNKNOWN (still index it)
        if not pid:
            pid = "UNKNOWN"
            meta["project_id"] = pid
            print(f"[INFO] Geen ProjectID gevonden voor {f.name}: indexeren onder PROJECT=UNKNOWN")

        # determine clients to attach: prefer mapping, else parsed cid, else UNKNOWN
        clients = proj_to_clients.get(pid, [])
        if not clients and cid:
            clients = [cid]
        if not clients:
            clients = ["UNKNOWN"]

        # chunk text: try sentence-based then fallback
        chunks = chunk_by_sentences(text, target_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        if not chunks:
            chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)

        # Prepare metas
        metas = []
        for i, c in enumerate(chunks):
            m = {
                "text": c,
                "client_id": None,  # set per client on save
                "project_id": pid,
                "filename": f.name,
                "filepath": str(f),
                "chunk_index": i,
                "source": "doc_file",
                "assign_method": "filename" if str(f).upper().find("C") >= 0 else "text_or_folder",
                "assign_confidence": 0.9,
                "file_fingerprint": f"file_{hash(str(f))}"
            }
            metas.append(m)

        # Embed defensively (single embed call per doc)
        try:
            embs = embedder.embed([m["text"] for m in metas])
            embs = _safe_to_float32_list(embs)
        except Exception as e:
            print(f"[ERROR] Embedding mislukt voor {f.name}: {e}")
            skipped.append((str(f), "embed_fail", str(e)))
            continue

        # For each client, dedupe and save
        for client in clients:
            client_key = client or "UNKNOWN"
            existing_rows, existing_emb = load_index(client_key, pid)
            existing_keys = build_existing_keys(existing_rows, dedupe_with_hash=DEDUPE_WITH_HASH)

            metas_to_add = []
            embs_to_add = []
            for idx_m, m in enumerate(metas):
                m_copy = dict(m)
                m_copy["client_id"] = client_key
                k = meta_key(m_copy, dedupe_with_hash=DEDUPE_WITH_HASH)
                if k in existing_keys:
                    continue
                metas_to_add.append(m_copy)
                embs_to_add.append(embs[idx_m])

            if not metas_to_add:
                continue

            # merge/save
            try:
                if existing_rows and existing_emb is not None:
                    if np is None:
                        raise RuntimeError("Numpy vereist voor embeddings opslaan")
                    old_arr = np.asarray(existing_emb, dtype=np.float32)
                    new_arr = np.asarray(embs_to_add, dtype=np.float32)
                    merged = np.vstack([old_arr, new_arr])
                    save_index(client_key, pid, (existing_rows + metas_to_add), merged.tolist())
                else:
                    save_index(client_key, pid, metas_to_add, embs_to_add)
            except Exception as e:
                print(f"[ERROR] saving index for {client_key}/{pid}: {e}")
                skipped.append((str(f), "save_fail", str(e)))
                continue

            total_chunks += len(metas_to_add)

    print(f"[INFO] Document indexing complete. Chunks created: {total_chunks}. Skipped items: {len(skipped)}")
    if skipped:
        for s in skipped[:20]:
            print(" -", s)
