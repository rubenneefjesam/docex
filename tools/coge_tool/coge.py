# tools/coge_tool/coge.py
import io
import difflib
import fitz  # PyMuPDF
import streamlit as st

def extract_pdf_text(pdf_file) -> str:
    text = []
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text.append(page.get_text("text"))
    return "\n".join(text)

def make_diff_html(text1: str, text2: str) -> str:
    diff = difflib.HtmlDiff(wrapcolumn=100)
    return diff.make_table(
        text1.splitlines(),
        text2.splitlines(),
        fromdesc="Versie 1",
        todesc="Versie 2",
        context=True,
        numlines=2
    )

def app():
    st.markdown("## 🔍 Coge")
    st.caption("Vergelijk 2 PDF’s (MVP)")

    # --- uploaders naast elkaar ---
    col1, col2 = st.columns(2)
    with col1:
        v1 = st.file_uploader("📄 Versie 1 (PDF)", type="pdf", key="pdf_v1")
    with col2:
        v2 = st.file_uploader("📄 Versie 2 (PDF)", type="pdf", key="pdf_v2")

    # --- toon diff zodra beide geüpload zijn ---
    if v1 and v2:
        v1.seek(0)
        v2.seek(0)

        st.success(f"✅ Beide bestanden geüpload: {v1.name}, {v2.name}")

        with st.spinner("PDF’s uitlezen..."):
            text1 = extract_pdf_text(v1)
            text2 = extract_pdf_text(v2)

        st.subheader("📊 Verschillen")
        html_diff = make_diff_html(text1, text2)

        st.markdown(
            """
            <style>
            table.diff {font-family: monospace; font-size: 13px;}
            .diff_header {background:#111; color:#fff; padding:4px;}
            .diff_next {background:#333; color:#fff;}
            .diff_add {background:#153f15;}
            .diff_chg {background:#3a3520;}
            .diff_sub {background:#3f1515;}
            td, th {padding:2px 6px; vertical-align:top;}
            </style>
            """,
            unsafe_allow_html=True
        )
        st.markdown(html_diff, unsafe_allow_html=True)
