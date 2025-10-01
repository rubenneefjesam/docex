import os
import json
from pathlib import Path
from groq import Groq
from PyPDF2 import PdfReader
import docx
import streamlit as st

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


def extract_line_items(file_path: Path) -> list[dict]:
    if client is None:
        return []
    text = read_text_from_file(file_path)
    field_prompts = {
        "Bedrijfsnaam": "Extraheren van de naam van het bedrijf dat de factuur verzendt.",
        "Factuurnummer": "Extraheren van het factuurnummer.",
        "Datum": "Extraheren van de factuurdatum in formaat DD-MM-YYYY.",
        "Productomschrijving": "Kort omschrijven welk product of welke dienst vermeld staat.",
        "Hoeveelheid": "Extraheren van de hoeveelheid (numeriek gedeelte).",
        "Eenheid": "Extraheren van de eenheid (bijv. stuks, kg, liter)."
    }
    instructions = "\n".join([f"- {f}: {p}" for f, p in field_prompts.items()])
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
    if content.startswith("```") and content.endswith("```"):
        lines = content.splitlines()
        content = "\n".join(lines[1:-1])
    try:
        data = json.loads(content)
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                item["Regelnummer"] = idx
            return data
    except json.JSONDecodeError:
        st.error("Kan JSON niet parsen, krijg:")
        st.code(content)
    return []
