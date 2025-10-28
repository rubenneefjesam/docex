# chatbot_app.py

from typing import Any, Dict, List
from .index_utils import build_index
from .embed_utils import index_exists, retrieve
from .utils import metadata_exists
from .ui import run as ui_run

def index(client_id: str, project_id: str) -> Dict[str, Any]:
    """
    Indexeer alle documenten voor de gegeven client/project.
    Retourneert dict met:
      - success: bool
      - indexed_chunks: int
    Gooit FileNotFoundError als client/project niet bestaat.
    """
    if not metadata_exists(client_id, project_id):
        raise FileNotFoundError(f"Geen data-folder voor {client_id}/{project_id}")
    n = build_index(client_id, project_id)
    return {"success": True, "indexed_chunks": n}

def validate(client_id: str, project_id: str) -> Dict[str, Any]:
    """
    Controleer of client/project bestaat en of er een index is.
    Retourneert dict met:
      - exists: bool
      - indexed: bool
      - found_chunks: int
    """
    exists = metadata_exists(client_id, project_id)
    indexed = exists and index_exists(client_id, project_id)
    found = len(retrieve(client_id, project_id, q_emb=[], top_k=0)) if indexed else 0
    return {"exists": exists, "indexed": indexed, "found_chunks": found}

def query(client_id: str, project_id: str, question: str) -> List[Dict[str, Any]]:
    """
    Embed de vraag, doe een retrieve en geef de resultaten terug.
    Vervang `...` door je eigen embed-logica.
    """
    # TODO: embed vraag
    q_emb: List[float] = ...  
    return retrieve(client_id, project_id, q_emb)

def run(*args: Any, **kwargs: Any) -> Any:
    """
    Primary entrypoint: start de UI. 
    Alle interacties (index, validate, query) gebeuren via callbacks in ui.py.
    """
    return ui_run(*args, **kwargs)

# alias-namen voor registries
app = run
main = run
render = run
