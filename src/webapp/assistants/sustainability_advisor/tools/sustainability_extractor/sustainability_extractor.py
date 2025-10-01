# sustainability_extractor.py
import re
import streamlit as st
import pandas as pd
from pathlib import Path

from .invoice_utils import extract_line_items
from .csv_utils import load_categories_data, ensure_categories_index
from .llm_utils import classify_category, client

CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"

# EU-getal parser voor prijzen (bijv. "1.262,50" of "€ 99,95")
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


def _categorize_and_compute(df: pd.DataFrame) -> pd.DataFrame:
    """Voer categorisatie + CO₂-berekening uit en retourneer nieuw DataFrame."""
    # 1) Laad categorieën + index
    cats = load_categories_data(CATEGORIES_CSV)
    cats = ensure_categories_index(cats)  # index = lower(category)
    category_list = cats["category"].tolist()

    # 2) Categoriseer via LLM
    with st.spinner("Categoriseren via LLM…"):
        df["Categorie"] = df["Productomschrijving"].apply(
            lambda desc: classify_category(desc, category_list, client)
        )

    # 3) Factor mappen en CO₂ berekenen
    if "Prijs" not in df.columns:
        df["Prijs"] = ""

    df["Emissiefactor_kgCO2e_per_EUR"] = (
        df["Categorie"]
        .astype(str)
        .str.lower()
        .str.strip()
        .map(cats["factor"])
        .fillna(0.0)
    )
    df["PrijsEUR"] = df["Prijs"].apply(_eu_to_float)
    df["CO2_kg"] = (
        df["Emissiefactor_kgCO2e_per_EUR"].astype(float) * df["PrijsEUR"].astype(float)
    ).round(3)

    return df


def app():
    st.set_page_config(page_title="Sustainability Extractor", layout="wide")
    st.title("📑 Sustainability Line Item Extractor & Categorizer")
    st.caption("Stap 1: extraheren → Stap 2: categoriseren → Stap 3: CO₂ berekenen")

    # Toggle: automatische categorisatie
    auto_categorize = st.toggle("Automatisch categoriseren", value=True, help=(
        "Als dit aan staat, worden lijnitems direct na extractie automatisch gecategoriseerd "
        "en wordt CO₂ per regel berekend."
    ))

    # Upload sectie
    uploads = st.file_uploader(
        "Upload factuurdocument(en)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
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
                        # Optioneel: als invoice_utils al 'Prijs' oplevert, meenemen:
                        "Prijs": item.get("Prijs", ""),
                    }
                    all_rows.append(row)

        if not all_rows:
            st.warning("Geen lijnitems gevonden.")
            return

        df = pd.DataFrame(all_rows)
        df.index = df.index + 1
        df.index.name = "Regelnummer"

        st.session_state["extract_df"] = df

        st.subheader("Geëxtraheerde lijnitems")
        base_cols = [
            "Datum", "Document", "Factuurnummer", "Bedrijfsnaam",
            "Productomschrijving", "Hoeveelheid", "Eenheid", "Prijs",
        ]
        st.dataframe(df[[c for c in base_cols if c in df.columns]])

        # Auto-run categorisatie + CO2 als toggle aan staat
        if auto_categorize:
            df2 = _categorize_and_compute(df.copy())
            st.session_state["categorized_df"] = df2  # optioneel bijhouden

            st.subheader("Gecategoriseerde lijnitems + CO₂")
            show_cols = [
                "Datum", "Document", "Factuurnummer", "Bedrijfsnaam",
                "Productomschrijving", "Hoeveelheid", "Eenheid", "Prijs",
                "Categorie", "Emissiefactor_kgCO2e_per_EUR", "CO2_kg",
            ]
            st.dataframe(df2[[c for c in show_cols if c in df2.columns]])

            csv = df2[[c for c in show_cols if c in df2.columns]].to_csv(index=True).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV (met CO₂)", data=csv,
                file_name="line_items_with_co2.csv", mime="text/csv"
            )

    # Handmatige flow blijft beschikbaar als toggle UIT staat
    if "extract_df" in st.session_state and not auto_categorize:
        df = st.session_state["extract_df"].copy()
        if st.button("🔖 Categoriseer & bereken CO₂"):
            df2 = _categorize_and_compute(df)
            st.session_state["categorized_df"] = df2

            st.subheader("Gecategoriseerde lijnitems + CO₂")
            show_cols = [
                "Datum", "Document", "Factuurnummer", "Bedrijfsnaam",
                "Productomschrijving", "Hoeveelheid", "Eenheid", "Prijs",
                "Categorie", "Emissiefactor_kgCO2e_per_EUR", "CO2_kg",
            ]
            st.dataframe(df2[[c for c in show_cols if c in df2.columns]])

            csv = df2[[c for c in show_cols if c in df2.columns]].to_csv(index=True).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV (met CO₂)", data=csv,
                file_name="line_items_with_co2.csv", mime="text/csv"
            )


if __name__ == "__main__":
    app()
