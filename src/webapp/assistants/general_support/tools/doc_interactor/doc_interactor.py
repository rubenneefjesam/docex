import os
import streamlit as st
import hashlib

from pathlib import Path
from groq import Groq
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import (
    extract_pdf_lines,
    full_text,
)

# ─── Groq‐client initiëren ─────────────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("Geen Groq-API-key gevonden; stop.")
        return None
    return Groq(api_key=key)

client = init_groq_client()
if client is None:
    st.stop()

# ─── Configuratie ────────────────────────────────────────────────
CHAT_MODEL = "llama-3.1-8b-instant"
MAX_PDF_MB  = 10
# Max tokens per prompt, zodat we niet over de limiet gaan:
MAX_CHARS_PER_PROMPT = 30000

# ─── PDF inlezen ────────────────────────────────────────────────
@st.cache_data
def load_document(pdf_bytes: bytes) -> str:
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

# ─── Prompt bouwen ───────────────────────────────────────────────
def build_prompt(text: str, question: str) -> str:
    # Truncate tekst tot MAX_CHARS_PER_PROMPT
    snippet = text if len(text) <= MAX_CHARS_PER_PROMPT else text[-MAX_CHARS_PER_PROMPT:]
    return (
        "Je bent een behulpzame assistent. Gebruik alleen de onderstaande tekst om de vraag te beantwoorden.\n\n"
        f"Tekst:\n{snippet}\n\n"
        f"Vraag: {question}\n"
        "Antwoord:"
    )

# ─── Chat aanroepen ──────────────────────────────────────────────
def ask_chat(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ─── Streamlit UI ───────────────────────────────────────────────
def app():
    st.title("🗂️ Document Q&A zonder embeddings")
    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te beginnen.")
        return

    if uploaded.size > MAX_PDF_MB * 1024**2:
        st.error(f"Max bestandsgrootte is {MAX_PDF_MB} MB.")
        return

    pdf_bytes = uploaded.getvalue()
    try:
        doc_text = load_document(pdf_bytes)
    except Exception as e:
        st.error(f"Fout bij PDF-extractie: {e}")
        return

    st.success(f"Document geladen ({len(doc_text.splitlines())} regels).")
    question = st.text_input("Stel je vraag")

    if not question:
        return

    prompt = build_prompt(doc_text, question)
    with st.spinner("Bezig met beantwoorden…"):
        try:
            answer = ask_chat(prompt)
        except Exception as e:
            st.error(f"Fout bij chat-aanroep: {e}")
            return

    st.markdown("**Antwoord:**")
    st.write(answer)

if __name__ == "__main__":
    app()
