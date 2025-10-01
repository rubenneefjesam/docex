from __future__ import annotations
import os
import re
import math
from typing import List, Dict, Any, Optional

import pandas as pd

# ────────────────────────────────────────────────────────────────
# Init LLM client (optioneel, mag None zijn)
# ────────────────────────────────────────────────────────────────
def init_groq_client():
    """
    Probeer een Groq client te initialiseren als GROQ_API_KEY aanwezig is.
    Als niet aanwezig → None (we vallen terug op rule-based).
    """
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_APIKEY")
    if not api_key:
        return None
    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception:
        return None


# ────────────────────────────────────────────────────────────────
# Stap 1: Extractie van productregels uit tekst
# ────────────────────────────────────────────────────────────────
_PRICE_RX = r"[-+]?\d[\d\.,]*"
_QTY_RX = r"[-+]?\d[\d\.,]*"

def _eu_to_float_fast(s: str) -> Optional[float]:
    if s is None:
        return None
    s = str(s)
    m = re.search(_PRICE_RX, s)
    if not m:
        return None
    num = m.group(0)
    if "," in num and "." in num:
        # "1.234,56" → "1234.56"
        num = num.replace(".", "").replace(",", ".")
    elif "," in num and "." not in num:
        # "123,45" → "123.45"
        num = num.replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None


def extract_invoice_rows(text: str, filename: str, client=None) -> List[Dict[str, Any]]:
    """
    Best-effort regex-extractie:
    Zoekt naar tabella-achtige lijnen met: omschrijving, qty, unit price, line total
    Voorbeelden die matchen:
      "Widget A 10 st € 15,00 € 150,00"
      "Service C 2 uur 50,00 100,00"
    """
    rows = []
    if not text:
        return rows

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # simpele heuristiek: als er valuta/bedragen op regel staan, pakken we die
    for idx, ln in enumerate(lines, start=1):
        # Probeer line_total als laatste bedrag op de regel
        money = re.findall(_PRICE_RX, ln)
        if len(money) >= 1:
            # Laatste bedrag is waarschijnlijk line_total
            line_total = _eu_to_float_fast(money[-1])
            # unit price → neem voorlaatste als beschikbaar en kleiner dan total
            unit_price = _eu_to_float_fast(money[-2]) if len(money) >= 2 else None
            if unit_price is not None and line_total is not None and unit_price > line_total:
                # Soms staat unit price ná total, corrigeer
                unit_price = None

            # quantity → heuristisch: getal direct vóór unit of voor bedragen
            qty = None
            unit = None
            m_qty = re.search(rf"({_QTY_RX})\s*(st|stuk|stuks|pcs|kg|m|uur|u|h)\b", ln.lower())
            if m_qty:
                qty = _eu_to_float_fast(m_qty.group(1))
                unit = m_qty.group(2)

            # description → lijn zonder de geldbedragen
            desc = re.sub(_PRICE_RX, "", ln)
            desc = re.sub(r"\s{2,}", " ", desc).strip()

            # sanity: we willen minimaal een description en een line_total
            if desc and (line_total is not None):
                # als unit_price, qty ontbreken → probeer af te leiden
                if unit_price is None and qty and qty > 0:
                    # ruw: unit_price ≈ total / qty
                    unit_price = round(line_total / qty, 4)
                elif unit_price and (not qty or qty == 0):
                    # qty ≈ total / unit_price
                    approx = line_total / unit_price if unit_price else None
                    if approx and approx > 0.1:
                        qty = round(approx, 4)

                rows.append(
                    {
                        "file": filename,
                        "line_no": idx,
                        "description": desc,
                        "quantity": qty,
                        "unit": unit,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    }
                )
    # unieker maken op (description, line_total) om obvious header/footers te filteren
    unique = {}
    for r in rows:
        key = (r["description"], r["line_total"])
        if key not in unique:
            unique[key] = r
    return list(unique.values())


