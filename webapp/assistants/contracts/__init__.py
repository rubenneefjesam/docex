DISPLAY_NAME = "Contracts"
IS_ASSISTANT = True
TOOLS = ["— Kies tool —"]

import streamlit as st
try:
    from .overview import render as _render_overview
except Exception:
    _render_overview = None

def render(tool=None):
    st.title(DISPLAY_NAME)
    if not tool or tool == "— Kies tool —":
        if callable(_render_overview):
            _render_overview()
        else:
            st.info("Selecteer links een tool om te starten.")
        return
    st.info(f"Tool '{tool}' is nog niet gekoppeld.")
