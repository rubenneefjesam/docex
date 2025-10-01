import streamlit as st
import pandas as pd
from pathlib import Path

from .csv_utils import load_categories_data, ensure_categories_index
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import (
    init_groq_client,
    extract_invoice_rows,
    classify_rows_with_llm_or_rules,
    compute_impacts,
)

st.set_page_config(page_title="Sustainability Extractor", layout="wide")

# ────────────────────────────────────────────────────────────────
# Init
# ────────────────────────────────────────────────────────────────
if "raw_texts" not in st.session_state:
    st.session_state.raw_texts = {}
if "extracted_df" not in st.session_state:
    st.session_state.extracted_df = None
if "result_df" not in st.session_state:
    st.session_state.result_df = None

client = init_groq_client()  # mag None zijn → fallback rules

# ────────────────────────────────────────────────────────────────
# Sidebar: Categorieën + factors laden
# ────────────────────────────────────────────────────────────────
st.sidebar.header("Categorieën & factoren")
categories_file = st.sidebar.file_uploader(
    "Laad categorie-/factorbestand (CSV met kolommen: category,factor,unit)",
    type=["csv"],
    key="cats_upl",
)
if categories_file:
    cats_df = load_categories_data(categories_file)
else:
    # fallback: embedded minimale tabel
    cats_df = pd.DataFrame(
        [
            {"category": "Staal", "factor": 1.95, "unit": "kgCO2e/€"},
            {"category": "Aluminium", "factor": 3.30, "unit": "kgCO2e/€"},
            {"category": "Kunststof", "factor": 1.10, "unit": "kgCO2e/€"},
            {"category": "Dienst", "factor": 0.20, "unit": "kgCO2e/€"},
            {"category": "Onbekend", "factor": 0.50, "unit": "kgCO2e/€"},
        ]
    )
cats_df = ensure_categories_index(cats_df)

with st.sidebar.expander("Voorbeeld categorieën", expanded=False):
    st.dataframe(cats_df, use_container_width=True)

# ────────────────────────────────────────────────────────────────
# Hoofd: Upload facturen
# ────────────────────────────────────────────────────────────────
st.title("Stainless Sustainability – Factuur Extractor & Categoriseerder")

uploaded = st.file_uploader(
    "Upload één of meerdere facturen (PDF / TXT / PNG / JPG)",
    type=["pdf", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

col_a, col_b = st.columns([1, 1])

with col_a:
    if st.button("1) Extraheren", type="primary", use_container_width=True):
        if not uploaded:
            st.warning("Upload eerst minimaal één bestand.")
        else:
            all_rows = []
            st.session_state.raw_texts.clear()
            for f in uploaded:
                fname = f.name
                text = read_text_from_file(f)
                st.session_state.raw_texts[fname] = text
                if not is_invoice(text):
                    # We laten hem wel door; alleen melding
                    st.info(f"⚠️ `{fname}` lijkt geen standaard factuur, poging tot extractie volgt.")
                rows = extract_invoice_rows(text, filename=fname, client=client)
                all_rows.extend(rows)

            if not all_rows:
                st.error("Geen productregels gevonden.")
                st.session_state.extracted_df = None
                st.session_state.result_df = None
            else:
                extracted_df = pd.DataFrame(all_rows)
                # Zorg voor baseline kolommen:
                for col in ["file", "line_no", "description", "quantity", "unit", "unit_price", "line_total"]:
                    if col not in extracted_df.columns:
                        extracted_df[col] = None
                # typecasts
                num_cols = ["quantity", "unit_price", "line_total"]
                for c in num_cols:
                    extracted_df[c] = pd.to_numeric(extracted_df[c], errors="coerce")
                st.session_state.extracted_df = extracted_df
                st.session_state.result_df = None
                st.success(f"Extractie gereed: {len(extracted_df)} regels gevonden.")

with col_b:
    if st.button("2) Categoriseren & berekening", use_container_width=True):
        df = st.session_state.extracted_df
        if df is None or df.empty:
            st.warning("Voer eerst stap 1 (Extraheren) uit.")
        else:
            classified = classify_rows_with_llm_or_rules(
                df,
                categories_index=cats_df.index,
                client=client,
            )
            result = compute_impacts(classified, category_factors=cats_df)
            st.session_state.result_df = result
            st.success("Categorisatie en berekening voltooid.")

# ────────────────────────────────────────────────────────────────
# Tabelweergave
# ────────────────────────────────────────────────────────────────
st.subheader("🧾 Geëxtraheerde productregels")
if st.session_state.extracted_df is not None:
    st.dataframe(st.session_state.extracted_df, use_container_width=True)

st.subheader("📊 Resultaat: categorieën en CO₂-impact")
if st.session_state.result_df is not None:
    st.dataframe(st.session_state.result_df, use_container_width=True)
    # downloads
    csv_bytes = st.session_state.result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download resultaat (CSV)",
        data=csv_bytes,
        file_name="sustainability_result.csv",
        mime="text/csv",
        use_container_width=True,
    )
