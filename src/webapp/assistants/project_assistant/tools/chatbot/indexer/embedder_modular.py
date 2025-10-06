# embedder_modular.py
"""
Verbeterde Embedder:
- Configurabele fallback-order via ENV EMBED_BACKENDS (bv. "sbert,openai,groq")
- Retries + exponential backoff + jitter voor netwerk/API calls
- Defensieve normalisatie van responses (altijd List[List[float]])
- Logging per-batch (backend, model, batch_size, latency)
- Expose `dim` property en `get_model_info()` voor inspectie
- Simpele metrics: calls, errors, total_time, last_error
"""
from typing import List, Optional, Any, Dict, Callable
import os
import time
import logging
import random

# Soft deps
try:
    import numpy as np  # type: ignore
except Exception:
    np = None

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None

try:
    import openai  # type: ignore
except Exception:
    openai = None

try:
    from groq import Groq  # type: ignore
except Exception:
    Groq = None

# Setup logger
logger = logging.getLogger("embedder")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(levelname)s] %(asctime)s %(name)s %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
logger.setLevel(os.environ.get("EMBED_LOG_LEVEL", "INFO"))

# Retry/backoff defaults (configurable via ENV)
_MAX_RETRIES = int(os.environ.get("EMBED_MAX_RETRIES", "3"))
_BACKOFF_BASE = float(os.environ.get("EMBED_BACKOFF_BASE", "0.3"))  # seconds
_BACKOFF_MAX = float(os.environ.get("EMBED_BACKOFF_MAX", "5.0"))
_BACKOFF_JITTER = float(os.environ.get("EMBED_BACKOFF_JITTER", "0.1"))

# Fallback order configurable via env var, default sbert -> openai -> groq
_DEFAULT_BACKENDS = os.environ.get("EMBED_BACKENDS", "sbert,openai,groq").split(",")

# Default model names
_DEFAULT_SBERT = os.environ.get("EMBED_MODEL", "all-MiniLM-L6-v2")
_DEFAULT_OAI_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
_DEFAULT_GROQ_MODEL = os.environ.get("GROQ_EMBED_MODEL", "embedding-1")


def _retry_backoff(fn: Callable, *args, max_retries: int = _MAX_RETRIES, **kwargs):
    """Generic retry wrapper with exponential backoff + jitter."""
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            start = time.time()
            res = fn(*args, **kwargs)
            duration = time.time() - start
            return res, duration, None
        except Exception as e:
            last_exc = e
            backoff = min(_BACKOFF_BASE * (2 ** (attempt - 1)), _BACKOFF_MAX)
            jitter = random.uniform(0, _BACKOFF_JITTER)
            sleep_for = backoff + jitter
            logger.warning(f"Embed call failed (attempt {attempt}/{max_retries}): {e}. Backing off {sleep_for:.2f}s")
            time.sleep(sleep_for)
    return None, 0.0, last_exc


