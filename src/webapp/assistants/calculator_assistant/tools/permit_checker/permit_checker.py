from __future__ import annotations
import os, re, json, tempfile, io, base64
from typing import List, Dict, Tuple

import streamlit as st
import docx
import fitz  # PyMuPDF

from webapp.assistants.general_support.tools.doc_generator.doc_generator import get_groq_client


# =========================
# Bestandslezers
# =========================

def _safe_read_docx_text(path: str) -> str:
    try:
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs if p.text.strip())
    except Exception:
        return ""

def _read_uploaded_text_and_pdfbytes(uploaded) -> tuple[str, bytes | None]:
    """
    Retourneer (plain_text, pdf_bytes_of_none).
    - Voor PDF: ook de originele bytes teruggeven (voor annotaties).
    """
    if not uploaded:
        return "", None
    name = (uploaded.name or "").lower()

    if name.endswith(".docx"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return _safe_read_docx_text(p), None

    if name.endswith(".pdf"):
        pdf_bytes = uploaded.getvalue()
        parts = []
        try:
            with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
                for page in doc:
                    parts.append(page.get_text("text"))
        except Exception:
            return "", pdf_bytes
        return "\n".join(parts), pdf_bytes

    # txt fallback
    try:
        return uploaded.read().decode("utf-8", errors="ignore"), None
    except Exception:
        return "", None


# =========================
# Prompting
# =========================

SYSTEM = (
    "Je bent een juridisch-ruimtelijk adviseur voor Nederland. "
    "Analyseer de projecttekst en bepaal welke vergunningen aangevraagd moeten worden "
    "voor de beschreven activiteiten (bouw, milieu, gebruik, water, natuur, etc.). "
    "Als er een zoekterm is meegegeven, beperk je dan strikt tot vergunningen die duidelijk relevant zijn voor die zoekterm. "
    "Geef UITSLUITEND een JSON-array terug met objecten: "
    '{"vergunning":"...","beschrijving":"...","waarom":"...","instanties":"...","citaat":"..."} '
    "waarbij 'citaat' een kort exact fragment is uit de projecttekst dat de noodzaak onderbouwt."
)

USER_TMPL = """\
Lees onderstaande projecttekst en genereer een gestructureerde lijst van relevante vergunningen.
Gebruik je kennis van Nederlandse regelgeving en het Omgevingsloket (https://www.omgevingsloket.nl/).
Zoekterm (optioneel): "{SEARCH}"

Geef ALLEEN de JSON-array terug, bijv.:
[
  {{
    "vergunning": "Omgevingsvergunning bouwen",
    "beschrijving": "Vereist voor het oprichten of verbouwen van een bouwwerk.",
    "waarom": "Omdat er een nieuw bouwwerk/uitbreiding staat beschreven in het plan.",
    "instanties": "Gemeente (aanvraag via Omgevingsloket)",
    "citaat": "…exact zinsdeel uit de tekst…"
  }}
]

TEKST:
{DOC}
"""

def _parse_json_array(text: str) -> List[Dict]:
    """Robuust het eerste JSON-array blok pakken, ook met fences/ruis."""
    if not text:
        return []
    text = re.sub(r"```(?:json)?", "", text)
    m = re.search(r"\[\s*{.*}\s*\]", text, flags=re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def extract_permits(doc_text: str, search: str) -> List[Dict]:
    if not (doc_text or "").strip():
        return []

    client = get_groq_client()
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(DOC=doc_text[:180_000], SEARCH=search or "")},
            ],
        )
        content = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return []

    items = _parse_json_array(content)
    out: List[Dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        out.append({
            "Vergunning":   (it.get("vergunning") or "").strip(),
            "Beschrijving": (it.get("beschrijving") or "").strip(),
            "Waarom nodig?":(it.get("waarom") or "").strip(),
            "Instanties":   (it.get("instanties") or "").strip(),
            "Citaat":       (it.get("citaat") or "").strip(),   # verborgen kolom, wel nodig voor highlights
        })
    return out


# =========================
# PDF-annotaties (alleen voor PDF)
# =========================

def _pick_snippet(s: str, min_len: int = 12, max_len: int = 160) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) > max_len:
        mid = len(s) // 2
        half = max_len // 2
        s = s[mid - half : mid + half]
    return s if len(s) >= min_len else s

def _add_highlight_with_note(page, snippet: str, color: Tuple[float, float, float], note: str) -> int:
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

