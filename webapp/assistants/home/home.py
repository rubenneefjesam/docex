# webapp/assistants/home.py
import streamlit as st
from webapp.registry import ASSISTANTS

def render():
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de **Document generator-app**. Kies een assistent en daarna een tool via de sidebar.")
    st.markdown("---")

    st.write("**Beschikbare assistenten:**")
    for key, meta in ASSISTANTS.items():
        st.write(f"- **{meta['label']}**")
        tools = meta.get("tools", {})
        if tools:
            for tkey, tmeta in tools.items():
                st.write(f"  - {tmeta['label']}")
        else:
            st.write("  - _Nog geen tools geconfigureerd_")

    st.markdown("---")
    st.write("Tip: je kunt direct linken naar een tool met de query params, bijv:")
    st.code("?assistant=general_support&tool=document_generator")
    st.write("")
