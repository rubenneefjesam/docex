import streamlit as st
from tools.docex_tool import docex

st.set_page_config(page_title="Docx Suite", layout="centered")
st.sidebar.title("Tools")
choice = st.sidebar.radio("Kies tool", ["Docex", "Info"])

if choice == "Docex":
    docex.run()
else:
    st.markdown("## Info & Tips\n- Tools staan in `/tools/*`.\n- Kies 'Docex' om je template te genereren.")
