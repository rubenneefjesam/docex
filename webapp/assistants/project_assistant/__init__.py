DISPLAY_NAME = "Project Assistant"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st
def render(tool=None):
    st.title(DISPLAY_NAME)
    st.write("Pagina-inhoud volgt.")
