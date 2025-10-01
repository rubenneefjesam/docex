# llm_utils.py
import os
import json
import re
import ast
import pandas as pd
import streamlit as st
from groq import Groq

# ────────────────────────────────────────────────────────────────
# Groq client
# ────────────────────────────────────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; extractie/classificatie werken niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception as e:
        st.error(f"❌ Groq-client kon niet initialiseren: {e}")
        return None

# ────────────────────────────────────────────────────────────────
# JSON helpers
# ────────────────────────────────────────────────────────────────
def parse_llm_json(content: str):
    s = (content or "").strip()
    s = re.sub(r'^\s*```(?:json)?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*```\s*$', '', s)
    start = min((idx for idx in (s.find('['), s.find('{')) if idx != -1), default=None)
    end = max(s.rfind(']'), s.rfind('}'))
    if start is not None and end is not None and end > start:
        s = s[start:end+1]
    s = re.sub(r',(?=\s*[\]}])', '', s)
    try:
        return json.loads(s)
    except Exception:
        return ast.literal_eval(s)

def _normalize_entries_llm(data):
    """
    Normaliseer LLM-output naar list[dict] met alleen scalars.
    - dict met lijsten -> list[dict] als alle lijsten even lang; anders pak eerste element.
    - list[dict] met lijstwaarden -> reduceer lijstwaarden naar eerste element.
    - anders -> []
    """
    def is_scalar(x):
        return not isinstance(x, (list, dict))

    if isinstance(data, dict):
        list_fields = {k: v for k, v in data.items() if isinstance(v, list)}
        if list_fields:
            lengths = {len(v) for v in list_fields.values()}
            if len(lengths) == 1:
                n = lengths.pop()
                out = []
                for i in range(n):
                    row = {}
                    for k, v in data.items():
                        row[k] = (v[i] if isinstance(v, list) else v)
                    out.append(row)
                return out
            else:
                # ongelijkmatige lijsten → neem eerste element per lijst
                row = {}
                for k, v in data.items():
                    row[k] = (v[0] if isinstance(v, list) and v else None) if isinstance(v, list) else v
                return [row]
        else:
            return [data]

    if isinstance(data, list):
        out = []
        for item in data:
            if isinstance(item, dict):
                row = {}
                for k, v in item.items():
                    row[k] = v[0] if isinstance(v, list) and v else (None if isinstance(v, list) else v)
                out.append(row)
        return out

    return []

# ────────────────────────────────────────────────────────────────
# Extractie via LLM
# ────────────────────────────────────────────────────────────────
def extract_invoice_fields(text: str, client: Groq) -> list[dict]:
    """
    Geeft list[dict] terug; elke dict is één REGEL met scalars:
      'Factuurnummer', 'Leverancier', 'Beschrijving product', 'Kwantiteit', 'Eenheid', 'Bedrag (EUR)'
    """
    if client is None:
        return []

    prompt = (
        "Je bent een assistent die factuurinformatie per REGEL uit een document haalt.\n"
        "Output-SCHEMA (ZEER BELANGRIJK):\n"
        "- Geef ALLEEN een JSON-ARRAY terug.\n"
        "- Elke array-entry is ÉÉN REGEL (object) met uitsluitEND SCALARS (géén arrays in een object).\n"
        "- Voor elke regel: gebruik exact de velden: "
        "'Factuurnummer', 'Leverancier', 'Beschrijving product', 'Kwantiteit', 'Eenheid', 'Bedrag (EUR)'.\n"
        "- 'Kwantiteit' en 'Bedrag (EUR)' moeten numeriek zijn (string met alleen getal, geen €-teken of duizendtallen).\n"
        "- Als iets onbekend is, laat het veld leeg of gebruik null.\n"
        "—\n"
        "Geef GEEN uitleg, GEEN code fences — ALLEEN de JSON-array.\n\n"
        f"Documenttekst:\n{text}"
    )

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    content = resp.choices[0].message.content

    try:
        data = parse_llm_json(content)
    except Exception:
        st.error("Kan JSON niet parsen, ontvangen payload:\n" + str(content))
        return []

    norm = _normalize_entries_llm(data)

    # Schoon & forceer sleutelset
    clean = []
    keys = ["Factuurnummer", "Leverancier", "Beschrijving product", "Kwantiteit", "Eenheid", "Bedrag (EUR)"]
    for r in norm:
        if not isinstance(r, dict):
            continue
        # trim strings
        r = {k: (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        for k in keys:
            r.setdefault(k, None)
        # Laat alleen regels toe die iets zinnigs bevatten
        if not any([r.get("Beschrijving product"), r.get("Bedrag (EUR)"), r.get("Kwantiteit")]):
            continue
        clean.append(r)

    return clean

# ────────────────────────────────────────────────────────────────
# Classificatie via LLM
# ────────────────────────────────────────────────────────────────
def classify_rows_with_llm(df: pd.DataFrame, categories: list[dict], client: Groq) -> pd.DataFrame:
    if client is None:
        st.error("Geen Groq-client actief. Controleer GROQ_API_KEY.")
        return df

    lines = [
        "Je bent een assistent die factuurregels classificeert.",
        "Categorieën (nummer: naam):"
    ]
    for cat in categories:
        lines.append(f"{cat['Categorie nummer']}: {cat['Categorie']}")
    lines.append(
        "\nClassificeer de onderstaande regels en geef als output een JSON-array met objecten met "
        "'Regel' (index) en 'Categorie' (nummer). Gebruik 'Onbekend' als fallback."
    )
    for idx, row in df.iterrows():
        lines.append(
            f"Regel={idx}, Beschrijving={row.get('Beschrijving product','')}, "
            f"Aantal={row.get('Kwantiteit','')}, Eenheid={row.get('Eenheid','')}, "
            f"BedragEUR={row.get('Bedrag (EUR)','')}"
        )
    full_prompt = "\n".join(lines)

    with st.status("Classificeren via LLM…", expanded=False) as status:
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0,
                messages=[{"role":"user","content":full_prompt}]
            )
            raw = resp.choices[0].message.content
            if not raw or not raw.strip():
                st.error("LLM stuurde een lege response terug.")
                status.update(state="error")
                return df

            try:
                result = parse_llm_json(raw)
            except Exception:
                st.error("Kan classificatie JSON niet parsen. Zie ‘Debug’ hieronder.")
                with st.expander("🔎 Debug: LLM response"):
                    st.code(raw)
                status.update(state="error")
                return df

            if not isinstance(result, list):
                st.error("LLM output is geen JSON-array. Zie ‘Debug’ hieronder.")
                with st.expander("🔎 Debug: LLM response"):
                    st.code(raw)
                status.update(state="error")
                return df

            df['Categorie nummer'] = 'Onbekend'
            df['Categorie'] = 'Onbekend'
            cat_map = {c['Categorie nummer']: c['Categorie'] for c in categories}

            for item in result:
                try:
                    idx = int(item.get('Regel', -1))
                except Exception:
                    continue
                cat_num = str(item.get('Categorie', 'Onbekend'))
                if idx in df.index:
                    df.at[idx, 'Categorie nummer'] = cat_num
                    df.at[idx, 'Categorie'] = cat_map.get(cat_num, 'Onbekend')

            status.update(label="Classificatie voltooid ✅", state="complete")
            return df

        except Exception as e:
            st.error(f"Er ging iets mis tijdens classificatie: {e}")
            with st.expander("🔎 Debug: prompt voorbeeld"):
                st.code("\n".join(lines[:30]) + "\n...\n(ingekort)")
            status.update(state="error")
            return df
