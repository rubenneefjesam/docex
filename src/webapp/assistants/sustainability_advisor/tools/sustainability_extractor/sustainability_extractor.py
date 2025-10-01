# csv_utils.py
from __future__ import annotations
import io
import re
import unicodedata
from pathlib import Path
from typing import Any, Union

import pandas as pd

# ────────────────────────────────────────────────────────────────
# llm_utils.py
import os
import streamlit as st
from groq import Groq
from typing import List

# initialise LLM client
def init_groq_client():
    key = os.getenv("GROQ_API_KEY", "").strip() or st.secrets.get("groq", {}).get("api_key", "").strip()
    if not key:
        st.error("Geen Groq API key gevonden; classificatie werkt niet.")
        return None
    return Groq(api_key=key)

client = init_groq_client()

def classify_category(description: str, categories: List[str], client=None) -> str:
    if client is None:
        client = globals().get("client")
    prompt = (
        "Kies precies één categorie uit de volgende lijst voor deze productomschrijving:
"
        f"{categories}
"
        f"Omschrijving: {description}
"
        "Antwoord alleen met de categorie-naam, zonder extra tekst."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()
import streamlit as st
from groq import Groq
from typing import List

def init_groq_client():
    key = os.getenv("GROQ_API_KEY", "").strip() or st.secrets.get("groq", {}).get("api_key", "").strip()
    if not key:
        st.error("Geen Groq API key")
        return None
    return Groq(api_key=key)

client = init_groq_client()

def classify_category(description: str, categories: List[str], client=None) -> str:
    if client is None:
        client = globals().get("client")
    prompt = (
        "Kies precies één categorie uit de volgende lijst voor deze productomschrijving:\n"
        f"{categories}\n"
        f"Omschrijving: {description}\n"
        "Antwoord alleen met de categorie-naam, zonder extra tekst."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()


# sustainability_extractor.py
import re
import streamlit as st
import pandas as pd
from pathlib import Path

from .invoice_utils import extract_line_items
from .csv_utils import load_categories_data, ensure_categories_index
from .llm_utils import classify_category, client

CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"

# EU-getal parser voor prijzen (bijv. "1.262,50" of "123,45" of "€ 99,95")
def _eu_to_float(s) -> float:
    if s is None:
        return 0.0
    s = str(s).strip()
    if s == "":
        return 0.0
    s = re.sub(r"[^0-9,.-]", "", s)  # verwijder valuta/tekens
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def app():
    st.set_page_config(page_title="Sustainability Extractor", layout="wide")
    st.title("📑 Sustainability Line Item Extractor & Categorizer")
    st.caption("Stap 1: extraheren → Stap 2: categoriseren → Stap 3: CO₂ berekenen")

    # Upload sectie
    uploads = st.file_uploader(
        "Upload factuurdocument(en)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    if not uploads:
        st.info("Upload minimaal één document.")
        return

    # Stap 1: Extractie
    if st.button("🚀 Extraheer lijnitems"):
        all_rows = []
        with st.spinner("Extractie via LLM…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                items = extract_line_items(tmp)
                for item in items:
                    row = {
                        "Document": uf.name,
                        "Datum": item.get("Datum", ""),
                        "Factuurnummer": item.get("Factuurnummer", ""),
                        "Bedrijfsnaam": item.get("Bedrijfsnaam", ""),
                        "Productomschrijving": item.get("Productomschrijving", ""),
                        "Hoeveelheid": item.get("Hoeveelheid", ""),
                        "Eenheid": item.get("Eenheid", ""),
                        # Optioneel: als invoice_utils al 'Prijs' teruggeeft, meenemen
                        "Prijs": item.get("Prijs", ""),
                    }
                    all_rows.append(row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            df.index = df.index + 1
            df.index.name = "Regelnummer"
            st.session_state["extract_df"] = df
            st.subheader("Geëxtraheerde lijnitems")
            cols = [
                "Datum","Document","Factuurnummer","Bedrijfsnaam",
                "Productomschrijving","Hoeveelheid","Eenheid","Prijs"
            ]
            # Alleen kolommen tonen die bestaan
            cols = [c for c in cols if c in df.columns]
            st.dataframe(df[cols])
        else:
            st.warning("Geen lijnitems gevonden.")

    # Stap 2 & 3: Categoriseren + CO₂ berekenen
    if "extract_df" in st.session_state:
        df = st.session_state["extract_df"].copy()
        if st.button("🔖 Categoriseer & bereken CO₂"):
            # 2) Laad en indexeer categorielijst
            cats = load_categories_data(CATEGORIES_CSV)
            cats = ensure_categories_index(cats)  # index = lower(category)
            category_list = cats["category"].tolist()

            # 2a) Classificeer per omschrijving
            with st.spinner("Categoriseren via LLM…"):
                df["Categorie"] = df["Productomschrijving"].apply(
                    lambda desc: classify_category(desc, category_list, client)
                )

            # 3) Emissiefactor mappen en CO₂ berekenen (factor [kgCO2e/EUR] × prijs [EUR])
            # Zorg dat we een Prijs-kolom hebben (desnoods leeg)
            if "Prijs" not in df.columns:
                df["Prijs"] = ""

            # Map factor per categorie (case-insensitive)
            df["Emissiefactor_kgCO2e_per_EUR"] = (
                df["Categorie"].astype(str).str.lower().str.strip().map(cats["factor"]).fillna(0.0)
            )
            # Parse prijs → float EUR
            df["PrijsEUR"] = df["Prijs"].apply(_eu_to_float)
            # CO2 per regel
            df["CO2_kg"] = (df["Emissiefactor_kgCO2e_per_EUR"].astype(float) * df["PrijsEUR"].astype(float)).round(3)

            st.subheader("Gecategoriseerde lijnitems + CO₂")
            show_cols = [
                "Datum","Document","Factuurnummer","Bedrijfsnaam","Productomschrijving",
                "Hoeveelheid","Eenheid","Prijs","Categorie","Emissiefactor_kgCO2e_per_EUR","CO2_kg"
            ]
            show_cols = [c for c in show_cols if c in df.columns]
            st.dataframe(df[show_cols])

            # Download CSV
            csv = df[show_cols].to_csv(index=True).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV (met CO₂)", data=csv,
                file_name="line_items_with_co2.csv", mime="text/csv"
            )

if __name__ == '__main__':
    app()