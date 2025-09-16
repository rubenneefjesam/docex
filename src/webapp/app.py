# src/webapp/app.py
import sys, os, traceback
import streamlit as st

from webapp.registry import ASSISTANTS

st.set_page_config(page_title="Tools", layout="wide")

# Debug-paneel bovenin: zie je welk Python/venv actief is
with st.expander("Environment debug", expanded=False):
    st.write({
        "sys.executable": sys.executable,
        "cwd": os.getcwd(),
        "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV"),
        "assistants": list(ASSISTANTS.keys()),
    })

# Kies assistant & tool
asst_key = st.sidebar.selectbox("Assistant", list(ASSISTANTS.keys()))
tool_keys = list(ASSISTANTS[asst_key]["tools"].keys())
if not tool_keys:
    st.warning("Deze assistant heeft nog geen tools.")
    st.stop()

tool_key = st.sidebar.selectbox("Tool", tool_keys)
tool_info = ASSISTANTS[asst_key]["tools"][tool_key]

st.sidebar.write(f"→ {asst_key} / {tool_key}")

# Resolve entrypoint (app/run) via onze nieuwe registry
try:
    entry = tool_info["resolver"]()  # <— BELANGRIJK: gebruikt nieuwe registry
except Exception as e:
    st.error(f"Kon entrypoint niet resolven voor {asst_key}.{tool_key}:\n{e}")
    st.code("".join(traceback.format_exc()))
    st.stop()

# Draai de tool binnen de Streamlit context
try:
    entry()  # verwacht een functie die de Streamlit UI rendert
except Exception as e:
    st.error(f"Fout bij uitvoeren van {asst_key}.{tool_key}: {e}")
    st.code("".join(traceback.format_exc()))
