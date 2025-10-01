import os
import io
import json
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

# ─── Extractie via Groq LLM ──────────────────────────────────────
def extract_line_items(file_path: Path) -> list[dict]:
    if client is None:
        return []
    text = read_text_from_file(file_path)
    # Definieer de gewenste velden en instructies voor de LLM
    field_prompts = {
        "Bedrijfsnaam": "Extraheren van de naam van het bedrijf dat de factuur verzendt.",
        "Factuurnummer": "Extraheren van het factuurnummer.",
        "Datum": "Extraheren van de factuurdatum in formaat DD-MM-YYYY.",
        "Productomschrijving": "Kort omschrijven welk product of welke dienst vermeld staat.",
        "Hoeveelheid": "Extraheren van de hoeveelheid (numeriek gedeelte).",
        "Eenheid": "Extraheren van de eenheid (bijv. stuks, kg, liter)."
    }
    instructions = "\n".join([f"- {field}: {instr}" for field, instr in field_prompts.items()])
    prompt = (
        "Je bent een assistent die factuurlijnitems uit een document haalt.\n"
        "Geef als output een JSON-array van objecten, waarbij elk object de volgende velden bevat:\n"
        f"  {', '.join(field_prompts.keys())}\n"
        f"Gebruik de volgende instructies per veld:\n{instructions}\n"
        "Documenttekst:\n" + text + "\n"
        "Geef alleen de JSON-array terug, zonder extra tekst of markdown."
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
            # Voeg een regelnummer toe
            for idx, item in enumerate(data, start=1):
                item["Regelnummer"] = idx
            return data
    except json.JSONDecodeError:
        st.error("Kan JSON niet parsen, krijg:")
        st.code(content)
    return []

# ─── Streamlit-applicatie ─────────────────────────────────────────
def app():
    st.set_page_config(page_title="Invoice Extractor", layout="wide")
    st.title("📄 Invoice Line Item Extractor (Groq LLM)")
    st.write("Upload je factuurdocumenten en klik op '🚀 Extraheer lijnitems'.")

    uploads = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    extract_btn = st.button("🚀 Extraheer lijnitems")

    if uploads and extract_btn:
        all_rows = []
        with st.spinner("Extraheren via Groq…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                items = extract_line_items(tmp)
                for item in items:
                    row = {"Document": uf.name}
                    row.update(item)
                    all_rows.append(row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            # Zorg dat kolomvolgorde logisch is
            cols = ["Document", "Regelnummer", "Bedrijfsnaam", "Factuurnummer", "Datum", "Productomschrijving", "Hoeveelheid", "Eenheid"]
            st.subheader("Extractie Resultaten")
            st.dataframe(df[cols], use_container_width=True)
            csv = df[cols].to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="line_items.csv",
                mime="text/csv"
            )
        else:
            st.warning("Geen lijnitems gevonden.")
    else:
        st.info("Upload documenten en klik op de knop om te starten.")

if __name__ == '__main__':
    app()