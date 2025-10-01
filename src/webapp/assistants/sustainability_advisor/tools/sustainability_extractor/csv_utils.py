# csv_utils.py
import re
import unicodedata
from pathlib import Path
import pandas as pd
import streamlit as st

def load_categories_csv(csv_path: Path) -> list[dict]:
    """
    Laadt categorieën.csv robuust in:
    - Herkent delimiters (; , \t)
    - Verwijdert BOM en unicode whitespace
    - Matcht kolomnamen flexibel ('Categorie nummer', 'Categorie')
    - Toont debug info via Streamlit
    """
    if not csv_path.exists():
        st.error(f"categorieen.csv niet gevonden op {csv_path}")
        return []

    # 1) Delimiter detectie
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline()
    if "\t" in header:
        sep = "\t"
    elif ";" in header:
        sep = ";"
    else:
        sep = ","

    # 2) Inlezen
    cat_df = pd.read_csv(csv_path, sep=sep, dtype=str, encoding="utf-8")

    # 3) Kolomnamen normaliseren
    def norm_ws(s: str) -> str:
        if s is None:
            return ""
        s = s.replace("\ufeff", "")  # BOM
        s = "".join(
            " " if unicodedata.category(ch) == "Zs" or ch.isspace() else ch
            for ch in s
        )
        s = re.sub(r"\s+", " ", s).strip()
        return s

    cat_df.columns = [norm_ws(c) for c in cat_df.columns]

    # 4) Fuzzy mapping
    def squash(s: str) -> str:
        s = norm_ws(s).lower()
        s = s.replace("categorie-nummer", "categorienummer")
        s = s.replace("categorie nummer", "categorienummer")
        s = re.sub(r"[^a-z0-9]", "", s)
        return s

    target_keys = {
        "categorienummer": "Categorie nummer",
        "categorie": "Categorie",
    }

    rename_map = {}
    for orig in cat_df.columns:
        squ = squash(orig)
        if squ in target_keys:
            rename_map[orig] = target_keys[squ]

    if rename_map:
        cat_df = cat_df.rename(columns=rename_map)

    # 5) Debug
    st.caption(f"📄 Gevonden kolommen in categorieën CSV: {', '.join(cat_df.columns)} (sep='{sep}')")

    # 6) Validatie
    required = {"Categorie nummer", "Categorie"}
    if not required.issubset(set(cat_df.columns)):
        st.error(
            "categorieen.csv mist verplichte kolommen. "
            f"Gevonden: {', '.join(cat_df.columns)}. "
            "Vereist: 'Categorie nummer' en 'Categorie'."
        )
        return []

    base_df = cat_df[["Categorie nummer", "Categorie"]].copy()
    return base_df.to_dict(orient="records")
