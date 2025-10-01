# csv_utils.py
from __future__ import annotations
import io
import re
import unicodedata
from pathlib import Path
from typing import Any, Union

import pandas as pd

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
_NUM_RE = re.compile(r"[-+]?\d[\d.,]*")

def _to_float_eu(s: Any) -> float | None:
    """Robuust getal parsen uit strings als '2,832 kg CO₂e/€' of '1.262,5' of 3.1."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    m = _NUM_RE.search(s)
    if not m:
        return None
    num = m.group(0)
    # EU-notatie: ',' als decimaal, '.' als duizendtsep
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None

def _norm_ws(s: str | None) -> str:
    """Normaliseer whitespace (incl. unicode spaces) en BOM’s in kolomnamen/waarden."""
    if s is None:
        return ""
    s = s.replace("\ufeff", "")
    s = "".join(" " if unicodedata.category(ch) == "Zs" or ch.isspace() else ch for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _squash_colname(s: str) -> str:
    """Vereenvoudig kolomnamen voor fuzzy matching."""
    s = _norm_ws(s).lower()
    s = s.replace("categorie-nummer", "categorienummer")
    s = s.replace("categorie nummer", "categorienummer")
    s = s.replace("emissiefactor (kg co₂e/€)", "emissiefactor")
    s = s.replace("emissiefactor (kg co2e/€)", "emissiefactor")
    s = s.replace("emissiefactor (kg co2e/eur)", "emissiefactor")
    s = s.replace("emissiefactor (kg/co2e/eur)", "emissiefactor")
    s = s.replace("emissiefactor kg co₂e/€", "emissiefactor")
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

def _detect_sep_from_head(s: str) -> str:
    if "\t" in s: return "\t"
    if ";" in s:  return ";"
    return ","


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────
def load_categories_data(source: Union[Path, str, bytes, io.BytesIO, io.StringIO, Any]) -> pd.DataFrame:
    """
    Laad categorie/factor CSV en normaliseer naar uniforme kolommen:
      - category (str)
      - factor (float)
      - unit (str, default 'kgCO2e/€')
      - category_number (str, optioneel)

    Ondersteunde schema's:
      A) category, factor, unit
      B) 'Categorie nummer', 'Categorie', 'Emissiefactor (kg CO₂e/€)'

    Parameters
    ----------
    source : Path | str | bytes | file-like
        Pad, bytes of file-like object (met .read()).

    Returns
    -------
    pd.DataFrame
        Genormaliseerde tabel.
    """
    # 1) Lees rauwe CSV in string
    raw_bytes: bytes
    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
    elif isinstance(source, (io.BytesIO,)):
        raw_bytes = source.getvalue()
    elif hasattr(source, "read"):  # Streamlit UploadedFile of file-like
        raw_bytes = source.read()
    else:
        # Path of str naar Path
        p = Path(str(source))
        raw_bytes = p.read_bytes()

    # 2) Detecteer delimiter uit header
    preview = raw_bytes[:4096].decode("utf-8", errors="ignore")
    sep = _detect_sep_from_head(preview)

    # 3) Lees DataFrame
    df = pd.read_csv(io.BytesIO(raw_bytes), sep=sep, dtype=str, encoding="utf-8")

    # 4) Kolomnamen normaliseren (whitespace + squash)
    original_cols = list(df.columns)
    df.columns = [_norm_ws(c) for c in df.columns]
    squashed = [_squash_colname(c) for c in df.columns]

    # 5) Fuzzy kolom-mapping
    # Doelen:
    # - 'category'
    # - 'factor'
    # - 'unit'
    # - 'category_number' (optioneel)
    mapping: dict[str, str] = {}  # van huidige kolomnaam -> doellabel
    for orig, squ in zip(df.columns, squashed):
        if squ in {"category", "categorie"}:
            mapping[orig] = "category"
        elif squ in {"factor", "emissiefactor"}:
            mapping[orig] = "factor"
        elif squ in {"unit", "eenheid"}:
            mapping[orig] = "unit"
        elif squ in {"categorienummer"}:
            mapping[orig] = "category_number"

    # 6) Speciaal geval: oud schema met 'Categorie' + 'Emissiefactor (...)'
    # Als 'factor' en 'category' nog ontbreken, probeer harde matches op Nederlandse namen
    lower_cols = {c.lower(): c for c in df.columns}
    if "factor" not in mapping:
        for k in lower_cols:
            if "emissiefactor" in _squash_colname(k):
                mapping[lower_cols[k]] = "factor"
                break
    if "category" not in mapping and "categorie" in lower_cols:
        mapping[lower_cols["categorie"]] = "category"
    if "category_number" not in mapping:
        # Probeer varianten op 'Categorie nummer'
        for k in lower_cols:
            if "categorienummer" in _squash_colname(k):
                mapping[lower_cols[k]] = "category_number"
                break

    # 7) Bouw genormaliseerd frame
    out = pd.DataFrame()
    if "category" in mapping:
        out["category"] = df[next(k for k, v in mapping.items() if v == "category")].astype(str).map(_norm_ws)
    else:
        raise ValueError(
            f"Kon geen kolom voor 'category' vinden. Gevonden kolommen: {original_cols}"
        )

    if "factor" in mapping:
        factor_raw = df[next(k for k, v in mapping.items() if v == "factor")]
        out["factor"] = factor_raw.map(_to_float_eu)
    else:
        raise ValueError(
            f"Kon geen kolom voor 'factor' (emissiefactor) vinden. Gevonden kolommen: {original_cols}"
        )

    # unit optioneel → default
    if "unit" in mapping:
        out["unit"] = df[next(k for k, v in mapping.items() if v == "unit")].astype(str).map(_norm_ws)
        out["unit"] = out["unit"].replace("", "kgCO2e/€")
    else:
        out["unit"] = "kgCO2e/€"

    # category_number optioneel
    if "category_number" in mapping:
        out["category_number"] = df[next(k for k, v in mapping.items() if v == "category_number")].astype(str).map(_norm_ws)

    # 8) Opschonen
    out["category"] = out["category"].fillna("").str.strip()
    out["factor"] = pd.to_numeric(out["factor"], errors="coerce").fillna(0.0)
    out["unit"] = out["unit"].fillna("kgCO2e/€").replace("", "kgCO2e/€")

    # Filter lege categories eruit
    out = out[out["category"] != ""].reset_index(drop=True)

    return out


def ensure_categories_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Zet index op lowercased 'category' voor eenvoudige lookups.
    Laat overige kolommen ongemoeid.
    """
    if "category" not in df.columns:
        raise ValueError("Kolom 'category' ontbreekt in DataFrame.")
    df = df.copy()
    df["__key__"] = df["category"].astype(str).str.lower().str.strip()
    df = df.set_index("__key__", drop=True)
    return df


# ────────────────────────────────────────────────────────────────
# (Optioneel) handige extra
# ────────────────────────────────────────────────────────────────
def factor_map_from_df(df_indexed: pd.DataFrame) -> dict[str, float]:
    """
    Maak een dict {category_key(lower): factor}.
    Handig als je met mapping wilt werken buiten pandas.
    """
    if "factor" not in df_indexed.columns:
        raise ValueError("Kolom 'factor' ontbreekt in DataFrame.")
    # Als df nog geen lowercased index heeft, alsnog zetten
    if df_indexed.index.name != "__key__":
        df_indexed = ensure_categories_index(df_indexed)
    return df_indexed["factor"].to_dict()
