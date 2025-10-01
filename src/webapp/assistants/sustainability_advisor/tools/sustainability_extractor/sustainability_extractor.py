# sustainability_extractor.py

import streamlit as st
import pandas as pd
import json
from pathlib import Path

from .csv_utils import load_categories_data
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import init_groq_client, extract_invoice_fields, classify_rows_with_llm
from .emissions_utils import compute_emissions, clean_keep_best_rows

st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")

@st.cache_data
def _load_categories_and_factors():
    csv_path = Path(__file__).parent / "categorieen.csv"
    return load_categories_data(csv_path)  # (cats, factor_map, meta)

def _lazy_client():
    return init_groq_client()

def app():
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF, DOCX of TXT om regels te extraheren, classificeren en CO₂ te berekenen.")

    # 1) Categorieën + emissiefactoren
    cats, factor_map, _ = _load_categories_and_factors()

    # 2) Upload
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if not st.button("🚀 Extraheer & Classificeer"):
        return
    if not files:
        st.warning("Upload eerst minimaal één document.")
        return

    client = _lazy_client()
    rows = []
    with st.spinner("Extraheren…"):
        for up in files:
            tmp = Path(f"/tmp/{up.name}")
            tmp.write_bytes(up.getvalue())
            txt = read_text_from_file(tmp)
            if not is_invoice(txt):
                st.warning(f"❌ {up.name} lijkt geen factuur te zijn.")
                continue
            entries = extract_invoice_fields(txt, client)
            for r in entries:
                rows.append({"Document": up.name, **r})

    if not rows:
        st.info("Geen factuurregels gevonden.")
        return

    # ─── Geen dedup vóór classification ────────────────────────────
    df = pd.DataFrame(rows)

    # ─── Classificatie via LLM ──────────────────────────────────────
    try:
        raw = classify_rows_with_llm(df, cats, client)
        if isinstance(raw, pd.DataFrame):
            out_df = raw
        else:
            parsed = json.loads(raw)
            out_df = pd.DataFrame(parsed)
    except Exception as e:
        st.error(f"❌ Kan classificatie niet parsen: {e}")
        st.code(raw, language="json")
        return

    # ─── Emissies berekenen ─────────────────────────────────────────
    out_df = compute_emissions(out_df, factor_map)

    # ─── Pas clean_keep_best_rows alleen toe als je echt wilt deduppen/ranken.
    #     Verwijder deze call als je álle regels wilt behouden:
    # out_df = clean_keep_best_rows(out_df)

    # ─── Resultaten tonen ───────────────────────────────────────────
    cols = [
        c for c in [
            "Document", "Factuurnummer", "Leverancier", "Beschrijving product",
            "Kwantiteit", "Eenheid", "Bedrag (EUR)",
            "Categorie nummer", "Categorie",
            "Emissiefactor (kg CO₂e/€)", "Totale kg CO₂e"
        ] if c in out_df.columns
    ]

    st.subheader("Resultaten")
    st.dataframe(out_df[cols], use_container_width=True)

    csv_bytes = out_df[cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV met CO₂-berekening",
        data=csv_bytes,
        file_name="factuur_data_co2.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    app()
