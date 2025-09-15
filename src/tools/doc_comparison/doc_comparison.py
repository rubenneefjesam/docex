# tools/doc_comparison/Document comparison.py
import io
import re
import difflib
import base64
from typing import List, Tuple, Dict, Optional
from tools.doc_extractor.doc_extractor import get_groq_client

import streamlit as st
import fitz  # PyMuPDF

# Hergebruik de Groq client loader uit Document generator (voor fallback-beschrijvingen)
from tools.doc_extractor.doc_extractor import get_groq_client

# =========================
# PDF / Extract helpers
# =========================

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
    flat: List[str] = []
    for p_idx, lines in enumerate(pages, start=1):
        for ln in lines:
            flat.append(f"p{p_idx}:{ln}")
    return flat

def parse_prefixed(line: str) -> Tuple[int, str]:
    m = re.match(r"p(\d+):(.*)", line, flags=re.DOTALL)
    if not m:
        return 1, line
    return int(m.group(1)), m.group(2).strip()

def pick_search_snippet(s: str, min_len: int = 12, max_len: int = 80) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        mid = len(s) // 2
        half = max_len // 2
        s = s[mid - half : mid + half]
    return s if len(s) >= min_len else s

def first_title_line(pages: List[List[str]]) -> str:
    if not pages or not pages[0]:
        return ""
    return pages[0][0].strip()

def full_text(pages: List[List[str]]) -> str:
    return "\n".join("\n".join(pg) for pg in pages)

def similarity_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

# =========================
# Domain heuristics
# =========================

UNKNOWN_TOKENS = {"", "-", "—", "n.v.t.", "nvt", "n/a", "na", "tbd", "onbekend", "niet ingevuld"}

LABEL_REGEXES = [
    ("prijs",      r"\b(prijs|bedrag|kosten|aanneemsom|tarief)\b"),
    ("datum",      r"\b(datum|date)\b"),
    ("email",      r"\b(e[- ]?mail|mail)\b"),
    ("telefoon",   r"\b(tel|telefoon|phone)\b"),
    ("contact",    r"\b(contact|contactpersoon|naam)\b"),
    ("project",    r"\b(project|projectnaam|opdracht|titel)\b"),
]

RE_NUMBER = re.compile(r"\b\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d+)?\b")
RE_DATE   = re.compile(r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}|\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b")
RE_EMAIL  = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_PHONE  = re.compile(r"\+?\d[\d\s\-\(\)]{6,}\d")

def split_label_value(s: str) -> Tuple[Optional[str], str]:
    if ":" in s:
        label, value = s.split(":", 1)
        return label.strip(), value.strip()
    return None, s.strip()

def label_key(label: Optional[str]) -> Optional[str]:
    if not label:
        return None
    lower = label.lower()
    for key, pat in LABEL_REGEXES:
        if re.search(pat, lower):
            return key
    return None

def is_unknown_value(v: str) -> bool:
    v_norm = re.sub(r"\s+", " ", v).strip().lower()
    return v_norm in UNKNOWN_TOKENS

def detect_number_change(old: str, new: str) -> Optional[Tuple[str, str]]:
    o = RE_NUMBER.findall(old)
    n = RE_NUMBER.findall(new)
    if o and n and (o[0] != n[0]):
        return o[0], n[0]
    return None

def detect_date_change(old: str, new: str) -> Optional[Tuple[str, str]]:
    o = RE_DATE.findall(old)
    n = RE_DATE.findall(new)
    if o and n and (o[0] != n[0]):
        return o[0], n[0]
    return None

def detect_contact_filled(old: str, new: str) -> Optional[str]:
    had_email = bool(RE_EMAIL.search(old))
    new_email = RE_EMAIL.search(new)
    if (not had_email) and new_email:
        return f"E-mail ingevuld: {new_email.group(0)}"
    had_phone = bool(RE_PHONE.search(old))
    new_phone = RE_PHONE.search(new)
    if (not had_phone) and new_phone:
        return f"Telefoonnummer ingevuld: {new_phone.group(0)}"
    return None

# =========================
# LLM fallback
# =========================

def llm_describe_change(client, old: str, new: str, change_type: str) -> str:
    prompt = (
        f"Beschrijf kort wat er is veranderd ({change_type}). "
        "Geef 1 zin, concreet (bv. 'Aantal aangepast van 20 naar 40')."
        f"\nOud: {old or '(leeg)'}\nNieuw: {new or '(leeg)'}"
    )
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {"role": "system", "content": "Antwoord alleen met de korte beschrijving."},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"{change_type.capitalize()}"

