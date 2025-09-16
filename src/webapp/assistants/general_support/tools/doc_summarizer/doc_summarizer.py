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
        doc = docx.Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    elif suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")

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

# ─── Samenvatting via Groq LLM ─────────────────────────────────────
def summarize_with_groq(text: str, fields: Dict[str, str]) -> List[Dict]:
    # Bouw de instructie
    instructions = "\n".join(f"- {name}: {desc}" for name, desc in fields.items())
    prompt = (
        "Je bent een samenvattingsassistent. Geef voor elk veld de gevraagde informatie."
        "Retourneer een JSON-array van objecten met deze velden:\n"
        f"  {', '.join(fields)}\n"
        f"Gebruik per veld de instructies:\n{instructions}\n"
        f"Brontekst:\n{text}\n"
        "Geef alleen de JSON-array zonder extra tekst."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        st.error("Fout bij parsen JSON van Groq:")
        st.code(resp.choices[0].message.content)
        return []

# ─── Streamlit UI ──────────────────────────────────────────────────
def app():
    st.set_page_config(page_title="📄 Document Summarizer (Groq)", layout="wide")
    st.title("📄 Document Summarizer")
    st.write("Upload documenten en genereer een gestructureerde samenvatting via Groq LLM.")

    uploads = st.file_uploader(
        "Upload PDF / DOCX / TXT / MD", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True
    )
    if not uploads:
        st.info("Nog geen bestanden geüpload.")
        return

    # Knop in main area om samenvatting te starten
    if not st.button("🚀 Genereer samenvatting via Groq"):
        return

    # Definieer velden en prompts via sidebar
    st.sidebar.header("Definieer samenvattingsvelden")
    fields: Dict[str, str] = {}
    for i in range(1, 7):
        name = st.sidebar.text_input(f"Veldnaam {i}", key=f"name{i}")
        desc = st.sidebar.text_area(
            f"Beschrijving {i}", height=50, key=f"desc{i}", placeholder=f"Wat wil je voor veld {i} extraheren?"
        )
        if name and desc:
            fields[name] = desc

    if not fields:
        st.sidebar.warning("Definieer minimaal één veld en beschrijving.")
        return

    if st.button("🚀 Genereer samenvatting via Groq"):
        all_results: List[StructuredSummary] = []
        for uf in uploads:
            tmp = Path(f"/tmp/{uf.name}")
            tmp.write_bytes(uf.getvalue())
            text = read_text(tmp)
            raw = summarize_with_groq(text, fields)
            for item in raw:
                ss = StructuredSummary(
                    file_name=uf.name,
                    title=item.get(next(iter(fields)), ""),
                    executive_summary="",
                    key_points=[], actions=[], risks=[], entities={}, word_count=len(text.split())
                )
                # Vul attributen als lists of strings
                for k, v in item.items():
                    if k in {"key_points","actions","risks"} and isinstance(v, list):
                        setattr(ss, k, v)
                    elif k == "entities" and isinstance(v, dict):
                        ss.entities = v
                    elif k == "executive_summary":
                        ss.executive_summary = v
                all_results.append(ss)

        # Toon resultaten
        for ss in all_results:
            with st.expander(f"📘 {ss.file_name}"):
                st.markdown(f"**Titel:** {ss.title}")
                st.markdown(f"**Samenvatting:** {ss.executive_summary}")
                for field in fields:
                    val = getattr(ss, field, None)
                    if isinstance(val, list):
                        st.markdown(f"### {field}")
                        st.write("\n".join(f"- {x}" for x in val))
                    elif val:
                        st.markdown(f"**{field}:** {val}")
                st.markdown(f"_Word count: {ss.word_count}_")

if __name__ == '__main__':
    app()
