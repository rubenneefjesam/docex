import os
import io
import re
import json
import tempfile
from typing import List, Dict, Optional

import streamlit as st
from groq import Groq
import docx


# =========================
# Helpers: bestanden & tekst
# =========================

def _safe_read_docx_text(path: str) -> str:
    try:
        d = docx.Document(path)
        return "\n".join(p.text.strip() for p in d.paragraphs if p.text.strip())
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
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


# =========================
# Groq client
# =========================

def _get_groq_client() -> Groq:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        try:
            key = (st.secrets.get("groq", {}) or {}).get("api_key", "").strip()
        except Exception:
            key = ""
    if not key:
        st.sidebar.error("❌ Groq API key niet gevonden. Zet GROQ_API_KEY of gebruik .streamlit/secrets.toml")
        st.stop()
    return Groq(api_key=key)


# =========================
# Prompting
# =========================

CLAUSE_SYSTEM = (
    "Je bent een juridisch assistent. "
    "Extraheer clausules uit contractteksten. "
    "Geef altijd een JSON-array met objecten met velden: "
    '{"clausule": "...", "tekst": "...", "uitleg": "...", "belang": "..."}'
)

CLAUSE_USER_TMPL = """\
Lees de onderstaande contracttekst en extraheer clausules die te maken hebben met:

- Aansprakelijkheid
- Duur / beëindiging
- Geheimhouding
- Betaling / prijs
- Geschillenbeslechting
- Overige belangrijke voorwaarden

Geef ALLEEN een JSON-array terug in dit formaat:

[
  {{
    "clausule": "Naam van de clausule (bv. Aansprakelijkheid)",
    "tekst": "Exact citaat uit het contract",
    "uitleg": "Korte interpretatie in heldere taal",
    "belang": "Waarom dit relevant is voor de partij"
  }},
  ...
]

TEKST:
{DOCUMENT}
"""

def extract_clauses(groq_client: Groq, text: str) -> List[Dict]:
    if not text.strip():
        return []
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0.2,
        messages=[
            {"role": "system", "content": CLAUSE_SYSTEM},
            {"role": "user", "content": CLAUSE_USER_TMPL.format(DOCUMENT=text[:200_000])},
        ],
    )
    content = resp.choices[0].message.content or ""
    try:
        data = json.loads(re.search(r"\[.*\]", content, re.S).group())
        return data if isinstance(data, list) else []
    except Exception:
        return []


# =========================
# Downloads
# =========================

def _download_bytes_csv(rows: List[Dict]) -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Clausule", "Tekst", "Uitleg", "Belang"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

def _download_bytes_json(rows: List[Dict]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


# =========================
# UI
# =========================

def run(show_nav: bool = True):
    st.set_page_config(page_title="Clausulezoeker", layout="wide", initial_sidebar_state="expanded")

    st.markdown(
        """
        <style>
        div[data-testid="stDataEditor"] td div {
            white-space: normal !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
            text-overflow: initial !important;
        }
        .big-header {font-size:2.2rem; font-weight:800; margin-bottom:0.25em;}
        .section-header {font-size:1.3rem; font-weight:700; margin:0.5em 0;}
        .stButton>button, .stDownloadButton>button {font-size:16px; font-weight:600;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='big-header'>📑 Clausulezoeker</div>", unsafe_allow_html=True)
    st.caption("Upload een contract (.docx of .txt) en krijg de belangrijkste clausules eruit gefilterd.")

    # 📤 Upload
    st.markdown("<div class='section-header'>📤 Document upload</div>", unsafe_allow_html=True)
    up = st.file_uploader("Kies .docx of .txt", type=["docx", "txt"], key="clause_doc")
    text = _read_uploaded_text(up)
    groq_client = None
    if up and text.strip():
        groq_client = _get_groq_client()
        st.success("Document geladen. Klik hieronder op ‘Zoek clausules’.")
    elif up:
        st.warning("Kon geen tekst lezen uit het bestand.")

    # 🔎 Extractie
    st.markdown("<div class='section-header'>🔎 Extractie</div>", unsafe_allow_html=True)
    do_extract = st.button("🚀 Zoek clausules", type="primary", use_container_width=True, disabled=not (up and text.strip()))

    rows: List[Dict] = []
    if do_extract and up and text.strip():
        with st.spinner("Clausules zoeken…"):
            rows = extract_clauses(groq_client, text)

        if rows:
            st.success(f"Gevonden clausules: {len(rows)}")
            st.data_editor(
                rows,
                use_container_width=True,
                column_config={
                    "clausule": st.column_config.TextColumn("Clausule", width="small"),
                    "tekst": st.column_config.TextColumn("Tekst", width="large"),
                    "uitleg": st.column_config.TextColumn("Uitleg", width="medium"),
                    "belang": st.column_config.TextColumn("Belang", width="medium"),
                },
                hide_index=True,
                disabled=True
            )

            st.markdown("<div class='section-header'>💾 Export</div>", unsafe_allow_html=True)
            csv_b = _download_bytes_csv(rows)
            json_b = _download_bytes_json(rows)

            c1, c2 = st.columns(2)
            with c1:
                st.download_button("⬇️ CSV", data=csv_b, file_name="clausules.csv", mime="text/csv", use_container_width=True)
            with c2:
                st.download_button("⬇️ JSON", data=json_b, file_name="clausules.json", mime="application/json", use_container_width=True)
        else:
            st.info("Geen clausules gevonden.")
    else:
        st.info("Upload een document en klik op ‘Zoek clausules’.")


def app():
    run(show_nav=False)

def render():
    run(show_nav=False)

def main():
    run()
