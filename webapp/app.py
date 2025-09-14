# webapp/app.py

import sys
from pathlib import Path

# --- projectroot aan sys.path toevoegen ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# Dynamic loader helpers: probeer meerdere kandidaat-modules en callables
import importlib

def load_tool_module_candidate(*candidates):
    for cand in candidates:
        try:
            mod = importlib.import_module(cand)
            return mod
        except Exception:
            continue
    return None

def call_first_callable(module, names=("run","app","main")):
    for n in names:
        fn = getattr(module, n, None)
        if callable(fn):
            return fn()
    raise RuntimeError(f"No callable entrypoint found in module {module.__name__}")



# --- correcte imports ---
# Docgen komt uit docex.py (pas dit aan als het in steps.py staat)
from tools.plan_creator import docgen
# Coge komt uit coge.py
from tools.coge_tool.coge import coge

# --- Streamlit setup ---
st.set_page_config(page_title="Docgen Suite", layout="wide")

with st.sidebar:
    st.header("Navigatie / Tools")
    choice = st.radio("", ["Home", "Informatie", "Docgen", "Coge"], index=0)
    st.markdown("---")

if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de **Docgen-app**. Kies een tool via de sidebar.")

elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: **Docgen** = Document generator, **Coge** = compare (placeholder).")

elif choice == "Docgen":
    st.markdown("<h1 style=\'font-size:28px; font-weight:700\'>✍️ Docgen</h1>", unsafe_allow_html=True)
    docmod = load_tool_module_candidate(
        "tools.doc_generator.docgen",
        "tools.plan_creator.dogen",
        "tools.doc_generator",
        "tools.plan_creator"
    )
    if docmod:
        try:
            call_first_callable(docmod)
        except Exception as e:
            st.error(f"Fout bij starten Docgen: {e}")
    else:
        st.error("Docgen module niet gevonden (controleer tools/doc_generator of tools/plan_creator)")

elif choice == "Coge":
    st.markdown("<h1 style=\'font-size:28px; font-weight:700\'>🔍 Coge</h1>", unsafe_allow_html=True)
    cogemod = load_tool_module_candidate(
        "tools.doc_comparison.coge",
        "tools.coge_tool.coge",
        "tools.doc_comparison"
    )
    if cogemod:
        try:
            call_first_callable(cogemod)
        except Exception as e:
            st.error(f"Fout bij starten Coge: {e}")
    else:
        st.error("Coge module niet gevonden (controleer tools/doc_comparison)")
