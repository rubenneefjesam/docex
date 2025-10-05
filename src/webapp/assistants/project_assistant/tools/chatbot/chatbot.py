#!/usr/bin/env python3
"""
Streamlit app: Client+Project RAG (file-based index)

- Geen externe vector DB: index per client_project opgeslagen op schijf
- Embeddings: sentence-transformers (fallback: OpenAI embeddings)
- LLM: Groq chat (als GROQ_API_KEY aanwezig) else OpenAI (if OPENAI_API_KEY)

Gebruik:
    pip install -r requirements.txt
    streamlit run streamlit_client_rag.py

Bestanden:
  /data/              # uploads (origineel)
  /index/             # per-client_project index: JSONL + .npy embeddings
  /logs/

Dit bestand volgt de structuur en stijl van je voorbeeld: helpers, clients, parsing,
LLM client factory, UI met ingest en chat, download-export.
"""

import os
import io
import re
import json
import math
import tempfile
from typing import List, Dict, Optional, Tuple
from pathlib import Path

import streamlit as st

# Try imports that may not be present in all environments
try:
    import docx
except Exception:
    docx = None

try:
    import numpy as np
except Exception:
    np = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

# Optional APIs
try:
    from groq import Groq
except Exception:
    Groq = None

try:
    import openai
except Exception:
    openai = None


# -------------------------
# Config & paths
# -------------------------
BASE = Path(__file__).parent.resolve()
DATA_DIR = BASE / "data"
INDEX_DIR = BASE / "index"
LOG_DIR = BASE / "logs"
for d in (DATA_DIR, INDEX_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

EMBED_MODEL_NAME = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 600))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 100))
TOP_K = int(os.environ.get("TOP_K", 6))


# =========================
# Helpers: bestanden & tekst
# =========================

def _safe_read_docx_text(path: str) -> str:
    """Lees plain text uit een .docx; leeg bij fout."""
    if not docx:
        return ""
    try:
        d = docx.Document(path)
        parts = []
        for p in d.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts)
    except Exception:
        return ""


