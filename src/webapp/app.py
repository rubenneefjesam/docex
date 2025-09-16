# src/webapp/app.py
from pathlib import Path
import sys
import traceback
import os
import streamlit as st

# --- Path safety net (zorg dat src/ op sys.path staat) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]   # .../docex
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
# ---------------------------------------------------------

from webapp.components.sidebar import render_sidebar
from webapp.registry import ASSISTANTS
from webapp.home.home import render as render_home
from webapp.home.info import render as render_info
from webapp.home.contact import render as render_contact
from webapp.core.tool_loader import load_tool_module_candidate, call_first_callable

# Streamlit page setup
st.set_page_config(page_title="Docgen Suite", layout="wide")


def render_assistant_info(key: str):
    """Dynamically import and call the render() of an assistant’s info module."""
    module_path = f"webapp.assistants.{key}.info"
    try:
        mod = __import__(module_path, fromlist=["render"])
        render = getattr(mod, "render", None)
        if callable(render):
            render()
        else:
            st.header(f"{ASSISTANTS[key]['label']} — Info")
            st.write("Geen extra informatie beschikbaar.")
    except Exception as e:
        st.error(f"Kon info-module niet laden voor '{key}': {e}")


# Sidebar selections
page, assistant_key, tool_key = render_sidebar(default_assistant="general_support")

if page == "Home":
    render_home()
elif page == "Info":
    render_info()
elif page == "Contact":
    render_contact()
else:
    # Assistenten-mode
    if assistant_key in ASSISTANTS and not tool_key:
        # Alleen een assistent geselecteerd → toon zijn info
        render_assistant_info(assistant_key)
    elif assistant_key in ASSISTANTS and tool_key in ASSISTANTS[assistant_key]["tools"]:
        # Assistent + tool geselecteerd → run de tool
        meta = ASSISTANTS[assistant_key]["tools"][tool_key]
        candidates = meta.get("page_module_candidates", [])
        mod = load_tool_module_candidate(meta["label"], *candidates)
        try:
            call_first_callable(mod, meta["label"])
        except Exception:
            error_text = traceback.format_exc()
            st.error(f"Fout bij starten '{meta['label']}':\n{error_text}")
            print(error_text)
    else:
        # Onjuiste selectie
        st.warning("Ongeldige selectie. Kies een assistent en een tool.")
        render_home()


# --- Optioneel: Debug-info (alleen als DEBUG_ENV=1 staat) ---
if os.environ.get("DEBUG_ENV") == "1":
    import json
    st.sidebar.title("Environment debug")
    st.json({
        "sys.executable": sys.executable,
        "cwd": os.getcwd(),
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
        "assistants": list(ASSISTANTS.keys()),
    })
# -----------------------------------------------------------
