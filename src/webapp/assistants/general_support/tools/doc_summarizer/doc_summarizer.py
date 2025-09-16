from __future__ import annotations
import os, json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict
import streamlit as st
from groq import Groq
from PyPDF2 import PdfReader
import docx

# ─── Groq Client Initialisatie ───────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; samenvatting werkt niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        st.error("❌ Ongeldige Groq-API-key.")
        return None

client = init_groq_client()

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = docx.Document(str(file_path))
        return "\n".join(p.text for p in document.paragraphs)
    elif suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")

# ─── Dataclass voor samenvatting ──────────────────────────────────
@dataclass
class StructuredSummary:
    file_name: str
    title: str
    executive_summary: str
    key_points: List[str]
    actions: List[str]
    risks: List[str]
    entities: Dict[str, List[str]]
    word_count: int

# ─── Samenvatting met Groq LLM ────────────────────────────────────
def summarize_with_groq(text: str, file_name: str) -> StructuredSummary:
    prompt = (
        "Je bent een documentassistent. Maak van de volgende tekst een gestructureerde samenvatting in JSON."
        " JSON-object moet de volgende keys bevatten:"
        " title (string), executive_summary (string), key_points (array van strings),"
        " actions (array van strings), risks (array van strings),"
        " entities (object met lijsten: years, eur, emails, urls), word_count (aantal woorden)."
        f"\nTekst: {text}\n"
        "Geef alleen de JSON-output zonder extra toelichting."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        data = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        st.error("Fout bij parsen van samenvatting:")
        st.code(resp.choices[0].message.content)
        # fallback lege
        data = {"title":"","executive_summary":"","key_points":[],"actions":[],"risks":[],"entities":{},"word_count":len(text.split())}
    return StructuredSummary(file_name=file_name, **data)

# ─── Streamlit UI ──────────────────────────────────────────────────

def app():
    st.set_page_config(page_title="📄 Document Summarizer (Groq)", layout="wide")
    st.title("📄 Document Summarizer")
    st.write("Upload één of meerdere documenten en klik op ‘Genereer samenvatting’ om een JSON-samenvatting te ontvangen.")

    uploads = st.file_uploader(
        "Upload PDF / DOCX / TXT / MD", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True
    )
    if not uploads:
        st.info("Nog geen bestanden geüpload.")
        return

    if not st.button("🚀 Genereer samenvatting via Groq"):
        return

    summaries: List[StructuredSummary] = []
    for uf in uploads:
        tmp = Path(f"/tmp/{uf.name}")
        tmp.write_bytes(uf.getvalue())
        text = read_text(tmp)
        summaries.append(summarize_with_groq(text, uf.name))

    for ss in summaries:
        with st.expander(f"📘 {ss.file_name}", expanded=True):
            st.subheader(ss.title)
            st.markdown("**Executive summary:**")
            st.write(ss.executive_summary)
            st.markdown("**Key points:**")
            st.markdown("\n".join(f"- {kp}" for kp in ss.key_points))
            st.markdown("**Actions:**")
            st.markdown("\n".join(f"- {a}" for a in ss.actions))
            st.markdown("**Risks:**")
            st.markdown("\n".join(f"- {r}" for r in ss.risks))
            st.markdown("**Entities:**")
            for k,v in ss.entities.items():
                st.write(f"- **{k}**: {', '.join(v)}")
            st.write(f"_Word count: {ss.word_count}_")
            # Download JSON per document
            js = json.dumps(asdict(ss), ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                label="⬇️ Download JSON",
                data=js,
                file_name=f"{ss.file_name}_summary.json",
                mime="application/json"
            )

if __name__ == '__main__':
    app()