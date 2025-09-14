# webapp/assistants/general_support/__init__.py
DISPLAY_NAME = "General support"
IS_ASSISTANT = True
TOOLS = ["— Kies tool —", "Document generator", "Document comparison"]

import streamlit as st

try:
    from .document_generator import render as _render_docgen
except Exception:
    _render_docgen = None

try:
    from .document_comparison import render as _render_doccmp
except Exception:
    _render_doccmp = None

def render(tool):
    st.title(DISPLAY_NAME)
    st.write("Korte omschrijving van General support.")
    if not tool or tool == "— Kies tool —":
        st.info("Selecteer een tool in de sidebar.")
        return

    if tool == "Document generator":
        if callable(_render_docgen):
            return _render_docgen(tool)
        st.error("Document generator niet beschikbaar (check document_generator.py).")
    elif tool == "Document comparison":
        if callable(_render_doccmp):
            return _render_doccmp(tool)
        st.error("Document comparison niet beschikbaar (check document_comparison.py).")
    else:
        st.write("Onbekende tool:", tool)
