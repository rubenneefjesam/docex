# src/.../indexer/projects_indexer.py
from pathlib import Path
import pandas as pd
from typing import Dict, List, Any
from .config       import PROJECT_ID_HEADER_CANDIDATES, DEDUPE_WITH_HASH
from .headers      import find_header
from .embeddings   import safe_to_float32_list, vstack_defensive
from ..index_utils import load_index, save_index
from .utils        import row_to_text
from .chunker      import chunk_text_simple
from .id_utils     import parse_ids_from_filename_or_path

def index_projects_from_csv(
    projects_csv: Path,
    proj_to_clients: Dict[str, List[str]],
    embedder: Any
) -> int:
    df_projects = pd.read_csv(projects_csv, dtype=str).fillna("")
    proj_col = find_header(list(df_projects.columns), PROJECT_ID_HEADER_CANDIDATES)
    if not proj_col:
        raise ValueError("projects CSV mist een project-kolom")

    count = 0
    for idx, r in df_projects.iterrows():
        raw_pid = r[proj_col].strip()
        if not raw_pid:
            continue
        pid = parse_ids_from_filename_or_path(raw_pid)[1] or raw_pid.upper()
        clients = proj_to_clients.get(pid, ["UNKNOWN"])
        # embed per client, save via vstack_defensive
        # … jouw bestaande project-indexeer logic hier …
        count += 1
    return count
