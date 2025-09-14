DISPLAY_NAME = "Info"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st

def render(tool=None):
    st.header(DISPLAY_NAME)
    st.write("Algemene informatie over de app en documentatie.")
    st.write("- Versie: 1.0.0")
    st.write("- Documentatie: zie `/docs`")
    st.write("- Auteur: Team X")
    if tool and tool != "— Kies tool —":
        st.warning(f"Onverwachte tool geselecteerd: {tool}")
