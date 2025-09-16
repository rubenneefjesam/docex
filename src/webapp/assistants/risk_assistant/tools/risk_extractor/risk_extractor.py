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
    """Lees plain text uit een .docx; leeg bij fout."""
    try:
        d = docx.Document(path)
        parts = []
        for p in d.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""

def _read_uploaded_text(uploaded) -> str:
    """Ondersteun .docx en .txt als input voor risico-extractie."""
    if not uploaded:
        return ""
    name = (uploaded.name or "").lower()
    if name.endswith(".docx"):
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return _safe_read_docx_text(p)
    # fallback: .txt
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


# =========================
# Helpers: Groq client
# =========================

def _get_groq_client() -> Groq:
    """Zoek GROQ_API_KEY in env of in st.secrets['groq']['api_key']."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        try:
            key = (st.secrets.get("groq", {}) or {}).get("api_key", "").strip()
        except Exception:
            key = ""
    if not key:
        st.sidebar.error("❌ Groq API key niet gevonden. Zet GROQ_API_KEY of gebruik .streamlit/secrets.toml")
        st.stop()
    try:
        return Groq(api_key=key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()


# =========================
# Parser: modeloutput → list
# =========================

def _parse_json_list(text: str) -> List[Dict]:
    """Probeer een JSON-array te vinden in (mogelijk rommelige) modeloutput."""
    cleaned = re.sub(r"\d+\s*:\s*{", "{", text or "")
    start, end = cleaned.find("["), cleaned.rfind("]") + 1
    cand = cleaned[start:end] if start != -1 and end != -1 else cleaned
    try:
        data = json.loads(cand)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


# =========================
# Prompting
# =========================

EXTRACTION_SYSTEM = (
    "Je bent een nauwkeurige annotator. "
    "Extraheer uitsluitend een JSON-array met objecten met exact de velden: "
    '{"risico": "...", "oorzaak": "...", "gevolg": "...", "beheersmaatregel": "..."} '
    "Gebruik geen extra tekst, uitleg of markdown."
)

EXTRACTION_USER_TMPL = """\
Lees de onderstaande tekst en extraheer alle herkenbare risico-items.
GEEF UITSLUITEND EEN JSON-ARRAY terug met objecten:

[
  {{
    "risico": "korte titel/essentie van het risico",
    "oorzaak": "wat is de primaire oorzaak",
    "gevolg": "wat kan er gebeuren (impact)",
    "beheersmaatregel": "uitgebreide maatregelenset: preventief + detectief + correctief (concreet)"
  }},
  ...
]

Richtlijnen:
- Combineer duplicaten (zelfde risico) tot één item met geconsolideerde beheersmaatregelen.
- Houd de tone of voice zakelijk, duidelijk en activerend.
- Als een veld onbekend is: laat het veld leeg als lege string, niet 'n.v.t.'.

