# tools/object_counter/ui.py

import streamlit as st
from .ui_logic import render_object_counter_ui


def run(show_nav: bool = True):
    st.set_page_config(
        page_title="Object Counter",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Eventueel paginatitel / globale uitleg
    st.markdown("<h1>🔢 Object Counter (OpenAI Vision)</h1>", unsafe_allow_html=True)

    # Alle UI-functionaliteit in aparte module
    render_object_counter_ui()


def app():
    run(show_nav=False)