def annotate_pdf_with_permits(pdf_bytes: bytes, rows: List[Dict]) -> tuple[bytes, int]:
    """
    Kleur: geel. Note: 'Vergunning — Waarom nodig?'
    """
    total = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for row in rows:
            verg  = row.get("Vergunning") or ""
            why   = row.get("Waarom nodig?") or ""
            citaat= row.get("Citaat") or ""
            snippet = _pick_snippet(citaat)
            if not snippet:
                continue
            note = f"{verg} — {why or 'vereist volgens tekst'}"
            for p in doc:
                total += _add_highlight_with_note(p, snippet, (1.0, 0.85, 0.0), note)
        out = io.BytesIO()
        doc.save(out, deflate=True)
        return out.getvalue(), total

def _show_pdf_inline(pdf_bytes: bytes, height: int = 900) -> None:
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    st.markdown(
        f"""<iframe src="data:application/pdf;base64,{b64}" width="100%" height="{height}" type="application/pdf"></iframe>""",
        unsafe_allow_html=True,
    )


# =========================
# UI (links besturing + tabel, rechts preview)
# =========================

def app() -> None:
    st.markdown("## 🏛️ Vergunning Checker")
    st.caption("Upload links een projectdocument. Rechts zie je (bij PDF) het document met markeringen. Onder de knop staat de gestructureerde lijst met vergunningen.")

    col_left, col_right = st.columns([2, 3], gap="large")

    with col_left:
        up = st.file_uploader("📤 Document (PDF, DOCX of TXT)", type=["pdf", "docx", "txt"], key="permit_doc")
        search = st.text_input("🔎 Zoekterm (optioneel, bv. 'geluid', 'water', 'natuur')", value="")

        text, pdf_bytes = _read_uploaded_text_and_pdfbytes(up)

        if up:
            n = len(text or "")
            if n == 0:
                st.error("Kon geen tekst extraheren. Is het een gescande PDF/afbeelding? (OCR kan later)")
            elif n < 400:
                st.warning(f"Er is weinig tekst gevonden (~{n} tekens). Resultaten kunnen beperkt zijn.")

        do = st.button("🚀 Analyseer vergunningen", type="primary", use_container_width=True, disabled=not (up and (text or "").strip()))

        rows: List[Dict] = []
        if do and up and (text or "").strip():
            with st.spinner("Vergunningen analyseren…"):
                rows = extract_permits(text, search)

            # Tabel ONDER de knop
            if rows:
                st.success(f"Gevonden vergunningen: **{len(rows)}**")
                # styling voor wrapping
                st.markdown(
                    """
                    <style>
                    div[data-testid="stDataEditor"] td div {
                        white-space: normal !important;
                        word-break: break-word !important;
                        overflow-wrap: anywhere !important;
                        text-overflow: initial !important;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                # toon zonder 'Citaat' kolom (wel behouden in rows voor highlights)
                rows_for_grid = [
                    {k: v for k, v in r.items() if k != "Citaat"} for r in rows
                ]
                st.data_editor(
                    rows_for_grid,
                    use_container_width=True,
                    hide_index=True,
                    disabled=True,
                    column_config={
                        "Vergunning":    st.column_config.TextColumn("Vergunning", width="medium"),
                        "Beschrijving":  st.column_config.TextColumn("Beschrijving", width="large"),
                        "Waarom nodig?": st.column_config.TextColumn("Waarom nodig?", width="large"),
                        "Instanties":    st.column_config.TextColumn("Instanties", width="medium"),
                    },
                )
            else:
                st.info("Geen vergunningen gevonden of model gaf geen output.")

    with col_right:
        # PDF-preview met highlights rechts
        if not up:
            st.info("Upload links een document om te starten.")
            return

        if not do:
            # toon originele PDF indien beschikbaar
            if pdf_bytes:
                _show_pdf_inline(pdf_bytes, height=900)
            else:
                st.info("Preview met markeringen is alleen beschikbaar voor PDF-bestanden.")
            return

        # we willen annoteren als: PDF + er zijn resultaten (rows)
        # rows zitten in de closure van de linkerkolom; dus herbereken kort (veilig & cheap)
        if (text or "").strip():
            rows = extract_permits(text, search)  # idem als links — houdt UI simpel
        else:
            rows = []

        if pdf_bytes and rows:
            with st.spinner("Annotaties toevoegen aan PDF…"):
                annotated_bytes, total = annotate_pdf_with_permits(pdf_bytes, rows)
            st.success(f"Highlights geplaatst: **{total}**")
            _show_pdf_inline(annotated_bytes, height=900)
            st.download_button(
                "⬇️ Download geannoteerde PDF",
                data=annotated_bytes,
                file_name=f"{(up.name or 'document').rsplit('.',1)[0]}_vergunningen.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            if not pdf_bytes:
                st.info("Preview met markeringen is alleen beschikbaar voor PDF-bestanden.")
            else:
                _show_pdf_inline(pdf_bytes, height=900)  # geen resultaten → toon origineel


def run() -> None:
    return app()

def render() -> None:
    return app()

def main() -> None:
    return app()
