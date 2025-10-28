import os
import io
import tempfile
import re
import json
import streamlit as st
import pdfplumber
import pandas as pd

# ------------------------------------------------
# Helper: PDF parser voor code en omschrijving
# ------------------------------------------------

def extract_code_description_pairs_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Extraheert code en bijbehorende omschrijvingen uit een PDF.

    Werking:
    - Opent de PDF met pdfplumber en leest alle tekst.
    - Zoekt naar codeblokken afgebakend met ```...``` of indented blokken.
    - Pakt de paragrafen vóór elk codeblok als omschrijving.

    Retour:
    - Lijst van dicts met keys 'code' en 'omschrijving'.
    """
    text = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    # Vind codeblokken tussen backticks
    pattern = re.compile(r"(?P<desc>.*?)```(?P<code>.*?)```", re.DOTALL)
    matches = pattern.finditer(text)
    pairs = []
    for m in matches:
        desc = m.group('desc').strip().replace('\n', ' ')
        code = m.group('code').strip()
        if desc and code:
            pairs.append({'omschrijving': desc, 'code': code})
    return pairs


# -----------------------------
# Streamlit UI - hoofdfunctie
# -----------------------------

def run(show_nav: bool = True):
    st.set_page_config(page_title="PDF Code Ontsluiter", layout="wide")
    st.markdown("## 📑 PDF Code Ontsluiter")
    st.write("Upload een PDF met codeblokken (```code```) en genereer een overzichtstabel met code en omschrijving.")

    pdf_file = st.file_uploader("Kies een PDF", type="pdf", key="pdf")
    if pdf_file:
        pdf_bytes = pdf_file.read()
        st.info("PDF geüpload, bezig met analyseren...")
        try:
            pairs = extract_code_description_pairs_from_pdf(pdf_bytes)
            if not pairs:
                st.warning("Geen codeblokken gevonden tussen ```...".")
            else:
                df = pd.DataFrame(pairs)
                st.markdown("### 📋 Gevonden code en omschrijvingen")
                st.table(df[['code', 'omschrijving']])
        except Exception as e:
            st.error(f"Fout bij verwerken PDF: {e}")

if __name__ == "__main__":
    run()
