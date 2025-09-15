import streamlit as st
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import app

st.set_page_config(page_title="Doc Compare Test", layout="wide")
app()
