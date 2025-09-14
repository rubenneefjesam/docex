DISPLAY_NAME = "Contact"
IS_ASSISTANT = False
TOOLS = ["— Kies tool —"]

import streamlit as st

def render(tool=None):
    st.header(DISPLAY_NAME)
    st.write("Contactinformatie en support.")
    st.write("- E-mail: support@example.com")
    st.write("- Chat: #ai-innovation")
    st.write("- Telefoon: 012-3456789")
    if tool and tool != "— Kies tool —":
        st.warning(f"Onverwachte tool geselecteerd: {tool}")
