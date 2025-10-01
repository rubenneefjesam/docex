import os
import io
import json
import re
import ast
import streamlit as st
import pandas as pd
from pathlib import Path
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
        st.error("⚠️ Geen Groq-API-key gevonden; extractie werkt niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        st.error("❌ Ongeldige Groq-API-key.")
        return None

client = init_groq_client()

# ─── Helper om JSON uit LLM-antwoorden te parsen ────────────────
def parse_llm_json(content: str):
    s = content.strip()
    # Verwijder ``` of ```json fences
    s = re.sub(r'^\s*```(?:json)?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*```\s*$', '', s)
    # Houd alleen het deel tussen eerste [/{ en laatste ]/}
    start_idx = None
    for ch in ['[', '{']:
        i = s.find(ch)
        if i != -1:
            start_idx = i if start_idx is None else min(start_idx, i)
    end_idx = max(s.rfind(']'), s.rfind('}'))
    if start_idx is not None and end_idx != -1 and end_idx > start_idx:
        s = s[start_idx:end_idx+1]
    # Verwijder trailing komma's
    s = re.sub(r',(?=\s*[\]}])', '', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # Fallback op Python literal
        return ast.literal_eval(s)

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text_from_file(file_path: Path) -> str:
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

# ─── Eenvoudige factuur-detectie ─────────────────────────────────
def is_invoice(text: str) -> bool:
    return bool(re.search(r"factuurnummer|factuur\s*nr", text, re.IGNORECASE)) and \
           bool(re.search(r"€\s*\d", text))

# ─── Extractie via Groq LLM ────────────────────────────────────────
def extract_invoice_fields(text: str) -> list[dict]:
    if client is None:
        return []
    field_prompts = {
        "Factuurnummer": "Haal het factuurnummer uit (inclusief letters en streepjes).",
        "Leverancier": "Noem de naam van de leverancier zoals vermeld op de factuur.",
        "Beschrijving product": "Geef per regel de productomschrijving.",
        "Kwantiteit": "Haal de aantallen per productregel op.",
        "Eenheid": "Haal de eenheid per productregel op, bijvoorbeeld stuks, kg, m."
    }
    fields = list(field_prompts.keys())
    instructions = "\n".join(f"- {f}: {p}" for f, p in field_prompts.items())
    prompt = (
        "Je bent een assistent die factuurinformatie uit een document haalt.\n"
        "Reageer ALLEEN met pure JSON (zonder code fences, zonder uitleg), gebruik dubbele aanhalingstekens en geen trailing comma’s.\n"
        "Geef als output een JSON-array van objecten met de velden: " + ", ".join(fields) + "\n"
        + instructions + "\n\n"
        "Documenttekst:\n" + text + "\n"
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    content = resp.choices[0].message.content
    try:
        data = parse_llm_json(content)
    except Exception:
        st.error("Kan JSON niet parsen, ontvang:\n" + content)
        return []
    # Ondersteun zowel dict als list
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        st.error("Onverwacht formaat, verwacht JSON-array.")
        return []
    return data

# ─── Streamlit-applicatie ─────────────────────────────────────────
def app():
    st.set_page_config(page_title="Factuur Extractor", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM)")
    st.write("Upload PDF/DOCX/TXT-facturen en krijg een CSV met factuurnummer, leverancier, productbeschrijving, kwantiteit en eenheid.")

    uploads = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    extract_btn = st.button("🚀 Extraheer factuurdata")

    if uploads and extract_btn:
        all_rows = []
        with st.spinner("Controleren en extraheren…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                text = read_text_from_file(tmp)
                if not is_invoice(text):
                    st.warning(f"❌ {uf.name} lijkt geen factuur te zijn.")
                    continue
                entries = extract_invoice_fields(text)
                for entry in entries:
                    # Converteer lijsten naar platte tekst
                    for key, val in entry.items():
                        if isinstance(val, list):
                            entry[key] = ", ".join(str(v) for v in val)
                    row = {"Document": uf.name}
                    row.update(entry)
                    all_rows.append(row)

        if all_rows:
            df = pd.DataFrame(all_rows)
            cols = ["Document", "Factuurnummer", "Leverancier", "Beschrijving product", "Kwantiteit", "Eenheid"]
            st.subheader("Extractie Resultaten")
            st.dataframe(df[cols], use_container_width=True)
            csv = df[cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="factuur_data.csv",
                mime="text/csv"
            )
        else:
            st.info("Geen factuurdata gevonden of alle documenten afgewezen.")

    else:
        st.info("Upload één of meer documenten en klik op ‘Extraheer factuurdata’ om te starten.")

if __name__ == '__main__':
    app()