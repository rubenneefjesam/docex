import streamlit as st

def app():
    """
    Simpele Coge-app: voorlopig alleen 'Hallo'
    """
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("## 🔍 Coge")
    with col2:
        st.write("Hallo 👋")