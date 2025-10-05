# src/.../chatbot/indexer/runner.py
from pathlib import Path
from .embedder_modular import Embedder
from .csv_indexer import index_clients_projects_from_csv
from .doc_indexer import index_documents
from ..utils import DATA_DIR

def main():
    print("[START] index runner. data dir:", DATA_DIR)
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

    embedder = Embedder()
    proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder)
    total = index_documents(DATA_DIR, proj_to_clients, embedder)
    print("[DONE] total chunks created:", total)

if __name__ == "__main__":
    main()
