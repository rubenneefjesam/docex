# src/.../indexer/clients_indexer.py
from pathlib import Path
import pandas as pd
from typing import Dict, List
from .config        import CLIENT_ID_HEADER_CANDIDATES, PROJECT_ID_HEADER_CANDIDATES, DEDUPE_WITH_HASH
from .headers       import find_header
from .embeddings    import safe_to_float32_list, vstack_defensive
from ..index_utils  import load_index, save_index
from .utils         import row_to_text
from .chunker       import chunk_text_simple
from .id_utils      import parse_ids_from_filename_or_path
from typing         import Any

def index_clients_projects_from_csv(
    clients_csv: Path,
    projects_csv: Path,
    embedder: Any
) -> Dict[str, List[str]]:
    # 1) lees CSV’s, bepaal client_id_col en project_id_col
    df_clients = pd.read_csv(clients_csv, dtype=str).fillna("")
    df_projects= pd.read_csv(projects_csv, dtype=str).fillna("")
    client_col = find_header(list(df_clients.columns), CLIENT_ID_HEADER_CANDIDATES)
    proj_col_c = find_header(list(df_clients.columns), PROJECT_ID_HEADER_CANDIDATES)
    proj_col_p = find_header(list(df_projects.columns), PROJECT_ID_HEADER_CANDIDATES)
    if not client_col or not (proj_col_c or proj_col_p):
        raise ValueError("CSV mis column")

    proj_to_clients: Dict[str, List[str]] = {}
    for idx, row in df_clients.iterrows():
        raw_cid = row[client_col].strip()
        raw_pid = row[proj_col_c or proj_col_p].strip()
        if not raw_cid or not raw_pid:
            continue
        cid = parse_ids_from_filename_or_path(raw_cid)[0] or raw_cid.upper()
        pid = parse_ids_from_filename_or_path(raw_pid)[1] or raw_pid.upper()

        # **record mapping**:
        proj_to_clients.setdefault(pid, []).append(cid)

        # embed + save index … gebruik safe_to_float32_list en vstack_defensive
        # … (hier komt jouw bestaande embed/merge logic)
    # teruggeven
    return proj_to_clients
