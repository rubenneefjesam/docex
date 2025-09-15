# src/webapp/app2.py
import sys
from pathlib import Path

# Zet <repo>/src in sys.path, ongeacht waar je runt
REPO_ROOT = Path(__file__).resolve().parents[2]   # /workspaces/docex
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import app

st.set_page_config(page_title="Doc Compare Test", layout="wide")
app()
