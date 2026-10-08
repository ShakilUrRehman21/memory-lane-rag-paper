from pathlib import Path
from pydantic import BaseModel
import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


class Settings(BaseModel):
    PROJECT_NAME: str = "Memory Lane RAG"
    VERSION: str = "1.1.0"
    API_PREFIX: str = "/api"

    # Base paths. ML_DATA_DIR lets tests and benchmarks run against an isolated store.
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = Path(_env("ML_DATA_DIR", str(BASE_DIR / "data")))
    STORAGE_DIR: Path = DATA_DIR / "storage"
    DB_PATH: Path = STORAGE_DIR / "memory_lane.db"
    UPLOADS_DIR: Path = STORAGE_DIR / "uploads"
    VECTOR_STORE_DIR: Path = STORAGE_DIR / "vectors"  # kept for backward compatibility (vectors now live in SQLite)

    # Embeddings. Backends: "wordllama" (default, offline, 256-d), "st:<hf-model-id>" for
    # sentence-transformers (e.g. "st:BAAI/bge-m3", "st:Qwen/Qwen3-Embedding-0.6B"),
    # "openai:<model>" (e.g. "openai:text-embedding-3-small"), or "hash" (the original
    # v1.0 word-hashing features, kept only for ablation / backward comparison).
    EMBEDDING_BACKEND: str = _env("ML_EMBEDDING_BACKEND", "wordllama")
    DEFAULT_LLM_MODEL: str = "gemini-2.5-flash"

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Retrieval
    DEFAULT_TOP_K: int = 10
    RRF_K: int = 60
    # Stratification: "router" (v1.0 behaviour: only for evolution-intent queries), "always",
    # "soft" (part of the k slots by pure relevance, the rest spread over uncovered epochs), or "off".
    # Default selected by a pre-registered rule on dev data only (scripts/select_stratification.py):
    # "router" keeps LoCoMo-dev Recall@5 at the "off" level (0.403) while raising MLLB-dev temporal
    # coverage from 0.865 to 0.917; "always" reaches 0.977 coverage but drops Recall@5 to 0.309.
    # Use "always" for purely longitudinal workloads.
    STRATIFICATION_MODE: str = _env("ML_STRATIFICATION_MODE", "router")
    # "soft" mode: fraction of the k slots filled purely by relevance before stratifying the rest.
    SOFT_RELEVANCE_FRACTION: float = float(_env("ML_SOFT_RELEVANCE_FRACTION", "0.5"))
    # Epochs: "year" (v1.0 behaviour) or "adaptive" (span of the candidate pool split into
    # at most MAX_EPOCHS equal-width bins, never narrower than MIN_EPOCH_DAYS).
    EPOCH_MODE: str = _env("ML_EPOCH_MODE", "adaptive")
    MAX_EPOCHS: int = 6
    MIN_EPOCH_DAYS: int = 30

    # Change detection
    # 0.42 in v1.0 was set for the word-hashing features. 0.70 was selected on the DEV split of
    # MLLB-Synth v1 (scripts/calibrate_drift.py; mean change-point F1 0.344 vs 0.241 at 0.42) and is
    # embedder-specific: re-calibrate when changing ML_EMBEDDING_BACKEND.
    SEMANTIC_DRIFT_THRESHOLD: float = float(_env("ML_DRIFT_THRESHOLD", "0.70"))
    POLARITY_INVERSION_THRESHOLD: float = 0.75
    SPARSE_EVIDENCE_DAYS: int = 180
    # Restrict change detection to the topic(s) named in the query when possible.
    QUERY_FOCUSED_CHANGES: bool = _env("ML_QUERY_FOCUSED_CHANGES", "1") == "1"

    # Read-only queries: v1.0 wrote change points / relationships to the DB on every query.
    PERSIST_ANALYSIS_ON_QUERY: bool = _env("ML_PERSIST_ANALYSIS", "0") == "1"

    def ensure_directories(self) -> None:
        for d in (self.DATA_DIR, self.STORAGE_DIR, self.UPLOADS_DIR, self.VECTOR_STORE_DIR):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
