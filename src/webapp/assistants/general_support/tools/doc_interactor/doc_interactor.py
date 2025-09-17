import streamlit as st
from typing import List, Dict, Any
import hashlib
import numpy as np

from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import (
    extract_pdf_lines,
    full_text,
)
from webapp.assistants.general_support.tools.doc_generator.doc_generator import (
    get_groq_client,
)

# =========================
# Configuratie
# =========================
EMBEDDING_MODEL = st.sidebar.selectbox(
    "Embedding model", ["groq-embedding-1.0", "groq-embedding-1.1"], index=1
)
CHAT_MODEL = st.sidebar.selectbox(
    "Chatmodel", ["llama-3.1-8b-instant", "llama-3.1-16b-instant"], index=0
)
MAX_PDF_MB = 10  # Max uploadgrootte in MB

# =========================
# Lazy singleton voor Groq-client
# =========================
_groq_client: Any = None

def groq_client() -> Any:
    global _groq_client
    if _groq_client is None:
        _groq_client = get_groq_client()
    return _groq_client

# =========================
# Hulpfuncties (zonder UI-calls)
# =========================
def _make_cache_key(*args: Any) -> str:
    h = hashlib.sha256()
    for a in args:
        h.update(str(a).encode("utf-8"))
    return h.hexdigest()

@st.cache_data(show_spinner=False, ttl=3600)
def load_document(pdf_bytes: bytes, cache_key: str) -> str:
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

@st.cache_data(show_spinner=False, ttl=3600)
def embed_document(
    text: str, model: str, cache_key: str, batch_size: int = 256
) -> List[Dict[str, Any]]:
    client = groq_client()
    # Splits op schone niet-lege regels
    lines = [ln for ln in text.splitlines() if ln.strip()]
    embeddings = []
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        embeddings.extend(resp.data)
    return [{"text": ln, "emb": emb.embedding} for ln, emb in zip(lines, embeddings)]

@st.cache_data(show_spinner=False, ttl=3600)
def retrieve_relevant(
    query: str,
    docs: List[Dict[str, Any]],
    model: str,
    cache_key: str,
    top_k: int = 5,
) -> List[str]:
    client = groq_client()
    q_emb = client.embeddings.create(model=model, input=[query]).data[0].embedding
    q_arr = np.array(q_emb)
    sims = [
        (float(np.dot(np.array(d["emb"]), q_arr) / (np.linalg.norm(d["emb"]) * np.linalg.norm(q_arr))), d["text"])
        for d in docs
    ]
    sims.sort(key=lambda x: x[0], reverse=True)
    return [txt for _, txt in sims[:top_k]]

def ask_chat(context: str, query: str, model: str) -> str:
    client = groq_client()
    system_msg = (
        "Je bent een behulpzame assistent. Gebruik **uitsluitend** de context hieronder:\n"
        f"{context}\n"
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": query},
        ],
    )
    return resp.choices[0].message.content.strip()

# =========================
# Streamlit-applicatie
# =========================
def app() -> None:
    st.title("🗂️ Document Chatbot")
    st.sidebar.markdown("#### Instellingen")
    uploaded = st.file_uploader("Upload je PDF-bestand", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te beginnen.")
        return

    if uploaded.size > MAX_PDF_MB * 1024**2:
        st.error(f"Maximale bestandsgrootte is {MAX_PDF_MB} MB.")
        return

    pdf_bytes = uploaded.getvalue()
    # cache key: inhoud PDF + gekozen embed-model
    key = _make_cache_key(hashlib.sha256(pdf_bytes).hexdigest(), EMBEDDING_MODEL)

    try:
        text = load_document(pdf_bytes, key)
        docs = embed_document(text, EMBEDDING_MODEL, key)
    except Exception as e:
        st.error(f"Fout bij documentverwerking: {e}")
        return

    st.success(f"Document geladen, {len(text.splitlines())} regels gevonden.")
    query = st.text_input("Typ je vraag")

    if not query:
        return

    with st.spinner("Content ophalen…"):
        try:
            snippets = retrieve_relevant(query, docs, EMBEDDING_MODEL, key)
        except Exception as e:
            st.error(f"Fout bij ophalen relevante content: {e}")
            return

    if not snippets:
        st.warning("Geen relevante tekstdelen gevonden.")
        return

    context = "\n".join(snippets)
    try:
        answer = ask_chat(context, query, CHAT_MODEL)
    except Exception as e:
        st.error(f"Fout bij chat-aanroep: {e}")
        return

    st.markdown("**Antwoord:**")
    st.write(answer)

if __name__ == "__main__":
    app()
