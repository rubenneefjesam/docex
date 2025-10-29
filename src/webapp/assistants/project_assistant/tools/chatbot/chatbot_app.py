"""
Chatbot applicatiemodule — beheert indexering, validatie en queryfunctionaliteit
voor de Client/Project Chat tool.

Deze versie:
- voorkomt dubbele Streamlit-processen;
- detecteert automatisch of ze binnen Streamlit draait;
- start enkel de UI als onderdeel van het hoofdproces.
"""

from typing import Any, Dict, List
from pathlib import Path
import os

# -------------------------------------------------------
# Lokale imports
# -------------------------------------------------------
from .index_utils import build_index
from .embed_utils import index_exists, retrieve
from .utils import metadata_exists
from .ui import run as ui_run


# -------------------------------------------------------
# Kernfunctionaliteit
# -------------------------------------------------------
def index(client_id: str, project_id: str) -> Dict[str, Any]:
    """
    Bouw of vernieuw de index voor een client/project.
    """
    if not metadata_exists(client_id, project_id):
        raise FileNotFoundError(f"Geen data-folder voor {client_id}/{project_id}")
    n = build_index(client_id, project_id)
    return {"success": True, "indexed_chunks": n}


def validate(client_id: str, project_id: str) -> Dict[str, Any]:
    """
    Controleer of client/project bestaat en of er een geldige index aanwezig is.
    """
    exists = metadata_exists(client_id, project_id)
    indexed = exists and index_exists(client_id, project_id)
    found = len(retrieve(client_id, project_id, q_emb=[], top_k=0)) if indexed else 0
    return {
        "exists": exists,
        "indexed": indexed,
        "found_chunks": found,
    }


def query(client_id: str, project_id: str, question: str) -> List[Dict[str, Any]]:
    """
    Dummy queryfunctie — embed de vraag en haal relevante context op.
    (In de toekomst vervangen door echte embed-logica.)
    """
    q_emb: List[float] = []  # TODO: implement real embedding logic
    return retrieve(client_id, project_id, q_emb)


# -------------------------------------------------------
# UI runner (enkel via bestaande Streamlit sessie)
# -------------------------------------------------------
def run(*args: Any, **kwargs: Any) -> Any:
    """
    Start de Streamlit UI.

    Detecteert automatisch of we al binnen Streamlit draaien
    (via omgevingsvariabelen). Zo ja: voer enkel de UI uit.
    """
    if any(k in os.environ for k in ["STREAMLIT_SERVER_PORT", "STREAMLIT_RUNTIME", "STREAMLIT_ACTIVE"]):
        os.environ["STREAMLIT_ACTIVE"] = "1"
        return ui_run(*args, **kwargs)

    # Als iemand dit script direct uitvoert (zeldzaam): fallback
    print("ℹ️  Chatbot wordt binnen app.py verwacht — geen tweede proces gestart.")
    os.environ["STREAMLIT_ACTIVE"] = "1"
    return ui_run(*args, **kwargs)


# -------------------------------------------------------
# Aliassen voor registry-compatibiliteit
# -------------------------------------------------------
app = run
main = run
render = run
