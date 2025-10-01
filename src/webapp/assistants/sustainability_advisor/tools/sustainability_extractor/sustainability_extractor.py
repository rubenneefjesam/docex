# sustainability_extractor.py
import os
import json
import re
import ast
import streamlit as st
import pandas as pd
from pathlib import Path
from groq import Groq
from PyPDF2 import PdfReader
import docx

from .csv_utils import load_categories_csv

# ─── Groq Client Initialisatie ───────────────────────────────────
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

client = init_groq_client()

# ─── JSON helper ────────────────────────────────────────────────
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

# ─── Bestandstekst ──────────────────────────────────────────────
def read_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".docx":
        doc = docx.Document(str(path))
        return "\n".join(para.text for para in doc.paragraphs)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    raise ValueError(f"Onbekend bestandstype: {suffix}")

# ─── Factuur grove check ────────────────────────────────────────
def is_invoice(text: str) -> bool:
    return bool(re.search(r"factuurnummer|factuur\s*nr", text, re.IGNORECASE)) and \
           bool(re.search(r"€\s*\d", text))

# ─── Extractie via LLM ──────────────────────────────────────────
def extract_invoice_fields(text: str) -> list[dict]:
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

# ─── Classificatie helper ───────────────────────────────────────
def classify_rows_with_llm(df: pd.DataFrame, categories: list[dict]) -> pd.DataFrame:
    """
    Verwacht dat df de kolommen bevat:
    - Beschrijving product, Kwantiteit, Eenheid
    Output: df met extra kolommen: Categorie nummer, Categorie
    """
    if client is None:
        st.error("Geen Groq-client actief. Controleer GROQ_API_KEY.")
        return df

    # Bouw prompt
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
            except Exception as e:
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

            # Map categorie-nummer → categorie-naam
            cat_map = {c['Categorie nummer']: c['Categorie'] for c in categories}

            # Init kolommen
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

# ─── Streamlit-app ────────────────────────────────────────────────
def app():
    st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën.")

    # 1) Laad categorieën (eenmalig) en cache in session
    if "categories" not in st.session_state:
        csv_path = Path(__file__).parent / 'categorieen.csv'
        st.session_state["categories"] = load_categories_csv(csv_path)

    categories = st.session_state.get("categories", [])
    if not categories:
        st.stop()

    # 2) Upload facturen
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf","docx","txt"],
        accept_multiple_files=True
    )

    # 3) Extracteer
    if st.button("🚀 Extraheer factuurdata", type="primary"):
        if not files:
            st.warning("Upload eerst ten minste één document.")
        else:
            rows = []
            with st.spinner("Controleren en extraheren…"):
                for up in files:
                    tmp = Path(f"/tmp/{up.name}")
                    tmp.write_bytes(up.getvalue())
                    txt = read_text_from_file(tmp)
                    if not is_invoice(txt):
                        st.warning(f"❌ {up.name} lijkt geen factuur te zijn.")
                        continue
                    entries = extract_invoice_fields(txt)
                    for e in entries:
                        list_keys = [k for k,v in e.items() if isinstance(v, list)]
                        if list_keys:
                            length = len(e[list_keys[0]])
                            for i in range(length):
                                row = {"Document": up.name}
                                for k,val in e.items():
                                    row[k] = val[i] if isinstance(val,list) else val
                                rows.append(row)
                        else:
                            row = {"Document": up.name}
                            row.update(e)
                            rows.append(row)
            st.session_state["extracted_rows"] = rows

    rows = st.session_state.get("extracted_rows", [])
    if rows:
        df = pd.DataFrame(rows)
        st.session_state["df"] = df  # persist
        cols = [c for c in ["Document","Factuurnummer","Leverancier","Beschrijving product","Kwantiteit","Eenheid"] if c in df.columns]
        st.subheader("Extractie Resultaten")
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("Geen data gevonden (nog).")
        # Knop hieronder disabled
        st.button("Classificeer regels", disabled=True)
        return

    # 4) Classificeer-knop (alleen actief als er data is)
    if st.button("Classificeer regels"):
        df = st.session_state.get("df", pd.DataFrame())
        if df.empty:
            st.warning("Er zijn geen regels om te classificeren.")
            return
        # uitvoering + UI feedback
        out_df = classify_rows_with_llm(df.copy(), categories)
        if 'Categorie' in out_df.columns:
            cols = [c for c in ["Document","Factuurnummer","Leverancier","Beschrijving product","Kwantiteit","Eenheid","Categorie nummer","Categorie"] if c in out_df.columns]
            st.subheader("Geklasseerde Resultaten")
            st.dataframe(out_df[cols], use_container_width=True)
            csv2 = out_df[cols].to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download met Categorieën", data=csv2, file_name="factuur_data_geclassificeerd.csv", mime="text/csv")
        else:
            st.info("Geen categorieën toegekend (zie debug meldingen hierboven).")

if __name__ == '__main__':
    app()
