# webapp/app.py
import streamlit as st
from tools.docex_tool import docex

st.set_page_config(page_title="Docx Suite", layout="wide")

# ===== SIDEBAR: precies twee secties =====
st.sidebar.title("Navigatie")
nav_choice = st.sidebar.radio("", ["Home", "Informatie"], index=0)

st.sidebar.markdown("---")

st.sidebar.title("Kies tool")
tool_choice = st.sidebar.radio("", ["Docex", "Coge"], index=0)

# ===== HOOFDPAGINA: toon Navigatie-content (Home of Informatie) =====
if nav_choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write(
        """
        Welkom bij de DOCX-app.
        - Gebruik de sidebar om te schakelen tussen Home en Informatie.
        - Kies een tool (Docex of Coge) in de sidebar om die te gebruiken.
        """
    )
else:
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write(
        """
        Info:
        - Docex: Document generator (je bestaande tool).
        - Coge: Vergelijk / compare feature (voor nu een titelscherm).
        """
    )

st.markdown("---")

# ===== TOOL: activeer de gekozen tool (Docex of Coge) =====
if tool_choice == "Docex":
    # roept jouw bestaande tool aan (zorg dat tools/docex_tool/docex.run() beschikbaar is)
    docex.run()

else:  # Coge
    st.markdown("<h2 style='font-size:22px; font-weight:700'>🔍 Coge</h2>", unsafe_allow_html=True)
    st.write("Coge — (voor nu) enkel titel / placeholder. Ik kan hier later de compare-UI toevoegen.")
