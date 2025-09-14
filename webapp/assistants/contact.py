# webapp/assistants/contact.py
DISPLAY_NAME = "Contact"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st

def render(tool=None):
    st.header(DISPLAY_NAME)
    st.write("Contactpagina")
    st.markdown("""
- **E-mail:** support@example.com  
- **Telefoon:** 012-3456789
""")
