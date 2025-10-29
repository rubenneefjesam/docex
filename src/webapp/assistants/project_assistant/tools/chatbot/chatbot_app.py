# chatbot_app.py
"""
Chatbot applicatiemodule — beheert indexering, validatie en queryfunctionaliteit
voor de Client/Project Chat tool.

Deze versie:
- voorkomt dubbele Streamlit-processen;
- detecteert automatisch of ze binnen Streamlit draait;
- kan standalone of via registry worden gestart.
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
# UI runner
# -------------------------------------------------------
def run(*args: Any, **kwargs: Any) -> Any:
    """
    Start de Streamlit UI.
    - Als we al binnen Streamlit draaien (STREAMLIT_ACTIVE=1): alleen de UI starten.
    - Anders: zelfstandig via `streamlit run ui.py`.
    """
    if os.environ.get("STREAMLIT_ACTIVE") == "1":
        # Binnen Streamlit — alleen de UI uitvoeren.
        return ui_run(*args, **kwargs)

    try:
        import subprocess

        ui_file = Path(__file__).resolve().parent / "ui.py"
        if not ui_file.exists():
            raise FileNotFoundError(f"UI-bestand niet gevonden: {ui_file}")

        print("🚀 Start Chatbot UI (standalone)...")
        subprocess.run(["streamlit", "run", str(ui_file)], check=True)

    except KeyboardInterrupt:
        print("🛑 Chatbot UI handmatig gestopt.")
    except Exception as e:
        print(f"⚠️  Fout bij starten van Streamlit UI: {e}")
        raise


# -------------------------------------------------------
# Aliassen voor registry-compatibiliteit
# -------------------------------------------------------
app = run
main = run
render = run
