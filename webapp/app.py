# webapp/app.py

# --- ensure project root on sys.path (MUST come first) ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
import streamlit as st
from webapp.components.sidebar import render_sidebar
from webapp.registry import ASSISTANTS

st.set_page_config(page_title="Docgen Suite", layout="wide")

# --- ensure project root on sys.path ---
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Sidebar -> keuze ophalen
assistant, tool = render_sidebar(default_assistant="general_support")

# Fallback naar Home-kaart als er (nog) geen tool is
if not tool or assistant not in ASSISTANTS:
    st.markdown("## 🏠 Home")
    st.write("Welkom bij de **Document generator-app**. Kies een tool via de sidebar.")
else:
    # Modulepad van de pagina ophalen uit registry
    page_module_path = ASSISTANTS[assistant]["tools"][tool]["page_module"]

    # Pagina-module importeren en renderen
    try:
        mod = importlib.import_module(page_module_path)
    except Exception as e:
        st.error(f"Kon pagina-module niet laden: `{page_module_path}`\n\n{e}")
    else:
        render = getattr(mod, "render", None)
        if callable(render):
            render()
        else:
            st.error(f"Pagina `{page_module_path}` heeft geen render() functie.")