# ────────────────────────────────────────────────────────────────
# Stap 2: Categoriseren (LLM of rule-based fallback)
# ────────────────────────────────────────────────────────────────
def _rule_based_category(desc: str, categories_index) -> str:
    d = (desc or "").lower()
    # heel simpele keyword-set; breid uit naar wens
    if any(k in d for k in ["staal", "steel", "inox"]):
        return "staal"
    if any(k in d for k in ["aluminium", "aluminum", "alu"]):
        return "aluminium"
    if any(k in d for k in ["kunststof", "plastic", "pvc", "poly"]):
        return "kunststof"
    if any(k in d for k in ["uur", "u ", "service", "arbeid", "consult", "installatie"]):
        return "dienst"

    # fuzzy fallback: pak eerste category met hoogste overlappende token
    toks = {t for t in re.findall(r"[a-zA-Z]+", d) if len(t) > 2}
    best_key = "onbekend"
    best_score = -1
    for key in categories_index:
        base = re.sub(r"[^a-z]", "", key)
        score = len(toks.intersection({base}))  # erg simpel
        if score > best_score:
            best_score = score
            best_key = key
    return best_key


def classify_rows_with_llm_or_rules(df: pd.DataFrame, categories_index, client=None) -> pd.DataFrame:
    out = df.copy()
    cats_lower = set(categories_index)  # al lower-case in ensure_categories_index
    results: List[str] = []

    use_llm = client is not None
    prompt_tpl = (
        "Classificeer de volgende omschrijving naar één van deze categorieën "
        f"(exact label teruggeven): {sorted(list(cats_lower))}\n\n"
        "Omschrijving: \"{desc}\"\nAntwoord: "
    )

    if use_llm:
        try:
            # Groq chat call; modelnaam eventueel aanpassen aan jouw stack
            model_name = os.getenv("GROQ_MODEL", "llama3-70b-8192")
        except Exception:
            use_llm = False

    for _, row in out.iterrows():
        desc = row.get("description", "") or ""
        cat_key = None
        if use_llm:
            try:
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "Je bent een nauwkeurige categorisatiemodule."},
                        {"role": "user", "content": prompt_tpl.format(desc=desc)},
                    ],
                    temperature=0.0,
                    max_tokens=8,
                )
                raw = completion.choices[0].message.content.strip().lower()
                # schoonmaken
                raw = re.sub(r"[^a-zà-ÿ0-9 \-]", "", raw)
                if raw in cats_lower:
                    cat_key = raw
            except Exception:
                cat_key = None

        if not cat_key:
            cat_key = _rule_based_category(desc, categories_index)

        # als nog steeds niets, zet naar 'onbekend' indien beschikbaar
        if cat_key not in cats_lower:
            cat_key = "onbekend" if "onbekend" in cats_lower else next(iter(cats_lower))

        results.append(cat_key)

    out["category_key"] = results
    return out


# ────────────────────────────────────────────────────────────────
# Stap 3: Berekening impacts
# ────────────────────────────────────────────────────────────────
def compute_impacts(df: pd.DataFrame, category_factors: pd.DataFrame) -> pd.DataFrame:
    """
    Verwacht df met kolom 'category_key' en 'line_total'.
    category_factors: index = lowercased category, kolommen: factor, unit
    """
    out = df.copy()
    out["line_total"] = pd.to_numeric(out["line_total"], errors="coerce").fillna(0.0)

    def factor_for(key: str):
        key_l = (key or "").lower()
        if key_l in category_factors.index:
            r = category_factors.loc[key_l]
            return float(r["factor"]), str(r["unit"])
        # default fallback
        return 0.5, "kgCO2e/€"

    factors = out["category_key"].apply(lambda k: factor_for(k)[0])
    units = out["category_key"].apply(lambda k: factor_for(k)[1])
    out["emission_factor"] = factors
    out["emission_unit"] = units
    out["emissions"] = out["line_total"] * out["emission_factor"]

    # Handige volgorde van kolommen
    cols_order = [
        "file", "line_no", "description",
        "quantity", "unit", "unit_price", "line_total",
        "category_key", "emission_factor", "emission_unit", "emissions",
    ]
    for c in cols_order:
        if c not in out.columns:
            out[c] = None
    out = out[cols_order]

    return out
