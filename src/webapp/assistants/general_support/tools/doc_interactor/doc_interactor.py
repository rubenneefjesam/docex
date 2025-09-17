import streamlit as st
from typing import List
from webapp.assistants.general_support.tools.doc_interactor.doc_interactor import extract_pdf_lines, full_text
from webapp.assistants.general_support.tools.doc_generator.doc_generator import get_groq_client

# =========================
# Configuratie
# =========================
# Pas EMBEDDING_MODEL aan naar het beschikbare Groq-embeddingmodel in jouw omgeving.
EMBEDDING_MODEL = "groq-embedding-1.1"
CHAT_MODEL = "llama-3.1-8b-instant"

# =========================
# Document Chatbot Tool
# =========================
def load_document(pdf_bytes: bytes) -> str:
    """Extraheer volledige tekst uit de PDF"""
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

@st.cache_data(show_spinner=False)
def embed_document(text: str) -> List[dict]:
    """Genereer embeddings per regel met Groq-client"""
    client = get_groq_client()
    lines = text.split("\n")
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=lines
        )
    except Exception as e:
        st.error(f"Embeddingfout: controleer EMBEDDING_MODEL of API-toegang. Details: {e}")
        return []
    # Return list van {"text": regel, "embedding": vector}
    return [{"text": line, "embedding": emb.embedding} for line, emb in zip(lines, response.data)]

@st.cache_data(show_spinner=False)
def retrieve_relevant(query: str, docs: List[dict], top_k: int = 5) -> List[str]:
    """Vind de meest relevante regels op basis van cosine-similariteit"""
    client = get_groq_client()
    try:
        q_emb = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=query
        ).data[0].embedding
    except Exception as e:
        st.error(f"Embeddingfout bij query: {e}")
        return []
    import numpy as np
    scores = []
    for doc in docs:
        vec = np.array(doc["embedding"])
        sim = float(np.dot(vec, q_emb) / (np.linalg.norm(vec) * np.linalg.norm(q_emb)))
        scores.append((sim, doc["text"]))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [text for _, text in scores[:top_k]]

# =========================
# Streamlit-app
# =========================
def app() -> None:
    st.title("🗂️ Document Chatbot")

    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te starten.")
        return

    pdf_bytes = uploaded.getvalue()
    doc_text = load_document(pdf_bytes)
    docs = embed_document(doc_text)
    if not docs:
        return

    st.success(f"Document geladen met {len(doc_text.splitlines())} regels.")
    query = st.text_input("Vraag:")
    if query:
        with st.spinner("Ophalen relevante content…"):
            snippets = retrieve_relevant(query, docs)
        if not snippets:
            st.warning("Geen relevante content gevonden.")
            return
        context = "\n".join(snippets)
        system_msg = (
            "Je bent een behulpzame assistant. Gebruik alleen de onderstaande context uit het document om de vraag te beantwoorden."
            f"\nContext:\n{context}\n"
        )
        client = get_groq_client()
        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": query},
                ],
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            st.error(f"Chatfout: {e}")
            return
        st.markdown("**Antwoord:**")
        st.write(answer)


def run() -> None:
    return app()


def render() -> None:
    return app()

if __name__ == "__main__":
    app()
