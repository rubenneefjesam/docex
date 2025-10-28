import io
import re
import streamlit as st
from PyPDF2 import PdfReader
import pandas as pd

# ------------------------------------------------
# Helper: PDF parser voor code en omschrijving
# ------------------------------------------------

def extract_code_description_pairs_from_pdf(pdf_bytes: bytes) -> list[dict]:
    """
    Extraheert code en bijbehorende omschrijvingen uit een PDF per regel.

    Werking:
    - Opent de PDF met PyPDF2 en leest alle tekst.
    - Verdeelt de tekst in losse regels.
    - Gebruikt een regex om lijnen te matchen in het formaat xx.xx.xx gevolgd door omschrijving.

    Retour:
    - Lijst van dicts met keys 'code' en 'omschrijving'.
    """
    # PDF lezen en platte tekst verzamelen
    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        # Splits op line breaks en bewaar
        full_text.extend(page_text.splitlines())

    # Regex voor code + omschrijving: drie groepen cijfers gescheiden door punten
    pattern = re.compile(r"^(?P<code>\d{2}\.\d{2}\.\d{2})\s+(?P<omschrijving>.+)$")
    pairs = []
    missed = []
    for line in full_text:
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            pairs.append({
                'code': m.group('code'),
                'omschrijving': m.group('omschrijving').strip()
            })
        else:
            missed.append(line)
    # Optioneel: loggemissed regels in console of sidebar
    if missed:
        st.sidebar.markdown(f"**Niet-gematchte regels:** {len(missed)}")
    return pairs


# -----------------------------
# Streamlit UI - hoofdfunctie
# -----------------------------

def run(show_nav: bool = True):
    st.set_page_config(page_title="PDF Code Ontsluiter", layout="wide")
    st.markdown("## 📑 PDF Code Ontsluiter")
    st.write("Upload een PDF met regels in formaat xx.xx.xx gevolgd door omschrijving.")

    pdf_file = st.file_uploader("Kies een PDF", type="pdf", key="pdf")
    if pdf_file:
        pdf_bytes = pdf_file.read()
        st.info("PDF geüpload, bezig met analyseren...")
        try:
            pairs = extract_code_description_pairs_from_pdf(pdf_bytes)
            if not pairs:
                st.warning("Geen code-omschrijving-patronen gevonden op de pagina's.")
            else:
                df = pd.DataFrame(pairs)
                df = df[['code', 'omschrijving']]
                st.markdown("### 📋 Gevonden codes en omschrijvingen")
                st.table(df)
                # Download-optie
                csv = df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name="codes_omschrijving.csv",
                    mime="text/csv",
                )
        except Exception as e:
            st.error(f"Fout bij verwerken PDF: {e}")

if __name__ == "__main__":
    run()

# Entrypoint export voor registry
def app():
    run()