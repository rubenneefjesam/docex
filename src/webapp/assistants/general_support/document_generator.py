# src/webapp/assistants/general_support/document_generator.py
import streamlit as st
from tools.doc_generator.doc_generator import run as _run_doc_generator


def render():
    """
    Entry-point voor de Streamlit-pagina ‘Document generator’.
    De echte logica zit in tools/doc_generator/doc_generator.py; we roepen
    alleen de run()-functie aan met show_nav=True.
    """
    st.markdown("### 🚀 Document generator", unsafe_allow_html=True)
    st.caption(
        "Start de generator-tool hieronder. (Deze pagina is de UI/glue; de implementatie zit in /tools.)"
    )

    try:
        _run_doc_generator(show_nav=True)
    except Exception as e:
        st.error(f"Fout bij starten Document generator: {e}")
