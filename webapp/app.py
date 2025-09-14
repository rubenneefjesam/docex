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

# Sidebar -> keuze ophalen (nu: main_menu, assistant, tool)
main_menu, assistant, tool = render_sidebar(default_assistant="general_support")

# Route based on main_menu
if main_menu == "Home":
    try:
        home_mod = importlib.import_module("webapp.assistants.home")
        render_home = getattr(home_mod, "render", None)
        if callable(render_home):
            render_home()
        else:
            st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
            st.write("Welkom bij de Document generator-app.")
    except Exception as e:
        st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
        st.write("Welkom bij de Document generator-app.")
        st.error(f"Kon home pagina niet laden: {e}")

elif main_menu == "Info":
    try:
        info_mod = importlib.import_module("webapp.assistants.info")
        render_info = getattr(info_mod, "render", None)
        if callable(render_info):
            render_info()
        else:
            st.header("Info")
            st.write("Informatiepagina")
    except Exception as e:
        st.header("Info")
        st.write("Informatiepagina")
        st.error(f"Kon info pagina niet laden: {e}")

elif main_menu == "Contact":
    try:
        contact_mod = importlib.import_module("webapp.assistants.contact")
        render_contact = getattr(contact_mod, "render", None)
        if callable(render_contact):
            render_contact()
        else:
            st.header("Contact")
            st.write("Contactpagina")
    except Exception as e:
        st.header("Contact")
        st.write("Contactpagina")
        st.error(f"Kon contact pagina niet laden: {e}")

else:  # "Assistenten" mode -> use registry to load selected tool page
    if not tool or assistant not in ASSISTANTS:
        # show home-ish placeholder if no tool selected
        try:
            home_mod = importlib.import_module("webapp.assistants.home")
            render_home = getattr(home_mod, "render", None)
            if callable(render_home):
                render_home()
                # also show a small hint
                st.info("Kies bovenin een assistent en daarna een tool om te starten.")
            else:
                st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
                st.write("Welkom bij de Document generator-app. Kies een tool via de sidebar.")
        except Exception:
            st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
            st.write("Welkom bij de Document generator-app. Kies een tool via the sidebar.")
    else:
        page_module_path = ASSISTANTS[assistant]["tools"][tool]["page_module"]
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
