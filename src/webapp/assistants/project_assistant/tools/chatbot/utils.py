# src/.../chatbot/indexer/utils.py
from pathlib import Path
import os

BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"
INDEX_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 600))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))

def row_to_text(prefix: str, row: dict) -> str:
    parts = [f"{k}: {v}" for k, v in row.items()]
    return f"{prefix}\n" + "\n".join(parts)
