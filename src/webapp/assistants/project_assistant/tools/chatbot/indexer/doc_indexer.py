# src/.../chatbot/indexer/doc_indexer.py
from pathlib import Path
from typing import Dict, List, Optional
import re
import numpy as _np

from .io_utils_extended import find_files_in_dir, read_and_meta
from .chunker import chunk_by_sentences, chunk_text_simple
from .index_utils import load_index, save_index
from .embedder_modular import Embedder
from ..utils import CHUNK_SIZE, CHUNK_OVERLAP

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

def index_documents(data_dir: Path, proj_to_clients: Dict[str, List[str]], embedder: Embedder) -> int:
    files = find_files_in_dir(data_dir, exts=[".pdf", ".docx", ".txt"])
    total_chunks = 0
    skipped = 0

    for f in files:
        text, meta = read_and_meta(f)
        if not (text or "").strip():
            print(f"[WARN] geen tekst in {f}, skipping")
            skipped += 1
            continue

        cid = meta.get("client_id")
        pid = meta.get("project_id")

        if not pid:
            pid = _find_pid_from_ancestors(Path(meta.get("filepath", str(f))))
            if pid:
                print(f"[INFO] pid from folder for {f.name}: {pid}")

        if not pid:
            pid = _find_pid_in_text(text)
            if pid:
                print(f"[INFO] pid in text for {f.name}: {pid}")

        if not pid:
            pid = "UNKNOWN"
            print(f"[INFO] no PID for {f.name}, indexing under UNKNOWN")

        clients = proj_to_clients.get(pid, [])
        if not clients and cid:
            clients = [cid]
        if not clients:
            clients = ["UNKNOWN"]

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
                print(f"[ERROR] embed failed for {f.name}: {e}")
                skipped += 1
                continue

            rows, emb_arr = load_index(client or "UNKNOWN", pid)
            if rows and emb_arr is not None:
                new_rows = rows + metas
                new_emb = _np.vstack([emb_arr, _np.array(embs, dtype=_np.float32)])
                save_index(client or "UNKNOWN", pid, new_rows, new_emb.tolist())
            else:
                save_index(client or "UNKNOWN", pid, metas, embs)

            total_chunks += len(metas)

    print(f"[INFO] documents indexed. chunks: {total_chunks}, skipped files: {skipped}")
    return total_chunks
