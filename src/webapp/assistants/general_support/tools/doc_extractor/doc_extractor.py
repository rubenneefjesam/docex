import streamlit as st
import pandas as pd
from pathlib import Path
import io

# Externe bibliotheken voor tekstuitlezing
from PyPDF2 import PdfReader
import docx

# Functie om tekst uit bestand te halen zonder read_any
def read_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    text = ""
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        for page in reader.pages:
            text += page.extract_text() or ""
    elif suffix in [".docx"]:
        doc = docx.Document(str(file_path))
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif suffix in [".txt"]:
        text = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")
    return text

# Extractie via OpenAI
import openai

def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    # Tekst uit document
    try:
        text = read_text_from_file(file_path)
    except Exception as e:
        return {field: f"Error reading file: {e}" for field in field_prompts}

    results = {}
    for field_name, prompt in field_prompts.items():
        full_prompt = (
            f"Je bent een assistent die specifieke informatie uit een document haalt.\n"
            f"Veld: {field_name}\n"
            f"Instructie: {prompt}\n\n"
            f"Documenttekst:\n{text}\n\n"
            f"Geef alleen de waarde voor '{field_name}', zonder extra tekst."
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0
            )
            results[field_name] = response.choices[0].message.content.strip()
        except Exception as e:
            results[field_name] = f"Error: {e}"
    return results

# Streamlit-applicatie
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor zonder read_any")
    st.write("Upload documenten, vul kolomnamen en prompts in, en klik op ‘Extraheer informatie’.")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.subheader("1️⃣ Upload documenten")
        uploads = st.file_uploader(
            label="Kies documenten (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True
        )

    with col2:
        st.subheader("2️⃣ Kolomnamen (optioneel)")
        names = [st.text_input(f"Kolomnaam {i+1}", key=f"name_{i}") for i in range(10)]

    with col3:
        st.subheader("3️⃣ Prompt beschrijvingen")
        prompts = [
            st.text_area(
                f"Prompt {i+1}", height=80,
                placeholder=f"Instructie voor kolom {i+1}",
                key=f"prompt_{i}"
            )
            for i in range(10)
        ]

    field_prompts = {
        name.strip(): prompt.strip()
        for name, prompt in zip(names, prompts)
        if name.strip() and prompt.strip()
    }

    if uploads and field_prompts and st.button("🚀 Extraheer informatie"):
        results = []
        with st.spinner("Extraheren..."):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                row = {"Document": uf.name}
                extracted = extract_fields(tmp, field_prompts)
                row.update(extracted)
                results.append(row)
        # Toon resultaat
        df = pd.DataFrame(results)
        cols = ["Document"] + [c for c in df.columns if c != "Document"]
        st.subheader("Extractie Resultaten")
        st.dataframe(df[cols], use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv, file_name="extracted_data.csv", mime="text/csv")
    else:
        st.info("Upload minimaal één document én definieer een veldnaam + prompt om te starten.")

if __name__ == '__main__':
    app()