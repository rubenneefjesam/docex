# reassign_unknown.py
#!/usr/bin/env python3
"""
Reassign UNKNOWN chunks → probeer ze te koppelen aan project-indices.
Idempotent (dedupe), batching, veilige backups, duidelijke logging.

Plaats dit bestand in:
  src/webapp/assistants/project_assistant/tools/chatbot/indexer/reassign_unknown.py

Run als module vanuit repo root:
  export PYTHONPATH=$(pwd)/src
  ./.venv/bin/python -m webapp.assistants.project_assistant.tools.chatbot.indexer.reassign_unknown
"""
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import json, re, shutil, os
import hashlib

# numpy optioneel (voor directe npy merges), save_index gebruikt list->json
try:
    import numpy as _np
except Exception:
    _np = None

from .embedder_modular import Embedder
from .csv_indexer import index_clients_projects_from_csv
from ..index_utils import load_index, save_index

# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.resolve()           # .../chatbot/indexer
CHATBOT_DIR = BASE.parent                        # .../chatbot
INDEX_DIR = CHATBOT_DIR / "index"
DATA_DIR = CHATBOT_DIR / "data"

BATCH_SIZE = int(os.environ.get("REASSIGN_EMBED_BATCH", "128"))
DEDUPE_WITH_HASH = os.environ.get("REASSIGN_DEDUPE_WITH_HASH", "1") == "1"
MAX_ROWS_PER_TARGET = int(os.environ.get("REASSIGN_MAX_ROWS_PER_TARGET", "200000"))  # safety cap

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
def _debug_paths():
    print("[DEBUG] CHATBOT_DIR:", CHATBOT_DIR)
    print("[DEBUG] INDEX_DIR :", INDEX_DIR)
    print("[DEBUG] DATA_DIR  :", DATA_DIR)

def _backup(path: Path):
    if not path.exists():
        return
    bp = path.with_suffix(path.suffix + ".backup")
    try:
        shutil.copy(path, bp)
        print(f"[INFO] backup {path.name} -> {bp.name}")
    except Exception as e:
        print(f"[WARN] backup failed for {path}: {e}")

