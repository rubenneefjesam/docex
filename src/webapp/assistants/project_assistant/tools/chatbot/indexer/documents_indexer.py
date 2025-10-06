# src/.../indexer/documents_indexer.py
from pathlib import Path
from typing import Dict, List, Any
from .config       import CHUNK_SIZE, CHUNK_OVERLAP, DEDUPE_WITH_HASH
from .utils        import row_to_text
from .chunker      import chunk_text_simple, chunk_by_sentences
from .embeddings   import safe_to_float32_list, vstack_defensive
from .id_utils     import parse_ids_from_filename_or_path, find_pid_in_text, find_pid_from_ancestors
from ..index_utils import load_index, save_index
from .io_utils_extended import find_files_in_dir, read_and_meta

def index_documents(
    data_dir: Path,
    proj_to_clients: Dict[str, List[str]],
    embedder: Any
) -> int:
    total = 0
    files = find_files_in_dir(data_dir, exts=[".txt", ".pdf", ".docx"])
    for f in files:
        text, meta = read_and_meta(f)
        # bepaal pid, cid, fallback logic
        # chunk & embed met safe_to_float32_list
        # save index met vstack_defensive
        # verhoog total
    return total
