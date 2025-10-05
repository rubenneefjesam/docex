#!/usr/bin/env python3
"""
Force-assign UNKNOWN rows that contain a client id (C###) to the client's mapped project.
Place in indexer/ and run as module (see instructions above).
"""
from pathlib import Path
import json, re, csv, shutil, sys

try:
    import numpy as _np
except Exception:
    _np = None

# relative imports (works when run with -m)
from .embedder_modular import Embedder
from ..index_utils import load_index, save_index

BASE = Path(__file__).parent.resolve()        # .../chatbot/indexer
CHATBOT_DIR = BASE.parent                      # .../chatbot
INDEX_DIR = CHATBOT_DIR / "index"
DATA_DIR = CHATBOT_DIR / "data"

CLIENTS_CSV = DATA_DIR / "Clients__10_rows__-_with_ProjectID_assigned.csv"
UNKNOWN_GLOB = list(INDEX_DIR.glob("index_UNKNOWN*.jsonl"))

def load_clients_map(csv_path):
    m = {}
    if not csv_path.exists():
        return m
    with csv_path.open(encoding="utf-8", errors="ignore") as fh:
        r = csv.DictReader(fh)
        # try many possible keynames
        for row in r:
            # prefer KlantID / ProjectID but fallback to generic
            keys = {k.lower(): v for k, v in row.items()}
            cid = (keys.get("klantid") or keys.get("clientid") or keys.get("klant_id") or keys.get("client_id") or keys.get("klant") or "").strip().upper()
            pid = (keys.get("projectid") or keys.get("project") or keys.get("project_id") or "").strip().upper()
            if cid and pid:
                m[cid] = pid
    return m

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

def find_client_in_row(row):
    # search filename, filepath, text for C### pattern
    for field in ("filename", "filepath", "text"):
        val = (row.get(field) or "")
        m = re.search(r"(C\d{1,6})", val.upper())
        if m:
            return m.group(1)
    return None

def append_jsonl(path: Path, metas):
    with path.open("a", encoding="utf-8") as fh:
        for m in metas:
            fh.write(json.dumps(m, ensure_ascii=False) + "\n")

def append_embeddings(target_emb_path: Path, new_embs):
    if _np is None:
        print("[WARN] numpy not available; embeddings will NOT be saved.")
        return
    new_arr = _np.array(new_embs, dtype=_np.float32)
    if target_emb_path.exists():
        try:
            old = _np.load(target_emb_path)
            merged = _np.vstack([old, new_arr])
            _np.save(target_emb_path, merged)
            return
        except Exception as e:
            print(f"[WARN] failed to append to existing emb file {target_emb_path}: {e} — overwriting with just new embeddings.")
    _np.save(target_emb_path, new_arr)

def main():
    print("[START] force_assign_by_client")
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

    for r in all_rows:
        client_found = find_client_in_row(r)
        if not client_found:
            # try a looser parse: allow 'Klant-ID: C006' inside text (already covered by text search)
            continue
        # find project via csv mapping
        pid = clients_map.get(client_found)
        if not pid:
            # fallback: try parse project in same row (maybe present in text)
            m = re.search(r"(P\d{1,6})", (r.get("text") or "").upper())
            if m:
                pid = m.group(1)
        if not pid:
            print(f"[SKIP] client {client_found} found but no project mapping; row skipped.")
            continue

        # prepare meta
        meta = dict(r)
        meta["client_id"] = client_found
        meta["project_id"] = pid
        target = (client_found, pid)
        batches.setdefault(target, []).append(meta)

    moved = 0
    skipped = 0

    for (client_id, pid), metas in batches.items():
        texts = [m["text"] for m in metas]
        try:
            embs = embedder.embed(texts)
        except Exception as e:
            print(f"[ERROR] embedding failed for {client_id}/{pid}: {e}")
            skipped += len(metas)
            continue

        # append jsonl
        target_json = INDEX_DIR / f"index_{client_id}_{pid}.jsonl"
        append_jsonl(target_json, metas)

        # append embeddings
        target_emb = INDEX_DIR / f"emb_{client_id}_{pid}.npy"
        append_embeddings(target_emb, embs)

        moved += len(metas)
        print(f"[INFO] appended {len(metas)} chunks -> {target_json.name}")

    print(f"[DONE] moved {moved} chunks; skipped {skipped}.")
    print("You can inspect index files in", INDEX_DIR)

if __name__ == "__main__":
    main()
