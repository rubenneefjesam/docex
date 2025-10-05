import os
import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# relative/local imports (indexer package)
from .io_utils_extended import find_files_in_dir, read_and_meta, parse_ids_from_filename
from .chunker import chunk_text_simple, chunk_by_sentences
from .embedder_modular import Embedder
from .index_utils import load_index, save_index

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


def row_to_text(prefix: str, row: Dict) -> str:
    parts = [f"{k}: {v}" for k, v in row.items()]
    return f"{prefix}\n" + "\n".join(parts)


def index_clients_projects_from_csv(clients_csv: Path, projects_csv: Path, embedder: Embedder) -> Dict[str, List[str]]:
    """
    Index client rows and project rows from CSVs.
    Returns mapping: project_id -> list of client_ids
    """
    df_clients = pd.read_csv(clients_csv, dtype=str).fillna("")
    df_projects = pd.read_csv(projects_csv, dtype=str).fillna("")

    if "KlantID" not in df_clients.columns or "ProjectID" not in df_clients.columns:
        raise SystemExit("clients CSV moet kolommen 'KlantID' en 'ProjectID' bevatten")
    if "ProjectID" not in df_projects.columns:
        raise SystemExit("projects CSV moet kolom 'ProjectID' bevatten")

    proj_to_clients: Dict[str, List[str]] = {}
    clients_indexed = 0

    # index client rows
    for _, r in df_clients.iterrows():
        cid = str(r["KlantID"]).strip()
        pid = str(r["ProjectID"]).strip()
        if not cid or not pid:
            continue
        text = row_to_text("Client record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        metas = [
            {"text": c, "client_id": cid, "project_id": pid, "source": "clients_csv", "chunk_index": i}
            for i, c in enumerate(chunks)
        ]
        try:
            embs = embedder.embed([m["text"] for m in metas])
        except Exception as e:
            print(f"[ERROR] embedding clients CSV row {cid}/{pid}: {e}")
            continue

        rows, emb_arr = load_index(cid, pid)
        if rows and emb_arr is not None:
            # merge
            new_rows = rows + metas
            if np is None:
                raise RuntimeError("Numpy vereist voor embeddings opslaan")
            new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
            save_index(cid, pid, new_rows, new_emb.tolist())
        else:
            save_index(cid, pid, metas, embs)
        proj_to_clients.setdefault(pid, []).append(cid)
        clients_indexed += 1

    # index projects, duplicate per client
    projects_indexed = 0
    for _, r in df_projects.iterrows():
        pid = str(r["ProjectID"]).strip()
        if not pid:
            continue
        text = row_to_text("Project record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        clients = proj_to_clients.get(pid, []) or [""]
        metas_base = [
            {"text": c, "project_id": pid, "source": "projects_csv", "chunk_index": i}
            for i, c in enumerate(chunks)
        ]
        for cid in clients:
            metas = []
            for m in metas_base:
                mm = m.copy()
                mm["client_id"] = cid or "UNKNOWN"
                metas.append(mm)
            try:
                embs = embedder.embed([m["text"] for m in metas])
            except Exception as e:
                print(f"[ERROR] embedding project {pid} for client {cid}: {e}")
                continue

            rows, emb_arr = load_index(cid or "UNKNOWN", pid)
            if rows and emb_arr is not None:
                new_rows = rows + metas
                if np is None:
                    raise RuntimeError("Numpy vereist voor embeddings opslaan")
                new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
                save_index(cid or "UNKNOWN", pid, new_rows, new_emb.tolist())
            else:
                save_index(cid or "UNKNOWN", pid, metas, embs)
        projects_indexed += 1

    print(f"[INFO] clients indexed: {clients_indexed}, projects indexed: {projects_indexed}")
    return proj_to_clients


def _find_pid_from_ancestors(path: Path) -> Optional[str]:
    """Search the parent and grandparent folder names for P\d+ patterns."""
    for anc in (path.parent, path.parent.parent):
        if not anc:
            continue
        m = re.search(r"(P\d{1,6})", anc.name.upper())
        if m:
            return m.group(1)
    return None


def _find_pid_in_text(text: str) -> Optional[str]:
    m = re.search(r"\b(P\d{1,6})\b", text.upper())
    if m:
        return m.group(1)
    return None


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

        # fallback 1: try to find project id from ancestor folders
        if not pid:
            pid = _find_pid_from_ancestors(Path(meta.get("filepath", str(f))))
            if pid:
                meta["project_id"] = pid
                print(f"[INFO] PID gevonden via folder voor {f.name}: {pid}")

        # fallback 2: try to find in text
        if not pid:
            pid = _find_pid_in_text(text)
            if pid:
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

        for client in clients:
            metas = []
            for i, c in enumerate(chunks):
                metas.append({
                    "text": c,
                    "client_id": client or "UNKNOWN",
                    "project_id": pid,
                    "filename": f.name,
                    "filepath": str(f),
                    "chunk_index": i,
                    "source": "doc_file",
                })

            try:
                embs = embedder.embed([m["text"] for m in metas])
            except Exception as e:
                print(f"[ERROR] Embedding mislukt voor {f.name}: {e}")
                skipped.append((str(f), "embed_fail", str(e)))
                continue

            # merge with existing index if present
            rows, emb_arr = load_index(client or "UNKNOWN", pid)
            if rows and emb_arr is not None:
                if np is None:
                    raise RuntimeError("Numpy vereist voor embeddings opslaan")
                new_rows = rows + metas
                new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
                save_index(client or "UNKNOWN", pid, new_rows, new_emb.tolist())
            else:
                save_index(client or "UNKNOWN", pid, metas, embs)

            total_chunks += len(metas)

    print(f"[INFO] Document indexing complete. Chunks created: {total_chunks}. Skipped items: {len(skipped)}")
    if skipped:
        for s in skipped[:20]:
            print(" -", s)


def main():
    print("[START] Index script. Data dir:", DATA_DIR)
    if not DATA_DIR.exists():
        raise SystemExit("Data dir bestaat niet: " + str(DATA_DIR))

    # find CSVs
    clients_csv = None
    projects_csv = None
    for f in sorted(DATA_DIR.glob("*.csv")):
        n = f.name.lower()
        if "client" in n or "klant" in n:
            clients_csv = f
        if "project" in n:
            projects_csv = f

    if not clients_csv or not projects_csv:
        raise SystemExit("Zorg dat clients.csv en projects.csv in data/ staan")

    print("[INFO] Found:", clients_csv.name, projects_csv.name)
    embedder = Embedder()

    proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder)
    index_documents(DATA_DIR, proj_to_clients, embedder)
    print("[DONE] Indexing finished. Index files written to:", INDEX_DIR)


if __name__ == "__main__":
    main()