class Embedder:
    """
    Modulair embedder met:
      - fallback order configurable via ENV EMBED_BACKENDS
      - retries/backoff for remote APIs
      - normalization of responses
      - metrics and logging
    """

    def __init__(self, model_name: Optional[str] = None):
        # Config
        self.preferred_model = model_name or _DEFAULT_SBERT
        self._openai_model = _DEFAULT_OAI_MODEL
        self._groq_model = _DEFAULT_GROQ_MODEL
        self._backends = [b.strip() for b in _DEFAULT_BACKENDS if b.strip()]
        self.backend = None  # selected backend string
        self.model = None  # holds SBERT model if used
        self._oai_client = None
        self._groq_client = None

        # metrics
        self.calls = 0
        self.errors = 0
        self.total_time = 0.0
        self.last_error: Optional[str] = None
        self._dim: Optional[int] = None
        self._initialized_backend: Optional[str] = None
        self._initialized_model_name: Optional[str] = None

        # Try initialize in configured order
        for b in self._backends:
            if b == "sbert" and SentenceTransformer is not None:
                try:
                    self.model = SentenceTransformer(self.preferred_model)
                    self.backend = "sbert"
                    self._initialized_backend = "sbert"
                    self._initialized_model_name = self.preferred_model
                    break
                except Exception as e:
                    logger.debug(f"Failed to init SBERT ({self.preferred_model}): {e}")
                    self.model = None
            if b == "openai" and openai is not None and os.environ.get("OPENAI_API_KEY"):
                try:
                    # support both new and legacy openai usage
                    if hasattr(openai, "OpenAI"):
                        self._oai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
                    else:
                        openai.api_key = os.environ.get("OPENAI_API_KEY")
                        self._oai_client = None
                    self.backend = "openai"
                    self._initialized_backend = "openai"
                    self._initialized_model_name = self._openai_model
                    break
                except Exception as e:
                    logger.debug(f"Failed to init OpenAI client: {e}")
                    self._oai_client = None
            if b == "groq" and Groq is not None and os.environ.get("GROQ_API_KEY"):
                try:
                    self._groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
                    self.backend = "groq"
                    self._initialized_backend = "groq"
                    self._initialized_model_name = self._groq_model
                    break
                except Exception as e:
                    logger.debug(f"Failed to init Groq client: {e}")
                    self._groq_client = None

        if not self.available():
            raise RuntimeError(
                "Geen embedder beschikbaar. Installeer sentence-transformers of zet OPENAI_API_KEY of configureer GROQ_API_KEY."
            )

        logger.info(f"[embedder] initialized backend={self.backend} model={self._initialized_model_name}")

    # ---------- properties ----------
    @property
    def dim(self) -> Optional[int]:
        """Embedding dimensionality after first embed call (read-only)."""
        return self._dim

    def get_model_info(self) -> Dict[str, Optional[str]]:
        return {
            "backend": self.backend,
            "model": self._initialized_model_name,
            "dim": str(self._dim) if self._dim is not None else None,
        }

    def available(self) -> bool:
        return (self.backend == "sbert" and self.model is not None) or \
               (self.backend == "openai" and (openai is not None) or self._oai_client is not None) or \
               (self.backend == "groq" and self._groq_client is not None)

    # ---------- helpers ----------
    def _ensure_dim(self, batch_embs: List[List[float]]):
        if not batch_embs:
            return
        d = len(batch_embs[0])
        if self._dim is None:
            self._dim = d
            logger.debug(f"Set embedding dim to {d}")
        elif self._dim != d:
            # Provide super clear error for debugging
            raise ValueError(f"Embedding dimension mismatch: expected {self._dim}, got {d} (backend={self.backend})")

    def _to_float32(self, arr_like: Any) -> List[List[float]]:
        """Return JSON-friendly list-of-lists, coerced to float32 where possible."""
        if np is not None:
            try:
                return np.asarray(arr_like, dtype=np.float32).tolist()
            except Exception:
                # fallback to manual conversion
                pass
        # fallback
        return [[float(x) for x in row] for row in arr_like]

    def _normalize_openai_resp(self, resp: Any) -> List[List[float]]:
        """
        Normalize response from OpenAI (new or legacy) to List[List[float]].
        Accepts: client.embeddings.create(...) returned object or dict.
        """
        # new client: resp.data is iterable of objects with .embedding
        data = getattr(resp, "data", None) or resp.get("data") if isinstance(resp, dict) else None
        if data is None:
            raise ValueError("OpenAI response missing 'data'")
        out = []
        for d in data:
            emb = getattr(d, "embedding", None) or (d.get("embedding") if isinstance(d, dict) else None)
            if emb is None:
                raise ValueError("OpenAI response element missing 'embedding'")
            out.append(emb)
        return out

    def _normalize_groq_resp(self, resp: Any) -> List[List[float]]:
        """
        Normalize response from Groq SDK to List[List[float]].
        """
        data = getattr(resp, "data", None) or (resp.get("data") if isinstance(resp, dict) else None)
        if data is None:
            raise ValueError("Groq response missing 'data'")
        out = []
        for d in data:
            emb = getattr(d, "embedding", None) or (d.get("embedding") if isinstance(d, dict) else None)
            if emb is None:
                raise ValueError("Groq response element missing 'embedding'")
            out.append(emb)
        return out

    # ---------- main embed method ----------
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts. Returns List[List[float]] (float32 compatible)."""
        if not texts:
            return []

        self.calls += 1
        start_total = time.time()

        # Choose backend (already selected on init)
        backend = self.backend

        # Wrap sbert path (local)
        if backend == "sbert":
            try:
                t0 = time.time()
                arr = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False)
                latency = time.time() - t0
                logger.debug(f"[embed][sbert] batch_size={len(texts)} latency={latency:.3f}s")
                out = self._to_float32(arr)
                # ensure dim consistency
                self._ensure_dim(out)
                self.total_time += (time.time() - start_total)
                return out
            except Exception as e:
                self.errors += 1
                self.last_error = str(e)
                logger.exception(f"[embed][sbert] failed: {e}")
                raise

        # Wrap OpenAI path with retries
        if backend == "openai":
            def _call_openai():
                # Use new client if present
                if getattr(self, "_oai_client", None):
                    return self._oai_client.embeddings.create(model=self._openai_model, input=texts)
                # Fallback to legacy openai
                return openai.Embedding.create(model=self._openai_model, input=texts)

            resp, call_latency, exc = _retry_backoff(_call_openai)
            if exc:
                self.errors += 1
                self.last_error = str(exc)
                logger.exception(f"[embed][openai] failed after retries: {exc}")
                raise exc

            try:
                out = self._normalize_openai_resp(resp)
                self._ensure_dim(out)
                out32 = self._to_float32(out)
                logger.debug(f"[embed][openai] batch_size={len(texts)} api_latency={call_latency:.3f}s")
                self.total_time += (time.time() - start_total)
                return out32
            except Exception as e:
                self.errors += 1
                self.last_error = str(e)
                logger.exception(f"[embed][openai] normalization error: {e}")
                raise

        # Wrap Groq path with retries
        if backend == "groq":
            def _call_groq():
                return self._groq_client.embeddings.create(model=self._groq_model, input=texts)

            resp, call_latency, exc = _retry_backoff(_call_groq)
            if exc:
                self.errors += 1
                self.last_error = str(exc)
                logger.exception(f"[embed][groq] failed after retries: {exc}")
                raise exc

            try:
                out = self._normalize_groq_resp(resp)
                self._ensure_dim(out)
                out32 = self._to_float32(out)
                logger.debug(f"[embed][groq] batch_size={len(texts)} api_latency={call_latency:.3f}s")
                self.total_time += (time.time() - start_total)
                return out32
            except Exception as e:
                self.errors += 1
                self.last_error = str(e)
                logger.exception(f"[embed][groq] normalization error: {e}")
                raise

        # If somehow none matched
        raise RuntimeError("Embedder backend niet beschikbaar of niet geïnitialiseerd.")

    # Utilities for debugging / health
    def summary(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "model": self._initialized_model_name,
            "dim": self._dim,
            "calls": self.calls,
            "errors": self.errors,
            "total_time_s": round(self.total_time, 3),
            "last_error": self.last_error,
        }
