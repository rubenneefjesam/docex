# === FILE: embed_utils.py ===
"""Embedder wrapper: local sentence-transformers, OpenAI fallback."""
import os
from typing import List


try:
import numpy as np
except Exception:
np = None


try:
from sentence_transformers import SentenceTransformer
except Exception:
SentenceTransformer = None


try:
import openai
except Exception:
openai = None




class Embedder:
def __init__(self, model_name: str = None):
self.model_name = model_name or os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
self.model = None
self.use_openai = False
if SentenceTransformer is not None:
try:
self.model = SentenceTransformer(self.model_name)
except Exception:
self.model = None
if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
openai.api_key = os.environ.get("OPENAI_API_KEY")
self.use_openai = True


def embed(self, texts: List[str]) -> List[List[float]]:
if not texts:
return []
if self.model is not None:
arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
return [list(map(float, x)) for x in np.array(arr)]
if self.use_openai:
model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
resp = openai.Embedding.create(model=model, input=texts)
return [r["embedding"] for r in resp["data"]]
raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY.")
