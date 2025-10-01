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
    if s is None:
        return ""
    s = s.replace("\ufeff", "")
    s = "".join(" " if unicodedata.category(ch) == "Zs" or ch.isspace() else ch for ch in s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _squash_colname(s: str) -> str:
    s = _norm_ws(s).lower()
    s = s.replace("categorie-nummer", "categorienummer").replace("categorie nummer", "categorienummer")
    s = s.replace("emissiefactor (kg co₂e/€)", "emissiefactor")
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
    raw_bytes: bytes
    if isinstance(source, (bytes, bytearray)):
        raw_bytes = bytes(source)
    elif hasattr(source, "read"):
        raw_bytes = source.read()
    else:
        raw_bytes = Path(str(source)).read_bytes()

    preview = raw_bytes[:4096].decode("utf-8", errors="ignore")
    sep = _detect_sep_from_head(preview)

    df = pd.read_csv(io.BytesIO(raw_bytes), sep=sep, dtype=str, encoding="utf-8")
    original_cols = list(df.columns)
    df.columns = [_norm_ws(c) for c in df.columns]
    squashed = [_squash_colname(c) for c in df.columns]

    mapping: dict[str,str] = {}
    for orig, squ in zip(df.columns, squashed):
        if squ in {"category", "categorie"}:
            mapping[orig] = "category"
        elif squ in {"factor", "emissiefactor"}:
            mapping[orig] = "factor"
        elif squ in {"unit", "eenheid"}:
            mapping[orig] = "unit"
        elif squ == "categorienummer":
            mapping[orig] = "category_number"

    lower_cols = {c.lower(): c for c in df.columns}
    if "factor" not in mapping:
        for k in lower_cols:
            if "emissiefactor" in _squash_colname(k):
                mapping[lower_cols[k]] = "factor"
                break
    if "category" not in mapping and "categorie" in lower_cols:
        mapping[lower_cols["categorie"]] = "category"

    out = pd.DataFrame()
    if "category" in mapping:
        out["category"] = df[next(k for k,v in mapping.items() if v=="category")].map(_norm_ws)
    else:
        raise ValueError(f"Geen kolom voor 'category' in: {original_cols}")

    if "factor" in mapping:
        out["factor"] = df[next(k for k,v in mapping.items() if v=="factor")].map(_to_float_eu)
    else:
        raise ValueError(f"Geen kolom voor 'factor' in: {original_cols}")

    out["unit"] = (df[next(k for k,v in mapping.items() if v=="unit")].map(_norm_ws)
                   if "unit" in mapping else pd.Series("kgCO2e/€", index=df.index))
    if "category_number" in mapping:
        out["category_number"] = df[next(k for k,v in mapping.items() if v=="category_number")].map(_norm_ws)

    out = out[out["category"].astype(bool)].reset_index(drop=True)
    return out


def ensure_categories_index(df: pd.DataFrame) -> pd.DataFrame:
    if "category" not in df.columns:
        raise ValueError("Kolom 'category' ontbreekt")
    df = df.copy()
    df["__key__"] = df["category"].str.lower().str.strip()
    return df.set_index("__key__", drop=True)


# ────────────────────────────────────────────────────────────────
# llm_utils.py
import streamlit as st
from groq import Groq
from typing import List

def init_groq_client():
    key = os.getenv("GROQ_API_KEY", "").strip() or st.secrets.get("groq", {}).get("api_key", "").strip()
    if not key:
        st.error("Geen Groq API key")
        return None
    return Groq(api_key=key)

client = init_groq_client()

def classify_category(description: str, categories: List[str], client=None) -> str:
    if client is None:
        client = globals().get("client")
    prompt = (
        "Kies precies één categorie uit de volgende lijst voor deze productomschrijving:\n"
        f"{categories}\n"
        f"Omschrijving: {description}\n"
        "Antwoord alleen met de categorie-naam, zonder extra tekst."
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role":"user","content":prompt}]
    )
    return resp.choices[0].message.content.strip()


# sustainability_extractor.py
import os
import streamlit as st
import pandas as pd
from pathlib import Path
from invoice_utils import extract_line_items
from csv_utils import load_categories_data, ensure_categories_index
from llm_utils import classify_category, client

CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"


def app():
    st.set_page_config(page_title="Sustainability Extractor", layout="wide")
    st.title("📑 Sustainability Line Item Extractor & Categorizer")

    # Upload sectie
    uploads = st.file_uploader(
        "Upload factuurdocument(en)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
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
                    }
                    all_rows.append(row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            df.index = df.index + 1
            df.index.name = "Regelnummer"
            st.session_state["extract_df"] = df
            st.subheader("G geëxtraheerde lijnitems")
            st.dataframe(df)
        else:
            st.warning("Geen lijnitems gevonden.")

    # Stap 2: Classificatie
    if "extract_df" in st.session_state:
        df = st.session_state["extract_df"]
        if st.button("🔖 Categoriseer lijnitems"):
            # Laad en indexeer categorielijst
            cats = load_categories_data(CATEGORIES_CSV)
            cats_idx = ensure_categories_index(cats)
            category_list = cats["category"].tolist()

            # Classificeer per omschrijving
            with st.spinner("Categoriseren via LLM…"):
                df["Categorie"] = df["Productomschrijving"].apply(
                    lambda desc: classify_category(desc, category_list, client)
                )
            st.subheader("Gecategoriseerde lijnitems")
            st.dataframe(df)


if __name__ == '__main__':
    app()