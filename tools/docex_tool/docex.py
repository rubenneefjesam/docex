# webapp/app.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# probeer docex run() te importeren
try:
    from tools.docex_tool import run as docex_run
except Exception:
    docex_run = None

# probeer coge (flexibel: run of render)
coge_run = None
coge_render = None
try:
    from tools.coge.coge_tool import run as coge_run
except Exception:
    try:
        from tools.coge.coge_tool import render as coge_render
    except Exception:
        coge_run = None
        coge_render = None

st.set_page_config(page_title="DOCX Suite", layout="wide")

tabs = st.tabs(["Home", "Docex", "Coge", "Info"])

# Home
with tabs[0]:
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write(
        "- Gebruik de tabs bovenaan om te schakelen tussen Home, Docex, Coge en Info.\n"
        "- Docex: Document generator.\n"
        "- Coge: Vergelijk/compare feature (placeholder)."
    )

# Docex (zonder eigen sidebar)
with tabs[1]:
    if docex_run:
        # forceer geïntegreerde modus: geen zijbalk vanuit de tool
        docex_run(show_sidebar=False, initial_page="Generator")
    else:
        st.error("Docex niet gevonden. Controleer tools/docex_tool/docex.py")

# Coge
with tabs[2]:
    if coge_run:
        coge_run(show_sidebar=False)  # als Coge vergelijkbare interface heeft
    elif coge_render:
        # render verwacht mogelijk Streamlit object
        coge_render(st)
    else:
        st.info("Coge placeholder: upload twee bestanden om te vergelijken (nog niet geïmplementeerd).")

# Info
with tabs[3]:
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Info</h1>", unsafe_allow_html=True)
    st.write(
        "- **Docex:** Word-template generator (gebruik de Generator-tab om direct te starten).\n"
        "- **Coge:** Vergelijk/compare feature (placeholder).\n\n"
        "Er is bewust geen sidebar — alles staat in de hoofdcontent (rechts)."
    )
