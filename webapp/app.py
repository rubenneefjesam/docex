# webapp/app.py

import sys
from pathlib import Path

# --- projectroot aan sys.path toevoegen ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# --- correcte imports ---
# Docgen komt uit docex.py (pas dit aan als het in steps.py staat)
from tools.plan_creator import docgen
# Coge komt uit coge.py
from tools.coge_tool.coge import coge

# --- Streamlit setup ---
st.set_page_config(page_title="Docgen Suite", layout="wide")

with st.sidebar:
    st.header("Navigatie / Tools")
    choice = st.radio("", ["Home", "Informatie", "Docgen", "Coge"], index=0)
    st.markdown("---")

if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de **Docgen-app**. Kies een tool via de sidebar.")

elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: **Docgen** = Document generator, **Coge** = compare (placeholder).")

elif choice == "Docgen":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>✍️ Docgen</h1>", unsafe_allow_html=True)
    docgen.run()

elif choice == "Coge":
    coge.app()
