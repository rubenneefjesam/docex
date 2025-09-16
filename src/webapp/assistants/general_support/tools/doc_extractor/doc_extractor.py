import streamlit as st
import pandas as pd
from pathlib import Path
from .readers import read_any
import openai

# Extractie via LLM: leest het document in en stuurt per veld de prompt + tekst naar OpenAI

def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    # Lees het document (pdf/docx/txt)
    try:
        _, text = read_any(file_path)
    except Exception as e:
        st.error(f"Fout bij inlezen {file_path.name}: {e}")
        return {field: "" for field in field_prompts}

    results: dict[str, str] = {}
    for field_name, prompt in field_prompts.items():
        # Combineer veldprompt met documenttekst
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
            extracted = response.choices[0].message.content.strip()
        except Exception as e:
            st.warning(f"Kan veld '{field_name}' niet extraheren: {e}")
            extracted = ""
        results[field_name] = extracted
    return results

# Streamlit-applicatie
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor")
    st.write("Upload documenten, definieer velden en klik op ‘Extraheer informatie’.")

    # Drie kolommen: upload, kolomnamen, prompts
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        st.subheader("1️⃣ Upload documenten")
        uploads = st.file_uploader(
            label="Kies documenten (PDF, DOCX, TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Maximaal 10 documenten"
        )

    with col2:
        st.subheader("2️⃣ Kolomnamen (optioneel)")
        names = [st.text_input(f"Naam veld {i+1}", key=f"name_{i}") for i in range(10)]

    with col3:
        st.subheader("3️⃣ Prompt beschrijvingen")
        st.write("Beschrijf wat je uit het document wilt halen. Bijvoorbeeld: 'Geef risico in max 3 woorden'")
        prompts = [
            st.text_area(
                f"Prompt {i+1}",
                height=80,
                placeholder=f"Beschrijf hier de inhoud voor kolom {i+1}...",
                key=f"prompt_{i}"
            )
            for i in range(10)
        ]

    # Maak dict veldnaam->prompt
    field_prompts = {
        name.strip(): prompt.strip()
        for name, prompt in zip(names, prompts)
        if name.strip() and prompt.strip()
    }

    # Wanneer upload én velden aanwezig: extractieknop
    if uploads and field_prompts:
        if st.button("🚀 Extraheer informatie"):
            results = []
            with st.spinner("Extraheren via LLM..."):
                for uf in uploads:
                    tmp = Path(f"/tmp/{uf.name}")
                    tmp.write_bytes(uf.getvalue())
                    extracted = extract_fields(tmp, field_prompts)
                    row = {"Document": uf.name, **extracted}
                    results.append(row)
            # Toon tabel
            if results:
                df = pd.DataFrame(results)
                cols = ["Document"] + [c for c in df.columns if c != "Document"]
                st.subheader("Extractie Resultaten")
                st.dataframe(df[cols], use_container_width=True)
                # Download CSV
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name="extracted_data.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Geen resultaten om weer te geven.")
    else:
        st.info("Upload minimaal één document én definieer minstens één veld met prompt om te starten.")

if __name__ == '__main__':
    app()