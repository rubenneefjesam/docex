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
MAX_PDF_MB = 10  # Max uploadgrootte


# =========================
# Singleton Groq-client
# =========================
@st.experimental_singleton
def groq_client() -> Any:
    return get_groq_client()


# =========================
# Helpers (zonder UI-calls)
# =========================
def hash_for_cache(*args: Any) -> str:
    m = hashlib.sha256()
    for a in args:
        m.update(str(a).encode("utf-8"))
    return m.hexdigest()


@st.cache_data(show_spinner=False, ttl=3600)
def load_document(pdf_bytes: bytes, cache_key: str) -> str:
    """Extraheer volledige tekst uit de PDF."""
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)


@st.cache_data(show_spinner=False, ttl=3600)
def embed_document(
    text: str, model: str, cache_key: str, batch_size: int = 256
) -> List[Dict[str, Any]]:
    """
    Genereer embeddings per regel in batches.
    - `model`: modelnaam
    - `batch_size`: grootte per Groq API-call
    """
    client = groq_client()
    lines = [line for line in text.splitlines() if line.strip()]
    embeddings = []
    for i in range(0, len(lines), batch_size):
        batch = lines[i : i + batch_size]
        resp = client.embeddings.create(model=model, input=batch)
        embeddings.extend(resp.data)
    return [{"text": line, "emb": emb.embedding} for line, emb in zip(lines, embeddings)]


@st.cache_data(show_spinner=False, ttl=3600)
def retrieve_relevant(
    query: str,
    docs: List[Dict[str, Any]],
    model: str,
    cache_key: str,
    top_k: int = 5,
) -> List[str]:
    """Vind de meest relevante regels op basis van cosine-similarity."""
    client = groq_client()
    q_emb = client.embeddings.create(model=model, input=[query]).data[0].embedding
    scores = []
    q_arr = np.array(q_emb)
    for d in docs:
        v = np.array(d["emb"])
        sim = float(np.dot(v, q_arr) / (np.linalg.norm(v) * np.linalg.norm(q_arr)))
        scores.append((sim, d["text"]))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scores[:top_k]]


def ask_chat(context: str, query: str, model: str) -> str:
    """Stuur prompt naar chat-API en geef het antwoord terug."""
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
# Streamlit-app
# =========================
def app() -> None:
    st.title("🗂️ Document Chatbot")
    st.sidebar.markdown("#### Configuratie")
    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te starten.")
        return

    if uploaded.size > MAX_PDF_MB * 1024**2:
        st.error(f"Maximale bestandsgrootte is {MAX_PDF_MB} MB.")
        return

    pdf_bytes = uploaded.getvalue()
    # Unieke key voor caching: bestand + model-versie
    cache_key = hash_for_cache(hashlib.sha256(pdf_bytes).hexdigest(), EMBEDDING_MODEL)

    try:
        doc_text = load_document(pdf_bytes, cache_key)
        docs = embed_document(doc_text, EMBEDDING_MODEL, cache_key)
    except Exception as e:
        st.error(f"Fout tijdens documentverwerking: {e}")
        return

    st.success(f"Document geladen: {len(doc_text.splitlines())} regels.")
    query = st.text_input("Vraag:")

    if not query:
        return

    with st.spinner("Ophalen relevante content…"):
        try:
            snippets = retrieve_relevant(
                query, docs, EMBEDDING_MODEL, cache_key
            )
        except Exception as e:
            st.error(f"Fout tijdens retrieval: {e}")
            return

    if not snippets:
        st.warning("Geen relevante content gevonden.")
        return

    context = "\n".join(snippets)
    try:
        answer = ask_chat(context, query, CHAT_MODEL)
    except Exception as e:
        st.error(f"Chatfout: {e}")
        return

    st.markdown("**Antwoord:**")
    st.write(answer)


if __name__ == "__main__":
    app()
