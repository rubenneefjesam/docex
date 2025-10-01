# sustainability_extractor.py
import streamlit as st
import pandas as pd
from pathlib import Path

from .csv_utils import load_categories_data
from .file_utils import read_text_from_file, is_invoice
from .llm_utils import init_groq_client, extract_invoice_fields, classify_rows_with_llm

client = init_groq_client()

def _to_float_eu_fast(x) -> float | None:
    """Kleine helper voor bedragen: accepteert '1.234,56' of '1234.56' of '€ 1.234,56'."""
    import re
    if x is None:
        return None
    s = str(x).strip()
    # pak eerste getal
    m = re.search(r"[-+]?\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0)
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None

def _compute_emissions(df: pd.DataFrame, factor_map: dict[str, float]) -> pd.DataFrame:
    # normaliseer mogelijke kolommen voor bedrag
    if "Bedrag (EUR)" not in df.columns and "Kosten" in df.columns:
        df["Bedrag (EUR)"] = df["Kosten"]

    if "Bedrag (EUR)" in df.columns:
        df["Bedrag (EUR) [num]"] = df["Bedrag (EUR)"].apply(_to_float_eu_fast)
    else:
        df["Bedrag (EUR) [num]"] = None

    # lookup factor
    def get_factor(catnum: str) -> float | None:
        if not catnum:
            return None
        return factor_map.get(str(catnum))

    df["Emissiefactor (kg CO₂e/€)"] = df.get("Categorie nummer", "").apply(get_factor)

    # bereken totale kg CO2e
    def mul(a, b):
        try:
            if a is None or b is None:
                return None
            return float(a) * float(b)
        except Exception:
            return None

    df["Totale kg CO₂e"] = df.apply(
        lambda r: mul(r.get("Bedrag (EUR) [num]"), r.get("Emissiefactor (kg CO₂e/€)")),
        axis=1
    )

    # afronden/opschonen optioneel
    if "Totale kg CO₂e" in df.columns:
        df["Totale kg CO₂e"] = df["Totale kg CO₂e"].astype("float64", errors="ignore").round(4)
    if "Emissiefactor (kg CO₂e/€)" in df.columns:
        df["Emissiefactor (kg CO₂e/€)"] = df["Emissiefactor (kg CO₂e/€)"].astype("float64", errors="ignore").round(6)

    return df

def app():
    st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën + CO₂-berekening.")

    auto_classify = st.toggle(
        "Automatisch classificeren na extractie",
        value=True,
        help="Voer direct na het extraheren ook de classificatie en CO₂-berekening uit."
    )

    # 1) Laad categorieën + factors
    if "categories" not in st.session_state or "factor_map" not in st.session_state:
        csv_path = Path(__file__).parent / 'categorieen.csv'
        cats, factor_map, _meta = load_categories_data(csv_path)
        st.session_state["categories"] = cats
        st.session_state["factor_map"] = factor_map

    categories = st.session_state.get("categories", [])
    factor_map = st.session_state.get("factor_map", {})
    if not categories or not factor_map:
        st.stop()

    # 2) Upload facturen
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    # 3) Extracteer (incl. optioneel automatische classificatie + CO2)
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
            st.session_state.pop("df", None)

            if rows:
                base_df = pd.DataFrame(rows)
                if auto_classify:
                    st.info("Automatische classificatie en CO₂-berekening wordt uitgevoerd…")
                    out_df = classify_rows_with_llm(base_df.copy(), categories, client)
                    out_df = _compute_emissions(out_df, factor_map)
                    st.session_state["df"] = out_df
                    st.success("Extractie + classificatie + CO₂ voltooid ✅")
                else:
                    st.session_state["df"] = base_df

    # 4) Toon hoofdtabel
    df = st.session_state.get("df", pd.DataFrame())
    if df.empty:
        st.info("Nog geen gegevens om te tonen.")
        st.button("Classificeer & bereken CO₂", disabled=True)
        return

    # kolomvolgorde
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

    # 5) Handmatige classificatie + CO₂ (alleen als toggle uit staat)
    if not auto_classify:
        if st.button("Classificeer & bereken CO₂"):
            if df.empty:
                st.warning("Er zijn geen regels om te classificeren.")
                return
            out_df = classify_rows_with_llm(df.copy(), categories, client)
            out_df = _compute_emissions(out_df, factor_map)
            st.session_state["df"] = out_df
            st.success("Classificatie + CO₂ voltooid ✅")
            st.rerun()

if __name__ == '__main__':
    app()
