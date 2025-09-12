# webapp/app.py
import streamlit as st
from tools.docex_tool import docex  # jouw bestaande tool

st.set_page_config(page_title="Docx Suite", layout="wide")

# Sidebar: Navigatie + Kies tool (elk precies één keer)
st.sidebar.header("Navigatie")
nav_choice = st.sidebar.radio("", ["Home", "Informatie"], index=0)

st.sidebar.markdown("---")

st.sidebar.header("Kies tool")
tool_choice = st.sidebar.radio("", ["(geen)", "Docex", "Coge"], index=0)

# ===== Main: toon alleen de geselecteerde navigatie-pagina =====
if nav_choice == "Home":
    st.markdown("<h1 style='font-size:32px; font-weight:700'>🏠 Home</h1>", unsafe_allow_html=True)
    st.write(
        """
        Welkom bij de DOCX-app.
        - Gebruik de sidebar om te schakelen tussen Home en Informatie.
        - Kies een tool (Docex of Coge) in de sidebar om die te gebruiken.
        """
    )
else:
    st.markdown("<h1 style='font-size:28px; font-weight:700'>ℹ️ Informatie</h1>", unsafe_allow_html=True)
    st.write(
        """
        Info:
        - Docex: Document generator (je bestaande tool).
        - Coge: Vergelijk / compare feature (placeholder).
        """
    )

st.markdown("---")

# ===== Tool area: toon de gekozen tool **alleen** =====
if tool_choice == "Docex":
    # Docex verschijnt alleen wanneer 'Docex' is geselecteerd
    docex.run()

elif tool_choice == "Coge":
    # Placeholder Coge; hier kun je later de compare-UI toevoegen
    st.markdown("<h2 style='font-size:22px; font-weight:700'>🔍 Coge</h2>", unsafe_allow_html=True)
    st.write("Coge — placeholder voor compare-feature.")
# else "(geen)" -> toon geen tool (alleen de nav content)
