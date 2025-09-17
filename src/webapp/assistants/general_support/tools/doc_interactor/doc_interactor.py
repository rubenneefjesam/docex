import streamlit as st
from typing import List
from webapp.assistants.general_support.tools.doc_comparison.doc_comparison import extract_pdf_lines, full_text
from webapp.assistants.general_support.tools.doc_generator.doc_generator import get_groq_client

# =========================
# Document Chatbot Tool
# =========================
def load_document(pdf_bytes: bytes) -> str:
    # Extract full text from PDF
    pages = extract_pdf_lines(pdf_bytes)
    return full_text(pages)

@st.cache_data(show_spinner=False)
def embed_document(text: str) -> List[dict]:
    # Use Groq client to generate embeddings
    client = get_groq_client()
    embeddings = client.embeddings.create(
        model="groq-embedding-1.0",
        input=text.split("\n")
    )
    # Return list of {"text": line, "embedding": vec}
    return [{"text": line, "embedding": emb.embedding} for line, emb in zip(text.split("\n"), embeddings.data)]

@st.cache_data(show_spinner=False)
def retrieve_relevant(query: str, docs: List[dict], top_k: int = 5) -> List[str]:
    client = get_groq_client()
    q_emb = client.embeddings.create(
        model="groq-embedding-1.0",
        input=query
    ).data[0].embedding
    # compute cosine similarity
    import numpy as np
    scores = []
    for doc in docs:
        vec = np.array(doc["embedding"])
        sim = np.dot(vec, q_emb) / (np.linalg.norm(vec) * np.linalg.norm(q_emb))
        scores.append((sim, doc["text"]))
    scores.sort(reverse=True, key=lambda x: x[0])
    return [text for _, text in scores[:top_k]]


def app() -> None:
    st.title("🗂️ Document Chatbot")
    uploaded = st.file_uploader("Upload PDF", type="pdf")
    if not uploaded:
        st.info("Upload een PDF om te starten.")
        return

    pdf_bytes = uploaded.getvalue()
    doc_text = load_document(pdf_bytes)
    docs = embed_document(doc_text)

    st.success(f"Document geladen ({len(doc_text.splitlines())} regels). Stel je vraag hieronder:")
    query = st.text_input("Vraag:")
    if query:
        with st.spinner("Bezig met ophalen van relevante content…"):
            snippets = retrieve_relevant(query, docs)
        # build prompt
        context = "\n".join(snippets)
        system_msg = f"Je bent een behulpzame assistent. Gebruik alleen de onderstaande context uit het document om de vraag te beantwoorden.\nContext:\n{context}\n"
        client = get_groq_client()
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": query},
            ],
        )
        answer = resp.choices[0].message.content.strip()
        st.markdown("**Antwoord:**")
        st.write(answer)


def run() -> None:
    return app()

def render() -> None:
    return app()

if __name__ == "__main__":
    app()
