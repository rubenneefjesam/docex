# csv_utils.py
import re
import unicodedata
from pathlib import Path
import pandas as pd
import streamlit as st

_NUM_RE = re.compile(r"[-+]?\d[\d.,]*")

def _to_float_eu(s: str | float | int) -> float | None:
    """Robuust getal parsen uit strings als '2,832 kg CO₂e/€ climatiq.io' of '1.262,5'."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    m = _NUM_RE.search(s)
    if not m:
        return None
    num = m.group(0)
    # EU-notatie: als er een komma in staat, neem die als decimaal en strip punten
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    return float(num)

def load_categories_data(csv_path: Path):
    """
    Laadt categorieen.csv robuust in en retourneert:
      - categories: list[dict] met 'Categorie nummer' en 'Categorie'
      - factor_map: dict[str categorie nummer] -> float emissiefactor (kg CO₂e/€)
      - meta_df: volledige DataFrame (optioneel nuttig voor debug)
    """
    if not csv_path.exists():
        st.error(f"categorieen.csv niet gevonden op {csv_path}")
        return [], {}, pd.DataFrame()

    # delimiter detectie
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
        header = f.readline()
    if "\t" in header:
        sep = "\t"
    elif ";" in header:
        sep = ";"
    else:
        sep = ","

    df = pd.read_csv(csv_path, sep=sep, dtype=str, encoding="utf-8")

    # kolomnamen normaliseren
    def norm_ws(s: str) -> str:
        if s is None: return ""
        s = s.replace("\ufeff", "")
        s = "".join(" " if unicodedata.category(ch) == "Zs" or ch.isspace() else ch for ch in s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    df.columns = [norm_ws(c) for c in df.columns]

    # fuzzy renaming
    def squash(s: str) -> str:
        s = norm_ws(s).lower()
        s = s.replace("categorie-nummer", "categorienummer")
        s = s.replace("categorie nummer", "categorienummer")
        s = re.sub(r"[^a-z0-9]", "", s)
        return s

    targets = {
        "categorienummer": "Categorie nummer",
        "categorie": "Categorie",
        "emissiefactorkgco2ee": "Emissiefactor (kg CO₂e/€)",
        "emissiefactor": "Emissiefactor (kg CO₂e/€)",  # fallback
    }
    rename_map = {}
    for orig in df.columns:
        squ = squash(orig)
        if squ in targets:
            rename_map[orig] = targets[squ]
    if rename_map:
        df = df.rename(columns=rename_map)

    st.caption(f"📄 Kolommen CSV: {', '.join(df.columns)} (sep='{sep}')")

    # verplichte kolommen
    req = {"Categorie nummer", "Categorie", "Emissiefactor (kg CO₂e/€)"}
    if not req.issubset(df.columns):
        st.error(
            "categorieen.csv mist verplichte kolommen. "
            f"Gevonden: {', '.join(df.columns)}. "
            "Vereist: 'Categorie nummer', 'Categorie', 'Emissiefactor (kg CO₂e/€)'."
        )
        return [], {}, df

    # factor map parsen
    df["Emissiefactor (kg CO₂e/€) [num]"] = df["Emissiefactor (kg CO₂e/€)"].apply(_to_float_eu)
    factor_map = {
        str(row["Categorie nummer"]): float(row["Emissiefactor (kg CO₂e/€) [num]"])
        for _, row in df.iterrows()
        if row["Emissiefactor (kg CO₂e/€) [num]"] is not None
    }

    categories = df[["Categorie nummer", "Categorie"]].to_dict(orient="records")
    return categories, factor_map, df
