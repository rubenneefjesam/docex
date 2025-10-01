# csv_utils.py
from __future__ import annotations
import io
import re
import unicodedata
from pathlib import Path
from typing import Any, Union, Tuple, List, Dict

import pandas as pd

# ────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────
_NUM_RE = re.compile(r"[-+]?\d[\d.,]*")

def _to_float_eu(s: Any) -> float | None:
    """Parseert EU-genoteerde getallen ('2,832', '1.262,5', '3.1', '2,832 kg CO₂e/€')."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    m = _NUM_RE.search(s)
    if not m:
        return None
    num = m.group(0)
    if "," in num:
        num = num.replace(".", "").replace(",", ".")
    try:
        return float(num)
    except ValueError:
        return None

def _norm_ws(s: str | None) -> str:
    """Normaliseer whitespace (incl. NBSP) en BOM’s."""
    if s is None:
        return ""
    s = s.replace("\ufeff", "")
    s = "".join(" " if unicodedata.category(ch) == "Zs" or ch.isspace() else ch for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _squash_colname(s: str) -> str:
    """Vereenvoudig kolomnamen voor fuzzy matching (lower + verwijder niet-alfanumeriek)."""
    s = _norm_ws(s).lower()
    # veel voorkomende varianten normaliseren
    s = s.replace("categorie-nummer", "categorienummer")
    s = s.replace("categorie nummer", "categorienummer")
    # emissiefactor varianten
    s = s.replace("emissiefactor (kg co₂e/€)", "emissiefactor")
    s = s.replace("emissiefactor (kg co2e/€)", "emissiefactor")
    s = s.replace("emissiefactor (kg co2e/eur)", "emissiefactor")
    s = s.replace("emissiefactor (kg/co2e/eur)", "emissiefactor")
    s = s.replace("emissiefactor kg co₂e/€", "emissiefactor")
    # alles wat geen [a-z0-9] is weghalen
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

def _detect_sep_from_head(s: str) -> str:
    if "\t" in s: return "\t"
    if ";" in s:  return ";"
    return ","


# ────────────────────────────────────────────────────────────────
# Kern
# ────────────────────────────────────────────────────────────────
def _build_header_views(cols: List[str]) -> List[Tuple[str, str, str]]:
    """
    Return list of tuples: (original, normalized, squashed)
    """
    views = []
    for c in cols:
        n = _norm_ws(c)
        q = _squash_colname(c)
        views.append((c, n, q))
    return views

def _pick_category_col(views: List[Tuple[str, str, str]]) -> str | None:
    """
    Kies kolom voor 'category':
      - norm.lower() in {'categorie', 'category'}
      - of squash begint met 'categor'
    """
    # directe match op norm
    for orig, norm, squ in views:
        if norm.lower() in {"categorie", "category"}:
            return orig
    # prefix match op squash
    for orig, norm, squ in views:
        if squ.startswith("categor"):
            return orig
    return None

def _pick_factor_col(views: List[Tuple[str, str, str]]) -> str | None:
    """
    Kies kolom voor 'factor':
      - squash bevat 'emissiefactor'
    """
    for orig, norm, squ in views:
        if "emissiefactor" in squ:
            return orig
    return None

def _pick_unit_col(views: List[Tuple[str, str, str]]) -> str | None:
    """
    Kies kolom voor 'unit' (optioneel):
      - norm.lower() in {'unit', 'eenheid'} of squash in {'unit','eenheid'}
    """
    for orig, norm, squ in views:
        if norm.lower() in {"unit", "eenheid"} or squ in {"unit", "eenheid"}:
            return orig
    return None

def _pick_catnum_col(views: List[Tuple[str, str, str]]) -> str | None:
    """
    Kies kolom voor optionele 'category_number':
      - squash == 'categorienummer'
    """
    for orig, norm, squ in views:
        if squ == "categorienummer":
            return orig
    return None


# ────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────
def load_categories_data(source: Union[Path, str, bytes, io.BytesIO, io.StringIO, Any]) -> pd.DataFrame:
    """
    Laad categorie/factor CSV en normaliseer naar uniforme kolommen:
      - category (str)
      - factor (float)
      - unit (str, default 'kgCO2e/€')
      - category_number (optioneel)
    """
    # 1) Lees bytes
    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
    elif hasattr(source, "read"):  # UploadedFile of file-like
        raw_bytes = source.read()
    else:
        raw_bytes = Path(str(source)).read_bytes()

    # 2) Detecteer delimiter uit header
    preview = raw_bytes[:4096].decode("utf-8", errors="ignore")
    sep = _detect_sep_from_head(preview)

    # 3) Lees DataFrame
    df = pd.read_csv(io.BytesIO(raw_bytes), sep=sep, dtype=str, encoding="utf-8")

    # 4) Header-views opbouwen
    original_cols = list(df.columns)
    views = _build_header_views(original_cols)

    # 5) Kolommen kiezen via robuuste pickers
    col_category = _pick_category_col(views)
    col_factor   = _pick_factor_col(views)
    col_unit     = _pick_unit_col(views)
    col_catnum   = _pick_catnum_col(views)

    # 6) Valideer verplichte kolommen
    missing: Dict[str, List[str]] = {}
    if not col_category:
        missing["category"] = original_cols
    if not col_factor:
        missing["factor"] = original_cols
    if missing:
        problems = "; ".join([f"{k}→kon niet mappen uit {v}" for k, v in missing.items()])
        raise ValueError(f"Kolommen niet gevonden: {problems}")

    # 7) Bouw genormaliseerd frame
    out = pd.DataFrame()
    out["category"] = df[col_category].astype(str).map(_norm_ws)
    out["factor"]   = df[col_factor].map(_to_float_eu)

    if col_unit:
        out["unit"] = df[col_unit].astype(str).map(_norm_ws).replace("", "kgCO2e/€")
    else:
        out["unit"] = "kgCO2e/€"

    if col_catnum:
        out["category_number"] = df[col_catnum].astype(str).map(_norm_ws)

    # 8) Opschonen
    out["category"] = out["category"].fillna("").str.strip()
    out["factor"]   = pd.to_numeric(out["factor"], errors="coerce").fillna(0.0)
    out["unit"]     = out["unit"].fillna("kgCO2e/€").replace("", "kgCO2e/€")
    out = out[out["category"] != ""].reset_index(drop=True)

    return out

def ensure_categories_index(df: pd.DataFrame) -> pd.DataFrame:
    """Zet index op lowercased 'category' voor eenvoudige lookups."""
    if "category" not in df.columns:
        raise ValueError("Kolom 'category' ontbreekt.")
    df = df.copy()
    df["__key__"] = df["category"].astype(str).str.lower().str.strip()
    return df.set_index("__key__", drop=True)