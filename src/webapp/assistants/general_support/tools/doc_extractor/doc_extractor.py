import os
import io
import json
from pathlib import Path

import streamlit as st
import pandas as pd
from groq import Groq
from PyPDF2 import PdfReader
import docx

# ─── Groq Client Initialisatie ───────────────────────────────────
@st.cache_resource
def init_groq_client():
    """
    Initialiseert een Groq-client vanuit env-var of Streamlit secrets.
    Toont een foutmelding als er geen geldige key gevonden wordt.
    """
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        key = st.secrets.get("groq", {}).get("api_key", "").strip()
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; extractie werkt niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        st.error("❌ Ongeldige Groq-API-key.")
        return None

client = init_groq_client()

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text_from_file(file_path: Path) -> str:
    """
    Leest tekst uit PDF, DOCX of TXT.
    """
    suffix = file_path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            text += page.extract_text() or ""
    elif suffix == ".docx":
        doc = docx.Document(str(file_path))
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")
    return text

# ─── Extractie via Groq LLM (gepaarde output) ─────────────────────
def extract_paired_entries(file_path: Path, field_prompts: dict[str, str]) -> list[dict]:
    """
    Extraheert velden uit document als lijst met dicts.
    field_prompts: mapping veldnaam -> instructie.
    """
    if client is None:
        return []
    text = read_text_from_file(file_path)
    fields = list(field_prompts.keys())
    instructions = "\n".join(f"- {f}: {p}" for f, p in field_prompts.items())
    prompt = (
        "Je bent een assistent die specifieke informatie uit een document haalt.\n"
        "Geef als output een JSON-array van objecten, met properties:\n"
        f"  {', '.join(fields)}\n\n"
        "Gebruik de volgende instructies per property:\n"
        f"{instructions}\n\n"
        "Documenttekst:\n"
        f"{text}\n\n"
        "Geef alleen de JSON-array terug, zonder extra tekst of markdown."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        st.error("Kan JSON niet parsen, ontvang:")
        st.code(content)
    return []

# ─── Streamlit-applicatie ─────────────────────────────────────────
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor (Groq LLM)")
    st.write(
        "Upload documenten, definieer kolommen en prompts, en klik op ‘Extraheer informatie’."
    )

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.subheader("1️⃣ Upload documenten")
        uploads = st.file_uploader(
            "Kies documenten (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
        )
        extract_btn = st.button("🚀 Extraheer informatie")

    with col2:
        st.subheader("2️⃣ Kolomnamen (optioneel)")
        names = [st.text_input(f"Veldnaam {i+1}", key=f"name_{i}") for i in range(7)]

    with col3:
        st.subheader("3️⃣ Promptbeschrijvingen")
        prompts = [
            st.text_input(
                f"Prompt {i+1}",
                placeholder=f"Instructie voor kolom {i+1}",
                key=f"prompt_{i}",
            )
            for i in range(7)
        ]

    field_prompts = {n: p for n, p in zip(names, prompts) if n.strip() and p.strip()}

    if uploads and field_prompts and extract_btn:
        all_rows: list[dict] = []
        with st.spinner("Extraheren via Groq…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                entries = extract_paired_entries(tmp, field_prompts)
                for entry in entries:
                    row = {"Document": uf.name}
                    row.update(entry)
                    all_rows.append(row)

        if all_rows:
            df = pd.DataFrame(all_rows)
            cols = ["Document"] + [c for c in df.columns if c != "Document"]
            st.subheader("Extractie Resultaten")
            st.dataframe(df[cols], use_container_width=True)

            csv = df[cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="extracted_data.csv",
                mime="text/csv",
            )
        else:
            st.warning("Geen gestructureerde entries gevonden.")
    else:
        st.info(
            "Upload documenten en definieer minimaal één veldnaam + prompt om te starten."
        )

if __name__ == '__main__':
    app()