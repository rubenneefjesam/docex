# llm_utils.py  (vervang extract_invoice_rows + voeg helpers toe)
import re
from typing import List, Dict, Any, Optional

_PRICE_RX = r"(?:€\s*)?[-+]?\d[\d\.,]*"   # ondersteunt optioneel € en EU-notatie
_QTY_UNIT_RX = r"(?P<qty>[-+]?\d[\d\.,]*)\s*(?P<unit>st|stuk|stuks|pcs|kg|m|mm|cm|uur|u\b|h\b)"

YEAR_RX = re.compile(r"\b(19\d{2}|20\d{2})\b")
DATE_LINE_RX = re.compile(r"\b\d{1,2}\s*[-/.]\s*\d{1,2}\s*[-/.]\s*(19|20)\d{2}\b")
TOTAL_WORDS = re.compile(r"\b(sub)?totaal|total|sum|btw|vat|grand total|balance\b", re.I)
META_WORDS = re.compile(r"\b(factuur|invoice|iban|kvk|bank|betalingskenmerk|klantnummer|referentie|inv\b)\b", re.I)
ONLY_SYMBOLS = re.compile(r"^[\s€%\-–—]*$")

def _eu_to_float_fast(s: str) -> Optional[float]:
    if s is None:
        return None
    s = str(s).strip()
    m = re.search(r"[-+]?\d[\d\.,]*", s)
    if not m:
        return None
    num = m.group(0)
    if "," in num and "." in num:
        num = num.replace(".", "").replace(",", ".")
    elif "," in num:
        num = num.replace(",", ".")
    try:
        return float(num)
    except Exception:
        return None

def _looks_like_year(n: float) -> bool:
    return 1900 <= n <= 2099

def _clean_line(s: str) -> str:
    # normaliseer en-dash/em-dash → gewone hyphen
    return s.replace("–", "-").replace("—", "-").strip()

def _is_skip_line(ln: str) -> bool:
    if not ln or ONLY_SYMBOLS.match(ln):
        return True
    if DATE_LINE_RX.search(ln):
        return True
    if TOTAL_WORDS.search(ln):
        return True
    # veelvoorkomende kop/voetwoorden
    if META_WORDS.search(ln):
        return True
    # losse '%' of '€' of heel korte snippers
    core = re.sub(r"[\s€%]", "", ln)
    if len(core) < 3:
        return True
    return False


def extract_invoice_rows(text: str, filename: str, client=None) -> List[Dict[str, Any]]:
    """
    Striktere extractor:
      - vereist 2 bedragen (unit_price + line_total) of 1 bedrag + (qty+unit)
      - filtert datum/headers/totals/negatieven/losse symbolen
    """
    rows: List[Dict[str, Any]] = []
    if not text:
        return rows

    lines = [ _clean_line(ln) for ln in text.splitlines() ]
    lines = [ ln for ln in lines if ln ]  # non-empty

    for idx, ln in enumerate(lines, start=1):
        if _is_skip_line(ln):
            continue

        # alle “bedragen” in de regel
        money_raw = re.findall(_PRICE_RX, ln)
        money = [_eu_to_float_fast(m) for m in money_raw]
        money = [v for v in money if v is not None]

        # filter negatieve en “jaartallen” die geen valuta-context hebben
        money = [v for v in money if v >= 0 and not _looks_like_year(v)]

        # hoeveelheid + eenheid
        m_qty = re.search(_QTY_UNIT_RX, ln.lower())
        qty = _eu_to_float_fast(m_qty.group("qty")) if m_qty else None
        unit = m_qty.group("unit") if m_qty else None

        # beschrijving: haal bedragen en valuta eruit
        desc = re.sub(_PRICE_RX, "", ln)
        desc = re.sub(r"\s{2,}", " ", desc).strip()

        # beschrijving moet echte tekst bevatten
        has_letters = re.search(r"[a-zA-ZÀ-ÿ]", desc) is not None
        if not has_letters or len(desc) < 4:
            # als beschrijving te karig is, sla over
            continue

        # match-criteria:
        # - (≥2 bedragen)  of  (≥1 bedrag en qty+unit aanwezig)
        if len(money) >= 2:
            # neem laatste als total, voorlaatste als unit_price
            line_total = money[-1]
            unit_price = money[-2]
            # sanity: unit_price <= line_total (met kleine tolerantie)
            if unit_price > line_total and (qty is None or qty <= 1.01):
                # waarschijnlijk geen unit price; degradeer naar enkel bedrag
                unit_price = None
            # qty afleiden indien kan
            if (qty is None or qty == 0) and unit_price:
                approx = line_total / unit_price if unit_price else None
                if approx and approx > 0.1:
                    qty = round(approx, 4)

        elif len(money) == 1 and qty:
            # alleen total en qty; derive unit_price
            line_total = money[0]
            unit_price = round(line_total / qty, 4) if qty else None
        else:
            # onvoldoende data voor productregel
            continue

        # nog een safeguard tegen totaalregels die erdoor glippen
        if TOTAL_WORDS.search(desc):
            continue

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

    # dedup op (description, line_total)
    unique = {}
    for r in rows:
        key = (r["description"], r["line_total"])
        if key not in unique:
            unique[key] = r
    return list(unique.values())
