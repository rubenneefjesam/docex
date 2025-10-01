# invoice_utils.py
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st
from groq import Groq
from PyPDF2 import PdfReader
import docx

# PyMuPDF (fitz) voor betere PDF-extractie; fallback naar PyPDF2
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


# ────────────────────────────────────────────────────────────────
# Groq Client
# ────────────────────────────────────────────────────────────────
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


# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
_CURRENCY_RX = re.compile(r"(?:€|eur)\s*[-+]?\d[\d.,]*", re.IGNORECASE)
_QTY_UNIT_RX = re.compile(r"\b\d+[\d.,]*\s*(?:st|stuk|stuks|pcs)\b", re.IGNORECASE)
# Optioneel: simpele “10x ” vóór een woord weghalen, maar NIET bij maat-strings met mm/cm/m/Ø in de buurt.
_PREFIX_MULT_RX = re.compile(r"\b(\d+)\s*x\s+(?!\d)")

def _clean_description(desc: str) -> str:
    """Verwijder geldbedragen en hoeveelheid+tel-eenheid uit de omschrijving; laat maatvoering intact."""
    if not desc:
        return desc
    s = str(desc)

    # 1) geldbedragen weg: "€ 32,50", "EUR 260.00"
    s = _CURRENCY_RX.sub("", s)

    # 2) hoeveelheid + tel-eenheid weg: "8 stuks", "10 pcs"
    s = _QTY_UNIT_RX.sub("", s)

    # 3) optioneel: '10x ' als prefix weg (alleen als het geen maat is)
    if not re.search(r"(mm|cm|\b[0-9]+x[0-9])|Ø", s, flags=re.IGNORECASE):
        s = _PREFIX_MULT_RX.sub("", s)

    # 4) opschonen spaties & randtekens
    s = re.sub(r"\s{2,}", " ", s).strip(" -–—:;\t\n\r ")
    return s


def _strip_code_fences(s: str) -> str:
    """Verwijder ``` of ```json fences en geef binnenste inhoud terug."""
    s = s.strip()
    if s.startswith("```") and s.endswith("```"):
        lines = s.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return s


def _first_json_array(text: str) -> str:
    """
    Zoek de eerste JSON-array substring in text. Handig als het model
    per ongeluk extra tekst print rondom de JSON.
    """
    text = text.strip()
    if text.startswith("["):
        return text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


# ────────────────────────────────────────────────────────────────
# Bestanden lezen
# ────────────────────────────────────────────────────────────────
def read_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    text = ""

    if suffix == ".pdf":
        # 1) Probeer PyMuPDF
        if fitz is not None:
            try:
                with fitz.open(str(file_path)) as doc:
                    parts = []
                    for page in doc:
                        parts.append(page.get_text("text"))
                    text = "\n".join(parts)
            except Exception:
                text = ""

        # 2) Fallback PyPDF2
        if not text:
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


# ────────────────────────────────────────────────────────────────
# Extractie
# ────────────────────────────────────────────────────────────────
def extract_line_items(file_path: Path) -> List[Dict[str, Any]]:
    """
    Laat de LLM lijnitems extraheren en retourneer een lijst van dicts
    met o.a. Bedrijfsnaam, Factuurnummer, Datum, Productomschrijving, Hoeveelheid,
    Eenheid en (optioneel) Prijs (EUR).
    """
    if client is None:
        return []

    text = read_text_from_file(file_path)

    # Velden (incl. Prijs voor CO2-berekening downstream)
    field_prompts = {
        "Bedrijfsnaam": "Extraheren van de naam van het bedrijf dat de factuur verzendt.",
        "Factuurnummer": "Extraheren van het factuurnummer.",
        "Datum": "Extraheren van de factuurdatum in formaat DD-MM-YYYY.",
        # Beschrijvende tekst zó letterlijk mogelijk, maar zonder aantallen/valuta
        "Productomschrijving": (
            "Geef ALLEEN de beschrijvende tekst van het artikel (materiaal, bewerking/afwerking, "
            "type/vorm, relevante afmetingen incl. symbolen zoals 'Ø' en '1000x2000x5mm'). "
            "NEEM GEEN aantallen (bijv. '8 stuks', '10x'), GEEN tel-eenheden (st, stuks, pcs) en "
            "GEEN geldbedragen/valuta (bijv. 'EUR 260,00', '€ 32,50') op. "
            "Behoud materialen (bijv. 'stalen'), termen als 'gelast', symbolen en maatvoering. "
            "Niet parafraseren; alleen meerdere spaties tot één samenvoegen."
        ),
        "Hoeveelheid": "Extraheren van de hoeveelheid (numeriek gedeelte).",
        "Eenheid": "Extraheren van de eenheid (bijv. stuks, kg, liter).",
        "Prijs": "Totaalbedrag van de betreffende regel in EUR (alleen getal, EU-notatie toegestaan).",
    }

    instructions = "\n".join([f"- {field}: {instr}" for field, instr in field_prompts.items()])
    prompt = (
        "Je bent een assistent die factuurlijnitems uit een document haalt.\n"
        "Geef als output een JSON-array van objecten, waarbij elk object de volgende velden bevat:\n"
        f"  {', '.join(field_prompts.keys())}\n"
        "Voor 'Productomschrijving': houd je strikt aan de instructies; neem geen aantallen of valuta op.\n"
        f"Gebruik de volgende instructies per veld:\n{instructions}\n"
        "Documenttekst:\n" + text + "\n"
        "Geef alleen de JSON-array terug, zonder extra tekst of markdown."
    )

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content or ""
    content = _strip_code_fences(content)
    content = _first_json_array(content)

    try:
        data = json.loads(content)
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                item["Regelnummer"] = idx
                # Safeguard: verwijder kwantitatieve info uit omschrijving, maar laat maatvoering intact
                if "Productomschrijving" in item and item["Productomschrijving"]:
                    item["Productomschrijving"] = _clean_description(item["Productomschrijving"])
            return data
        else:
            st.error("LLM-output is geen JSON-array.")
            st.code(content)
    except json.JSONDecodeError:
        st.error("Kan JSON niet parsen uit LLM-output:")
        st.code(content)

    return []