def describe_change(old_line: str, new_line: str) -> str:
    _, old_txt = parse_prefixed(old_line)
    _, new_txt = parse_prefixed(new_line)

    old_label, old_val = split_label_value(old_txt)
    new_label, new_val = split_label_value(new_txt)
    key = label_key(new_label or old_label)

    if key and is_unknown_value(old_val) and not is_unknown_value(new_val) and new_val:
        return f"Veld {key} ingevuld: van onbekend → {new_val}"

    contact_msg = detect_contact_filled(old_txt, new_txt)
    if contact_msg:
        return contact_msg

    nv = detect_number_change(old_txt, new_txt)
    if nv:
        return f"Aantal aangepast: {nv[0]} → {nv[1]}"

    dv = detect_date_change(old_txt, new_txt)
    if dv:
        return f"Datum aangepast: {dv[0]} → {dv[1]}"

    client = get_groq_client()
    return llm_describe_change(client, old_txt, new_txt, "replace")

def describe_insert(new_line: str) -> str:
    _, new_txt = parse_prefixed(new_line)
    label, val = split_label_value(new_txt)
    key = label_key(label)
    if key and not is_unknown_value(val) and val:
        return f"Nieuw veld: {key} = {val}"
    contact_msg = detect_contact_filled("", new_txt)
    if contact_msg:
        return contact_msg
    client = get_groq_client()
    return llm_describe_change(client, "", new_txt, "insert")

# =========================
# Annotaties (PDF)
# =========================

def add_highlight_with_note(page, text, color, note):
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
                    replaces: List[Tuple[str, str]]) -> bytes:
    GREEN = (0.1, 0.7, 0.1)
    YELLOW = (0.95, 0.8, 0.2)

    with fitz.open(stream=v2_bytes, filetype="pdf") as doc:
        for pref in inserts:
            p_idx, txt = parse_prefixed(pref)
            snippet = pick_search_snippet(txt)
            note = describe_insert(pref)
            if snippet and 1 <= p_idx <= len(doc):
                add_highlight_with_note(doc[p_idx - 1], snippet, GREEN, note)

        for old_pref, new_pref in replaces:
            p_idx, new_txt = parse_prefixed(new_pref)
            snippet = pick_search_snippet(new_txt)
            note = describe_change(old_pref, new_pref)
            if snippet and 1 <= p_idx <= len(doc):
                add_highlight_with_note(doc[p_idx - 1], snippet, YELLOW, note)

        out = io.BytesIO()
        doc.save(out, deflate=True)
        return out.getvalue()

# =========================
# UI helpers
# =========================

def show_pdf_inline(pdf_bytes: bytes, height: int = 800):
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    html = f'''
    <iframe
        src="data:application/pdf;base64,{b64}"
        width="100%"
        height="{height}"
        type="application/pdf">
    </iframe>
    '''
    st.markdown(html, unsafe_allow_html=True)

# =========================
# Streamlit app
# =========================

def app():
    st.markdown("## 🔍 Document comparison")
    st.caption("Contextuele annotaties in PDF v2 + frontend-waarschuwing")

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

    with st.spinner("PDF’s lezen…"):
        v1_pages = extract_pdf_lines(v1_bytes)
        v2_pages = extract_pdf_lines(v2_bytes)

    # Waarschuwing bij groot verschil
    title1 = first_title_line(v1_pages)
    title2 = first_title_line(v2_pages)
    sim_global = similarity_ratio(full_text(v1_pages), full_text(v2_pages))
    sim_title = similarity_ratio(title1, title2) if title1 and title2 else 0.0

    if sim_global < 0.55 or sim_title < 0.5:
        st.warning(
            f"⚠️ Documenten lijken sterk te verschillen.\n\n"
            f"**Titel v1:** {title1 or '(onbekend)'}\n\n"
            f"**Titel v2:** {title2 or '(onbekend)'}\n\n"
            f"**Globale gelijkenis:** {sim_global:.2f} | **Titelgelijkenis:** {sim_title:.2f}"
        )

    with st.spinner("Verschillen detecteren en annoteren…"):
        flat_a = flatten_with_page_prefix(v1_pages)
        flat_b = flatten_with_page_prefix(v2_pages)

        sm = difflib.SequenceMatcher(None, flat_a, flat_b, autojunk=False)
        inserts: List[str] = []
        replaces: List[Tuple[str, str]] = []

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "insert":
                inserts.extend(flat_b[j1:j2])
            elif tag == "replace":
                old = flat_a[i1:i2]
                new = flat_b[j1:j2]
                for o, n in zip(old, new):
                    replaces.append((o, n))

        out_bytes = annotate_pdf_v2(v2_bytes, inserts, replaces)

    # Stats
    st.subheader("📊 Markeringen")
    st.write(f"➕ Toegevoegd (groen): **{len(inserts)}** regels")
    st.write(f"🔁 Gewijzigd (geel): **{len(replaces)}** regels")

    # Inline preview
    st.subheader("👀 Preview geannoteerde PDF")
    show_pdf_inline(out_bytes, height=900)

    # Download
    st.download_button(
        "⬇️ Download geannoteerde PDF (v2)",
        data=out_bytes,
        file_name=f"{v2.name.rsplit('.pdf', 1)[0]}_annotated.pdf",
        mime="application/pdf",
    )