def _read_uploaded_text(uploaded) -> str:
    """Ondersteun .docx en .txt als input voor ingest."""
    if not uploaded:
        return ""
    name = (uploaded.name or "").lower()
    if name.endswith(".docx") and docx:
        tmpd = tempfile.mkdtemp()
        p = os.path.join(tmpd, "input.docx")
        with open(p, "wb") as f:
            f.write(uploaded.getbuffer())
        return _safe_read_docx_text(p)
    # fallback: .txt
    try:
        return uploaded.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def parse_ids_from_filename(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse client_id en project_id uit bestandsnaam, returns (client, project).
    Verwacht patronen zoals C007_P1024, C7-P1024, client007_project1024, of expliciete C### / P####.
    """
    if not name:
        return None, None
    s = name.upper()
    # common regex: C followed by 1-4 digits and P followed by digits
    m = re.search(r"(C\d{1,4}).*?(P\d{1,5})", s)
    if m:
        return m.group(1), m.group(2)
    # fallback: capture numbers with keywords
    m2 = re.search(r"CLIENT[_-]?(\d{1,4}).*?PROJECT[_-]?(\d{1,5})", s)
    if m2:
        return f"C{m2.group(1)}", f"P{m2.group(2)}"
    return None, None


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple sliding-window chunker on characters (keeps words intact at boundaries)."""
    if not text:
        return []
    text = text.strip()
    chunks = []
    start = 0
    L = len(text)
    while start < L:
        end = start + size
        if end >= L:
            chunks.append(text[start:L].strip())
            break
        # try to cut at last whitespace before end
        slice_ = text[start:end]
        last_space = slice_.rfind(" ")
        if last_space > int(size * 0.6):
            end = start + last_space
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
    return [c for c in chunks if c]


# =========================
# Embeddings (local or OpenAI)
# =========================

class Embedder:
    def __init__(self):
        self.model_name = EMBED_MODEL_NAME
        self.model = None
        self.use_openai = False
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception:
                self.model = None
        # fallback to OpenAI if available
        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            self.use_openai = True
            openai.api_key = os.environ.get("OPENAI_API_KEY")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if self.model is not None:
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return [list(map(float, x)) for x in np.array(arr)]
        if self.use_openai:
            # OpenAI batch embeddings (ada-embedding-002 or text-embedding-3-small)
            model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
            resp = openai.Embedding.create(model=model, input=texts)
            return [r["embedding"] for r in resp["data"]]
        raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY.")


# =========================
# LLM client factories
# =========================

def _get_groq_client() -> Optional[Groq]:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        try:
            key = (st.secrets.get("groq", {}) or {}).get("api_key", "").strip()
        except Exception:
            key = ""
    if not key or Groq is None:
        return None
    try:
        return Groq(api_key=key)
    except Exception:
        return None


def _get_openai_available() -> bool:
    return (openai is not None) and bool(os.environ.get("OPENAI_API_KEY") or getattr(st.secrets, "openai", None))


def _call_llm_system_prompt(prompt: str, system: str, groq_client: Optional[Groq] = None) -> str:
    """Call Groq chat if available, else OpenAI ChatCompletion if config present.
    Returns the assistant content (string).
    """
    if groq_client and Groq is not None:
        try:
            resp = groq_client.chat.completions.create(
                model=os.environ.get("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
                temperature=0.2,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            st.error(f"Groq model call failed: {e}")
            return ""

    # fallback: OpenAI chat completion
    if _get_openai_available():
        try:
            api_key = os.environ.get("OPENAI_API_KEY") or (st.secrets.get("openai", {}) or {}).get("api_key")
            openai.api_key = api_key
            model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            st.error(f"OpenAI model call failed: {e}")
            return ""

    st.error("Geen LLM beschikbaar: zet GROQ_API_KEY of OPENAI_API_KEY in env/st.secrets.")
    return ""


# =========================
# Index persistence (file-based)
# =========================

def _index_path(client_id: str, project_id: str) -> Path:
    suffix = f"{client_id}_{project_id}".upper()
    safe = re.sub(r"[^A-Z0-9_]+", "_", suffix)
    return INDEX_DIR / f"index_{safe}.jsonl"


def _emb_path(client_id: str, project_id: str) -> Path:
    suffix = f"{client_id}_{project_id}".upper()
    safe = re.sub(r"[^A-Z0-9_]+", "_", suffix)
    return INDEX_DIR / f"emb_{safe}.npy"


def index_exists(client_id: str, project_id: str) -> bool:
    return _index_path(client_id, project_id).exists() and _emb_path(client_id, project_id).exists()


def save_index(client_id: str, project_id: str, chunks: List[Dict], embeddings: List[List[float]]):
    p = _index_path(client_id, project_id)
    embp = _emb_path(client_id, project_id)
    # write jsonl
    with open(p, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    # write numpy
    if np is None:
        raise RuntimeError("Numpy ontbreekt; kan embeddings niet saven")
    arr = np.array(embeddings, dtype=np.float32)
    np.save(embp, arr)


def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[np.ndarray]]:
    p = _index_path(client_id, project_id)
    embp = _emb_path(client_id, project_id)
    rows = []
    if p.exists():
        with open(p, "r", encoding="utf-8") as fh:
            for L in fh:
                try:
                    rows.append(json.loads(L))
                except Exception:
                    continue
    emb = None
    if embp.exists() and np is not None:
        emb = np.load(embp)
    return rows, emb


# -------------------------
# Retrieval
# -------------------------

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    # a: (n, d), b: (d,) -> scores (n,)
    if a is None or b is None:
        return np.array([])
    a_norm = np.linalg.norm(a, axis=1)
    b_norm = np.linalg.norm(b)
    # avoid div by zero
    denom = a_norm * (b_norm + 1e-12)
    sims = (a @ b) / denom
    return sims


def retrieve(client_id: str, project_id: str, query: str, embedder: Embedder, top_k: int = TOP_K) -> List[Dict]:
    rows, emb = load_index(client_id, project_id)
    if not rows or emb is None or len(rows) == 0:
        return []
    q_emb = np.array(embedder.embed([query])[0], dtype=np.float32)
    sims = _cosine_sim(emb, q_emb)
    idx = np.argsort(-sims)[:top_k]
    results = []
    for i in idx:
        r = rows[int(i)].copy()
        r["_score"] = float(sims[int(i)])
        results.append(r)
    return results


# -------------------------
# Downloads
# -------------------------

def _download_bytes_json(rows: List[Dict]) -> bytes:
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


def _download_bytes_csv(rows: List[Dict]) -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=[k for k in (rows[0].keys() if rows else ["text"])])
    w.writeheader()
    for r in rows:
        w.writerow({k: (v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False)) for k, v in r.items()})
    return buf.getvalue().encode("utf-8")


# -------------------------
# UI
# -------------------------

def run():
    st.set_page_config(page_title="Client/Project Chat (Local RAG)", layout="wide")

    st.markdown(
        """
        <style>
        div[data-testid="stDataFrame"] td div,
        div[data-testid="stDataEditor"] td div { white-space: normal !important; word-break: break-word !important; }
        .big-header {font-size:2rem; font-weight:800;}
        .section-header {font-size:1.1rem; font-weight:700; margin-top:0.5rem}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='big-header'>📁 Client/Project Chat — Local file index</div>", unsafe_allow_html=True)
    st.caption("Upload bestanden en start een gesprek op basis van client_id + project_id. Geen centrale DB nodig.")

    # Sidebar: ingest & model config
    st.sidebar.header("Ingestie & Config")
    up = st.sidebar.file_uploader("Upload document (.docx or .txt)", type=["docx", "txt"], key="up_files", accept_multiple_files=True)
    st.sidebar.markdown("---")
    st.sidebar.write("Index status:")
    existing = [p.name for p in INDEX_DIR.glob("*.jsonl")]
    st.sidebar.write(f"Indices gevonden: {len(existing)}")
    st.sidebar.markdown("---")

    # Client / project input (required)
    st.markdown("<div class='section-header'>🔎 Start sessie</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        client_id = st.text_input("client_id (bv. C007)")
    with col2:
        project_id = st.text_input("project_id (bv. P1024)")
    with col3:
        if st.button("Laad context / validate"):
            st.session_state["client_project"] = (client_id.strip().upper() if client_id else "", project_id.strip().upper() if project_id else "")

    if "client_project" in st.session_state:
        ci, pi = st.session_state["client_project"]
    else:
        ci, pi = None, None

    # Ingest flow
    st.markdown("<div class='section-header'>📥 Ingestie</div>", unsafe_allow_html=True)
    ingest_col = st.columns([1, 1, 1])[0]
    if up and st.button("Ingest bestanden", key="ingest"):
        embedder = Embedder()
        total = 0
        for f in up:
            text = _read_uploaded_text(f)
            if not text.strip():
                st.warning(f"Kon geen tekst lezen uit {f.name}")
                continue
            # determine ids
            cid, pid = parse_ids_from_filename(f.name)
            if not cid or not pid:
                # fallback to current session client/project
                cid = cid or (ci or "")
                pid = pid or (pi or "")
            if not cid or not pid:
                st.error(f"Geen client/project gevonden voor {f.name}. Gebruik bestandsnaam of vul boven client/project.")
                continue
            # chunk
            chunks = chunk_text(text)
            meta_chunks = []
            for i, c in enumerate(chunks):
                meta_chunks.append({
                    "text": c,
                    "client_id": cid,
                    "project_id": pid,
                    "filename": f.name,
                    "chunk_index": i,
                })
            # create embeddings
            embs = embedder.embed([c["text"] for c in meta_chunks])
            # merge with existing index if present
            rows, emb_arr = load_index(cid, pid)
            if rows and emb_arr is not None:
                # append
                new_rows = rows + meta_chunks
                new_emb = np.vstack([emb_arr, np.array(embs, dtype=np.float32)])
                save_index(cid, pid, new_rows, new_emb.tolist())
            else:
                save_index(cid, pid, meta_chunks, embs)
            # save original file
            dst = DATA_DIR / f.name
            with open(dst, "wb") as fh:
                fh.write(f.getbuffer())
            total += len(meta_chunks)
        st.success(f"Ingestie klaar — toegevoegd ~{total} chunks")

    # Show basic index status for current client/project
    if ci and pi:
        rows, emb = load_index(ci, pi)
        st.markdown(f"**Actieve context:** {ci} / {pi} — gevonden chunks: {len(rows)}")
        if not rows:
            st.info("Nog geen index voor deze client/project. Upload bestanden (of check bestandsnaam parsing).")

    # Chat area
    st.markdown("<div class='section-header'>💬 Chat</div>", unsafe_allow_html=True)
    if not (ci and pi):
        st.info("Vul boven client_id en project_id in en klik 'Laad context / validate' om te starten.")
        return

    groq_client = _get_groq_client()
    embedder = Embedder()

    q = st.text_input("Stel een vraag over deze client/project:")
    if st.button("Vraag stellen") and q.strip():
        with st.spinner("Zoeken en genereren…"):
            results = retrieve(ci, pi, q, embedder, top_k=TOP_K)
            if not results:
                st.warning("Geen relevante documenten gevonden voor deze client/project.")
            else:
                # build context
                context = "\n\n---\n\n".join([f"[source={r.get('filename')}#chunk={r.get('chunk_index')}]\n{r.get('text')}" for r in results])
                system = (
                    f"Je bent een behulpzame assistent. Gebruik uitsluitend de gestructureerde context hieronder en geef geen informatie die niet expliciet in deze context staat."
                )
                prompt = f"Context (client={ci} project={pi}):\n{context}\n\nBeantwoord de vraag: {q}\n\nLever een duidelijk antwoord en vermeld onderaan de gebruikte bronnen (bestand en chunk-index). Als antwoord niet te vinden is, zeg: 'Ik kan dat niet bevestigen vanuit de beschikbare project-/klantgegevens.'"
                answer = _call_llm_system_prompt(prompt, system, groq_client=groq_client)

                st.markdown("**Antwoord:**")
                st.write(answer)

                st.markdown("**Gebruikte bronnen (top-k):**")
                for r in results:
                    st.write(f"- {r.get('filename')} — chunk {r.get('chunk_index')} (score={r.get('_score'):.3f})")

                # offer download of context
                ctx_b = _download_bytes_json(results)
                st.download_button("⬇️ Download gebruikte context (JSON)", data=ctx_b, file_name=f"context_{ci}_{pi}.json", mime="application/json")


# Entrypoints

def app():
    run()


def main():
    run()


if __name__ == "__main__":
    main()
