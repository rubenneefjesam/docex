# sustainability_extractor.py
import streamlit as st
import pandas as pd
from pathlib import Path

from .csv_utils import load_categories_csv
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import init_groq_client, extract_invoice_fields, classify_rows_with_llm

client = init_groq_client()

def app():
    st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën.")

    # 1) Laad categorieën (eenmalig) en cache in session
    if "categories" not in st.session_state:
        csv_path = Path(__file__).parent / 'categorieen.csv'
        st.session_state["categories"] = load_categories_csv(csv_path)

    categories = st.session_state.get("categories", [])
    if not categories:
        st.stop()

    # 2) Upload facturen
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf","docx","txt"],
        accept_multiple_files=True
    )

    # 3) Extracteer
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
                    entries = extract_invoice_fields(txt, client)
                    for e in entries:
                        list_keys = [k for k,v in e.items() if isinstance(v, list)]
                        if list_keys:
                            length = len(e[list_keys[0]])
                            for i in range(length):
                                row = {"Document": up.name}
                                for k,val in e.items():
                                    row[k] = val[i] if isinstance(val,list) else val
                                rows.append(row)
                        else:
                            row = {"Document": up.name}
                            row.update(e)
                            rows.append(row)
            st.session_state["extracted_rows"] = rows
            # reset vorige classificatie
            st.session_state.pop("df", None)

    # 4) Toon hoofdtabel (en bewaar in session)
    rows = st.session_state.get("extracted_rows", [])
    if rows:
        df = pd.DataFrame(rows)
        # als er al geclassificeerd is, merge de categorie-kolommen terug
        classified_df = st.session_state.get("df")
        if isinstance(classified_df, pd.DataFrame) and not classified_df.empty:
            for col in ["Categorie nummer", "Categorie"]:
                if col in classified_df.columns:
                    df[col] = classified_df[col]
        st.session_state["df"] = df

        cols = [c for c in [
            "Document","Factuurnummer","Leverancier","Beschrijving product",
            "Kwantiteit","Eenheid","Categorie nummer","Categorie"
        ] if c in df.columns]

        st.subheader("Extractie Resultaten")
        st.dataframe(df[cols], use_container_width=True)

        # Downloadknop indien categorieën aanwezig
        if {"Categorie nummer","Categorie"}.issubset(df.columns):
            csv2 = df[cols].to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download met Categorieën", data=csv2,
                               file_name="factuur_data_geclassificeerd.csv", mime="text/csv")
    else:
        st.info("Geen data gevonden (nog).")
        st.button("Classificeer regels", disabled=True)
        return

    # 5) Classificeer-knop: overschrijft hoofdtabel en rerun
    if st.button("Classificeer regels"):
        df = st.session_state.get("df", pd.DataFrame())
        if df.empty:
            st.warning("Er zijn geen regels om te classificeren.")
            return
        out_df = classify_rows_with_llm(df.copy(), categories, client)
        st.session_state["df"] = out_df  # overschrijf
        st.success("Classificatie voltooid ✅")
        st.rerun()

if __name__ == '__main__':
    app()
