# webapp/assistants/info.py
DISPLAY_NAME = "Info"
TOOLS = ["— Kies tool —"]  # geen tools, maar volg de conventie

import streamlit as st

def render(tool):
    st.title(DISPLAY_NAME)
    st.write("Algemene informatie over de app en documentatie.")
    st.write("- Versie: 1.0.0")
    st.write("- Documentatie: zie /docs in de repository")
    st.write("- Auteur: Team X")
    if tool and tool != "— Kies tool —":
        st.warning(f"Onverwachte tool geselecteerd: {tool}")