import streamlit as st

def render():
    st.header("Contact")
    st.write("Contactpagina")

# webapp/assistants/contact.py
import streamlit as st

def render():
    """
    Contact-pagina voor de app.
    Zet hier je supportgegevens, e-mail, of een formulier.
    """
    st.header("Contact")
    st.write("""
        Heb je vragen of feedback?  
        Stuur een e-mail naar **support@jouwdomein.nl** of bel **(012) 345-6789**.
    """)
