# tools/object_analyzer/ui.py

import streamlit as st
from .ui_logic import render_object_counter_ui


def run(show_nav: bool = True):
    st.set_page_config(
        page_title="Object Analyzer",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        "<h1>🧠 Object Analyzer (OpenAI Vision)</h1>",
        unsafe_allow_html=True
    )

    # Start de analyzer UI
    render_object_counter_ui()


def app():
    run(show_nav=False)
