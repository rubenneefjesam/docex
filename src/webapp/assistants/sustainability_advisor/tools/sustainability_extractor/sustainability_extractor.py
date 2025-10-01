# sustainability_extractor.py
import streamlit as st
import pandas as pd
from pathlib import Path
from invoice_utils import extract_line_items
from csv_utils import load_categories_data, ensure_categories_index
from llm_utils import classify_category, client


CATEGORIES_CSV = Path(__file__).parent / "categorieen.csv"




def app():
st.set_page_config(page_title="Sustainability Extractor", layout="wide")
st.title("📑 Sustainability Line Item Extractor & Categorizer")


uploads = st.file_uploader("Upload factuurdocument(en)", type=["pdf","docx","txt"], accept_multiple_files=True)
if not uploads:
st.info("Upload minimaal één document.")
return


if st.button("🚀 Extraheer lijnitems"):
all_rows = []
with st.spinner("Extractie via LLM…"):
for uf in uploads:
tmp = Path(f"/tmp/{uf.name}")
tmp.write_bytes(uf.getvalue())
items = extract_line_items(tmp)
for item in items:
row = {
"Document": uf.name,
"Datum": item.get("Datum",""),
"Factuurnummer": item.get("Factuurnummer",""),
"Bedrijfsnaam": item.get("Bedrijfsnaam",""),
"Productomschrijving": item.get("Productomschrijving",""),
"Hoeveelheid": item.get("Hoeveelheid",""),
"Eenheid": item.get("Eenheid",""),
}
all_rows.append(row)
if all_rows:
df = pd.DataFrame(all_rows)
df.index = df.index + 1
df.index.name = "Regelnummer"
st.session_state["extract_df"] = df
st.write(df)
else:
st.warning("Geen lijnitems gevonden.")


if "extract_df" in st.session_state:
df = st.session_state["extract_df"]
if st.button("🔖 Categoriseer lijnitems"):
cats = load_categories_data(CATEGORIES_CSV)
cats_idx = ensure_categories_index(cats)
category_list = cats["category"].tolist()
with st.spinner("Categoriseren via LLM…"):
df["Categorie"] = df["Productomschrijving"].apply(
lambda desc: classify_category(desc, category_list, client)
)
st.write(df)


if __name__ == '__main__':
app()