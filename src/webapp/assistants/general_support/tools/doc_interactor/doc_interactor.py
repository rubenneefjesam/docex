import os
import streamlit as st
import hashlib
import numpy as np
from pathlib import Path

# Gebruik dezelfde Groq-lib als in je summarizer
from groq import Groq

# PDF‐parsing
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
        st.error("Geen Groq-API-key gevonden; alles valt stil.")
        return None
    return Groq(api_key=key)

client = init_groq_client()
if client is None:
    st.stop()

# ─── Configuratie ────────────────────────────────────────────────
EMBEDDING_MODEL = "groq-embedding-1.0"  # kies een model dat WÉL bestaat
CHAT_MODEL      = "llama-3.1-8b-instant"
MAX_PDF_MB      = 10

# ─── Hulpfuncties ───────────────────────────────────────────────
def _make_key(*args) -> str:
    h = hashlib.sha256()
    for a in args:
        h.update(str(a).encode())
    return h.hexdigest()

@st.cache_data(show_spinner=False, ttl=3600)
def load_document(pdf_bytes: bytes, key: str) -> str:
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

@st.cache_data(show_spinner=False, ttl=3600)
def embed_document(text: str, key: str) -> list[dict]:
    lines = [l for l in text.splitlines() if l.strip()]
    all_embs = []
    batch_size = 256
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i+batch_size]
        resp  = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        all_embs.extend(resp.data)
    return [{"text": t, "emb": e.embedding} for t, e in zip(lines, all_embs)]

@st.cache_data(show_spinner=False, ttl=3600)
def retrieve_relevant(query: str, docs: list[dict], key: str, top_k: int=5) -> list[str]:
    q_emb = client.embeddings.create(model=EMBEDDING_MODEL, input=[query]).data[0].embedding
    q_arr = np.array(q_emb)
    sims = [
        (float(np.dot(np.array(d["emb"]), q_arr) / (np.linalg.norm(d["emb"]) * np.linalg.norm(q_arr))), d["text"])
        for d in docs
    ]
    sims.sort(key=lambda x: x[0], reverse=True)
    return [txt for _, txt in sims[:top_k]]

def ask_chat(context: str, query: str) -> str:
    system = f"Je bent een behulpzame assistent. Gebruik alleen deze context:\n{context}"
    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": query},
        ],
    )
    return resp.choices[0].message.content.strip()

# ─── Streamlit UI ───────────────────────────────────────────────
def app():
    st.title("🗂️ Document Chatbot (één Groq-client)")
    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te starten.")
        return

    if uploaded.size > MAX_PDF_MB * 1024**2:
        st.error(f"Max bestand is {MAX_PDF_MB} MB.")
        return

    raw = uploaded.getvalue()
    key = _make_key(hashlib.sha256(raw).hexdigest(), EMBEDDING_MODEL)

    try:
        text = load_document(raw, key)
        docs = embed_document(text, key)
    except Exception as e:
        st.error(f"Fout bij verwerken PDF: {e}")
        return

    st.success(f"Verwerkt: {len(text.splitlines())} regels.")
    q = st.text_input("Vraag:")
    if not q:
        return

    with st.spinner("Ophalen relevante passages…"):
        try:
            snippets = retrieve_relevant(q, docs, key)
        except Exception as e:
            st.error(f"Fout bij retrieval: {e}")
            return

    if not snippets:
        st.warning("Geen relevante tekst gevonden.")
        return

    ctx = "\n".join(snippets)
    try:
        ans = ask_chat(ctx, q)
    except Exception as e:
        st.error(f"Fout bij chatbot-aanroep: {e}")
        return

    st.markdown("**Antwoord:**")
    st.write(ans)

if __name__ == "__main__":
    app()
