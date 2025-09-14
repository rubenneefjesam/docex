import streamlit as st
try:
    from . import DISPLAY_NAME
except ImportError:
    DISPLAY_NAME = None

def render():
    title = DISPLAY_NAME or "Assistent"
    st.subheader(f"Welkom bij {title}")
    st.write("Dit is de startpagina voor deze assistent.")
    st.write("Selecteer links in de sidebar een tool om te beginnen.")
