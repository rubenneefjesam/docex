# runner.py
from pathlib import Path
from typing import Optional
import os
import csv
import sys
import argparse
import logging

from .embedder_modular import Embedder
from .doc_indexer import index_documents
from ..utils import DATA_DIR  # keep existing project utility if available

logger = logging.getLogger("index_runner")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s runner %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
logger.setLevel(os.environ.get("RUNNER_LOG_LEVEL", "INFO"))


def _select_csvs(data_dir: Path, clients_override: Optional[Path] = None, projects_override: Optional[Path] = None):
    if clients_override and projects_override:
        return clients_override, projects_override

    candidates = sorted(data_dir.glob("*.csv"))
    clients = [c for c in candidates if any(k in c.name.lower() for k in ["client", "klant"])]
    projects = [p for p in candidates if "project" in p.name.lower()]

    # choose most recently modified as fallback
    clients_csv = max(clients, key=lambda p: p.stat().st_mtime) if clients else None
    projects_csv = max(projects, key=lambda p: p.stat().st_mtime) if projects else None
    return clients_csv, projects_csv


def _fallback_index_clients_projects_from_csv(clients_csv: Path, projects_csv: Path):
    """Minimal fallback (no embeddings) that tries to create mapping project -> [clients]."""
    def read(path: Path):
        with path.open(encoding="utf-8", errors="ignore") as fh:
            return list(csv.DictReader(fh))
    clients = read(clients_csv)
    projects = read(projects_csv)
    proj_to_clients = {}
    def norm(val, kind):
        if not val:
            return ""
        v = str(val).strip().upper().replace(" ", "")
        if kind == "client" and not v.startswith("C") and v.isdigit():
            v = "C" + v
        if kind == "project" and not v.startswith("P") and v.isdigit():
            v = "P" + v
        return v
    # map from clients CSV
    for r in clients:
        cid = (r.get("KlantID") or r.get("ClientID") or r.get("klantid") or r.get("client_id") or r.get("Klant") or "").strip()
        pid = (r.get("ProjectID") or r.get("project") or r.get("project_id") or r.get("ProjectNr") or "").strip()
        cid_n, pid_n = norm(cid, "client"), norm(pid, "project")
        if cid_n and pid_n:
            proj_to_clients.setdefault(pid_n, [])
            if cid_n not in proj_to_clients[pid_n]:
                proj_to_clients[pid_n].append(cid_n)
    # ensure project keys exist
    for r in projects:
        pid = (r.get("ProjectID") or r.get("project") or r.get("project_id") or r.get("ProjectNr") or "").strip()
        pid_n = norm(pid, "project")
        if pid_n:
            proj_to_clients.setdefault(pid_n, proj_to_clients.get(pid_n, []))
    logger.info(f"[csv_indexer:fallback] mapped_projects={len(proj_to_clients)}")
    return proj_to_clients


def main(argv=None):
    parser = argparse.ArgumentParser(description="Index runner")
    parser.add_argument("--data-dir", type=Path, default=Path(os.getenv("DATA_DIR", DATA_DIR)), help="Data directory with docs and CSVs")
    parser.add_argument("--clients", type=Path, help="Optional override clients CSV")
    parser.add_argument("--projects", type=Path, help="Optional override projects CSV")
    parser.add_argument("--dry-run", action="store_true", help="Do a dry run (no writes)")
    parser.add_argument("--skip-csv", action="store_true", help="Skip CSV indexing, only index documents using existing mapping")
    args = parser.parse_args(argv)

    data_dir: Path = args.data_dir
    if not data_dir.exists():
        logger.error("Data dir bestaat niet: %s", data_dir)
        sys.exit(2)

    logger.info("[START] index runner. data dir: %s", data_dir)

    # select CSVs
    clients_csv, projects_csv = _select_csvs(data_dir, clients_override=args.clients, projects_override=args.projects)
    if not args.skip_csv:
        if not clients_csv or not projects_csv:
            logger.error("Zorg dat clients.csv en projects.csv in data/ staan (of specificeer --clients/--projects).")
            sys.exit(2)
        logger.info("[INFO] using clients_csv: %s", clients_csv.name)
        logger.info("[INFO] using projects_csv: %s", projects_csv.name)
    else:
        logger.info("[INFO] skipping CSV-based indexing (--skip-csv set)")

    # Init embedder (used by CSV indexing and doc indexing)
    try:
        embedder = Embedder()
    except Exception as e:
        logger.error("Embedder init failed: %s", e)
        sys.exit(3)

    # Try to import the richer CSV indexer and run it (pass embedder)
    proj_to_clients = {}
    if not args.skip_csv:
        try:
            # prefer the improved csv indexer module
            from .index_csvs_modular import index_clients_projects_from_csv  # type: ignore
            proj_to_clients = index_clients_projects_from_csv(clients_csv, projects_csv, embedder)
        except Exception as e:
            logger.warning(f"[SWARN] csv_indexer import/use failed: {e} — using fallback loader.")
            proj_to_clients = _fallback_index_clients_projects_from_csv(clients_csv, projects_csv)

    logger.info("mapping loaded: projects=%d", len(proj_to_clients))

    # If dry-run: just report what would be done
    if args.dry_run:
        logger.info("[DRY-RUN] Would now index documents with mapping (projects=%d). Exiting.", len(proj_to_clients))
        return

    # Run document indexer
    try:
        total = index_documents(data_dir, proj_to_clients, embedder)
        logger.info("[DONE] total chunks created: %s", total)
    except Exception as e:
        logger.exception("Document indexing failed: %s", e)
        sys.exit(4)


if __name__ == "__main__":
    main()
