from __future__ import annotations
import os, re, json, tempfile
from typing import List, Dict

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

def _read_uploaded_text(uploaded) -> str:
    if not uploaded:
        return ""
    name = (uploaded.name or "").lower()

    if name.endswith(".docx"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return _safe_read_docx_text(p)

    if name.endswith(".pdf"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.pdf")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        parts = []
        try:
            with fitz.open(p) as doc:
                for page in doc:
                    parts.append(page.get_text("text"))
        except Exception:
            return ""
        return "\n".join(parts)

    # txt fallback
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


# =========================
# Prompting
# =========================

SYSTEM = (
    "Je bent een juridisch-ruimtelijk adviseur voor Nederland. "
    "Analyseer de projecttekst en bepaal welke vergunningen aangevraagd moeten worden "
    "voor de beschreven activiteiten (bouw, milieu, gebruik, water, natuur, etc.). "
    "Geef UITSLUITEND een JSON-array terug met objecten: "
    '{"vergunning":"...","beschrijving":"...","waarom":"...","instanties":"..."} '
    "Wees specifiek en concreet, maar maak geen feitelijke claims buiten de tekst; maak dan een redelijke inschatting."
)

USER_TMPL = """\
Lees onderstaande projecttekst en genereer een gestructureerde lijst van relevante vergunningen.
Gebruik je kennis van Nederlandse regelgeving en verwijs in je overwegingen (niet in de JSON) naar het Omgevingsloket (https://www.omgevingsloket.nl/).
Let op: geef ALLEEN de JSON-array terug, zonder extra tekst.

Voorbeeld:
[
  {{
    "vergunning": "Omgevingsvergunning bouwen",
    "beschrijving": "Vereist voor het oprichten of verbouwen van een bouwwerk.",
    "waarom": "Omdat er een nieuw bouwwerk/uitbreiding staat beschreven in het plan.",
    "instanties": "Gemeente (aanvraag via Omgevingsloket)"
  }},
  {{
    "vergunning": "Activiteiten milieubelastende inrichtingen",
    "beschrijving": "Melding of vergunning voor milieubelastende activiteiten (emissies, geluid, afvalwater).",
    "waarom": "Beschrijving duidt op opslag/uitstoot/lozingen.",
    "instanties": "Gemeente/Omgevingsdienst (via Omgevingsloket)"
  }}
]

TEKST:
{DOC}
"""

def _parse_json_array(text: str) -> List[Dict]:
    """Robuust het eerste JSON-array blok pakken, ook als er fences of uitleg omheen staat."""
    if not text:
        return []
    # strip code fences
    text = re.sub(r"```(?:json)?", "", text)
    m = re.search(r"\[\s*{.*}\s*\]", text, flags=re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group())
        return data if isinstance(data, list) else []
    except Exception:
        return []

def extract_permits(doc_text: str) -> List[Dict]:
    if not (doc_text or "").strip():
        return []

    client = get_groq_client()
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(DOC=doc_text[:180_000])},
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
            "Vergunning": (it.get("vergunning") or "").strip(),
            "Beschrijving": (it.get("beschrijving") or "").strip(),
            "Waarom nodig?": (it.get("waarom") or "").strip(),
            "Instanties": (it.get("instanties") or "").strip(),
        })
    return out


# =========================
# UI (upload links, output rechts)
# =========================

def app() -> None:
    st.markdown("## 🏛️ Vergunning Checker")
    st.caption("Upload links een projectdocument. Rechts verschijnt een gestructureerde lijst met relevante vergunningen.")

    # kolommen
    col_left, col_right = st.columns([2, 3], gap="large")

    with col_left:
        up = st.file_uploader("📤 Document (PDF, DOCX of TXT)", type=["pdf", "docx", "txt"], key="permit_doc")
        text = _read_uploaded_text(up)

        # kwaliteit/diagnose
        if up:
            n = len(text or "")
            if n == 0:
                st.error("Kon geen tekst extraheren uit dit bestand. Is het een gescande PDF/afbeelding? (OCR volgt later)")
            elif n < 400:
                st.warning(f"Er is erg weinig tekst gevonden (~{n} tekens). Resultaten kunnen beperkt zijn.")

        do = st.button("🚀 Analyseer vergunningen", type="primary", use_container_width=True, disabled=not (up and (text or "").strip()))

    with col_right:
        if not up:
            st.info("Upload links een document om te starten.")
            return

        if not do:
            st.info("Klik op ‘Analyseer vergunningen’ om te starten.")
            return

        with st.spinner("Vergunningen analyseren…"):
            rows = extract_permits(text)

        if not rows:
            st.info("Geen vergunningen gevonden of model gaf geen output.")
            st.markdown("ℹ️ Check handmatig via het [Omgevingsloket](https://www.omgevingsloket.nl/).")
            return

        # Styling voor wrapping
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

        st.success(f"Gevonden vergunningen: **{len(rows)}**")
        st.data_editor(
            rows,
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
        st.markdown("ℹ️ Meer info en officiële checks: [Omgevingsloket](https://www.omgevingsloket.nl/).")

def run() -> None:
    return app()

def render() -> None:
    return app()

def main() -> None:
    return app()
