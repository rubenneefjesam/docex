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
    """Parseert robuust EU-genoteerde getallen (bijv. '2,832', '1.262,5', '3.1')."""
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
    """Normaliseer whitespace (incl. unicode spaces, BOM’s)."""
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
      - category_number (optioneel)
    """
    # 1) Lees rauwe CSV in string
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

    # 4) Kolomnamen normaliseren
    original_cols = list(df.columns)
    df.columns = [_norm_ws(c) for c in df.columns]
    squashed = [_squash_colname(c) for c in df.columns]

    # 5) Fuzzy kolom-mapping
    mapping: dict[str, str] = {}
    for orig, squ in zip(df.columns, squashed):
        if squ in {"category", "categorie"}:
            mapping[orig] = "category"
        elif squ in {"factor", "emissiefactor"}:
            mapping[orig] = "factor"
        elif squ in {"unit", "eenheid"}:
            mapping[orig] = "unit"
        elif squ == "categorienummer":
            mapping[orig] = "category_number"

    # Extra fallback-routes
    lower_cols = {c.lower(): c for c in df.columns}

    # Category fallback
    if "category" not in mapping:
        if "categorie" in lower_cols:
            mapping[lower_cols["categorie"]] = "category"
        else:
            for k in lower_cols:
                if "categor" in _squash_colname(k):
                    mapping[lower_cols[k]] = "category"
                    break

    # Factor fallback
    if "factor" not in mapping:
        for k in lower_cols:
            if "emissiefactor" in _squash_colname(k):
                mapping[lower_cols[k]] = "factor"
                break

    # Unit fallback
    if "unit" not in mapping:
        for k in lower_cols:
            if _squash_colname(k) in {"unit", "eenheid"}:
                mapping[lower_cols[k]] = "unit"
                break

    # 6) Bouw genormaliseerd frame
    out = pd.DataFrame()

    # category
    if "category" in mapping:
        out["category"] = df[next(k for k, v in mapping.items() if v == "category")].astype(str).map(_norm_ws)
    else:
        raise ValueError(f"Kon geen kolom voor 'category' vinden. Gevonden: {original_cols}")

    # factor
    if "factor" in mapping:
        factor_raw = df[next(k for k, v in mapping.items() if v == "factor")]
        out["factor"] = factor_raw.map(_to_float_eu)
    else:
        raise ValueError(f"Kon geen kolom voor 'factor' vinden. Gevonden: {original_cols}")

    # unit (optioneel)
    if "unit" in mapping:
        out["unit"] = df[next(k for k, v in mapping.items() if v == "unit")].astype(str).map(_norm_ws)
        out["unit"] = out["unit"].replace("", "kgCO2e/€")
    else:
        out["unit"] = "kgCO2e/€"

    # category_number (optioneel)
    if "category_number" in mapping:
        out["category_number"] = df[next(k for k, v in mapping.items() if v == "category_number")].astype(str).map(_norm_ws)

    # 7) Opschonen
    out["category"] = out["category"].fillna("").str.strip()
    out["factor"] = pd.to_numeric(out["factor"], errors="coerce").fillna(0.0)
    out["unit"] = out["unit"].fillna("kgCO2e/€").replace("", "kgCO2e/€")
    out = out[out["category"] != ""].reset_index(drop=True)

    return out


def ensure_categories_index(df: pd.DataFrame) -> pd.DataFrame:
    """Zet index op lowercased 'category' voor eenvoudige lookups."""
    if "category" not in df.columns:
        raise ValueError("Kolom 'category' ontbreekt.")
    df = df.copy()
    df["__key__"] = df["category"].astype(str).str.lower().str.strip()
    return df.set_index("__key__", drop=True)
