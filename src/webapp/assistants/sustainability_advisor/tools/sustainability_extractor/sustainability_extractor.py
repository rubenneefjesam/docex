import streamlit as st
import pandas as pd
from pathlib import Path
from .invoice_utils import extract_line_items


def app():
    st.set_page_config(page_title="Invoice Extractor", layout="wide")
    st.title("📄 Invoice Line Item Extractor (Groq LLM)")
    st.write("Upload je factuurdocumenten en klik op '🚀 Extraheer lijnitems'.")

    uploads = st.file_uploader(
        "Kies documenten (PDF, DOCX, TXT)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )
    extract_btn = st.button("🚀 Extraheer lijnitems")

    if uploads and extract_btn:
        all_rows = []
        with st.spinner("Extraheren via Groq…"):
            for uf in uploads:
                tmp = Path(f"/tmp/{uf.name}")
                tmp.write_bytes(uf.getvalue())
                items = extract_line_items(tmp)
                for item in items:
                    row = {
                        "Document": uf.name,
                        "Datum": item.get("Datum", ""),
                        "Factuurnummer": item.get("Factuurnummer", ""),
                        "Bedrijfsnaam": item.get("Bedrijfsnaam", ""),
                        "Productomschrijving": item.get("Productomschrijving", ""),
                        "Hoeveelheid": item.get("Hoeveelheid", ""),
                        "Eenheid": item.get("Eenheid", "")
                    }
                    all_rows.append(row)
        if all_rows:
            df = pd.DataFrame(all_rows)
            # Zet index vanaf 1 en gebruik als Regelnummer
            df.index = df.index + 1
            df.index.name = "Regelnummer"
            # Kolomvolgorde
            cols = ["Datum", "Document", "Factuurnummer", "Bedrijfsnaam", "Productomschrijving", "Hoeveelheid", "Eenheid"]
            st.subheader("Extractie Resultaten")
            st.dataframe(df[cols], use_container_width=True)
            csv = df[cols].to_csv(index=True).encode("utf-8")
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name="line_items.csv",
                mime="text/csv"
            )
        else:
            st.warning("Geen lijnitems gevonden.")
    else:
        st.info("Upload documenten en klik op de knop om te starten.")


if __name__ == '__main__':
    app()