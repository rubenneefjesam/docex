# chatbot_app.py
"""
Chatbot applicatiemodule — start de lokale Streamlit-UI,
en beheert indexering, validatie en query-functionaliteit.

Automatische padcorrectie voorkomt dubbele 'src/webapp' problemen.
"""

from typing import Any, Dict, List
from pathlib import Path
import subprocess

from .index_utils import build_index
from .embed_utils import index_exists, retrieve
from .utils import metadata_exists
from .ui import run as ui_run


# -------------------------------------------------------
# Core functies
# -------------------------------------------------------
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
    # TODO: eigen embedding logica toevoegen
    q_emb: List[float] = ...
    return retrieve(client_id, project_id, q_emb)


# -------------------------------------------------------
# Streamlit UI Runner
# -------------------------------------------------------
def run(*args: Any, **kwargs: Any) -> Any:
    """
    Start de Streamlit UI.
    Deze functie zorgt voor een veilig pad naar de hoofd-app,
    ongeacht de huidige werkdirectory.
    """
    try:
        # Gebruik het bestaande ui.py als Streamlit-app
        ui_file = Path(__file__).resolve().parent / "ui.py"

        if ui_file.exists():
            subprocess.run(["streamlit", "run", str(ui_file)], check=True)
        else:
            # fallback naar de globale webapp/app.py
            app_path = Path(__file__).resolve().parents[4] / "webapp/app.py"
            if not app_path.exists():
                raise FileNotFoundError(f"Geen geldig Streamlit-pad gevonden: {app_path}")
            subprocess.run(["streamlit", "run", str(app_path)], check=True)

    except Exception as e:
        print(f"⚠️  Fout bij starten van Streamlit: {e}")
        raise


# -------------------------------------------------------
# Aliassen voor registry compatibility
# -------------------------------------------------------
app = run
main = run
render = run
s