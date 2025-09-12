# tools/coge_tool/coge.py
import io
import re
import difflib
from typing import List, Tuple, Dict

import streamlit as st
import fitz  # PyMuPDF

# Hergebruik client uit Docex
from tools.docex_tool.docex import get_groq_client

# -----------------------------
# PDF helpers
# -----------------------------

@st.cache_data(show_spinner=False)
def extract_pdf_lines(pdf_bytes: bytes) -> List[List[str]]:
    """Retourneer per pagina een lijst regels (stripped)."""
    pages: List[List[str]] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text = page.get_text("text")
            lines = [ln.strip() for ln in text.splitlines()]
            lines = [ln for ln in lines if ln]  # filter lege regels
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
    """Kies een substring om in de PDF te zoeken (stabieler)."""
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        mid = len(s) // 2
        half = max_len // 2
        s = s[mid - half : mid + half]
    return s if len(s) >= min_len else s

# -----------------------------
# LLM helper
# -----------------------------

def llm_describe_change(client, old: str, new: str, change_type: str) -> str:
    """
    Vraag LLM om kort en concreet te beschrijven wat er is veranderd.
    change_type = insert | delete | replace
    """
    prompt = (
        f"Beschrijf heel kort wat er is veranderd ({change_type}). "
        "Geef 1 zin, concreet (bv. 'Aantal aangepast van 20 naar 40', "
        "'Naam toegevoegd: Heijmans'). "
        f"\nOud: {old or '(leeg)'}\nNieuw: {new or '(leeg)'}"
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {"role": "system", "content": "Antwoord alleen met de korte beschrijving, geen extra uitleg."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"{change_type.capitalize()} (LLM-fout: {e})"

# -----------------------------
# Annotaties
# -----------------------------

def add_highlight_with_note(page, text, color, note):
    """Highlight tekst en voeg sticky note toe met uitleg."""
    if not text:
        return 0
    try:
        rects = page.search_for(text)
    except Exception:
        return 0

    count = 0
    for r in rects:
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=color)
        annot.update()

        note_point = fitz.Point(r.x1, r.y0)
        note_annot = page.add_text_annot(note_point, note, icon="Comment")
        note_annot.update()
        count += 1
    return count

def annotate_pdf_v2(v2_bytes: bytes,
                    inserts: List[str],
                    replaces: List[Tuple[str, str]],
                    deletes_by_page: Dict[int, int],
                    client) -> bytes:
    GREEN = (0.1, 0.7, 0.1)   # inserts
    YELLOW = (0.95, 0.8, 0.2) # replaces

    with fitz.open(stream=v2_bytes, filetype="pdf") as doc:
        # Toevoegingen
        for pref in inserts:
            p_idx, txt = parse_prefixed(pref)
            snippet = pick_search_snippet(txt)
            desc = llm_describe_change(client, "", txt, "insert")
            if snippet and 1 <= p_idx <= len(doc):
                add_highlight_with_note(doc[p_idx - 1], snippet, GREEN, desc)

        # Gewijzigd
        for pref_old, pref_new in replaces:
            p_idx, txt_new = parse_prefixed(pref_new)
            _, txt_old = parse_prefixed(pref_old)
            snippet = pick_search_snippet(txt_new)
            desc = llm_describe_change(client, txt_old, txt_new, "replace")
            if snippet and 1 <= p_idx <= len(doc):
                add_highlight_with_note(doc[p_idx - 1], snippet, YELLOW, desc)

        # Verwijderd → FreeText-notitie
        for p_idx, count in deletes_by_page.items():
            if count <= 0:
                continue
            if 1 <= p_idx <= len(doc):
                rect = fitz.Rect(36, 36, 300, 80)
                note = doc[p_idx - 1].add_freetext_annot(
                    rect,
                    f"−{count} regel(s) verwijderd t.o.v. versie 1",
                    fontsize=9,
                    rotate=0,
                )
                note.set_colors(stroke=(0.7, 0.1, 0.1), fill=(1, 0.95, 0.95))
                note.update()

        out = io.BytesIO()
        doc.save(out, deflate=True)
        return out.getvalue()

# -----------------------------
# Streamlit app
# -----------------------------

def app():
    st.markdown("## 🔍 Coge")
    st.caption("Contextuele PDF-vergelijking met highlights + LLM-opmerkingen")

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
        v1_pages = extract_pdf_lines(v1_bytes)
        v2_pages = extract_pdf_lines(v2_bytes)

        flat_a = flatten_with_page_prefix(v1_pages)
        flat_b = flatten_with_page_prefix(v2_pages)

        sm = difflib.SequenceMatcher(None, flat_a, flat_b, autojunk=False)
        inserts, deletes, replaces = [], [], []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "insert":
                inserts.extend(flat_b[j1:j2])
            elif tag == "delete":
                deletes.extend(flat_a[i1:i2])
            elif tag == "replace":
                old = flat_a[i1:i2]
                new = flat_b[j1:j2]
                for o, n in zip(old, new):
                    replaces.append((o, n))

        # deletions per pagina tellen
        deletes_by_page: Dict[int, int] = {}
        for pref in deletes:
            p_idx, _ = parse_prefixed(pref)
            deletes_by_page[p_idx] = deletes_by_page.get(p_idx, 0) + 1

        client = get_groq_client()
        out_bytes = annotate_pdf_v2(v2_bytes, inserts, replaces, deletes_by_page, client)

    # Stats
    st.subheader("📊 Markeringen aangebracht")
    st.write(f"➕ Toegevoegd (groen): **{len(inserts)}** regels")
    st.write(f"🔁 Gewijzigd (geel): **{len(replaces)}** regels")
    st.write(f"➖ Verwijderd (rode notitie): **{sum(deletes_by_page.values())}** regels")

    # Download
    st.download_button(
        "⬇️ Download geannoteerde PDF (v2)",
        data=out_bytes,
        file_name=f"{v2.name.rsplit('.pdf', 1)[0]}_annotated.pdf",
        mime="application/pdf",
    )
