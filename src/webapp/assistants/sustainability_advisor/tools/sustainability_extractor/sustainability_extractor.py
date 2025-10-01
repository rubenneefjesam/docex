# sustainability_extractor.py
import streamlit as st
import pandas as pd
from pathlib import Path

from .csv_utils import load_categories_data
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import init_groq_client, extract_invoice_fields, classify_rows_with_llm
from .emissions_utils import compute_emissions, clean_keep_best_rows

client = init_groq_client()

def app():
    st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën + CO₂-berekening.")

    auto_classify = st.toggle(
        "Automatisch classificeren na extractie",
        value=True,
        help="Voer direct na het extraheren ook de classificatie en CO₂-berekening uit."
    )

    # 1) Categorieën + emissiefactoren
    if "categories" not in st.session_state or "factor_map" not in st.session_state:
        csv_path = Path(__file__).parent / 'categorieen.csv'
        cats, factor_map, _meta = load_categories_data(csv_path)
        st.session_state["categories"] = cats
        st.session_state["factor_map"] = factor_map

    categories = st.session_state.get("categories", [])
    factor_map = st.session_state.get("factor_map", {})
    if not categories or not factor_map:
        st.stop()

    # 2) Upload
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    # 3) Extractie (+ optioneel classificatie & CO₂)
    if st.button("🚀 Extraheer factuurdata", type="primary"):
        if not files:
            st.warning("Upload eerst ten minste één document.")
        else:
            rows = []
            with st.spinner("Controleren en extraheren…"):
                for up in files:
                    tmp = Path(f"/tmp/{up.name}")
                    tmp.write_bytes(up.getvalue())
                    txt = read_text_from_file(tmp)
                    if not is_invoice(txt):
                        st.warning(f"❌ {up.name} lijkt geen factuur te zijn.")
                        continue

                    # LLM → list[dict] (scalars per regel)
                    entries = extract_invoice_fields(txt, client)
                    for r in entries:
                        row = {"Document": up.name}
                        row.update(r)
                        rows.append(row)

            st.session_state["extracted_rows"] = rows
            st.session_state.pop("df", None)

            if rows:
                base_df = pd.DataFrame(rows)

                # Dedup op logische subset
                subset = [c for c in [
                    "Document", "Factuurnummer", "Leverancier",
                    "Beschrijving product", "Kwantiteit", "Eenheid", "Bedrag (EUR)"
                ] if c in base_df.columns]
                if subset:
                    base_df = base_df.drop_duplicates(subset=subset).reset_index(drop=True)

                if auto_classify:
                    st.info("Automatische classificatie en CO₂-berekening wordt uitgevoerd…")
                    out_df = classify_rows_with_llm(base_df.copy(), categories, client)
                    out_df = compute_emissions(out_df, factor_map)
                    out_df = clean_keep_best_rows(out_df)
                    st.session_state["df"] = out_df
                    st.success("Extractie + classificatie + CO₂ voltooid ✅")
                else:
                    st.session_state["df"] = base_df

    # 4) Tabel tonen
    df = st.session_state.get("df", pd.DataFrame())
    if df.empty:
        st.info("Nog geen gegevens om te tonen.")
        st.button("Classificeer & bereken CO₂", disabled=True)
        return

    cols_order = [
        "Document", "Factuurnummer", "Leverancier", "Beschrijving product",
        "Kwantiteit", "Eenheid", "Bedrag (EUR)", "Categorie nummer", "Categorie",
        "Emissiefactor (kg CO₂e/€)", "Totale kg CO₂e"
    ]
    cols = [c for c in cols_order if c in df.columns]

    st.subheader("Resultaten")
    st.dataframe(df[cols], use_container_width=True)

    # Download
    if "Totale kg CO₂e" in df.columns:
        csv2 = df[cols].to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇️ Download met Categorieën & CO₂",
            data=csv2,
            file_name="factuur_data_geclassificeerd_co2.csv",
            mime="text/csv"
        )

    # 5) Handmatig (wanneer auto uit staat)
    if not auto_classify:
        if st.button("Classificeer & bereken CO₂"):
            if df.empty:
                st.warning("Er zijn geen regels om te classificeren.")
                return
            out_df = classify_rows_with_llm(df.copy(), categories, client)
            out_df = compute_emissions(out_df, factor_map)
            out_df = clean_keep_best_rows(out_df)
            st.session_state["df"] = out_df
            st.success("Classificatie + CO₂ voltooid ✅")
            st.rerun()

if __name__ == '__main__':
    app()
