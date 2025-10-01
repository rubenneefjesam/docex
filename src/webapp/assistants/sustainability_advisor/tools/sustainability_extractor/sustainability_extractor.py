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

# ─── Groq Client Initialisatie ───────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; extractie werkt niet.")
        return None
    try:
        return Groq(api_key=key)
    except Exception as e:
        st.error(f"❌ Groq-client kon niet initialiseren: {e}")
        return None

client = init_groq_client()

# ─── Helper om JSON uit LLM-antwoorden te parsen ────────────────
def parse_llm_json(content: str):
    s = content.strip()
    s = re.sub(r'^\s*```(?:json)?\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s*```\s*$', '', s)
    start = min((idx for idx in (s.find('['), s.find('{')) if idx != -1), default=None)
    end = max(s.rfind(']'), s.rfind('}'))
    if start is not None and end is not None and end > start:
        s = s[start:end+1]
    s = re.sub(r',(?=\s*[\]}])', '', s)
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return ast.literal_eval(s)

# ─── Bestandstekst Inlezen ────────────────────────────────────────
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

# ─── Simpele factuur-detectie ────────────────────────────────────
def is_invoice(text: str) -> bool:
    return bool(re.search(r"factuurnummer|factuur\s*nr", text, re.IGNORECASE)) and \
           bool(re.search(r"€\s*\d", text))

# ─── Extractie via Groq LLM ────────────────────────────────────────
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
        st.error("Kan JSON niet parsen, ontvangen payload:\n" + content)
        return []
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        st.error("Onbekend formaat: verwacht JSON-array.")
        return []
    return data

# ─── Streamlit-app ────────────────────────────────────────────────
def app():
    st.set_page_config(page_title="Factuur Extractor & Classificeerder", layout="wide")
    st.title("📄 Factuur Extractor (Groq LLM) & Classificeerder")
    st.write("Upload PDF/DOCX/TXT-facturen, extraheer regels en classificeer op basis van categorieën.")

    # 1) Laad categorieën
    csv_path = Path(__file__).parent / 'categorieen.csv'
    if not csv_path.exists():
        st.error(f"categorieen.csv niet gevonden op {csv_path}")
        return
    first_line = csv_path.read_text(encoding="utf-8", errors="ignore").splitlines()[0] if csv_path.stat().st_size else ""
    sep = '\t' if first_line.count('\t') > 0 else ','
    cat_df = pd.read_csv(csv_path, sep=sep, dtype=str)
    if not {'Categorie nummer','Categorie'}.issubset(cat_df.columns):
        st.error("categorieen.csv mist de kolommen 'Categorie nummer' en/of 'Categorie'.")
        return
    cat_df = cat_df[['Categorie nummer','Categorie']]
    categories = cat_df.to_dict(orient='records')

    # 2) Upload facturen
    files = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf","docx","txt"],
        accept_multiple_files=True
    )
    if not files:
        st.info("Upload één of meer facturen om te starten.")
        return
    if not st.button("🚀 Extraheer factuurdata"):
        return

    # 3) Extractie
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

    if not rows:
        st.info("Geen data gevonden.")
        return

    df = pd.DataFrame(rows)
    cols = [c for c in ["Document","Factuurnummer","Leverancier","Beschrijving product","Kwantiteit","Eenheid"] if c in df.columns]
    st.subheader("Extractie Resultaten")
    st.dataframe(df[cols], use_container_width=True)

    # 4) Classificeer-knop
    if st.button("Classificeer regels"):
        with st.spinner("Classificeren…"):
            # Prompt bouwen
            lines = [
                "Je bent een assistent die factuurregels classificeert.",
                "Categorieën (nummer: naam):"
            ]
            for cat in categories:
                lines.append(f"{cat['Categorie nummer']}: {cat['Categorie']}")
            lines.append("\nClassificeer de onderstaande regels en geef als output een JSON-array met objecten met 'Regel' (index) en 'Categorie' (nummer). Gebruik 'Onbekend' als fallback.")
            for idx,row in df.iterrows():
                lines.append(f"Regel={idx}, Beschrijving={row.get('Beschrijving product','')}, Aantal={row.get('Kwantiteit','')}, Eenheid={row.get('Eenheid','')}")
            full_prompt = "\n".join(lines)

            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0,
                messages=[{"role":"user","content":full_prompt}]
            )
            try:
                result = parse_llm_json(resp.choices[0].message.content)
            except Exception:
                st.error("Kan classificatie JSON niet parsen:\n" + resp.choices[0].message.content)
                return

            cat_map = {c['Categorie nummer']: c['Categorie'] for c in categories}
            df['Categorie nummer'] = 'Onbekend'
            df['Categorie'] = 'Onbekend'
            for item in result:
                idx = int(item.get('Regel', -1))
                cat_num = item.get('Categorie', 'Onbekend')
                if idx in df.index:
                    df.at[idx,'Categorie nummer'] = cat_num
                    df.at[idx,'Categorie'] = cat_map.get(cat_num,'Onbekend')

        st.subheader("Geklasseerde Resultaten")
        st.dataframe(df[cols + ['Categorie nummer','Categorie']], use_container_width=True)
        csv2 = df[cols + ['Categorie nummer','Categorie']].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download met Categorieën", data=csv2, file_name="factuur_data_geclassificeerd.csv", mime="text/csv")

if __name__ == '__main__':
    app()
