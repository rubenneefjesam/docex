import streamlit as st
try:
    from . import DISPLAY_NAME as _DISPLAY_NAME
except Exception:
    _DISPLAY_NAME = None

def render():
    title = _DISPLAY_NAME or "Assistent"
    st.subheader(f"Welkom bij {title}")
    st.write("Dit is de startpagina voor deze assistent. Kies links een tool om te beginnen.")
