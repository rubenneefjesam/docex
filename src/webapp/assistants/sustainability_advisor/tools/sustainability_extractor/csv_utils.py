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
if ";" in s: return ";"
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
return df.set_index("__key__", drop=True)