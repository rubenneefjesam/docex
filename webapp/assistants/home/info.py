# webapp/assistants/info.py
import streamlit as st

def render():
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Info</h1>", unsafe_allow_html=True)
    st.write("Informatie over de Document generator-app en hoe je 'm gebruikt.")
    st.markdown("---")
    st.write("- Versie: development")
    st.write("- Auteur: jouw team")
    st.write("- Beschrijving: toolset om documenten te analyseren en genereren.")