TEKST:
{DOCUMENT}
"""

def extract_risks(groq_client: Groq, text: str) -> List[Dict]:
    """Roep LLM aan en normaliseer de uitkomst."""
    if not (text or "").strip():
        return []

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {"role": "user", "content": EXTRACTION_USER_TMPL.format(DOCUMENT=text[:200_000])},
            ],
        )
    except Exception as e:
        st.error(f"Fout bij model-aanroep: {e}")
        return []

    content = resp.choices[0].message.content or ""
    items = _parse_json_list(content)

    # Normaliseer keys en filter lege entries
    normed: List[Dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        risico = (it.get("risico") or "").strip()
        oorzaak = (it.get("oorzaak") or "").strip()
        gevolg = (it.get("gevolg") or "").strip()
        maat = (it.get("beheersmaatregel") or it.get("maatregel") or "").strip()
        if any([risico, oorzaak, gevolg, maat]):
            normed.append({
                "Risico": risico,
                "Oorzaak": oorzaak,
                "Gevolg": gevolg,
                "Beheersmaatregel (uitgebreid)": maat
            })
    return normed


# =========================
# Downloads
# =========================

def _download_bytes_csv(rows: List[Dict]) -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["Risico", "Oorzaak", "Gevolg", "Beheersmaatregel (uitgebreid)"])
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8")

def _download_bytes_json(rows: List[Dict]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")

def _download_bytes_excel(rows: List[Dict]) -> bytes:
    """
    Schrijf naar .xlsx met xlsxwriter of openpyxl; val terug naar CSV als geen engine beschikbaar is.
    """
    try:
        import pandas as pd
    except Exception:
        return _download_bytes_csv(rows)

    from io import BytesIO
    df = pd.DataFrame(rows)
    b = BytesIO()

    engine: Optional[str] = None
    # Probeer xlsxwriter
    try:
        import xlsxwriter  # noqa: F401
        engine = "xlsxwriter"
    except Exception:
        # Probeer openpyxl
        try:
            import openpyxl  # noqa: F401
            engine = "openpyxl"
        except Exception:
            return _download_bytes_csv(rows)

    with pd.ExcelWriter(b, engine=engine) as writer:
        df.to_excel(writer, index=False, sheet_name="Risico's")
    return b.getvalue()


# =========================
# UI
# =========================

def run(show_nav: bool = True):
    st.set_page_config(page_title="Risico Extractor", layout="wide", initial_sidebar_state="expanded")

# 🔹 CSS voor tekstterugloop in de tabel
    st.markdown(
        """
        <style>
        /* Forceer wrapping in st.data_editor cellen */
        div[data-testid="stDataFrame"] td div,
        div[data-testid="stDataEditor"] td div {
            white-space: normal !important;
            word-break: break-word !important;
            overflow-wrap: anywhere !important;
            text-overflow: initial !important;
        }

        /* Je eerdere styling mag er ook nog bij */
        .big-header {font-size:2.2rem; font-weight:800; margin-bottom:0.25em;}
        .section-header {font-size:1.3rem; font-weight:700; margin:0.5em 0;}
        .stButton>button, .stDownloadButton>button {font-size:16px; font-weight:600;}
        </style>
        """,
        unsafe_allow_html=True
    )
    
# CSS toevoegen voor wrapping
    st.markdown(
        """
        <style>
        /* Forceer wrapping in datatabel cellen */
        .stDataFrame, .stDataEditor td div, .stDataEditor td {
            white-space: normal !important;
            word-wrap: break-word !important;
            overflow-wrap: anywhere !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <style>
        .big-header {font-size:2.2rem; font-weight:800; margin-bottom:0.25em;}
        .section-header {font-size:1.3rem; font-weight:700; margin:0.5em 0;}
        .stButton>button, .stDownloadButton>button {font-size:16px; font-weight:600;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='big-header'>⚠️ Risico Extractor</div>", unsafe_allow_html=True)
    st.caption("Upload links een document (.docx of .txt). Rechts verschijnen de geëxtraheerde risico’s.")

    col_left, col_right = st.columns([2, 3], gap="large")

    # ⬅️ LINKS: upload
    with col_left:
        st.markdown("<div class='section-header'>📤 Document upload</div>", unsafe_allow_html=True)
        up = st.file_uploader("Kies .docx of .txt", type=["docx", "txt"], key="risk_doc")
        text = _read_uploaded_text(up)
        groq_client = None
        if up and text.strip():
            groq_client = _get_groq_client()
            st.success("Document geladen. Klik rechts op ‘Extractie starten’.")
        elif up:
            st.warning("Kon geen tekst lezen uit het bestand. Is het een geldige .docx of .txt?")

    # ➡️ RECHTS: extractie + tabel + downloads
    with col_right:
        st.markdown("<div class='section-header'>🧠 Extractie</div>", unsafe_allow_html=True)
        do_extract = st.button(
            "🚀 Extractie starten",
            type="primary",
            use_container_width=True,
            disabled=not (up and (text or "").strip())
        )
        rows: List[Dict] = []

        if do_extract and up and (text or "").strip():
            with st.spinner("Risico’s extraheren…"):
                rows = extract_risks(groq_client, text)

            if rows:
                st.success(f"Gevonden items: {len(rows)}")
                st.data_editor(
        rows,
        use_container_width=True,
        height=min(520, 80 + 32 * (len(rows) + 1)),
        column_config={
            "Risico": st.column_config.TextColumn("Risico", width="small"),
            "Oorzaak": st.column_config.TextColumn("Oorzaak", width="medium"),
            "Gevolg": st.column_config.TextColumn("Gevolg", width="medium"),
            "Beheersmaatregel (uitgebreid)": st.column_config.TextColumn("Beheersmaatregel (uitgebreid)", width="large"),
        },
        hide_index=True,
        disabled=True  # maakt de tabel read-only
    )

                st.markdown("<div class='section-header'>💾 Export</div>", unsafe_allow_html=True)
                csv_b = _download_bytes_csv(rows)
                json_b = _download_bytes_json(rows)
                xls_b = _download_bytes_excel(rows)

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.download_button("⬇️ CSV", data=csv_b, file_name="risico_extractie.csv",
                                       mime="text/csv", use_container_width=True)
                with c2:
                    st.download_button("⬇️ JSON", data=json_b, file_name="risico_extractie.json",
                                       mime="application/json", use_container_width=True)
                with c3:
                    st.download_button("⬇️ Excel", data=xls_b, file_name="risico_extractie.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)
            else:
                st.info("Geen risico’s gevonden of model gaf geen bruikbare output.")
        else:
            st.info("Klik op ‘Extractie starten’ nadat je links een document hebt geüpload.")


# Compat/entry points voor je loader
def app():
    run(show_nav=False)

def render():
    run(show_nav=False)

def main():
    run()
