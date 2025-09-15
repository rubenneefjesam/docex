# src/webapp/app2.py
import sys
from pathlib import Path

# Voeg <repo>/src toe aan sys.path (2 niveaus omhoog vanaf src/webapp/app2.py)
SRC = Path(__file__).resolve().parents[2] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import app

st.set_page_config(page_title="Doc Compare Test", layout="wide")
app()