def _load_jsonl(path: Path) -> List[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as fh:
        for L in fh:
            try:
                rows.append(json.loads(L))
            except Exception:
                continue
    return rows

def _find_pids_in_text(text: str) -> List[str]:
    return list(set(re.findall(r"\b(P\d{1,6})\b", (text or "").upper())))

def _norm_id(val: Optional[str], kind: str) -> Optional[str]:
    if not val:
        return None
    v = str(val).strip().upper().replace(" ", "")
    if not v:
        return None
    if kind == "client":
        return v if v.startswith("C") else ("C"+v if v.isdigit() else v)
    if kind == "project":
        return v if v.startswith("P") else ("P"+v if v.isdigit() else v)
    return v

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

def _embed_in_batches(embedder: Embedder, texts: List[str]) -> List[List[float]]:
    out: List[List[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i+BATCH_SIZE]
        vecs = embedder.embed(batch)
        out.extend(vecs)
    return out

def _select_csvs(data_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
    # Kies de meest recent gewijzigde clients/projects CSV in DATA_DIR
    candidates = sorted(data_dir.glob("*.csv"))
    clients = [c for c in candidates if any(k in c.name.lower() for k in ["client", "klant"])]
    projects = [p for p in candidates if "project" in p.name.lower()]
    clients_csv = max(clients, key=lambda p: p.stat().st_mtime) if clients else None
    projects_csv = max(projects, key=lambda p: p.stat().st_mtime) if projects else None
    return clients_csv, projects_csv

# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────
def main():
    print("[START] reassign_unknown")
    _debug_paths()

    if not INDEX_DIR.exists():
        print("[ERROR] index dir missing:", INDEX_DIR); return

    # Zoek UNKNOWN index files
    unknown_json_files = sorted(INDEX_DIR.glob("index_UNKNOWN*.jsonl"))
    if not unknown_json_files:
        print("[DONE] no UNKNOWN index files found.")
        return
    print("[INFO] UNKNOWN files:", [p.name for p in unknown_json_files])

    # Backups van UNKNOWN bronnen
    for uj in unknown_json_files:
        _backup(uj)

    # Load UNKNOWN rows
    all_rows: List[dict] = []
    for uj in unknown_json_files:
        rows = _load_jsonl(uj)
        if rows:
            all_rows.extend(rows)
    if not all_rows:
        print("[DONE] no rows in UNKNOWN files.")
        return
    print(f"[INFO] loaded UNKNOWN rows: {len(all_rows)}")

    # CSV mapping
    clients_csv, projects_csv = _select_csvs(DATA_DIR)
    print("[INFO] clients_csv:", clients_csv, "projects_csv:", projects_csv)
    proj_to_clients: Dict[str, List[str]] = {}
    client_to_projects: Dict[str, List[str]] = {}
    if clients_csv and projects_csv:
        proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder=None)
        for pid, clist in proj_to_clients.items():
            for c in clist:
                client_to_projects.setdefault(_norm_id(c, "client"), []).append(_norm_id(pid, "project"))
    else:
        print("[WARN] CSVs not found — proj_to_clients will be empty")

    # Prepare embedder
    embedder = Embedder()

    # Accumulate per target (client, pid)
    batches: Dict[Tuple[str, str], List[dict]] = {}
    duplicates, skipped = 0, 0

    for r in all_rows:
        text = r.get("text") or ""
        fn = (r.get("filename") or "")
        fp = (r.get("filepath") or "")

        resolved_pids: Set[str] = set()

        # 1) expliciet veld
        rid_pid = r.get("project_id")
        if rid_pid and rid_pid.upper() != "UNKNOWN":
            resolved_pids.add(_norm_id(rid_pid, "project"))

        # 2) bestandsnaam / pad
        m_fn_p = re.search(r"(P\d{1,6})", fn.upper())
        if m_fn_p:
            resolved_pids.add(m_fn_p.group(1))
        for anc in (Path(fp).parent, Path(fp).parent.parent if fp else None):
            if anc:
                m = re.search(r"(P\d{1,6})", anc.name.upper())
                if m:
                    resolved_pids.add(m.group(1))

        # 3) tekst
        for p in _find_pids_in_text(text):
            resolved_pids.add(p)

        # 4) mapping via client → project(s)
        rid_client = _norm_id(r.get("client_id"), "client")
        if rid_client and client_to_projects.get(rid_client):
            for pid in client_to_projects[rid_client]:
                resolved_pids.add(pid)

        if not resolved_pids:
            skipped += 1
            continue

        # Targets opbouwen
        for pid in sorted(resolved_pids):
            clients = proj_to_clients.get(pid) or ([rid_client] if rid_client else ["UNKNOWN"])
            for client in clients:
                tgt = (_norm_id(client, "client") or "UNKNOWN", _norm_id(pid, "project") or "UNKNOWN")
                meta = dict(r)
                meta["client_id"] = tgt[0]
                meta["project_id"] = tgt[1]
                batches.setdefault(tgt, []).append(meta)

    moved = 0

    for (client_id, pid), metas in batches.items():
        # Load bestaande index en dedupe idempotent
        rows_existing, emb_arr = load_index(client_id, pid)
        existing_keys = _build_existing_keys(rows_existing or [])

        new_metas: List[dict] = []
        for m in metas:
            k = _meta_key(m)
            if k in existing_keys:
                duplicates += 1
                continue
            new_metas.append(m)

        if not new_metas:
            continue

        if rows_existing and len(rows_existing) > MAX_ROWS_PER_TARGET:
            print(f"[WARN] target {client_id}/{pid} exceeds MAX_ROWS_PER_TARGET; skipping {len(new_metas)} metas.")
            skipped += len(new_metas)
            continue

        # Embed in batches
        try:
            embs = _embed_in_batches(embedder, [m["text"] for m in new_metas])
        except Exception as e:
            print(f"[ERROR] embedding failed for {client_id}/{pid}: {e}")
            skipped += len(new_metas)
            continue

        # Backups van targets vóór save
        target_json = INDEX_DIR / f"index_{client_id}_{pid}.jsonl"
        target_emb = INDEX_DIR / f"emb_{client_id}_{pid}.npy"
        _backup(target_json)
        _backup(target_emb)

        # Concat & save via save_index (zorgt voor JSON list opslag; emb als list)
        try:
            if rows_existing and emb_arr is not None and len(rows_existing) == len(emb_arr):
                # concat
                if _np is not None:
                    old = _np.array(emb_arr, dtype=_np.float32)
                    new = _np.array(embs, dtype=_np.float32)
                    if old.shape[1] != new.shape[1]:
                        raise ValueError(f"Embedding dimension mismatch for {client_id}/{pid}: old={old.shape}, new={new.shape}")
                    merged = _np.vstack([old, new]).tolist()
                else:
                    # numpy niet beschikbaar — blind concat lists
                    merged = (emb_arr or []) + embs
                save_index(client_id, pid, (rows_existing + new_metas), merged)
            else:
                # nieuw
                save_index(client_id, pid, new_metas, embs)
        except Exception as e:
            print(f"[ERROR] saving index failed for {client_id}/{pid}: {e}")
            skipped += len(new_metas)
            continue

        moved += len(new_metas)
        print(f"[INFO] appended {len(new_metas)} -> index_{client_id}_{pid}.jsonl")

    print(f"[DONE] moved={moved} duplicates_skipped={duplicates} other_skipped={skipped} targets={len(batches)}")

if __name__ == "__main__":
    main()
