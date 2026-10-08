"""
Pluggable text-embedding backends.

v1.0 used word-hashing features (MD5/SHA-256 buckets plus hand-picked keyword boosts) and
described them as "semantic embeddings". That function is preserved as the "hash" backend so
the original behaviour can be reproduced in ablations, but it is no longer the default.
"""
from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache
from typing import List

import numpy as np

log = logging.getLogger(__name__)


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    if m.ndim == 1:
        m = m[None, :]
    n = np.linalg.norm(m, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return m / n


class Embedder:
    name: str = "base"
    dim: int = 0

    def embed(self, texts: List[str]) -> np.ndarray:  # (n, dim), L2-normalised
        raise NotImplementedError

    def embed_one(self, text: str) -> np.ndarray:
        return self.embed([text])[0]


class HashEmbedder(Embedder):
    """Original v1.0 feature-hashing function (NOT a semantic embedding). Ablation only."""
    name = "hash"
    dim = 384
    _BOOSTS = {"ai": 10, "machine": 11, "learning": 12, "research": 13, "engineer": 14, "java": 15,
               "python": 16, "goal": 17, "decision": 18, "change": 19, "contradiction": 20}

    def _one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        for w in text.lower().split():
            vec[int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % self.dim] += 1.0
            vec[int(hashlib.sha256(w[:3].encode("utf-8")).hexdigest(), 16) % self.dim] += 0.5
        low = text.lower()
        for term, idx in self._BOOSTS.items():
            if term in low:
                vec[idx] += 2.0
        return vec

    def embed(self, texts):
        return _normalize(np.stack([self._one(t) for t in texts])) if texts else np.zeros((0, self.dim), np.float32)


class WordLlamaEmbedder(Embedder):
    """Static token embeddings distilled from an LLM (wordllama, ~16 MB, runs offline on CPU)."""

    def __init__(self, dim: int = 256):
        from wordllama import WordLlama  # optional dependency
        self._m = WordLlama.load(dim=dim)
        self.dim = dim
        self.name = f"wordllama-l2-supercat-{dim}"

    def embed(self, texts):
        if not texts:
            return np.zeros((0, self.dim), np.float32)
        return _normalize(self._m.embed(list(texts), norm=True))


class SentenceTransformerEmbedder(Embedder):
    """Any sentence-transformers model, e.g. BAAI/bge-m3 or Qwen/Qwen3-Embedding-0.6B."""

    def __init__(self, model_id: str):
        from sentence_transformers import SentenceTransformer  # optional dependency
        kwargs = {"trust_remote_code": True}
        device = os.getenv("ML_EMBEDDING_DEVICE")
        if device:
            kwargs["device"] = device
        self._m = SentenceTransformer(model_id, **kwargs)
        self.dim = int(self._m.get_sentence_embedding_dimension())
        self.name = f"st:{model_id}"
        self._bs = int(os.getenv("ML_EMBEDDING_BATCH", "32"))

    def embed(self, texts):
        if not texts:
            return np.zeros((0, self.dim), np.float32)
        return _normalize(self._m.encode(list(texts), batch_size=self._bs, normalize_embeddings=True,
                                         show_progress_bar=False))


class OpenAIEmbedder(Embedder):
    """OpenAI-compatible /v1/embeddings endpoint (OPENAI_API_KEY; OPENAI_BASE_URL optional)."""

    def __init__(self, model: str):
        import httpx
        self._httpx = httpx
        self.model = model
        self.name = f"openai:{model}"
        self.base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.key = os.getenv("OPENAI_API_KEY", "")
        self.dim = len(self.embed(["dimension probe"])[0])

    def embed(self, texts):
        if not texts:
            return np.zeros((0, self.dim), np.float32)
        out = []
        with self._httpx.Client(timeout=60.0) as c:
            for i in range(0, len(texts), 256):
                r = c.post(f"{self.base}/embeddings", headers={"Authorization": f"Bearer {self.key}"},
                           json={"model": self.model, "input": list(texts[i:i + 256])})
                r.raise_for_status()
                out.extend(d["embedding"] for d in sorted(r.json()["data"], key=lambda d: d["index"]))
        return _normalize(np.array(out, dtype=np.float32))


def build_embedder(spec: str) -> Embedder:
    spec = (spec or "wordllama").strip()
    if spec == "hash":
        return HashEmbedder()
    if spec.startswith("wordllama"):
        dim = int(spec.split(":")[1]) if ":" in spec else 256
        return WordLlamaEmbedder(dim)
    if spec.startswith("st:"):
        return SentenceTransformerEmbedder(spec[3:])
    if spec.startswith("openai:"):
        return OpenAIEmbedder(spec[7:])
    raise ValueError(f"Unknown embedding backend '{spec}'")


@lru_cache(maxsize=4)
def get_embedder(spec: str | None = None) -> Embedder:
    from app.core.config import settings
    spec = spec or settings.EMBEDDING_BACKEND
    try:
        return build_embedder(spec)
    except Exception as e:  # pragma: no cover - depends on optional packages
        if spec == "hash":
            raise
        log.warning("Embedding backend '%s' unavailable (%s); falling back to WordLlama/hash.", spec, e)
        try:
            return WordLlamaEmbedder()
        except Exception:
            log.warning("WordLlama unavailable; using the non-semantic 'hash' backend.")
            return HashEmbedder()
