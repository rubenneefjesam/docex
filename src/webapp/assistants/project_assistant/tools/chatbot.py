# streamlit_app.py (skeleton)
import streamlit as st
import chromadb
from chromadb.config import Settings
from openai import Embeddings, OpenAI
import os
from your_text_utils import extract_text_from_file, chunk_text

# init
st.set_page_config("Client Chat")
client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory="./index/chroma_db"))
collection = client.get_or_create_collection("documents", metadata={"hnsw:space":"cosine"})

# simple UI: upload / ingest
st.sidebar.header("Ingest files")
uploaded = st.sidebar.file_uploader("Upload files", accept_multiple_files=True)
if st.sidebar.button("Ingest"):
    for f in uploaded:
        raw_text = extract_text_from_file(f)           # pdf/docx handler
        client_id, project_id = parse_ids_from_name(f.name)
        chunks = chunk_text(raw_text)
        for i, chunk in enumerate(chunks):
            emb = get_embedding(chunk)                # wrapper for OpenAI or local model
            collection.add(
                documents=[chunk],
                metadatas=[{"client_id":client_id,"project_id":project_id,"filename":f.name,"chunk":i}],
                ids=[f"{f.name}-{i}"]
            )
    client.persist()
    st.success("Ingested!")

# chat UI (require client+project)
st.header("Chat per klant/project")
with st.form("start"):
    client_id = st.text_input("client_id (bv. C007)")
    project_id = st.text_input("project_id (bv. P1024)")
    start = st.form_submit_button("Laad context")
if start:
    # validate exists
    q = f"SELECT COUNT(*) FROM ... (optioneel check in meta files)"
    st.session_state["client_project"] = (client_id, project_id)
    st.success(f"Context geladen voor {client_id}/{project_id}")

# ask question
if "client_project" in st.session_state:
    question = st.text_input("Vraag")
    if st.button("Stel vraag"):
        client_id, project_id = st.session_state["client_project"]
        # retrieval filtered
        results = collection.query(
            query_texts=[question],
            n_results=6,
            where={"client_id": client_id, "project_id": project_id}
        )
        context = "\n\n".join(results["documents"][0])
        prompt = f"Gebruik alleen volgende context (client {client_id} project {project_id}):\n\n{context}\n\nBeantwoord: {question}"
        answer = call_llm(prompt)
        st.write("**Antwoord:**", answer)
        st.write("**Gebruikte bronnen:**")
        for m in results["metadatas"][0]:
            st.write(m["filename"], "chunk", m["chunk"])
