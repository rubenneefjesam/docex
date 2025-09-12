# webapp/app.py (Optie A)

import sys
from pathlib import Path

# ✅ Voeg project-root toe zodat 'tools' gevonden wordt
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from tools.docex_tool import docex  # jouw bestaande tool
from tools.coge_tool import coge # de nieuwe tool

st.set_page_config(page_title="Docx Suite", layout="wide")

# ---- Sidebar: één enkele keuze ----
with st.sidebar:
    st.header("Navigatie / Tools")
    choice = st.radio("", ["Home", "Informatie", "Docex", "Coge"], index=0)
    st.markdown("---")

# ---- Main ----
if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de DOCX-app. Kies een tool via de sidebar.")
elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: Docex = Document generator, Coge = compare (placeholder).")
elif choice == "Docex":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>✍️ Docex</h1>", unsafe_allow_html=True)
    docex.run()
elif choice == "Coge":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>✍️ Docex</h1>", unsafe_allow_html=True)
    docex.run()


