# webapp/app.py
import streamlit as st
from tools.docex_tool import docex

st.set_page_config(page_title="Docx Suite", layout="wide")

# Sidebar: Navigatie + simpele tool-selectie
st.sidebar.title("Tools")

# Navigatie (eerst kiezen wat de hoofdpagina toont)
nav = st.sidebar.radio("Navigatie", ["Home", "Info"], index=0)

st.sidebar.markdown("---")

# Simpele dropdown (selectbox) voor tool-keuze
tool_choice = st.sidebar.selectbox("Kies tool", ["(geen)", "Docex", "Coge"])

# --- Toon hoofdcontent (als er geen tool is gekozen) ---------------
if tool_choice == "(geen)":
    if nav == "Home":
        st.markdown("<div style='font-size:32px; font-weight:700'>🏠 Welkom bij de DOCX Generator</div>", unsafe_allow_html=True)
        st.write(
            """
            Gebruik deze tool om snel **Word-templates** bij te werken met **nieuwe context**.
            
            - Ga naar **Generator**
            - Upload je **template** en **context**
            - Klik op **Genereer aangepast document**
            - Download en behoud je opmaak!
            """
        )
    else:  # Info
        st.markdown("<div style='font-size:28px; font-weight:700'>ℹ️ Info & Tips</div>", unsafe_allow_html=True)
        st.write(
            """
            **Tips voor optimaal gebruik:**
            - Zorg voor unieke, duidelijke tekstfragmenten.
            - Houd context-bestanden kort en concreet.
            - Controleer altijd de uiteindelijke output.
            - Voor complexe documenten kun je secties apart bijwerken.
            """
        )

# --- TOOL: Docex (roept jouw bestaande tool aan) ---------------------
elif tool_choice == "Docex":
    docex.run()

# --- TOOL: Coge (slechts een titel zoals je vroeg) --------------------
elif tool_choice == "Coge":
    st.markdown("<div style='font-size:32px; font-weight:700'>🔍 Coge</div>", unsafe_allow_html=True)
    st.write("Coge — eenvoudige compare / generator (titelscherm).")
