# ui.py

import sys
from pathlib import Path
import streamlit as st
from typing import List, Dict, Any

# Zorg dat deze map importeerbaar is
_this_dir = Path(__file__).parent.resolve()
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

# Lokale imports
from .io_utils import (
    read_uploaded_text,
    parse_ids_from_filename,
    chunk_text,
    download_bytes_json,
)
from .embed_utils import Embedder, load_index, save_index, retrieve as idx_retrieve
from .llm_utils import get_groq_client, call_llm_system_prompt

BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TOP_K = int(__import__("os").environ.get("TOP_K", 6))


def run():
    st.set_page_config(page_title="Client/Project Chat (Local RAG)", layout="wide")
    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] td div,
        div[data-testid="stDataEditor"] td div {
            white-space: normal !important;
            word-break: break-word !important;
        }
        .big-header {font-size:2rem; font-weight:800;}
        .section-header {font-size:1.1rem; font-weight:700; margin-top:0.5rem}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='big-header'>📁 Client/Project Chat — Local file index</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Upload bestanden en start een gesprek op basis van client_id + project_id. Geen centrale DB nodig."
    )

    # Sidebar: ingestie & modelconfig
    st.sidebar.header("Ingestie & Config")
    up = st.sidebar.file_uploader(
        "Upload document (.docx of .txt)",
        type=["docx", "txt"],
        key="up_files",
        accept_multiple_files=True,
    )
    st.sidebar.markdown("---")
    existing = [p.name for p in (BASE / "index").glob("*.jsonl")]
    st.sidebar.write(f"Indices gevonden: {len(existing)}")
    st.sidebar.markdown("---")

    # Start sessie
    st.markdown("<div class='section-header'>🔎 Start sessie</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        client_id = st.text_input("client_id (bv. C007)")
    with col2:
        project_id = st.text_input("project_id (bv. P1024)")
    with col3:
        if st.button("Laad context / validate"):
            st.session_state["client_project"] = (
                client_id.strip().upper() if client_id else "",
                project_id.strip().upper() if project_id else "",
            )

    # fallback op globale index (LOCAL/INDEX)
    ci, pi = st.session_state.get("client_project", ("LOCAL", "INDEX"))

    # Ingest flow
    if up and st.button("Ingest bestanden"):
        embedder = Embedder()
        total = 0
        for f in up:
            text = read_uploaded_text(f)
            if not text.strip():
                st.warning(f"Kon geen tekst lezen uit {f.name}")
                continue
            cid, pid = parse_ids_from_filename(f.name)
            if not cid or not pid:
                cid = cid or (ci or "")
                pid = pid or (pi or "")
            if not cid or not pid:
                st.error(f"Geen client/project gevonden voor {f.name}.")
                continue
            metas = [
                {
                    "text": c,
                    "client_id": cid,
                    "project_id": pid,
                    "filename": f.name,
                    "chunk_index": i,
                }
                for i, c in enumerate(chunk_text(text))
            ]
            embs = embedder.embed_texts([m["text"] for m in metas])
            rows, emb_arr = load_index(cid, pid)
            if rows and emb_arr is not None:
                import numpy as _np
                save_index(
                    cid,
                    pid,
                    rows + metas,
                    _np.vstack([emb_arr, _np.array(embs, dtype=_np.float32)]).tolist(),
                )
            else:
                save_index(cid, pid, metas, embs)
            (DATA_DIR / f.name).write_bytes(f.getbuffer())
            total += len(metas)
        st.success(f"Ingestie klaar — toegevoegd ~{total} chunks")

    # ✅ Contextstatus met visueel vinkje
    if ci and pi:
        rows, _ = load_index(ci, pi)
        indexed = len(rows) > 0
        status_icon = "✅" if indexed else "❌"
        status_text = "Geïndexeerd" if indexed else "Niet geïndexeerd"

        st.markdown(
            f"**Actieve context:** {ci} / {pi} — gevonden chunks: {len(rows)} "
            f"&nbsp;&nbsp;{status_icon} "
            f"<span style='color: {'green' if indexed else 'red'}'>{status_text}</span>",
            unsafe_allow_html=True,
        )
        if st.button("🔄 Herlaad status"):
            st.rerun()

    st.markdown("## 💬 Chat")
    if not (ci and pi):
        st.info(
            "Vul boven client_id en project_id in en klik 'Laad context / validate' om te starten."
        )
        return

    groq_client = get_groq_client()
    embedder = Embedder()

    q = st.text_input("Stel een vraag over deze client/project:")
    if st.button("Vraag stellen") and q.strip():
        with st.spinner("Zoeken en genereren…"):
            try:
                q_emb = embedder.embed_texts([q])[0]
            except Exception as e:
                st.error(
                    "Embedding niet beschikbaar: installeer sentence-transformers of zet OPENAI_API_KEY."
                )
                st.write(str(e))
                return

            results = idx_retrieve(ci, pi, q_emb, top_k=TOP_K)
            if not results:
                st.warning("Geen relevante documenten gevonden voor deze client/project.")
            else:
                context = "\n\n---\n\n".join(
                    f"[source={r.get('filename','?')}#chunk={r.get('chunk_index','?')}]\n{r.get('text','')}"
                    for r in results
                )
                system = (
                    "Je bent een behulpzame assistent. Gebruik uitsluitend de gestructureerde context "
                    "en geef geen informatie die niet expliciet in deze context staat."
                )
                prompt = f"Context (client={ci} project={pi}):\n{context}\n\nBeantwoord de vraag: {q}"
                answer = call_llm_system_prompt(prompt, system, groq_client)
                st.markdown("**Antwoord:**")
                st.write(answer)
                st.markdown("**Gebruikte bronnen (top-k):**")
                for r in results:
                    st.write(
                        f"- {r.get('filename','?')} — chunk {r.get('chunk_index','?')} (score={r.get('_score', 0):.3f})"
                    )

                ctx_b = download_bytes_json(results)
                st.download_button(
                    "⬇️ Download gebruikte context (JSON)",
                    data=ctx_b,
                    file_name=f"context_{ci}_{pi}.json",
                    mime="application/json",
                )
