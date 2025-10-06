#!/usr/bin/env python3
# force_assign_by_client.py
"""
Force-assign UNKNOWN rows that contain a client id (C###) to the client's mapped project.
Verbeterd:
 - gebruikt file_fingerprint en meta_key dedupe
 - dry-run optie
 - defensieve embeddings append
"""
from pathlib import Path
import json, re, csv, shutil, sys, argparse

try:
    import numpy as _np
except Exception:
    _np = None

# relative imports
from .embedder_modular import Embedder
from ..index_utils import load_index, save_index
from .id_utils import parse_ids_from_filename_or_path
from ._meta_key import meta_key, build_existing_keys

BASE = Path(__file__).parent.resolve()
CHATBOT_DIR = BASE.parent
INDEX_DIR = CHATBOT_DIR / "index"
DATA_DIR = CHATBOT_DIR / "data"

CLIENTS_CSV = DATA_DIR / "Clients__10_rows__-_with_ProjectID_assigned.csv"
UNKNOWN_GLOB = list(INDEX_DIR.glob("index_UNKNOWN*.jsonl"))

def read_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as fh:
        for L in fh:
            try:
                rows.append(json.loads(L))
            except Exception:
                continue
    return rows

def backup(path: Path):
    if path.exists():
        bp = path.with_suffix(path.suffix + ".backup")
        shutil.copy(path, bp)
        print(f"[INFO] backup {path.name} -> {bp.name}")

def append_jsonl(path: Path, metas, dry_run: bool = False):
    if dry_run:
        print(f"[DRYRUN] would append {len(metas)} metas to {path.name}")
        return
    with path.open("a", encoding="utf-8") as fh:
        for m in metas:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")

def append_embeddings(target_emb_path: Path, new_embs, dry_run: bool = False):
    if _np is None:
        print("[WARN] numpy not available; embeddings will NOT be saved.")
        return
    new_arr = _np.array(new_embs, dtype=_np.float32)
    if dry_run:
        print(f"[DRYRUN] would append embeddings shape {new_arr.shape} to {target_emb_path.name}")
        return
    if target_emb_path.exists():
        try:
            old = _np.load(target_emb_path)
            merged = _np.vstack([old, new_arr])
            _np.save(target_emb_path, merged)
            return
        except Exception as e:
            print(f"[WARN] failed to append to existing emb file {target_emb_path}: {e} — overwriting with just new embeddings.")
    _np.save(target_emb_path, new_arr)

def load_clients_map(csv_path):
    m = {}
    if not csv_path.exists():
        return m
    with csv_path.open(encoding="utf-8", errors="ignore") as fh:
        r = csv.DictReader(fh)
        for row in r:
            keys = {k.lower(): v for k, v in row.items()}
            cid = (keys.get("klantid") or keys.get("clientid") or keys.get("klant_id") or keys.get("client_id") or keys.get("klant") or "").strip().upper()
            pid = (keys.get("projectid") or keys.get("project") or keys.get("project_id") or "").strip().upper()
            if cid and pid:
                m[cid] = pid
    return m

def find_client_in_row(row):
    # search filename, filepath, text for C### pattern
    for field in ("filename", "filepath", "text"):
        val = (row.get(field) or "")
        m = re.search(r"(C\d{1,6})", val.upper())
        if m:
            return m.group(1)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()
    dry_run = args.dry_run

    print("[START] force_assign_by_client (dry_run=%s)" % dry_run)
    print("CHATBOT_DIR:", CHATBOT_DIR)
    print("INDEX_DIR:", INDEX_DIR)
    print("DATA_DIR:", DATA_DIR)
    print("Clients CSV:", CLIENTS_CSV)
    if not INDEX_DIR.exists():
        print("[ERROR] index dir missing:", INDEX_DIR); return

    clients_map = load_clients_map(CLIENTS_CSV)
    if not clients_map:
        print("[WARN] clients mapping empty or CSV missing; script will skip if no mapping found.")

    if not UNKNOWN_GLOB:
        print("[DONE] no UNKNOWN jsonl files found.")
        return

    all_rows = []
    for uj in UNKNOWN_GLOB:
        print("[INFO] processing:", uj.name)
        backup(uj)
        all_rows.extend(read_jsonl(uj))

    if not all_rows:
        print("[DONE] no rows to process.")
        return

    embedder = Embedder()
    batches = {}  # (client, pid) -> list of metas
    skipped = 0

    for r in all_rows:
        client_found = find_client_in_row(r)
        if not client_found:
            # looser parse: maybe filename contains Cnnn
            client_found, _ = parse_ids_from_filename_or_path(Path(r.get("filename") or ""))
            if not client_found:
                continue
        pid = clients_map.get(client_found)
        if not pid:
            m = re.search(r"(P\d{1,6})", (r.get("text") or "").upper())
            if m:
                pid = m.group(1)
        if not pid:
            print(f"[SKIP] client {client_found} found but no project mapping; row skipped.")
            skipped += 1
            continue

        meta = dict(r)
        meta["client_id"] = client_found
        meta["project_id"] = pid
        # ensure fingerprint exists for dedupe
        if not meta.get("file_fingerprint"):
            meta["file_fingerprint"] = f"unknown_index_row_{hash(json.dumps(meta.get('text','')))}"
        target = (client_found, pid)
        batches.setdefault(target, []).append(meta)

    moved = 0
    for (client_id, pid), metas in batches.items():
        texts = [m.get("text") for m in metas]
        # dedupe against existing target index
        existing_rows, existing_emb = load_index(client_id, pid)
        existing_keys = build_existing_keys(existing_rows)
        metas_to_add = []
        embs_to_add = []
        for idx_m, m in enumerate(metas):
            if meta_key(m) in existing_keys:
                continue
            metas_to_add.append(m)
            # placeholder for embedding; will batch embed below
        if not metas_to_add:
            print(f"[INFO] nothing to add for {client_id}/{pid}")
            continue

        try:
            embs = embedder.embed([m.get("text") for m in metas_to_add])
        except Exception as e:
            print(f"[ERROR] embedding failed for {client_id}/{pid}: {e}")
            skipped += len(metas_to_add)
            continue

        # append jsonl & embeddings
        target_json = INDEX_DIR / f"index_{client_id}_{pid}.jsonl"
        target_emb = INDEX_DIR / f"emb_{client_id}_{pid}.npy"

        append_jsonl(target_json, metas_to_add, dry_run=dry_run)
        append_embeddings(target_emb, embs, dry_run=dry_run)

        moved += len(metas_to_add)
        print(f"[INFO] appended {len(metas_to_add)} chunks -> {target_json.name}")

    print(f"[DONE] moved {moved} chunks; skipped {skipped}.")
    print("You can inspect index files in", INDEX_DIR)

if __name__ == "__main__":
    main()
