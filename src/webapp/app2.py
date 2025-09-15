# src/webapp/app2.py
import sys
from pathlib import Path

# Zorg dat "<repo>/src" in sys.path staat (we zitten nu in "<repo>/src/webapp")
HERE = Path(__file__).resolve()
SRC = HERE.parents[1]  # ==> "<repo>/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import app

st.set_page_config(page_title="Doc Compare Test", layout="wide")
app()
