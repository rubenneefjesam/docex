import os
import io
import json
import re
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
    keywords = [
        r"factuurnummer", r"factuur\s*nr", r"btw", r"totaal\s*bedrag",
        r"leverancier", r"datum", r"omschrijving"
    ]
    hits = sum(bool(re.search(kw, text, re.IGNORECASE)) for kw in keywords)
    # Minimal één factuurnummer én één bedrag
    return bool(re.search(r"factuurnummer|factuur\s*nr", text, re.IGNORECASE)) and \
           bool(re.search(r"€\s*\d", text))

# ─── Extractie via Groq LLM ────────────────────────────────────────
def extract_invoice_fields(text: str) -> list[dict]:
    if client is None:
        return []
    # Vaste kolomnamen met instructies
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
        "Geef als output een JSON-array van objecten, waarbij elk object de volgende velden bevat:\n"
        f"  {', '.join(fields)}\n"
        f"{instructions}\n\n"
        "Documenttekst:\n" + text + "\n"
        "Geef alleen de JSON-array terug, zonder extra toelichting."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    content = resp.choices[0].message.content.strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        st.error("Kan JSON niet parsen, ontvang:\n" + content)
    return []

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
