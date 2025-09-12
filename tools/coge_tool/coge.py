# tools/coge_tool/coge.py
import io
import re
import difflib
from typing import List, Tuple, Dict

import streamlit as st
import fitz  # PyMuPDF

# -----------------------------
# Helpers
# -----------------------------

@st.cache_data(show_spinner=False)
def extract_pdf_lines(pdf_bytes: bytes) -> List[List[str]]:
    """Retourneer per pagina een lijst regels (stripped)."""
    pages: List[List[str]] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            lines = [ln.strip() for ln in text.splitlines()]
            # filter lege regels om ruis te verminderen
            lines = [ln for ln in lines if ln]
            pages.append(lines)
    return pages

def flatten_with_page_prefix(pages: List[List[str]]) -> List[str]:
    """Maak 1 lijst met 'p{idx}:{line}' zodat we paginainfo bewaren."""
    flat: List[str] = []
    for p_idx, lines in enumerate(pages, start=1):
        for ln in lines:
            flat.append(f"p{p_idx}:{ln}")
    return flat

def parse_prefixed(line: str) -> Tuple[int, str]:
    """Haal (page_idx, text) uit 'p{idx}:{line}'."""
    m = re.match(r"p(\d+):(.*)", line, flags=re.DOTALL)
    if not m:
        return 1, line
    return int(m.group(1)), m.group(2).strip()

def pick_search_snippet(s: str, min_len: int = 12, max_len: int = 80) -> str:
    """
    Kies een representatieve substring om op te zoeken in de PDF:
    - pak alleen alfanumerieke / spaties
    - beperk lengte (PyMuPDF search werkt stabieler met kortere snippers)
    """
    # vereenvoudig whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # als te lang, pak middenstuk
    if len(s) > max_len:
        mid = len(s) // 2
        half = max_len // 2
        s = s[mid - half : mid + half]
    # als te kort, laat zoals is; als nog te kort, skip
    return s if len(s) >= min_len else ""

def add_highlight(page: fitz.Page, text: str, color: Tuple[float, float, float]) -> int:
    """Zoek text in page en highlight alle hits. Retourneert aantal hits."""
    if not text:
        return 0
    
    rects = page.searchrects = page.search_for(text)  # zoekt alle hits

    count = 0
    for r in rects:
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=color)  # highlight-kleur
        annot.update()
        count += 1
    return count

def annotate_pdf_v2(v2_bytes: bytes,
                    inserts: List[str],
                    replaces_new: List[str],
                    deletes_by_page: Dict[int, int]) -> bytes:
    """
    Plaats highlights in v2:
      - inserts (groen)  -> tekst alleen nieuw in v2
      - replaces_new (geel) -> nieuwe variant bij wijziging
      - deletes_by_page -> optionele notitie bovenaan pagina met # deletions
    """
    GREEN = (0.1, 0.7, 0.1)
    YELLOW = (0.95, 0.8, 0.2)

    with fitz.open(stream=v2_bytes, filetype="pdf") as doc:
        # Highlight inserts
        for pref in inserts:
            p_idx, txt = parse_prefixed(pref)
            if 1 <= p_idx <= len(doc):
                page = doc[p_idx - 1]
                snippet = pick_search_snippet(txt)
                add_highlight(page, snippet, GREEN)

        # Highlight replaced (new side)
        for pref in replaces_new:
            p_idx, txt = parse_prefixed(pref)
            if 1 <= p_idx <= len(doc):
                page = doc[p_idx - 1]
                snippet = pick_search_snippet(txt)
                add_highlight(page, snippet, YELLOW)

        # Voeg (optioneel) kleine notitie voor deletions toe
        for p_idx, count in deletes_by_page.items():
            if count <= 0:
                continue
            if 1 <= p_idx <= len(doc):
                page = doc[p_idx - 1]
                # Plaats FreeText annotatie linksboven
                rect = fitz.Rect(36, 36, 300, 80)
                note = page.add_freetext_annot(
                    rect,
                    f"−{count} verwijderd(e) regel(s) t.o.v. versie 1",
                    fontsize=9,
                    rotate=0,
                )
                note.set_colors(stroke=(0.7, 0.1, 0.1), fill=(1, 0.95, 0.95))
                note.update()

        out = io.BytesIO()
        doc.save(out, deflate=True)
        return out.getvalue()

# -----------------------------
# UI
# -----------------------------

def app():
    st.markdown("## 🔍 Coge")
    st.caption("Wijzigingen markeren in PDF v2 (geen samenvatting)")

    col1, col2 = st.columns(2)
    with col1:
        v1 = st.file_uploader("📄 Versie 1 (PDF)", type="pdf", key="pdf_v1")
    with col2:
        v2 = st.file_uploader("📄 Versie 2 (PDF)", type="pdf", key="pdf_v2")

    if not (v1 and v2):
        st.info("Upload beide PDF’s om te starten.")
        return

    v1_bytes = v1.getvalue()
    v2_bytes = v2.getvalue()

    with st.spinner("PDF’s lezen en vergelijken…"):
        v1_pages = extract_pdf_lines(v1_bytes)  # List[List[str]]
        v2_pages = extract_pdf_lines(v2_bytes)

        flat_a = flatten_with_page_prefix(v1_pages)
        flat_b = flatten_with_page_prefix(v2_pages)

        # Diff op regelniveau (inclusief paginaprefix)
        sm = difflib.SequenceMatcher(None, flat_a, flat_b, autojunk=False)
        inserts: List[str] = []         # pX:regel (alleen in v2)
        deletes: List[str] = []         # pX:regel (alleen in v1) - niet highlightbaar in v2
        replaces_old: List[str] = []    # oude regels (v1)
        replaces_new: List[str] = []    # nieuwe regels (v2)

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "insert":
                inserts.extend(flat_b[j1:j2])
            elif tag == "delete":
                deletes.extend(flat_a[i1:i2])
            elif tag == "replace":
                replaces_old.extend(flat_a[i1:i2])
                replaces_new.extend(flat_b[j1:j2])

        # Tel deletions per pagina (voor optionele notitie)
        deletes_by_page: Dict[int, int] = {}
        for pref in deletes:
            p_idx, _ = parse_prefixed(pref)
            deletes_by_page[p_idx] = deletes_by_page.get(p_idx, 0) + 1

        # Annoteren in v2
        out_bytes = annotate_pdf_v2(
            v2_bytes=v2_bytes,
            inserts=inserts,
            replaces_new=replaces_new,
            deletes_by_page=deletes_by_page,
        )

    # Stats tonen
    st.subheader("📊 Markeringen aangebracht")
    st.write(f"➕ Toegevoegd (groen): **{len(inserts)}** regels")
    st.write(f"🔁 Gewijzigd (geel): **{len(replaces_new)}** regels")
    st.write(f"➖ Verwijderd (notitie): **{sum(deletes_by_page.values())}** regels")

    # Download annotated PDF
    st.download_button(
        "⬇️ Download geannoteerde PDF (v2)",
        data=out_bytes,
        file_name=f"{v2.name.rsplit('.pdf', 1)[0]}_annotated.pdf",
        mime="application/pdf",
    )

    # Optioneel: toon de geannoteerde PDF inline (afhankelijk van Streamlit-versie / browser PDF support)
    st.markdown("—")
    st.caption("Preview van geannoteerde v2 (browser PDF viewer):")
    st.download_button(  # eenvoudige workaround: tweede knop of instructie
        "🔁 Download / open in viewer als de inline preview niet werkt",
        data=out_bytes,
        file_name=f"{v2.name.rsplit('.pdf', 1)[0]}_annotated.pdf",
        mime="application/pdf",
    )
