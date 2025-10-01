# sustainability_extractor.py
import re
import difflib
import streamlit as st
import pandas as pd
from pathlib import Path

from .invoice_utils import extract_line_items
from .csv_utils import load_categories_data, ensure_categories_index
from .llm_utils import classify_category, client

CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"

# -----------------------------
# Helpers
# -----------------------------
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

_QUOTE_STRIP = " '\"`´“”‘’"
def _norm_cat(s: str) -> str:
    s = str(s).strip(_QUOTE_STRIP).strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()

def _rule_based_guess(desc: str) -> str | None:
    """Eenvoudige regels: aluminium/staal/coating-woorden."""
    d = (desc or "").lower()
    # coating/paint woorden → geverfde metaalproducten
    if any(w in d for w in ["gecoat", "coated", "coating", "gelakt", "geverfd", "poedercoat", "poedergecoat"]):
        return "geverfde metaalproducten (excl. machines en apparatuur)"
    # aluminium heeft voorrang
    if "aluminium" in d:
        return "aluminium en aluminiumproducten"
    # staal-achtige woorden
    if any(w in d for w in ["staal", "stalen", "steel", "h-profiel", "buis", "plaat", "strip", "profiel"]):
        return "basisijzer en staal & ferro-alloys en eerste producten"
    return None

def _canonical_from_key_or_fuzzy(key: str, cats_index: list[str]) -> str | None:
    """Geef de index-sleutel terug (lowercased) die het beste past."""
    if key in cats_index:
        return key
    m = difflib.get_close_matches(key, cats_index, n=1, cutoff=0.6)
    return m[0] if m else None

def _categorize_row(desc: str, category_list: list[str], cats_df_indexed: pd.DataFrame) -> tuple[str, float]:
    """
    Retourneert (canonieke_categorienaam, factor).
    - Probeert regelgebaseerd
    - Anders LLM
    - Normaliseert & fuzzy-matcht naar CSV
    """
    # 1) regelgebaseerde hint
    guess = _rule_based_guess(desc)
    chosen = guess
    if chosen is None:
        # 2) LLM
        chosen = classify_category(desc, category_list, client)

    # 3) normaliseer & fuzzy naar catalogus
    key = _norm_cat(chosen)
    idx_key = _canonical_from_key_or_fuzzy(key, cats_df_indexed.index.tolist())
    if idx_key is None:
        # laatste redmiddel: probeer ook de ruwe LLM-output (zonder lower) te normaliseren
        key2 = _norm_cat(chosen)
        idx_key = _canonical_from_key_or_fuzzy(key2, cats_df_indexed.index.tolist())

    if idx_key is None:
        # geen match → geef gekozen string terug, factor 0
        return (chosen, 0.0)

    # 4) haal canonieke naam + factor op
    canonical_name = cats_df_indexed.loc[idx_key, "category"]
    factor = float(cats_df_indexed.loc[idx_key, "factor"])
    return (canonical_name, factor)

def _categorize_and_compute(df: pd.DataFrame) -> pd.DataFrame:
    """Voer categorisatie + CO₂-berekening uit en retourneer nieuw DataFrame."""
    # 1) Laad categorieën + index
    cats = load_categories_data(CATEGORIES_CSV)              # kolommen: category, factor, unit, (opt: category_number)
    cats = ensure_categories_index(cats)                     # index = lower(category)
    category_list = cats["category"].tolist()                # voor LLM-keuze

    # 2) Categoriseer
    results = df["Productomschrijving"].apply(lambda d: _categorize_row(d, category_list, cats))
    df["Categorie"] = results.apply(lambda x: x[0])
    df["Emissiefactor_kgCO2e_per_EUR"] = results.apply(lambda x: x[1])

    # 3) CO₂ berekenen
    if "Prijs" not in df.columns:
        df["Prijs"] = ""
    df["PrijsEUR"] = df["Prijs"].apply(_eu_to_float)
    df["CO2_kg"] = (df["Emissiefactor_kgCO2e_per_EUR"].astype(float) * df["PrijsEUR"].astype(float)).round(3)

    return df

# -----------------------------
# App
# -----------------------------
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
        st.dataframe(df[[c for c in base_cols if c in df.columns]], use_container_width=True)

        if auto_categorize:
            df2 = _categorize_and_compute(df.copy())
            st.session_state["categorized_df"] = df2

            st.subheader("Gecategoriseerde lijnitems + CO₂")
            show_cols = [
                "Datum", "Document", "Factuurnummer", "Bedrijfsnaam",
                "Productomschrijving", "Hoeveelheid", "Eenheid", "Prijs",
                "Categorie", "Emissiefactor_kgCO2e_per_EUR", "CO2_kg",
            ]
            st.dataframe(df2[[c for c in show_cols if c in df2.columns]], use_container_width=True)

            csv = df2[[c for c in show_cols if c in df2.columns]].to_csv(index=True).encode("utf-8")
            st.download_button("⬇️ Download CSV (met CO₂)", data=csv,
                               file_name="line_items_with_co2.csv", mime="text/csv")

    # Handmatige flow als toggle UIT is
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
            st.dataframe(df2[[c for c in show_cols if c in df2.columns]], use_container_width=True)

            csv = df2[[c for c in show_cols if c in df2.columns]].to_csv(index=True).encode("utf-8")
            st.download_button("⬇️ Download CSV (met CO₂)", data=csv,
                               file_name="line_items_with_co2.csv", mime="text/csv")


if __name__ == "__main__":
    app()
