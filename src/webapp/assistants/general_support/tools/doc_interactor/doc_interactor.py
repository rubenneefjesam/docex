import os
import streamlit as st
from pathlib import Path
import tempfile
from groq import Groq
from PyPDF2 import PdfReader
import docx
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# ─── Groq Client Initialisatie ───────────────────────────────────
@st.cache_resource
def init_groq_client():
    key = (
        os.getenv("GROQ_API_KEY", "").strip()
        or st.secrets.get("groq", {}).get("api_key", "").strip()
    )
    if not key:
        st.error("⚠️ Geen Groq-API-key gevonden; tool werkt niet.")
        return None
    try:
        client = Groq(api_key=key)
        # Verbindingstest en modeloverzicht ophalen
        models = client.models.list()
        available = [m.id for m in models.data]
        st.info(f"Beschikbare modellen: {available}")
        return client
    except Exception as e:
        st.error(f"❌ Fout bij initialisatie Groq-client: {e}")
        return None

client = init_groq_client()

# ─── Bestandstekst Inlezen ────────────────────────────────────────
def read_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif suffix == ".docx":
        document = docx.Document(str(file_path))
        return "\n".join(p.text for p in document.paragraphs)
    elif suffix in [".txt", ".md"]:
        return file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Onbekend bestandstype: {suffix}")

# ─── Tekst Chunking ──────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    tokens = text.split()
    # Als er geen tokens zijn, niks te chunk’en
    if not tokens:
        return []

    # Veiligheid: overlap moet kleiner zijn dan chunk_size
    if overlap >= chunk_size:
        raise ValueError("`overlap` moet kleiner zijn dan `chunk_size`")

    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunks.append(" ".join(tokens[start:end]))
        # Als we aan het einde zijn gekomen, klaar
        if end == len(tokens):
            break
        # Beweeg start met overlap
        start = end - overlap

# ─── Embedding en Opslag in sessiestate ──────────────────────────
@st.cache_data(show_spinner=False)
def embed_chunks(chunks: list[str]) -> np.ndarray:
    try:
        resp = client.embeddings.create(model="embed-english-v1", input=chunks)
        return np.array([c.embedding for c in resp.data])
    except Exception as e:
        st.error(f"❌ Fout bij embeddings: {e}")
        return np.array([])

# ─── Vraag beantwoording ─────────────────────────────────────────
def answer_question(question: str, chunks: list[str], embeddings: np.ndarray) -> str:
    try:
        q_resp = client.embeddings.create(model="embed-english-v1", input=[question])
        q_emb = np.array(q_resp.data[0].embedding).reshape(1, -1)
        sims = cosine_similarity(q_emb, embeddings).flatten()
        top_idx = sims.argsort()[::-1][:5]
        context = "\n\n".join(chunks[i] for i in top_idx)
        prompt = (
            "Je bent een slimme documentassistent. Beantwoord de vraag op basis van de onderstaande context. "
            f"Context:\n{context}\n\nVraag: {question}\nAntwoord in duidelijke, beknopte taal."
        )
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ Fout bij ques- & chat-call: {e}")
        return "Er is iets misgegaan tijdens het beantwoorden. Controleer modelnamen en API-toegang."

# ─── Streamlit UI ──────────────────────────────────────────────────
def app():
    st.set_page_config(page_title="🤖 Document Bevrager", layout="wide")
    st.title("🤖 Document Bevrager")
    st.write("Upload één document, verwerk en stel vragen.")

    upload = st.file_uploader("Stap 1: Upload PDF/DOCX/TXT/MD", type=["pdf", "docx", "txt", "md"] )
    if not upload:
        st.info("Nog geen document geüpload.")
        return
    if not client:
        st.error("Geen Groq-client.")
        return

    if st.button("Stap 2: Verwerk document"):
        tmp_path = Path(tempfile.gettempdir()) / upload.name
        tmp_path.write_bytes(upload.getvalue())
        text = read_text(tmp_path)
        with st.spinner("Chunks maken…"): chunks = chunk_text(text)
        with st.spinner("Embeddings berekenen…"): embeddings = embed_chunks(chunks)
        st.session_state.chunks = chunks
        st.session_state.embeddings = embeddings
        st.success("Document verwerkt! Beschikbare chunk-count: " + str(len(chunks)))

    if "chunks" not in st.session_state:
        return

    question = st.text_input("Stap 3: Stel je vraag:")
    if st.button("Beantwoord vraag"):
        if not question.strip():
            st.warning("Voer eerst een vraag in.")
        else:
            with st.spinner("Bezig…"):
                answer = answer_question(question, st.session_state.chunks, st.session_state.embeddings)
            st.markdown(f"**Antwoord:** {answer}")

if __name__ == '__main__':
    app()