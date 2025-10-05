# runner.py
"""
Index-runner met deterministische CSV-selectie, preflight logging, en optionele filters via env.
"""
from pathlib import Path
import os

from .embedder_modular import Embedder
from .csv_indexer import index_clients_projects_from_csv
from .doc_indexer import index_documents
from ..utils import DATA_DIR

# Optionele filters (env)
INCLUDE_EXTS = os.environ.get("RUNNER_INCLUDE_EXTS", ".pdf,.docx,.txt").split(",")
MAX_FILES = int(os.environ.get("RUNNER_MAX_FILES", "0"))  # 0 = geen limiet

def _select_csvs(data_dir: Path):
    candidates = sorted(data_dir.glob("*.csv"))
    clients = [c for c in candidates if any(k in c.name.lower() for k in ["client", "klant"])]
    projects = [p for p in candidates if "project" in p.name.lower()]
    clients_csv = max(clients, key=lambda p: p.stat().st_mtime) if clients else None
    projects_csv = max(projects, key=lambda p: p.stat().st_mtime) if projects else None
    return clients_csv, projects_csv

def main():
    print("[START] index runner. data dir:", DATA_DIR)

    clients_csv, projects_csv = _select_csvs(DATA_DIR)
    if not clients_csv or not projects_csv:
        raise SystemExit("Zorg dat clients.csv en projects.csv in data/ staan (meest recente worden automatisch gekozen).")
    print("[INFO] using clients_csv:", clients_csv.name)
    print("[INFO] using projects_csv:", projects_csv.name)

    # Init embedder (print gekozen backend/model)
    embedder = Embedder()

    # CSV → mapping
    proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder=None)
    print(f"[INFO] mapping loaded: projects={len(proj_to_clients)}")

    # Run indexering
    total = index_documents(DATA_DIR, proj_to_clients, embedder)
    print("[DONE] total chunks created:", total)

if __name__ == "__main__":
    main()
