# embedder_modular.py
import os
from typing import List, Optional

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

try:
    from groq import Groq
except Exception:
    Groq = None


class Embedder:
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
        self.model = None
        self.use_openai = False
        self.use_groq = False
        self.groq = None

        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception:
                self.model = None

        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            self.use_openai = True

        if self.model is None and not self.use_openai and Groq is not None and os.environ.get("GROQ_API_KEY"):
            try:
                self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                self.use_groq = True
            except Exception:
                self.use_groq = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # local model
        if self.model is not None:
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            try:
                return [list(map(float, x)) for x in arr.tolist()]
            except Exception:
                return [list(map(float, x)) for x in list(arr)]
        # groq
        if self.use_groq and self.groq is not None:
            try:
                resp = self.groq.embeddings.create(model=os.environ.get("GROQ_EMBED_MODEL", "embedding-1"), input=texts)
                if isinstance(resp, dict) and "data" in resp:
                    return [d.get("embedding") for d in resp["data"]]
                return [d["embedding"] if isinstance(d, dict) else d for d in resp]
            except Exception:
                self.use_groq = False
        # openai
        if self.use_openai:
            model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
            try:
                resp = openai.Embedding.create(model=model, input=texts)
                return [d["embedding"] for d in resp["data"]]
            except Exception as e:
                raise RuntimeError(f"OpenAI embedding call failed: {e}")
        raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY (of configureer GROQ).")
