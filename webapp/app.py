# webapp/app.py (Optie A)

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from tools.docex_tool import docex
from tools.coge_tool import coge  # <-- import coge

st.set_page_config(page_title="Docx Suite", layout="wide")

with st.sidebar:
    st.header("Navigatie / Tools")
    choice = st.radio("", ["Home", "Informatie", "Docex", "Coge"], index=0)
    st.markdown("---")

if choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write("Welkom bij de DOCX-app. Kies een tool via de sidebar.")
elif choice == "Informatie":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write("Info: Docex = Document generator, Coge = compare (placeholder).")
elif choice == "Docex":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>✍️ Docex</h1>", unsafe_allow_html=True)
    docex.run()
elif choice == "Coge":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>🔍 Coge</h1>", unsafe_allow_html=True)
    import traceback
    from pathlib import Path

    try:
        st.write("🔧 Import check:", coge)
        st.write("📄 coge-module file:", getattr(coge, "__file__", "n/a"))

        coge_path = Path(ROOT) / "tools" / "coge_tool" / "coge.py"
        st.write("🗂️ coge.py exists?:", coge_path.exists(), str(coge_path))

        st.write("✅ calling coge.app() …")
        coge.app()
        st.success("coge.app() executed")
    except Exception as e:
        st.error(f"❌ Fout in coge.app(): {e}")
        st.code("".join(traceback.format_exception(type(e), e, e.__traceback__)))
