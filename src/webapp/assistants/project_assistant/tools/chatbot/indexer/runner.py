# runner.py
from pathlib import Path
import os, csv

from .embedder_modular import Embedder
from .doc_indexer import index_documents
from ..utils import DATA_DIR

def _select_csvs(data_dir: Path):
    candidates = sorted(data_dir.glob("*.csv"))
    clients = [c for c in candidates if any(k in c.name.lower() for k in ["client", "klant"])]
    projects = [p for p in candidates if "project" in p.name.lower()]
    clients_csv = max(clients, key=lambda p: p.stat().st_mtime) if clients else None
    projects_csv = max(projects, key=lambda p: p.stat().st_mtime) if projects else None
    return clients_csv, projects_csv

def _fallback_index_clients_projects_from_csv(clients_csv, projects_csv):
    """Minimale fallback als csv_indexer niet te importeren is."""
    def read(path: Path):
        with path.open(encoding="utf-8", errors="ignore") as fh:
            return list(csv.DictReader(fh))
    clients = read(Path(clients_csv))
    projects = read(Path(projects_csv))
    proj_to_clients = {}
    def norm(val, kind):
        if not val: return ""
        v = str(val).strip().upper().replace(" ", "")
        if kind == "client" and not v.startswith("C") and v.isdigit(): v = "C"+v
        if kind == "project" and not v.startswith("P") and v.isdigit(): v = "P"+v
        return v
    # map uit clients
    for r in clients:
        cid = (r.get("KlantID") or r.get("ClientID") or r.get("klantid") or r.get("client_id") or r.get("Klant") or "").strip()
        pid = (r.get("ProjectID") or r.get("project") or r.get("project_id") or r.get("ProjectNr") or "").strip()
        cid_n, pid_n = norm(cid, "client"), norm(pid, "project")
        if cid_n and pid_n:
            proj_to_clients.setdefault(pid_n, [])
            if cid_n not in proj_to_clients[pid_n]:
                proj_to_clients[pid_n].append(cid_n)
    # zorg dat elk project bestaat
    for r in projects:
        pid = (r.get("ProjectID") or r.get("project") or r.get("project_id") or r.get("ProjectNr") or "").strip()
        pid_n = norm(pid, "project")
        if pid_n:
            proj_to_clients.setdefault(pid_n, proj_to_clients.get(pid_n, []))
    print(f"[csv_indexer:fallback] mapped_projects={len(proj_to_clients)}")
    return proj_to_clients

def main():
    print("[START] index runner. data dir:", DATA_DIR)

    clients_csv, projects_csv = _select_csvs(DATA_DIR)
    if not clients_csv or not projects_csv:
        raise SystemExit("Zorg dat clients.csv en projects.csv in data/ staan (meest recente worden automatisch gekozen).")
    print("[INFO] using clients_csv:", clients_csv.name)
    print("[INFO] using projects_csv:", projects_csv.name)

    # Init embedder
    embedder = Embedder()

    # Probeer officiële csv_indexer, anders fallback
    try:
        from .csv_indexer import index_clients_projects_from_csv
        proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder=None)
    except Exception as e:
        print(f"[WARN] csv_indexer import/use failed: {e} — using fallback loader.")
        proj_to_clients = _fallback_index_clients_projects_from_csv(clients_csv, projects_csv)

    print(f"[INFO] mapping loaded: projects={len(proj_to_clients)}")

    total = index_documents(DATA_DIR, proj_to_clients, embedder)
    print("[DONE] total chunks created:", total)

if __name__ == "__main__":
    main()
