import streamlit as st
import pandas as pd
from pathlib import Path

# Placeholder for LLM extraction function
def extract_fields(file_path: Path, field_prompts: dict) -> dict:
    # TODO: implement actual extraction via LLM
    # Should return a dict mapping field_name -> extracted_value
    return {name: "" for name in field_prompts.keys()}

# Streamlit UI
def app():
    st.header("📄 Document Extractor")
    st.write("Upload documenten en definieer velden om informatie te extraheren.")

    # Upload
    uploads = st.file_uploader("Upload bestanden", type=["pdf", "docx", "txt"], accept_multiple_files=True)

    # Define fields
    st.sidebar.header("Definieer velden")
    with st.sidebar.form(key="fields_form", clear_on_submit=False):
        names = []
        prompts = []
        # First 10: kolomnamen      
        st.subheader("Kolomnamen (optioneel)")
        for i in range(10):
            names.append(st.text_input(f"Veldnaam {i+1}", key=f"name_{i}"))
        # Next 10: LLM prompts   
        st.subheader("Prompt beschrijvingen")
        for i in range(10):
            prompts.append(st.text_area(f"Prompt {i+1}", height=60, key=f"prompt_{i}"))

        submit = st.form_submit_button("Opslaan velden")

    # Ensure at least document column
    field_names = [n for n in names if n]
    field_prompts = {n: p for n, p in zip(names, prompts) if n and p}

    if uploads and field_prompts:
        if st.button("Extraheer informatie"):
            results = []
            with st.spinner("Bezig met extraheren..."):
                for uf in uploads:
                    tmp_path = Path(f"/tmp/{uf.name}")
                    tmp_path.write_bytes(uf.getvalue())
                    extracted = extract_fields(tmp_path, field_prompts)
                    row = {"Document": uf.name}
                    row.update(extracted)
                    results.append(row)
            # Display table
            df = pd.DataFrame(results)
            st.dataframe(df)
            # Download PDF placeholder
            st.download_button("⬇️ Download PDF", data=df.to_csv(index=False), file_name="extracted_table.pdf", mime="application/pdf")
    else:
        st.info("Upload bestanden en definieer ten minste één veld prompt.")

if __name__ == "__main__":
    app()
