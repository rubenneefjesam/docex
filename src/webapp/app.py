# src/webapp/app.py

import sys
from pathlib import Path
import traceback

import streamlit as st

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp.components.sidebar import render_sidebar
from webapp.registry import ASSISTANTS
from webapp.home.home import render as render_home
from webapp.home.info import render as render_info
from webapp.home.contact import render as render_contact
from webapp.core.tool_loader import load_tool_module_candidate, call_first_callable

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
    # 1) Only assistant selected → show its info
    if assistant_key in ASSISTANTS and not tool_key:
        render_assistant_info(assistant_key)

    # 2) Assistant + tool selected → load and run the tool
    elif assistant_key in ASSISTANTS and tool_key in ASSISTANTS[assistant_key]["tools"]:
        meta = ASSISTANTS[assistant_key]["tools"][tool_key]
        candidates = meta.get("page_module_candidates", [])
        mod = load_tool_module_candidate(meta["label"], *candidates)
        try:
            call_first_callable(mod, meta["label"])
        except Exception:
            st.error(f"Fout bij starten '{meta['label']}':\n{traceback.format_exc()}")

    else:
        # Should never happen if sidebar restricts keys correctly
        st.warning("Ongeldige selectie. Kies een assistent en een tool.")
        render_home()
