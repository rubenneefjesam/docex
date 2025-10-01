# llm_utils.py
import os
import json
import re
import ast
import pandas as pd
import streamlit as st
from groq import Groq

# ─── Groq client ─────────────────────────────────────────────────
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

# ─── JSON helper ─────────────────────────────────────────────────
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

# ─── Extractie via LLM ───────────────────────────────────────────
def extract_invoice_fields(text: str, client: Groq) -> list[dict]:
    if client is None:
        return []
    prompts = {
        "Factuurnummer": "Haal het factuurnummer uit (inclusief letters en streepjes).",
        "Leverancier": "Noem de naam van de leverancier zoals vermeld op de factuur.",
        "Beschrijving product": "Geef per regel de productomschrijving.",
        "Kwantiteit": "Haal de aantallen per productregel op.",
        "Eenheid": "Haal de eenheid per productregel op, bijvoorbeeld stuks, kg, m."
    }
    fields = list(prompts.keys())
    instr = "\n".join(f"- {k}: {v}" for k,v in prompts.items())
    prompt = (
        "Je bent een assistent die factuurinformatie uit een document haalt.\n"
        "Reageer ALLEEN met pure JSON (zonder code fences, zonder uitleg), gebruik dubbele aanhalingstekens en geen trailing comma’s.\n"
        f"Geef als output een JSON-array met objecten met de velden: {', '.join(fields)}\n"
        f"{instr}\n\nDocumenttekst:\n{text}"
    )
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        temperature=0,
        messages=[{"role":"user","content":prompt}]
    )
    content = resp.choices[0].message.content
    try:
        data = parse_llm_json(content)
    except Exception:
        st.error("Kan JSON niet parsen, ontvangen payload:\n" + str(content))
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        st.error("Onbekend formaat: verwacht JSON-array.")
        return []
    return data

# ─── Classificatie via LLM ───────────────────────────────────────
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
            f"Aantal={row.get('Kwantiteit','')}, Eenheid={row.get('Eenheid','')}"
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

            cat_map = {c['Categorie nummer']: c['Categorie'] for c in categories}
            df['Categorie nummer'] = 'Onbekend'
            df['Categorie'] = 'Onbekend'

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
