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

# Sidebar -> keuze ophalen (session-managed in sidebar)
assistant, tool = render_sidebar(default_assistant="general_support")

# Wanneer er geen tool geselecteerd is (of assistent geen tools heeft), toon Home
if not tool or assistant not in ASSISTANTS:
    try:
        home_mod = importlib.import_module("webapp.assistants.home")
        render_home = getattr(home_mod, "render", None)
        if callable(render_home):
            render_home()
        else:
            # fallback UI if home module missing or broken
            st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
            st.write("Welkom bij de Document generator-app. Kies een tool via de sidebar.")
    except Exception as e:
        st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
        st.write("Welkom bij de Document generator-app. Kies een tool via de sidebar.")
        st.error(f"Kon home pagina niet laden: {e}")
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
