import os
from typing import List

# optional imports
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

# Groq SDK optional (some tenants may offer embeddings via Groq; support gracefully)
try:
    from groq import Groq
except Exception:
    Groq = None


class Embedder:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
        self.model = None
        self.use_openai = False
        self.use_groq = False

        # try local sentence-transformers first
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception:
                self.model = None

        # OpenAI fallback
        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            self.use_openai = True

        # Groq fallback (only if explicitly configured)
        if self.model is None and not self.use_openai and Groq is not None and os.environ.get("GROQ_API_KEY"):
            # Note: Groq embedding availability is tenant-dependent. We attempt to use it, but do not assume success.
            try:
                self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                self.use_groq = True
            except Exception:
                self.use_groq = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return list of embedding vectors (plain Python lists)."""
        if not texts:
            return []

        # local model
        if self.model is not None:
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            # ensure numpy present
            if np is None:
                return [list(map(float, x)) for x in arr.tolist()]
            return [list(map(float, x)) for x in np.array(arr)]

        # Groq attempt (if configured)
        if self.use_groq:
            try:
                # Groq embedding API is provider-specific; attempt the common OpenAI-compatible route
                # If your Groq SDK exposes a different endpoint, adapt here.
                resp = self.groq.embeddings.create(model=os.environ.get("GROQ_EMBED_MODEL", "embedding-1"), input=texts)
                return [d["embedding"] for d in resp["data"]]
            except Exception:
                # fallthrough to other fallback
                self.use_groq = False

        # OpenAI fallback
        if self.use_openai:
            model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
            try:
                resp = openai.Embedding.create(model=model, input=texts)
                return [d["embedding"] for d in resp["data"]]
            except Exception as e:
                raise RuntimeError(f"OpenAI embedding call failed: {e}")

        raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY (of configureer Groq).")