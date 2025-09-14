DISPLAY_NAME = "Home"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st

def render(tool=None):
    st.markdown("<h1>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de Document generator-app.")
    if tool and tool != "— Kies tool —":
        st.warning(f"Onverwachte tool geselecteerd: {tool}")
