# tools/object_counter/client.py

import os
import streamlit as st
from groq import Groq

def get_groq_client() -> Groq:
    """
    Haalt de Groq-client op via env of .streamlit/secrets.toml.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        try:
            api_key = st.secrets.get("groq", {}).get("api_key", "").strip()
        except Exception:
            api_key = ""

    if not api_key:
        st.sidebar.error("❌ Geen Groq API key gevonden.")
        st.stop()

    try:
        return Groq(api_key=api_key)
    except Exception as e:
        st.sidebar.error(f"❌ Fout bij verbinden met Groq API: {e}")
        st.stop()
