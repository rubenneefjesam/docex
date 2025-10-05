# embedder_modular.py
import os
from typing import List, Optional, Tuple

# Soft deps
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
    """
    Modulair: probeert eerst Sentence-Transformers lokaal, dan OpenAI, dan Groq.
    Zorgt voor consistente float32 output en valideert embedding-dimensies tussen batches.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")

        self.model = None
        self.backend = None  # "sbert" | "openai" | "groq"

        self._openai_model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
        self._groq_model = os.environ.get("GROQ_EMBED_MODEL", "embedding-1")

        # Init volgorde
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
                self.backend = "sbert"
            except Exception:
                self.model = None

        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            try:
                # Nieuwere libs gebruiken client() api; val terug op legacy indien niet beschikbaar
                if hasattr(openai, "OpenAI"):
                    self._oai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                else:
                    openai.api_key = os.environ.get("OPENAI_API_KEY")
                    self._oai_client = None
                self.backend = "openai"
            except Exception:
                self.backend = None

        if self.model is None and self.backend is None and Groq is not None and os.environ.get("GROQ_API_KEY"):
            try:
                self._groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                self.backend = "groq"
            except Exception:
                self.backend = None

        if not self.available():
            raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY of configureer GROQ_API_KEY.")

        print(f"[embedder] backend={self.backend} model={self.model_name if self.backend=='sbert' else (self._openai_model if self.backend=='openai' else self._groq_model)}")

        self._dim: Optional[int] = None  # wordt lazy gezet na eerste call

    def available(self) -> bool:
        return (self.backend == "sbert" and self.model is not None) or \
               (self.backend == "openai") or \
               (self.backend == "groq")

    def _ensure_dim(self, batch_embs: List[List[float]]):
        """Stel referentiedimensie vast en controleer consistentie."""
        if not batch_embs:
            return
        d = len(batch_embs[0])
        if self._dim is None:
            self._dim = d
        elif self._dim != d:
            raise ValueError(f"Embedding dimension changed within run: was {self._dim}, now {d}")

    def _to_float32(self, arr_like) -> List[List[float]]:
        # Maak consistente float32 lists (JSON-friendly)
        if np is not None and hasattr(arr_like, "dtype"):
            return np.asarray(arr_like, dtype=np.float32).tolist()
        # fallback: python lists
        return [[float(x) for x in row] for row in arr_like]

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if self.backend == "sbert":
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False)
            out = self._to_float32(arr)

        elif self.backend == "openai":
            # Ondersteun zowel nieuwe als legacy client
            if getattr(self, "_oai_client", None):
                resp = self._oai_client.embeddings.create(model=self._openai_model, input=texts)
                out = [d.embedding for d in resp.data]
            else:
                resp = openai.Embedding.create(model=self._openai_model, input=texts)
                out = [d["embedding"] for d in resp["data"]]

        elif self.backend == "groq":
            resp = self._groq_client.embeddings.create(model=self._groq_model, input=texts)
            # Groq SDK kan dict of pydantic-achtige objecten geven
            data = getattr(resp, "data", None) or resp.get("data")  # type: ignore
            out = [getattr(d, "embedding", None) or d.get("embedding") for d in data]

        else:
            raise RuntimeError("Embedder backend niet geïnitialiseerd.")

        # Validatie + normalisatie
        if not out or not out[0]:
            raise ValueError("Lege embedding respons ontvangen.")
        self._ensure_dim(out)
        return self._to_float32(out)
