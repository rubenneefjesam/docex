from __future__ import annotations

import os
import tempfile
import re
import json
from typing import List, Dict

import streamlit as st
import docx
import fitz  # PyMuPDF

from webapp.assistants.general_support.tools.doc_generator.doc_generator import get_groq_client


# =========================
# Helpers: bestand lezen
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

    # DOCX
    if name.endswith(".docx"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return _safe_read_docx_text(p)

    # PDF
    if name.endswith(".pdf"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.pdf")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        parts = []
        with fitz.open(p) as doc:
            for page in doc:
                parts.append(page.get_text("text"))
        return "\n".join(parts)

    # TXT
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


# =========================
# Prompting
# =========================

SYSTEM = (
    "Je bent een juridisch-ruimtelijk adviseur. "
    "Analyseer het document en bepaal welke vergunningen aangevraagd moeten worden "
    "voor de beschreven activiteiten of bouw/ontwikkelplannen. "
    "Geef uitsluitend een JSON-array terug met objecten: "
    '{"vergunning":"...","beschrijving":"...","waarom":"...","instanties":"..."}'
)

USER_TMPL = """\
Lees onderstaande projecttekst en genereer een gestructureerde lijst van relevante vergunningen.
Gebruik hierbij ook de informatie van het officiële Omgevingsloket: https://www.omgevingsloket.nl/
en andere algemene kennis van Nederlandse vergunningen.

Voorbeeld output:
[
  {{
    "vergunning": "Omgevingsvergunning bouwen",
    "beschrijving": "Vergunning vereist voor het oprichten of verbouwen van een bouwwerk.",
    "waarom": "Omdat er een nieuw gebouw geplaatst wordt in het projectplan.",
    "instanties": "Gemeente via Omgevingsloket"
  }},
  {{
    "vergunning": "Milieuvergunning",
    "beschrijving": "Vergunning voor activiteiten die gevolgen hebben voor het milieu.",
    "waarom": "Omdat er sprake is van mogelijke uitstoot/afvalwater.",
    "instanties": "Gemeente / Provincie via Omgevingsloket"
  }}
]

TEKST:
{DOC}
"""


def extract_permits(text: str) -> List[Dict]:
    if not (text or "").strip():
        return []
    client = get_groq_client()

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(DOC=text[:180_000])},
            ],
        )
        content = resp.choices[0].message.content or ""
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return []

    # Zoek JSON-array in output
    m = re.search(r"\[\s*{.*}\]", content, flags=re.S)
    if not m:
        return []

    try:
        data = json.loads(m.group())
    except Exception:
        return []

    out: List[Dict] = []
    for it in data if isinstance(data, list) else []:
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
# UI
# =========================

def app() -> None:
    st.markdown("## 🏛️ Vergunning Checker")
    st.caption("Upload een projectdocument. De tool geeft een gestructureerde lijst met relevante vergunningen.")

    up = st.file_uploader("📤 Document (PDF, DOCX of TXT)", type=["pdf", "docx", "txt"], key="permit_doc")

    if not up:
        st.info("Upload een document om te starten.")
        return

    text = _read_uploaded_text(up)
    if not text.strip():
        st.warning("Kon geen tekst lezen uit het bestand.")
        return

    if st.button("🚀 Analyseer vergunningen", type="primary", use_container_width=True):
        with st.spinner("Vergunningen analyseren…"):
            rows = extract_permits(text)

        if not rows:
            st.info("Geen vergunningen gevonden of model gaf geen output.")
            return

        st.success(f"Gevonden vergunningen: **{len(rows)}**")
        st.data_editor(
            rows,
            use_container_width=True,
            hide_index=True,
            disabled=True,
            column_config={
                "Vergunning": st.column_config.TextColumn("Vergunning", width="medium"),
                "Beschrijving": st.column_config.TextColumn("Beschrijving", width="large"),
                "Waarom nodig?": st.column_config.TextColumn("Waarom nodig?", width="large"),
                "Instanties": st.column_config.TextColumn("Instanties", width="medium"),
            },
        )

        st.markdown("---")
        st.markdown("ℹ️ Meer info en officiële checks via het [Omgevingsloket](https://www.omgevingsloket.nl/).")


def run() -> None:
    return app()

def render() -> None:
    return app()

def main() -> None:
    return app()
