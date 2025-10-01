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
    # Verwijder code fences ``` of ```json
    s = re.sub(r'^\s*```(?:json)?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*```\s*$', '', s)
    # Extract het JSON-deel
    start = min((idx for idx in (s.find('['), s.find('{')) if idx != -1), default=None)
    end = max(s.rfind(']'), s.rfind('}'))
    if start is not None and end is not None and end > start:
        s = s[start:end+1]
    # Verwijder trailing komma's
    s = re.sub(r',(?=\s*[\]}])', '', s)
    # Probeer JSON laden
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
    prompts = {
        "Factuurnummer": "Haal het factuurnummer uit (inclusief letters en streepjes).",
        "Leverancier": "Noem de naam van de leverancier zoals vermeld op de factuur.",
        "Beschrijving product": "Geef per regel de productomschrijving.",
        "Kwantiteit": "Haal de aantallen per productregel op.",
        "Eenheid": "Haal de eenheid per productregel op, bijvoorbeeld stuks, kg, m."
    }
    fields = list(prompts.keys())
    instruction_lines = "\n".join(f"- {f}: {p}" for f, p in prompts.items())
    prompt = (
        "Je bent een assistent die factuurinformatie uit een document haalt.\n"
        "Reageer ALLEEN met pure JSON (zonder code fences, zonder uitleg), gebruik dubbele aanhalingstekens en geen trailing comma’s.\n"
        f"Geef als output een JSON-array van objecten met de velden: {', '.join(fields)}\n"
        f"{instruction_lines}\n\n"
        f"Documenttekst:\n{text}"
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
                tmp_path = Path(f"/tmp/{uf.name}")
                tmp_path.write_bytes(uf.getvalue())
                text = read_text_from_file(tmp_path)
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
            # Filter alleen bestaande kolommen
            default_cols = ["Document", "Factuurnummer", "Leverancier", "Beschrijving product", "Kwantiteit", "Eenheid"]
            cols = [c for c in default_cols if c in df.columns]
            if not cols:
                st.error("Geen verwachte kolommen gevonden. Beschikbare: " + ", ".join(df.columns))
                return
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