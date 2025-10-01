import streamlit as st
import pandas as pd
from pathlib import Path

from .csv_utils import load_categories_data
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import init_groq_client, extract_invoice_fields, classify_rows_with_llm
from .emissions_utils import compute_emissions, clean_keep_best_rows

# Page config
st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")

@st.cache_data
def _load_categories_and_factors():
    csv_path = Path(__file__).parent / 'categorieen.csv'
    return load_categories_data(csv_path)

def _lazy_client():
    return init_groq_client()

def app():
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën + CO₂-berekening.")

    # laad categorieën & emissiefactoren
    cats, factor_map, _meta = _load_categories_and_factors()

    # bestand upload
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if st.button("🚀 Extraheer & Classificeer"):
        if not files:
            st.warning("Upload eerst ten minste één document.")
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
                    row = {"Document": up.name}
                    row.update(r)
                    rows.append(row)

        if not rows:
            st.info("Geen regels gevonden.")
            return

        df = pd.DataFrame(rows)
        subset = [c for c in [
            "Document", "Factuurnummer", "Leverancier",
            "Beschrijving product", "Kwantiteit", "Eenheid", "Bedrag (EUR)"
        ] if c in df.columns]
        if subset:
            df = df.drop_duplicates(subset=subset).reset_index(drop=True)

        df = classify_rows_with_llm(df, cats, client)
        df = compute_emissions(df, factor_map)
        df = clean_keep_best_rows(df)

        st.subheader("Resultaten")
        cols = [
            c for c in [
                "Document", "Factuurnummer", "Leverancier", "Beschrijving product",
                "Kwantiteit", "Eenheid", "Bedrag (EUR)", "Categorie nummer", "Categorie",
                "Emissiefactor (kg CO₂e/€)", "Totale kg CO₂e"
            ] if c in df.columns
        ]
        st.dataframe(df[cols], use_container_width=True)

        csv_bytes = df[cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV",
            data=csv_bytes,
            file_name="facturen_co2.csv",
            mime="text/csv"
        )

if __name__ == '__main__':
    app()
