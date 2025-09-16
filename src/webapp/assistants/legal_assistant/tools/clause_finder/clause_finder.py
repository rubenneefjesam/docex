from __future__ import annotations

import io
import re
import base64
from typing import List, Dict, Tuple

import streamlit as st
import fitz  # PyMuPDF

# Hergebruik Groq client loader
from webapp.assistants.general_support.tools.doc_generator.doc_generator import get_groq_client


# =========================
# PDF helpers
# =========================

@st.cache_data(show_spinner=False)
def pdf_text_by_page(pdf_bytes: bytes) -> List[str]:
    """Geef per pagina de plain text terug."""
    pages: List[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pages.append(page.get_text("text"))
    return pages

def full_text(pages: List[str]) -> str:
    return "\n".join(pages)

def pick_search_snippet(s: str, min_len: int = 12, max_len: int = 120) -> str:
    """Maak een hanteerbaar zoekfragment (kort, maar herkenbaar)."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) > max_len:
        mid = len(s) // 2
        half = max_len // 2
        s = s[mid - half : mid + half]
    return s if len(s) >= min_len else s

def show_pdf_inline(pdf_bytes: bytes, height: int = 900) -> None:
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f"""
        <iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>
        """,
        unsafe_allow_html=True,
    )


# =========================
# LLM extractie
# =========================

SYSTEM = (
    "Je bent een juridisch assistent. "
    "Extraheer clausules uit contracttekst en geef UITSLUITEND een JSON-array terug met objecten: "
    '{"clausule":"...","citaat":"...","uitleg":"...","belang":"..."} '
    "waarbij 'citaat' exact uit het contract komt (liefst 1–3 zinnen)."
)

USER_TMPL = """\
Lees onderstaande contracttekst en extraheer clausules over o.a.:
- Aansprakelijkheid
- Duur en beëindiging
- Geheimhouding
- Betaling / prijs
- Geschillenbeslechting
- Intellectueel eigendom
- Overige belangrijke voorwaarden (bv. audit, boete, overmacht, overdracht, sub-licentie)

Geef ALLEEN een JSON-array terug, bijv.:
[
  {{
    "clausule": "Aansprakelijkheid",
    "citaat": "Exact citaat uit het contract...",
    "uitleg": "Korte interpretatie in heldere taal.",
    "belang": "Waarom dit relevant is voor de partij."
  }}
]

TEKST:
{DOC}
"""

def extract_clauses(text: str) -> List[Dict]:
    if not (text or "").strip():
        return []
    client = get_groq_client()
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(DOC=text[:200_000])},
            ],
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return []

    # Pak eerste JSON array
    m = re.search(r"\[\s*{.*}\s*\]", content, flags=re.S)
    if not m:
        return []

    import json
    try:
        data = json.loads(m.group())
    except Exception:
        return []

    out: List[Dict] = []
    for it in data if isinstance(data, list) else []:
        if not isinstance(it, dict):
            continue
        out.append({
            "Clausule": (it.get("clausule") or "").strip(),
            "Citaat": (it.get("citaat") or "").strip(),
            "Uitleg": (it.get("uitleg") or "").strip(),
            "Belang": (it.get("belang") or "").strip(),
        })
    return out


# =========================
# Annotaties
# =========================

# Kleuren per type clausule (RGB 0..1)
COLOR_MAP = {
    "aansprakelijkheid": (0.95, 0.8, 0.2),   # geel
    "duur":              (0.1, 0.7, 0.1),    # groen
    "beëindiging":       (0.1, 0.7, 0.1),    # groen
    "geheimhouding":     (0.2, 0.6, 0.95),   # blauw
    "betaling":          (0.9, 0.4, 0.2),    # oranje
    "prijs":             (0.9, 0.4, 0.2),    # oranje
    "geschillen":        (0.7, 0.3, 0.9),    # paars
    "intellectueel":     (0.95, 0.3, 0.5),   # roze
    "overmacht":         (0.4, 0.4, 0.4),    # grijs
}

def color_for_clause(name: str) -> Tuple[float, float, float]:
    n = (name or "").lower()
    for key, col in COLOR_MAP.items():
        if key in n:
            return col
    return (1.0, 0.85, 0.0)  # default geel

def add_highlight_with_note(page, snippet: str, color: Tuple[float, float, float], note: str) -> int:
    if not snippet:
        return 0
    try:
        rects = page.search_for(snippet)
    except Exception:
        return 0

    count = 0
    for r in rects:
        annot = page.add_highlight_annot(r)
        annot.set_colors(stroke=color)
        annot.update()
        pt = fitz.Point(r.x1, r.y0)
        note_annot = page.add_text_annot(pt, note, icon="Comment")
        note_annot.update()
        count += 1
    return count

def annotate_clauses(pdf_bytes: bytes, rows: List[Dict]) -> Tuple[bytes, int]:
    total = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for row in rows:
            clause = row.get("Clausule") or ""
            quote  = row.get("Citaat") or ""
            uitleg = row.get("Uitleg") or ""
            belang = row.get("Belang") or ""
            snippet = pick_search_snippet(quote, max_len=180)
            if not snippet:
                continue
            color = color_for_clause(clause)
            note = f"{clause} — {uitleg or belang or 'clausule aangetroffen'}"
            for p in doc:
                total += add_highlight_with_note(p, snippet, color, note)

        out = io.BytesIO()
        doc.save(out, deflate=True)
        return out.getvalue(), total


# =========================
# UI
# =========================

def app() -> None:
    st.markdown("## 📑 Clause Finder (PDF annotaties)")
    st.caption("Upload links een contract (PDF). Rechts zie je dezelfde PDF met gemarkeerde clausules.")

    col_left, col_right = st.columns(2)

    with col_left:
        up = st.file_uploader("📤 Contract (PDF)", type=["pdf"], key="clause_pdf")
        if not up:
            st.info("Upload een PDF om te starten.")
            return

        pdf_bytes = up.getvalue()

        with st.spinner("PDF lezen…"):
            pages = pdf_text_by_page(pdf_bytes)
            text = full_text(pages)

        st.markdown("### 🔎 Extractie")
        do_extract = st.button("🚀 Zoeken en annoteren", type="primary", use_container_width=True)

    with col_right:
        if not up:
            return
        st.markdown("### 👀 Preview geannoteerde PDF")

        if not do_extract:
            show_pdf_inline(pdf_bytes, height=900)
            return

        with st.spinner("Clausules zoeken…"):
            rows = extract_clauses(text)

        if not rows:
            st.info("Geen clausules gevonden door het model.")
            show_pdf_inline(pdf_bytes, height=900)
            return

        with st.spinner("Annotaties toevoegen…"):
            annotated_bytes, total_marks = annotate_clauses(pdf_bytes, rows)

        st.success(f"Gevonden clausules: **{len(rows)}** | Highlights geplaatst: **{total_marks}**")

        st.markdown("### 📋 Gevonden clausules")
        st.data_editor(
            rows,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            column_config={
                "Clausule": st.column_config.TextColumn("Clausule", width="small"),
                "Citaat":   st.column_config.TextColumn("Citaat", width="large"),
                "Uitleg":   st.column_config.TextColumn("Uitleg", width="medium"),
                "Belang":   st.column_config.TextColumn("Belang", width="medium"),
            },
        )

        show_pdf_inline(annotated_bytes, height=900)
        st.download_button(
            "⬇️ Download geannoteerde PDF",
            data=annotated_bytes,
            file_name=f"{up.name.rsplit('.pdf',1)[0]}_clausules.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

def run() -> None:
    return app()

def render() -> None:
    return app()

def main() -> None:
    return app()
