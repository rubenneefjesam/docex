# webapp/assistants/contact.py
DISPLAY_NAME = "Contact"
TOOLS = ["— Kies tool —"]  # Contact heeft meestal geen tools, maar lijst moet bestaan

import streamlit as st

def render(tool):
    st.title(DISPLAY_NAME)
    st.write("Contactinformatie en support.")
    st.write("- E-mail: support@example.com")
    st.write("- Interne chat: #ai-innovation")
    st.write("- Telefoon: 012-3456789")
    if tool and tool != "— Kies tool —":
        st.warning(f"Onverwachte tool geselecteerd: {tool}")
