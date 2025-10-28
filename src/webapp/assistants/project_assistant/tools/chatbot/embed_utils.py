# embed_utils.py
"""
Robuuste embedder wrapper:
- probeert lokale sentence-transformers eerst
- fallback naar Groq embeddings (indien geconfigureerd)
- fallback naar OpenAI embeddings (indien OPENAI_API_KEY aanwezig)

Retourneert altijd Python-lijsten van floats.
"""
import os
from typing import List, Optional

# optionele libs
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

        # probeer lokale sentence-transformers
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(self.model_name)
            except Exception:
                self.model = None

        # OpenAI fallback (activeer alleen als API key aanwezig)
        if self.model is None and openai is not None and os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            self.use_openai = True

        # Groq fallback (optioneel)
        if self.model is None and not self.use_openai and Groq is not None and os.environ.get("GROQ_API_KEY"):
            try:
                self.groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                self.use_groq = True
            except Exception:
                self.use_groq = False

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Geef embeddings terug als List[List[float]].
        Werkt met lokale model -> Groq -> OpenAI (in die volgorde).
        Werpt RuntimeError als geen embedder beschikbaar is of als externe call faalt.
        """
        if not texts:
            return []

        # lokale model
        if self.model is not None:
            arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            # arr kan numpy array of lijst zijn — converteer naar pure Python lists
            try:
                return [list(map(float, x)) for x in arr.tolist()]
            except Exception:
                # fallback: iterable to list
                return [list(map(float, x)) for x in list(arr)]

        # Groq embeddings (optioneel)
        if self.use_groq and self.groq is not None:
            try:
                resp = self.groq.embeddings.create(model=os.environ.get("GROQ_EMBED_MODEL", "embedding-1"), input=texts)
                # resp kan dict-like zijn: probeer 'data' pad
                if isinstance(resp, dict) and "data" in resp:
                    return [d.get("embedding") for d in resp["data"]]
                # anders fallback best effort
                return [d["embedding"] if isinstance(d, dict) else d for d in resp]
            except Exception:
                # disable groq fallback na mislukking
                self.use_groq = False

        # OpenAI fallback
        if self.use_openai:
            model = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
            try:
                resp = openai.Embedding.create(model=model, input=texts)
                return [d["embedding"] for d in resp["data"]]
            except Exception as e:
                raise RuntimeError(f"OpenAI embedding call failed: {e}")

        raise RuntimeError("Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY (of configureer GROQ).")

# -------------------------------------------------------
# Compatibiliteitshelpers voor UI-downloads
# -------------------------------------------------------

def download_bytes_json(rows: List[Dict]) -> bytes:
    """Converteer lijst van dicts naar JSON-bytes voor download in UI."""
    import json
    return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")


def download_bytes_csv(rows: List[Dict]) -> bytes:
    """Converteer lijst van dicts naar CSV-bytes voor download in UI."""
    import csv
    import io

    buf = io.StringIO()
    if not rows:
        buf.write("text\n")
        return buf.getvalue().encode("utf-8")

    fieldnames = list(rows[0].keys())
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(
            {
                k: (v if not isinstance(v, (list, dict)) else json.dumps(v, ensure_ascii=False))
                for k, v in r.items()
            }
        )
    return buf.getvalue().encode("utf-8")
