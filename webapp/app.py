# webapp/app.py
import streamlit as st
from tools.docex_tool import docex

st.set_page_config(page_title="Docx Suite", layout="wide")

st.sidebar.title("Tools")

# Simpele keuze (radio) voor tool-keuze — geen dropdown meer
tool_choice = st.sidebar.radio("Kies tool", ["(geen)", "Docex", "Coge"], index=0)

# Als geen tool gekozen -> toon Home (standaard). Info kort onderaan.
if tool_choice == "(geen)":
    st.markdown("<div style='font-size:32px; font-weight:700'>🏠 Welkom bij de DOCX Generator</div>", unsafe_allow_html=True)
    st.write(
        """
        Gebruik deze tool om snel **Word-templates** bij te werken met **nieuwe context**.
        
        - Upload je template en context
        - Klik op **Genereer aangepast document**
        - Download en behoud je opmaak!
        """
    )

    st.markdown("---")
    with st.expander("ℹ️ Info & Tips"):
        st.write(
            """
            **Tips voor optimaal gebruik:**
            - Zorg voor unieke, duidelijke tekstfragmenten.
            - Houd context-bestanden kort en concreet.
            - Controleer altijd de uiteindelijke output.
            - Voor complexe documenten kun je secties apart bijwerken.
            """
        )

# Docex: call jouw bestaande tool
elif tool_choice == "Docex":
    docex.run()

# Coge: eenvoudige titelscherm (of later uitbreiden)
elif tool_choice == "Coge":
    st.markdown("<div style='font-size:32px; font-weight:700'>🔍 Coge</div>", unsafe_allow_html=True)
    st.write("Coge — (voor nu) een eenvoudige compare / generator. Hier komt later de compare-UI.")