# llm_utils.py
import streamlit as st
from groq import Groq
from typing import List


def init_groq_client():
key = os.getenv("GROQ_API_KEY", "").strip() or st.secrets.get("groq", {}).get("api_key", "").strip()
if not key:
st.error("Geen Groq API key")
return None
return Groq(api_key=key)


client = init_groq_client()


def classify_category(description: str, categories: List[str], client=None) -> str:
if client is None:
client = globals().get("client")
prompt = (
"Kies precies één categorie uit de volgende lijst voor deze productomschrijving:\n"
f"{categories}\n"
f"Omschrijving: {description}\n"
"Antwoord alleen met de categorie-naam, zonder extra tekst."
)
resp = client.chat.completions.create(
model="llama-3.1-8b-instant",
temperature=0,
messages=[{"role":"user","content":prompt}]
)
return resp.choices[0].message.content.strip()