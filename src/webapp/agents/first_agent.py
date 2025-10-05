import streamlit as st
from pathlib import Path
import importlib

# 1) Vind alle sub-mappen in agent_tools als tools
TOOLS_DIR = Path(__file__).parent / "agent_tools"
tool_keys = [p.name for p in TOOLS_DIR.iterdir() if p.is_dir()]

st.title("First Agent Dashboard")

# 2) Maak twee kolommen
col1, col2 = st.columns(2)

with col1:
    st.header("Kolom 1")
    choice1 = st.selectbox("Kies een tool", [""] + tool_keys, index=0)
    if choice1:
        # Dynamisch importeren van het gekozen tool
        mod = importlib.import_module(f"webapp.first_agent.agent_tools.{choice1}.app")
        entry = getattr(mod, "run", None) or getattr(mod, "app", None)
        if callable(entry):
            entry()
        else:
            st.error(f"Geen geldig entry-point gevonden in {choice1}")

with col2:
    st.header("Kolom 2")
    choice2 = st.selectbox("Kies een tool", [""] + tool_keys, index=0, key="tool2")
    if choice2:
        mod = importlib.import_module(f"webapp.first_agent.agent_tools.{choice2}.app")
        entry = getattr(mod, "run", None) or getattr(mod, "app", None)
        if callable(entry):
            entry()
        else:
            st.error(f"Geen geldig entry-point gevonden in {choice2}")
