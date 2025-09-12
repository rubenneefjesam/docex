# webapp/app.py
import streamlit as st
import tempfile
import difflib
import os

from tools.docex_tool import docex
from core.docx_utils import read_docx

st.set_page_config(page_title="Docx Suite", layout="wide")

st.sidebar.title("Tools")

# 1) Nav: Home / Info
nav = st.sidebar.radio("Navigatie", ["Home", "Info"], index=0)

st.sidebar.markdown("---")

# 2) Tool-selectie (start met '(geen)' zodat we eerst Home/Info tonen)
tool_choice = st.sidebar.selectbox("Kies tool", ["(geen)", "Docex", "Coge"])

# If no tool selected -> show navigation page; else show the tool UI
if tool_choice == "(geen)":
    if nav == "Home":
        st.markdown("<div style='font-size:32px; font-weight:700'>🏠 Welkom bij de DOCX Generator</div>", unsafe_allow_html=True)
        st.write(
            """
            Gebruik deze tool om snel **Word-templates** bij te werken met **nieuwe context**.
            
            - Ga naar **Generator**
            - Upload je **template** en **context**
            - Klik op **Genereer aangepast document**
            - Download en behoud je opmaak!
            """
        )
    else:  # Info
        st.markdown("<div style='font-size:28px; font-weight:700'>ℹ️ Info & Tips</div>", unsafe_allow_html=True)
        st.write(
            """
            **Tips voor optimaal gebruik:**
            - Zorg voor unieke, duidelijke tekstfragmenten.
            - Houd context-bestanden kort en concreet.
            - Controleer altijd de uiteindelijke output.
            - Voor complexe documenten kun je secties apart bijwerken.
            """
        )

else:
    # --- TOOL: Docex ----------------------------------------------------
    if tool_choice == "Docex":
        # roep je bestaande tool aan
        docex.run()

    # --- TOOL: Coge (compare) -------------------------------------------
    else:  # Coge
        st.markdown("<div style='font-size:28px; font-weight:700'>🔍 Coge — Vergelijk twee documenten</div>", unsafe_allow_html=True)
        st.write("Upload twee documenten (.docx of .txt) en zie een tekst-diff (unified).")

        col1, col2 = st.columns(2)
        left_file = col1.file_uploader("Links (oud)", type=["docx", "txt"], key="left")
        right_file = col2.file_uploader("Rechts (nieuw)", type=["docx", "txt"], key="right")

        def _read_uploaded(uploaded):
            if not uploaded:
                return ""
            # Streamlit UploadedFile: schrijf tijdelijk naar disk en gebruik read_docx for docx
            try:
                if uploaded.type and "document" in uploaded.type:
                    tmpdir = tempfile.mkdtemp()
                    path = os.path.join(tmpdir, "tmp.docx")
                    with open(path, "wb") as f:
                        f.write(uploaded.getbuffer())
                    return read_docx(path)
                else:
                    return uploaded.read().decode("utf-8", errors="ignore")
            except Exception:
                # fallback: probeer als text
                try:
                    return uploaded.read().decode("utf-8", errors="ignore")
                except Exception:
                    return ""

        if left_file and right_file:
            left_text = _read_uploaded(left_file).splitlines()
            right_text = _read_uploaded(right_file).splitlines()

            diff = difflib.unified_diff(left_text, right_text, fromfile="left", tofile="right", lineterm="")
            diff_text = "\n".join(diff)
            if not diff_text.strip():
                st.success("Geen verschillen gevonden 🎉")
            else:
                st.code(diff_text, language="diff")
                st.download_button("Download diff als .txt", data=diff_text, file_name="diff.txt")
