import streamlit as st
import pandas as pd
from pathlib import Path

# Placeholder voor LLM extractie
# Hier kun je een template prompt samenstellen, bijvoorbeeld:
# "Extracteer de waarde voor '{field}' uit het volgende document: {text}"
def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    # TODO: implement actual extraction via LLM
    # field_prompts: dict met {kolomnaam: promptbeschrijving}
    # Voor elke kolom: voer prompt uit op documenttekst en geef resultaat terug
    return {field: "(nog te extraheren)" for field in field_prompts.keys()}

# Streamlit-applicatie
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor")
    st.write("Upload documenten, definieer velden en klik op ‘Extraheer informatie’. ")

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
        st.write("Beschrijf wat je uit het document wilt halen. Bijvoorbeeld: 'Geef risico in max 3 woorden' ")
        prompts = [
            st.text_area(
                f"Prompt {i+1}",
                height=80,
                placeholder="Beschrijf hier de inhoud voor kolom {i+1}...",
                key=f"prompt_{i}"
            )
            for i in range(10)
        ]

    # Combineer ingevulde kolomnamen en prompts tot velden
    field_prompts = {
        name: prompt
        for name, prompt in zip(names, prompts)
        if name.strip() and prompt.strip()
    }

    # Extraheren en tonen
    if uploads and field_prompts:
        if st.button("🚀 Extraheer informatie"):
            results = []
            with st.spinner("Extraheren..."):
                for uf in uploads:
                    tmp = Path(f"/tmp/{uf.name}")
                    tmp.write_bytes(uf.getvalue())
                    extracted = extract_fields(tmp, field_prompts)
                    row = {"Document": uf.name}
                    row.update(extracted)
                    results.append(row)
            # Toon resultaat
            if results:
                df = pd.DataFrame(results)
                # Zorg dat kolom 'Document' altijd links staat
                cols = ["Document"] + [c for c in df.columns if c != "Document"]
                df = df[cols]
                st.subheader("Extractie Resultaten")
                st.dataframe(df, use_container_width=True)

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