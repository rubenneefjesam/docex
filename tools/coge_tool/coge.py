import streamlit as st

def app():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown("## 🔍 Coge")
    with col2:
        st.write("Upload twee PDF’s om te vergelijken:")

        v1 = st.file_uploader("Versie 1 (PDF)", type="pdf", key="pdf_v1")
        v2 = st.file_uploader("Versie 2 (PDF)", type="pdf", key="pdf_v2")

        if v1 and v2:
            st.success(f"✅ Beide bestanden geüpload: {v1.name} en {v2.name}")
