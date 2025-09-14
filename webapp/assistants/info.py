# webapp/assistants/info.py
DISPLAY_NAME = "Info"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]  # alleen voor consistentie; niet gebruikt

import streamlit as st

def render(tool=None):  # tool optioneel maken
    st.header(DISPLAY_NAME)
    st.write("Informatiepagina")
    st.markdown("""
- **Versie:** 1.0.0  
- **Documentatie:** zie `/docs` in de repo  
- **Auteur:** Team X
""")
