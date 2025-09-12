# tools/coge_tool/coge.py
import io
import difflib
import fitz  # PyMuPDF
import streamlit as st

# ---- Helpers ---------------------------------------------------------------

def extract_pdf_text(pdf_file) -> str:
    """Lees een PDF-bestand en geef alle tekst terug als string."""
    text = []
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text.append(page.get_text("text"))
    return "\n".join(text)

def make_diff_html(text1: str, text2: str) -> str:
    """Genereer een HTML-tabel met verschillen tussen twee teksten."""
    diff = difflib.HtmlDiff(wrapcolumn=100)
    return diff.make_table(
        text1.splitlines(),
        text2.splitlines(),
        fromdesc="Versie 1",
        todesc="Versie 2",
        context=True,
        numlines=2
    )

# ---- Streamlit app ---------------------------------------------------------

def app():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("## 🔍 Coge")
    with col2:
        st.write("Upload twee PDF’s om te vergelijken:")

        v1 = st.file_uploader("Versie 1 (PDF)", type="pdf", key="pdf_v1")
        v2 = st.file_uploader("Versie 2 (PDF)", type="pdf", key="pdf_v2")

        if v1 and v2:
            # Zet file_uploader opnieuw naar begin voor fitz
            v1.seek(0)
            v2.seek(0)

            st.success(f"✅ Beide bestanden geüpload: {v1.name}, {v2.name}")

            # Extract text
            with st.spinner("PDF’s uitlezen..."):
                text1 = extract_pdf_text(v1)
                text2 = extract_pdf_text(v2)

            # Toon diff
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

            # Optioneel: exporteer diff als txt
            diff_lines = []
            for line in difflib.ndiff(text1.splitlines(), text2.splitlines()):
                if line.startswith(("+", "-", "?")):
                    diff_lines.append(line)
            diff_bytes = io.BytesIO("\n".join(diff_lines).encode("utf-8"))
            st.download_button(
                "⬇️ Download diff als .txt",
                data=diff_bytes,
                file_name=f"diff_{v1.name}_vs_{v2.name}.txt",
                mime="text/plain"
            )
