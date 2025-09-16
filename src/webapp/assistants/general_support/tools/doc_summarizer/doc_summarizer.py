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

# ─── Samenvatting via Groq LLM ────────────────────────────────────
def summarize_with_groq(text: str, file_name: str) -> StructuredSummary:
    prompt = (
        "Je bent een documentassistent. Maak van de volgende tekst een gestructureerde samenvatting. "
        f"\nTekst: {text}\n"
        "Geef alleen de JSON-output zonder extra toelichting."
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.choices[0].message.content.strip()
    # strip code fences
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.strip("```\n")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        st.error("Fout bij parsen van samenvatting:")
        st.code(raw)
        data = {
            "title": "",
            "executive_summary": "",
            "key_points": [],
            "actions": [],
            "risks": [],
            "entities": {"years": [], "eur": [], "emails": [], "urls": []},
            "word_count": len(text.split())
        }
    return StructuredSummary(
        file_name=file_name,
        title=data.get("title", ""),
        executive_summary=data.get("executive_summary", ""),
        key_points=data.get("key_points", []),
        actions=data.get("actions", []),
        risks=data.get("risks", []),
        entities=data.get("entities", {}),
        word_count=data.get("word_count", len(text.split()))
    )

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
            for kp in ss.key_points:
                st.write(f"- {kp}")
            st.markdown("**Actions:**")
            for a in ss.actions:
                st.write(f"- {a}")
            st.markdown("**Risks:**")
            for r in ss.risks:
                st.write(f"- {r}")
            st.markdown("**Entities:**")
            for k, vals in ss.entities.items():
                st.write(f"- **{k}**: {', '.join(vals)}")
            st.write(f"_Word count: {ss.word_count}_")
            js = json.dumps(asdict(ss), ensure_ascii=False, indent=2).encode("utf-8")
            st.download_button(
                label="⬇️ Download JSON",
                data=js,
                file_name=f"{ss.file_name}_summary.json",
                mime="application/json"
            )

if __name__ == '__main__':
    app()