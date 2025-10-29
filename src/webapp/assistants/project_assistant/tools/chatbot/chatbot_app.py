# chatbot_app.py
"""
Chatbot applicatiemodule — start de lokale Streamlit-UI,
en beheert indexering, validatie en query-functionaliteit.

Deze versie voorkomt dubbele Streamlit-processen.
"""

from typing import Any, Dict, List
from pathlib import Path

from .index_utils import build_index
from .embed_utils import index_exists, retrieve
from .utils import metadata_exists
from .ui import run as ui_run


# -------------------------------------------------------
# Core functies
# -------------------------------------------------------
def index(client_id: str, project_id: str) -> Dict[str, Any]:
    """Indexeer alle documenten voor de gegeven client/project."""
    if not metadata_exists(client_id, project_id):
        raise FileNotFoundError(f"Geen data-folder voor {client_id}/{project_id}")
    n = build_index(client_id, project_id)
    return {"success": True, "indexed_chunks": n}


def validate(client_id: str, project_id: str) -> Dict[str, Any]:
    """Controleer of client/project bestaat en of er een index is."""
    exists = metadata_exists(client_id, project_id)
    indexed = exists and index_exists(client_id, project_id)
    found = len(retrieve(client_id, project_id, q_emb=[], top_k=0)) if indexed else 0
    return {"exists": exists, "indexed": indexed, "found_chunks": found}


def query(client_id: str, project_id: str, question: str) -> List[Dict[str, Any]]:
    """Haal resultaten op voor een vraag."""
    q_emb: List[float] = []  # TODO: vervang door echte embeddinglogica
    return retrieve(client_id, project_id, q_emb)


# -------------------------------------------------------
# Streamlit UI Runner
# -------------------------------------------------------
def run(*args: Any, **kwargs: Any) -> Any:
    """
    Start de UI, tenzij deze module al door een Streamlit-proces
    wordt aangestuurd (zoals via src/webapp/app.py).
    """
    import os

    if os.environ.get("STREAMLIT_ACTIVE") == "1":
        # We draaien al binnen Streamlit — roep enkel de UI aan.
        return ui_run(*args, **kwargs)

    # Anders (losse uitvoering, bij handmatig `python chatbot_app.py`)
    try:
        import subprocess
        ui_file = Path(__file__).resolve().parent / "ui.py"
        subprocess.run(["streamlit", "run", str(ui_file)], check=True)
    except Exception as e:
        print(f"⚠️  Fout bij starten van Streamlit: {e}")
        raise


# -------------------------------------------------------
# Aliassen voor registry compatibility
# -------------------------------------------------------
app = run
main = run
render = run
