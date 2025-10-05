# === FILE: ui.py ===
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


TOP_K = int(os.environ.get("TOP_K", 6))




def run():
st.set_page_config(page_title="Client/Project Chat (Local RAG)", layout="wide")
st.markdown("<style>div[data-testid=\"stDataFrame\"] td div{white-space:normal}</style>", unsafe_allow_html=True)
st.header("📁 Client/Project Chat — Local file index")


up = st.sidebar.file_uploader("Upload document (.docx or .txt)", type=["docx", "txt"], accept_multiple_files=True)
existing = [p.name for p in (BASE / "index").glob("*.jsonl")]
st.sidebar.write(f"Indices gevonden: {len(existing)}")


col1, col2, col3 = st.columns([1,1,2])
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


# ingest
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
chunks = chunk_text(text)
metas = []
for i, c in enumerate(chunks):
metas.append({"text": c, "client_id": cid, "project_id": pid, "filename": f.name, "chunk_index": i})
embs = embedder.embed([m["text"] for m in metas])
rows, emb_arr = load_index(cid, pid)
if rows and emb_arr is not None:
import numpy as _np
new_rows = rows + metas
new_emb = _np.vstack([emb_arr, _np.array(embs, dtype=_np.float32)])
save_index(cid, pid, new_rows, new_emb.tolist())
else:
save_index(cid, pid, metas, embs)
dst = DATA_DIR / f.name
with open(dst, "wb") as fh:
fh.write(f.getbuffer())
total += len(metas)
st.success(f"Ingestie klaar — toegevoegd ~{total} chunks")

# context status
if ci and pi:
rows, emb = load_index(ci, pi)
st.markdown(f"**Actieve context:** {ci} / {pi} — gevonden chunks: {len(rows)}")


st.markdown("## 💬 Chat")
if not (ci and pi):
st.info("Vul boven client_id en project_id in en klik 'Laad context / validate' om te starten.")
return


groq_client = get_groq_client()
embedder = Embedder()


q = st.text_input("Stel een vraag over deze client/project:")
if st.button("Vraag stellen") and q.strip():
with st.spinner("Zoeken en genereren…"):
try:
q_emb = embedder.embed([q])[0]
except Exception as e:
st.error("Embedding niet beschikbaar: installeer sentence-transformers of zet OPENAI_API_KEY.")
st.write(str(e))
return
results = retrieve(ci, pi, q_emb, top_k=TOP_K)
if not results:
st.warning("Geen relevante documenten gevonden voor deze client/project.")
else:
context = "\n\n---\n\n".join([f"[source={r.get('filename')}#chunk={r.get('chunk_index')}]\n{r.get('text')}" for r in results])
system = ("Je bent een behulpzame assistent. Gebruik uitsluitend de gestructureerde context hieronder en geef geen informatie die niet expliciet in deze context staat.")
prompt = f"Context (client={ci} project={pi}):\n{context}\n\nBeantwoord de vraag: {q}\n\nLever een duidelijk antwoord en vermeld onderaan de gebruikte bronnen (bestand en chunk-index). Als antwoord niet te vinden is, zeg: 'Ik kan dat niet bevestigen vanuit de beschikbare project-/klantgegevens.'"
answer = call_llm_system_prompt(prompt, system, groq_client)
st.markdown("**Antwoord:**")
st.write(answer)
st.markdown("**Gebruikte bronnen (top-k):**)"
for r in results:
st.write(f"- {r.get('filename')} — chunk {r.get('chunk_index')} (score={r.get('_score'):.3f})")
ctx_b = download_bytes_json(results)
st.download_button("⬇️ Download gebruikte context (JSON)", data=ctx_b, file_name=f"context_{ci}_{pi}.json", mime="application/json")