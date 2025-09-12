# tools/coge_tool/coge.py
import io
import difflib
import fitz  # PyMuPDF
import streamlit as st

# ---- Helpers ---------------------------------------------------------------

@st.cache_data(show_spinner=False)
def extract_pdf_text_pages(pdf_bytes: bytes) -> list[str]:
    """Lees een PDF (bytes) en geef een lijst met pagina-teksten terug."""
    texts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            # Je kunt ook page.get_text("blocks") gebruiken voor meer structuur
            texts.append(page.get_text("text"))
    return texts

def join_clean(lines: list[str]) -> str:
    """Maak 1 string van pagina's en normaliseer whitespace lichtjes."""
    return "\n".join(s.strip() for s in lines if s is not None)

def diff_stats(a: str, b: str):
    """Snelle diff-statistieken op basis van opcodes."""
    sm = difflib.SequenceMatcher(None, a.splitlines(), b.splitlines())
    added = removed = replaced = equal = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "insert":
            added += (j2 - j1)
        elif tag == "delete":
            removed += (i2 - i1)
        elif tag == "replace":
            replaced += max(i2 - i1, j2 - j1)
        elif tag == "equal":
            equal += (i2 - i1)
    return added, removed, replaced, equal

def html_diff(a: str, b: str) -> str:
    """Maak een HTML-tabel met verschillen (links: v1, rechts: v2)."""
    hd = difflib.HtmlDiff(wrapcolumn=100)
    return hd.make_table(
        a.splitlines(), b.splitlines(),
        fromdesc="Versie 1", todesc="Versie 2",
        context=True, numlines=2
    )

# ---- UI --------------------------------------------------------------------

def app():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("## 🔍 Coge")
        st.caption("MVP: upload 2 PDF’s → toon verschillen")
    with col2:
        st.write("Upload twee PDF’s om te vergelijken:")
        v1 = st.file_uploader("Versie 1 (PDF)", type="pdf", key="pdf_v1")
        v2 = st.file_uploader("Versie 2 (PDF)", type="pdf", key="pdf_v2")

        if not (v1 and v2):
            st.info("📄 Selecteer **beide** PDF’s om te starten.")
            return

        # Lees bytes
        v1_bytes = v1.getvalue()
        v2_bytes = v2.getvalue()

        with st.spinner("PDF’s lezen…"):
            v1_pages = extract_pdf_text_pages(v1_bytes)
            v2_pages = extract_pdf_text_pages(v2_bytes)

        st.success(f"✅ Gelezen: {v1.name} ({len(v1_pages)} p.) en {v2.name} ({len(v2_pages)} p.)")

        # Combineer alle pagina’s tot 1 tekst (MVP)
        v1_text = join_clean(v1_pages)
        v2_text = join_clean(v2_pages)

        # Stats
        added, removed, replaced, equal = diff_stats(v1_text, v2_text)
        st.subheader("Samenvatting wijzigingen")
        st.write(
            f"- ➕ **Toegevoegd**: {added} regels\n"
            f"- ➖ **Verwijderd**: {removed} regels\n"
            f"- 🔁 **Gewijzigd**: {replaced} regels\n"
            f"- ✅ **Ongewijzigd**: {equal} regels"
        )

        # HTML diff
        st.subheader("Verschillen (context)")
        html = html_diff(v1_text, v2_text)
        st.markdown(
            """
            <style>
            table.diff {font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px;}
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
        st.markdown(html, unsafe_allow_html=True)

        # Optioneel: downloadbare eenvoudige changelog (txt)
        report_lines = []
        for line in difflib.ndiff(v1_text._
