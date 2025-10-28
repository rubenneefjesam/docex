# src/webapp/assistants/project_assistant/tools/chatbot/index_builder.py
"""
Index Builder: leest ALLE documenten onder /data, maakt chunks + embeddings,
en schrijft per (ClientID, ProjectID) een index weg in /index.

Werkt met:
- io_utils.read_text_from_file / chunk_to_records
- embed_utils.Embedder
- index_utils.save_index

Regels voor ClientID/ProjectID:
- Eerst uit bestandsnaam (C###, P####).
- Zo niet: project_id wordt via Clients_*.csv opgezocht (kolommen: ClientID,ProjectID).
- Als niets gevonden: project_id = "PUNKNOWN".
"""

from pathlib import Path
import csv
from collections import defaultdict
from typing import Dict, List, Tuple

from . import io_utils, embed_utils, index_utils


# -------------------------------
# Helpers
# -------------------------------

def _load_client_to_project_map(data_dir: Path) -> Dict[str, str]:
    """
    Zoekt naar een Clients_*.csv in data_dir en leest ClientID->ProjectID mapping.
    Verwacht minimaal kolommen: ClientID, ProjectID
    """
    mapping: Dict[str, str] = {}
    for p in data_dir.glob("Clients_*rows*.csv"):
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cid = (row.get("ClientID") or "").strip()
                    pid = (row.get("ProjectID") or "").strip()
                    if cid and pid:
                        mapping[cid.upper()] = pid.upper()
        except Exception:
            continue
    return mapping


def _allowed(path: Path) -> bool:
    return path.suffix.lower() in {".pdf", ".docx", ".txt", ".csv"}


def _infer_ids_from_record(rec: dict, client_to_proj: Dict[str, str]) -> Tuple[str, str]:
    cid = (rec.get("client_id") or "").upper() or "CUNKNOWN"
    pid = (rec.get("project_id") or "").upper()
    if not pid and cid in client_to_proj:
        pid = client_to_proj[cid]
    if not pid:
        pid = "PUNKNOWN"
    return cid, pid


# -------------------------------
# Build
# -------------------------------

def build_all_indices(data_dir: Path, batch_size: int = 64) -> None:
    """
    Doorzoekt recursief alle bestanden onder data_dir, leest tekst, maakt records,
    groepeert per (client_id, project_id), embedt en slaat indices op.
    """
    data_dir = data_dir.resolve()
    idx_dir = index_utils.INDEX_DIR
    idx_dir.mkdir(parents=True, exist_ok=True)

    client_to_proj = _load_client_to_project_map(data_dir)

    # verzamel records per (client, project)
    buckets: Dict[Tuple[str, str], List[dict]] = defaultdict(list)

    # Loop door alle submappen maar sla de index/ en logs/ over
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        if "index" in path.parts or "logs" in path.parts:
            continue
        if not _allowed(path):
            continue

        text = io_utils.read_text_from_file(path)
        if not text.strip():
            continue

        records = io_utils.chunk_to_records(text, path)
        if not records:
            continue

        for r in records:
            cid, pid = _infer_ids_from_record(r, client_to_proj)
            r["client_id"], r["project_id"] = cid, pid
            buckets[(cid, pid)].append(r)

    # Embedder
    embedder = embed_utils.Embedder()

    # Voor elke (client, project) index bouwen
    for (cid, pid), recs in buckets.items():
        texts = [r["text"] for r in recs]
        embeddings: List[List[float]] = []

        # batchgewijs embedden
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            embeddings.extend(embedder.embed(chunk))

        # Opslaan
        index_utils.save_index(cid, pid, recs, embeddings)

        print(f"[index_builder] Saved index for {cid}/{pid}: {len(recs)} chunks → {index_utils.index_path(cid, pid)}")


# -------------------------------
# CLI
# -------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bouw indices uit /data.")
    parser.add_argument(
        "--data",
        type=str,
        required=False,
        help="Pad naar data-map. Default is de lokale 'data' map naast dit script.",
    )
    parser.add_argument("--batch", type=int, default=64, help="Embedding batch size (default 64).")
    args = parser.parse_args()

    base = Path(args.data).resolve() if args.data else (Path(__file__).parent / "data").resolve()
    build_all_indices(base, batch_size=args.batch)
    print("[index_builder] DONE")
