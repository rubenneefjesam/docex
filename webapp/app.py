# webapp/app.py
import streamlit as st
from tools.docex_tool import docex  # jouw bestaande tool

st.set_page_config(page_title="Docx Suite", layout="wide")

# Sidebar: enkel één menu met vier keuzes
st.sidebar.header("Navigatie")
page = st.sidebar.radio("", ["Home", "Docex", "Coge", "Info"], index=0)

st.sidebar.markdown("")

# ===== Main: toon de geselecteerde pagina / tool =====
if page == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write(
        """
        Welkom bij de DOCX-app.
        - Gebruik de sidebar om te schakelen tussen Home, Docex, Coge en Info.
        - Kies Docex om je document-templates te genereren.
        """
    )

elif page == "Info":
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write(
        """
        Info:
        - Docex: Document generator (je bestaande tool).
        - Coge: Vergelijk / compare feature (placeholder).
        """
    )

elif page == "Docex":
    # Docex verschijnt alleen wanneer 'Docex' is geselecteerd
    docex.run()

elif page == "Coge":
    # Placeholder Coge; hier kun je later de compare-UI toevoegen
    st.markdown("<h2 style='font-size:22px; font-weight:700'>🔍 Coge</h2>", unsafe_allow_html=True)
    st.write("Coge — placeholder voor compare-feature.")
