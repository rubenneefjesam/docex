# src/.../indexer/config.py
import os
from pathlib import Path

BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 600))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))
REVIEW_QUEUE_CSV = os.environ.get("INDEX_REVIEW_QUEUE_CSV", "index_csvs_review_queue.csv")
DEDUPE_WITH_HASH = os.environ.get("INDEX_DEDUPE_WITH_HASH", "1") == "1"

CLIENT_ID_HEADER_CANDIDATES = ["klantid", "klant_id", "clientid", "client_id", "klant", "client"]
PROJECT_ID_HEADER_CANDIDATES = ["projectid", "project_id", "project", "project_id"]
