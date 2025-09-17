import os
import streamlit as st
import hashlib
import numpy as np

from groq import Groq
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import (
    extract_pdf_lines,
    full_text,
)

# ─── Groq‐client initiëren ────────────────────────────────────────
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
EMBEDDING_MODEL      = "groq-embedding-1.0"
CHAT_MODEL           = "llama-3.1-8b-instant"
MAX_PDF_MB           = 10
MAX_CHARS_PER_PROMPT = 30000  # ter bescherming tegen te grote prompts

# ─── Document laden ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_document(pdf_bytes: bytes) -> str:
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

# ─── Embedding voor bron‐retrieval ──────────────────────────────
@st.cache_data(show_spinner=False)
def embed_document(text: str) -> list[dict]:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    embeddings = []
    batch_size = 256
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend(resp.data)
    return [{"text": ln, "emb": e.embedding} for ln, e in zip(lines, embeddings)]

@st.cache_data(show_spinner=False)
def retrieve_relevant(query: str, docs: list[dict], top_k: int = 3) -> list[str]:
    q_emb = client.embeddings.create(model=EMBEDDING_MODEL, input=[query]).data[0].embedding
    q_arr = np.array(q_emb)
    sims = [
        (float(np.dot(np.array(d["emb"]), q_arr) / (np.linalg.norm(d["emb"]) * np.linalg.norm(q_arr))), d["text"])
        for d in docs
    ]
    sims.sort(key=lambda x: x[0], reverse=True)
    return [txt for _, txt in sims[:top_k]]

# ─── Korte samenvatting ─────────────────────────────────────────
@st.cache_data(show_spinner=False)
def build_summary(text: str) -> str:
    snippet = text if len(text) <= MAX_CHARS_PER_PROMPT else text[:MAX_CHARS_PER_PROMPT]
    prompt = (
        "Je bent een beknopte documentassistent. Geef een korte samenvatting "
        "van de onderstaande tekst (maximaal 5 zinnen):\n\n"
        f"{snippet}\n\n"
    )
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ─── Q&A aanroep ────────────────────────────────────────────────
def build_qa_prompt(text: str, question: str) -> str:
    snippet = text if len(text) <= MAX_CHARS_PER_PROMPT else text[-MAX_CHARS_PER_PROMPT:]
    return (
        "Je bent een behulpzame assistent. Gebruik alleen de onderstaande tekst\n"
        "om de vraag te beantwoorden:\n\n"
        f"{snippet}\n\n"
        f"Vraag: {question}\n"
        "Antwoord:"
    )

def ask_chat(prompt: str) -> str:
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()

# ─── Streamlit UI ───────────────────────────────────────────────
def app():
    st.set_page_config(layout="wide")
    st.title("🗂️ Document Q&A & Samenvatting met Bronvermelding")

    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te beginnen.")
        return
    if uploaded.size > MAX_PDF_MB * 1024**2:
        st.error(f"Max bestandsgrootte is {MAX_PDF_MB} MB.")
        return

    # Laad en embed document
    pdf_bytes = uploaded.getvalue()
    try:
        doc_text = load_document(pdf_bytes)
        docs     = embed_document(doc_text)
    except Exception as e:
        st.error(f"Fout bij documentverwerking: {e}")
        return

    # Genereer korte samenvatting (rechtsboven)
    summary = build_summary(doc_text)

    # Vraag & antwoord
    question = st.text_input("Stel je vraag over het document")

    answer = None
    sources = []
    if question:
        prompt = build_qa_prompt(doc_text, question)
        try:
            answer = ask_chat(prompt)
            # Bepaal bronnen voor dit antwoord
            sources = retrieve_relevant(question, docs, top_k=3)
        except Exception as e:
            st.error(f"Fout bij chat-aanroep of retrieval: {e}")
            return

    # Toon in twee kolommen
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("📥 Q&A")
        if not question:
            st.info("Typ een vraag om te starten.")
        else:
            st.markdown("**Antwoord:**")
            st.write(answer)

    with col2:
        st.header("📝 Korte Samenvatting")
        st.markdown(summary)
        if question:
            st.subheader("🔍 Bronnen voor dit antwoord")
            for i, src in enumerate(sources, start=1):
                st.markdown(f"{i}. {src}")

if __name__ == "__main__":
    app()
