import streamlit as st
import pandas as pd
from pathlib import Path

# Placeholder voor LLM extractie
# Vervang deze functie door echte LLM-aanroep
def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    # Return dict met veldnaam -> gevonden waarde (nu lege strings)
    return {field: "" for field in field_prompts.keys()}

# Streamlit-applicatie
def app():
    st.set_page_config(page_title="Document Extractor", layout="wide")
    st.title("📄 Document Extractor")
    st.write("Upload documenten en definieer velden om informatie te extraheren.")

    # Twee kolommen: links upload, rechts velddefinitie
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Upload documenten")
        uploads = st.file_uploader(
            label="Kies bestanden",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Maximaal 10 documenten"
        )

    with col2:
        st.subheader("Definieer velden")
        st.write("_Optioneel: ten minste één veld met prompt invullen._")
        names = [st.text_input(f"Kolomnaam {i+1}", key=f"name_{i}") for i in range(10)]
        prompts = [st.text_area(f"Prompt {i+1}", height=60, key=f"prompt_{i}") for i in range(10)]

    # Combineer ingevulde velden
    field_prompts = {name: prompt for name, prompt in zip(names, prompts) if name and prompt}

    # Extractieknop en resultaat onderaan
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
            # Toon resultaat als tabel
            if results:
                df = pd.DataFrame(results)
                st.subheader("Extractie Resultaten")
                st.dataframe(df, use_container_width=True)
                # Download-knoppen
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
        st.info("Upload minimaal één document en definieer één veld met prompt om te starten.")

if __name__ == '__main__':
    app()