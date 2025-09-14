# webapp/assistants/contact.py
import streamlit as st

def render():
    st.markdown("<h1 style='font-size:28px; font-weight:700'>✉️ Contact</h1>", unsafe_allow_html=True)
    st.write("Contactgegevens & support")
    st.markdown("---")
    st.write("- E-mail: it-support@voorbeeld.nl")
    st.write("- Telefoon: 012-3456789")
    st.write("- Interne procedure: open een ticket via JIRA `DOCGEN`")S