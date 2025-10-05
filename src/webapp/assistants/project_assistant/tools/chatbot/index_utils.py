# === FILE: index_utils.py ===
def load_index(client_id: str, project_id: str) -> Tuple[List[Dict], Optional[np.ndarray]]:
p = index_path(client_id, project_id)
e = emb_path(client_id, project_id)
rows = []
if p.exists():
with open(p, "r", encoding="utf-8") as fh:
for L in fh:
try:
rows.append(json.loads(L))
except Exception:
continue
emb = None
if e.exists() and np is not None:
emb = np.load(e)
return rows, emb




def _cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
if a is None or b is None:
return np.array([])
a_norm = np.linalg.norm(a, axis=1)
b_norm = np.linalg.norm(b)
denom = a_norm * (b_norm + 1e-12)
sims = (a @ b) / denom
return sims




def retrieve(client_id: str, project_id: str, q_emb: List[float], top_k: int = 6) -> List[Dict]:
rows, emb = load_index(client_id, project_id)
if not rows or emb is None or len(rows) == 0:
return []
import numpy as _np
q = _np.array(q_emb, dtype=_np.float32)
sims = _cosine_sim(emb, q)
idx = _np.argsort(-sims)[:top_k]
results = []
for i in idx:
r = rows[int(i)].copy()
r["_score"] = float(sims[int(i)])
results.append(r)
return results




def download_bytes_json(rows: List[Dict]) -> bytes:
return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")




def download_bytes_csv(rows: List[Dict]) -> bytes:
import csv
import io
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=[k for k in (rows[0].keys() if rows else ["text"])])
w.writeheader()
for r in rows:
w.writerow({k: (v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False)) for k, v in r.items()})
return buf.getvalue().encode("utf-8")