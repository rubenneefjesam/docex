import os
import io
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
    except Exception:
        st.error("❌ Ongeldige Groq-API-key.")
        return None

client = init_groq_client()

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            text += page.extract_text() or ""
    elif suffix == ".docx":
        doc = docx.Document(str(file_path))
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif suffix == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")
    return text

# ─── Extractie via Groq LLM ──────────────────────────────────────
def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    if client is None:
        return {field: "Geen client" for field in field_prompts}
    try:
        text = read_text_from_file(file_path)
    except Exception as e:
        return {field: f"Error lezen: {e}" for field in field_prompts}

    results: dict[str, list[str]] = {}
    for field_name, prompt in field_prompts.items():
        full_prompt = (
            f"Je bent een assistent die specifieke informatie uit een document haalt.\n"
            f"Veldnaam: {field_name}\n"
            f"Instructie: {prompt}\n\n"
            f"Documenttekst:\n{text}\n"
            f"Geef de waarden voor '{field_name}' als een genummerde of door komma's gescheiden lijst."
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                temperature=0,
                messages=[{"role": "user", "content": full_prompt}]
            )
            content = resp.choices[0].message.content.strip()
            # Splits op nummers, komma's of nieuwe regels
            items = []
            for part in content.replace('\r','\n').split('\n'):
                # verwijder leading nummers of bullets
                clean = part.strip()
                if not clean:
                    continue
                # strip leading '1.', 'a)' etc.
                clean = clean.lstrip('0123456789. )-')
                # split further on commas if present
                if ',' in clean:
                    for c in clean.split(','):
                        if c.strip(): items.append(c.strip())
                else:
                    items.append(clean)
            results[field_name] = items
        except Exception as e:
            results[field_name] = [f"Error: {e}"]
    return results

# ─── Streamlit-applicatie ─────────────────────────────────────────
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor (Groq LLM)")
    st.write("Upload documenten, definieer kolommen en prompts, en klik op ‘Extraheer informatie’. ")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.subheader("1️⃣ Upload documenten")
        uploads = st.file_uploader(
            "Kies documenten (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )

    with col2:
        st.subheader("2️⃣ Kolomnamen (optioneel)")
        names = [st.text_input(f"Veldnaam {i+1}", key=f"name_{i}") for i in range(10)]

    with col3:
        st.subheader("3️⃣ Promptbeschrijvingen")
        prompts = [
            st.text_area(
                f"Prompt {i+1}", height=80,
                placeholder=f"Instructie voor kolom {i+1}",
                key=f"prompt_{i}"
            )
            for i in range(10)
        ]

    field_prompts = {name.strip(): prompt.strip() for name, prompt in zip(names, prompts) if name.strip() and prompt.strip()}

    if uploads and field_prompts and st.button("🚀 Extraheer informatie"):
        all_rows = []
        with st.spinner("Extraheren via Groq…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                extracted = extract_fields(tmp, field_prompts)
                for field, values in extracted.items():
                    for val in values:
                        all_rows.append({"Document": uf.name, field: val})
        df = pd.DataFrame(all_rows)
        # Herstel kolomvolgorde: Document eerst
        cols = ["Document"] + [c for c in df.columns if c != "Document"]
        st.subheader("Extractie Resultaten")
        st.dataframe(df[cols], use_container_width=True)
        csv = df[cols].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv, file_name="extracted_data.csv", mime="text/csv")
    else:
        st.info("Upload documenten én definieer minstens één veldnaam + prompt om te starten.")

if __name__ == '__main__':
    app()