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
import os
import streamlit as st
import pandas as pd
from pathlib import Path
from .invoice_utils import extract_line_items
from .csv_utils import load_categories_data, ensure_categories_index
from .llm_utils import classify_category, client

CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"

def app():
    st.set_page_config(page_title="Sustainability Extractor", layout="wide")
    st.title("📑 Sustainability Line Item Extractor & Categorizer")

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
                    }
                    all_rows.append(row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            df.index = df.index + 1
            df.index.name = "Regelnummer"
            st.session_state["extract_df"] = df
            st.subheader("G geëxtraheerde lijnitems")
            st.dataframe(df)
        else:
            st.warning("Geen lijnitems gevonden.")

    # Stap 2: Classificatie
    if "extract_df" in st.session_state:
        df = st.session_state["extract_df"]
        if st.button("🔖 Categoriseer lijnitems"):
            # Laad en indexeer categorielijst
            cats = load_categories_data(CATEGORIES_CSV)
            cats_idx = ensure_categories_index(cats)
            category_list = cats["category"].tolist()

            # Classificeer per omschrijving
            with st.spinner("Categoriseren via LLM…"):
                df["Categorie"] = df["Productomschrijving"].apply(
                    lambda desc: classify_category(desc, category_list, client)
                )
            st.subheader("Gecategoriseerde lijnitems")
            st.dataframe(df)

if __name__ == '__main__':
    app()