# src/.../chatbot/indexer/csv_indexer.py
from pathlib import Path
from typing import Dict, List
import pandas as pd
import numpy as _np  # only for stacking later

from ..utils import CHUNK_SIZE, CHUNK_OVERLAP, row_to_text
from .chunker import chunk_text_simple
from .embedder_modular import Embedder
from ..index_utils import load_index, save_index

def index_clients_projects_from_csv(clients_csv: Path, projects_csv: Path, embedder: Embedder) -> Dict[str, List[str]]:
    df_clients = pd.read_csv(clients_csv, dtype=str).fillna("")
    df_projects = pd.read_csv(projects_csv, dtype=str).fillna("")

    if "KlantID" not in df_clients.columns or "ProjectID" not in df_clients.columns:
        raise SystemExit("clients CSV moet kolommen 'KlantID' en 'ProjectID' bevatten")
    if "ProjectID" not in df_projects.columns:
        raise SystemExit("projects CSV moet kolom 'ProjectID' bevatten")

    proj_to_clients = {}
    for _, r in df_clients.iterrows():
        cid = str(r["KlantID"]).strip()
        pid = str(r["ProjectID"]).strip()
        if not cid or not pid:
            continue
        text = row_to_text("Client record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        metas = [{"text": c, "client_id": cid, "project_id": pid, "source": "clients_csv", "chunk_index": i}
                 for i, c in enumerate(chunks)]
        try:
            embs = embedder.embed([m["text"] for m in metas])
        except Exception as e:
            print(f"[ERROR] embed clients row {cid}/{pid}: {e}")
            continue

        rows, emb_arr = load_index(cid, pid)
        if rows and emb_arr is not None:
            new_rows = rows + metas
            new_emb = _np.vstack([emb_arr, _np.array(embs, dtype=_np.float32)])
            save_index(cid, pid, new_rows, new_emb.tolist())
        else:
            save_index(cid, pid, metas, embs)

        proj_to_clients.setdefault(pid, []).append(cid)

    # index projects (duplicate per client)
    for _, r in df_projects.iterrows():
        pid = str(r["ProjectID"]).strip()
        if not pid:
            continue
        text = row_to_text("Project record", r.to_dict())
        chunks = chunk_text_simple(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        clients = proj_to_clients.get(pid, []) or [""]
        metas_base = [{"text": c, "project_id": pid, "source": "projects_csv", "chunk_index": i}
                      for i, c in enumerate(chunks)]
        for cid in clients:
            metas = []
            for m in metas_base:
                mm = m.copy()
                mm["client_id"] = cid or "UNKNOWN"
                metas.append(mm)
            try:
                embs = embedder.embed([m["text"] for m in metas])
            except Exception as e:
                print(f"[ERROR] embed project {pid} for client {cid}: {e}")
                continue

            rows, emb_arr = load_index(cid or "UNKNOWN", pid)
            if rows and emb_arr is not None:
                new_rows = rows + metas
                new_emb = _np.vstack([emb_arr, _np.array(embs, dtype=_np.float32)])
                save_index(cid or "UNKNOWN", pid, new_rows, new_emb.tolist())
            else:
                save_index(cid or "UNKNOWN", pid, metas, embs)

    return proj_to_clients
