# emissions_utils.py
import re
import pandas as pd

def to_float_eu(val) -> float | None:
    """
    Converteer '1.234,56', '1234.56', '€ 1.234,56' naar float.
    Pakt het eerste getal dat in de string voorkomt.
    """
    if val is None:
        return None
    s = str(val).strip()
    m = re.search(r"[-+]?\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0)
    # EU-decimaal: komma is decimal, punten zijn thousand-sep
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None

def compute_emissions(df: pd.DataFrame, factor_map: dict[str, float]) -> pd.DataFrame:
    """
    - Zorgt voor numerieke 'Bedrag (EUR) [num]'
    - Vult 'Emissiefactor (kg CO₂e/€)' obv 'Categorie nummer'
    - Berekent 'Totale kg CO₂e' = bedrag_num * factor
    """
    out = df.copy()

    # Alias bij alternatieve kolomnaam:
    if "Bedrag (EUR)" not in out.columns and "Kosten" in out.columns:
        out["Bedrag (EUR)"] = out["Kosten"]

    if "Bedrag (EUR)" in out.columns:
        out["Bedrag (EUR) [num]"] = out["Bedrag (EUR)"].apply(to_float_eu)
    else:
        out["Bedrag (EUR) [num]"] = None

    def lookup_factor(catnum: str):
        if not catnum:
            return None
        return factor_map.get(str(catnum))

    out["Emissiefactor (kg CO₂e/€)"] = out.get("Categorie nummer", "").apply(lookup_factor)

    out["Totale kg CO₂e"] = (
        pd.to_numeric(out["Bedrag (EUR) [num]"], errors="coerce")
        * pd.to_numeric(out["Emissiefactor (kg CO₂e/€)"], errors="coerce")
    )

    # afronding
    if "Totale kg CO₂e" in out.columns:
        out["Totale kg CO₂e"] = pd.to_numeric(out["Totale kg CO₂e"], errors="coerce").round(4)
    if "Emissiefactor (kg CO₂e/€)" in out.columns:
        out["Emissiefactor (kg CO₂e/€)"] = pd.to_numeric(out["Emissiefactor (kg CO₂e/€)"], errors="coerce").round(6)

    return out

def clean_keep_best_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Verwijder fallback/lege varianten en kies per logische regel de beste.
    Prioriteit:
      1) CO₂ berekend (Totale kg CO₂e != NaN)
      2) Categorie bekend (niet 'Onbekend')
      3) Hoogste 'Bedrag (EUR) [num]'
    Dedup key: (Document, Factuurnummer, Beschrijving product, Kwantiteit, Eenheid)
    """
    if df.empty:
        return df

    out = df.copy()

    # Houd regels die iets zinnigs hebben
    keep = (
        out.get("Totale kg CO₂e").notna()
        | (out.get("Categorie nummer").fillna("") != "Onbekend")
        | (out.get("Categorie").fillna("") != "Onbekend")
    )
    out = out[keep].copy()
    if out.empty:
        return out

    out["__co2_notnull__"] = out["Totale kg CO₂e"].notna().astype(int)
    out["__cat_known__"]   = (out["Categorie nummer"].fillna("") != "Onbekend").astype(int)
    out["__amount__"]      = pd.to_numeric(out.get("Bedrag (EUR) [num]"), errors="coerce").fillna(-1)

    key_cols = [c for c in ["Document","Factuurnummer","Beschrijving product","Kwantiteit","Eenheid"] if c in out.columns]

    # Sorteer op sleutel + prioriteit
    sort_cols = key_cols + ["__co2_notnull__", "__cat_known__", "__amount__"]
    sort_asc  = [True]*len(key_cols) + [False, False, False]

    out = (
        out.sort_values(by=sort_cols, ascending=sort_asc)
           .drop_duplicates(subset=key_cols, keep="first")
           .drop(columns=["__co2_notnull__", "__cat_known__", "__amount__"], errors="ignore")
           .reset_index(drop=True)
    )
    return out
