"""
Multimodal Math Mentor — Embedding Engine

Wraps sentence-transformers for generating vector embeddings.
"""

from __future__ import annotations

from functools import lru_cache

from backend.config import EMBEDDING_MODEL
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load and cache the embedding model (singleton)."""
    from sentence_transformers import SentenceTransformer  # lazy — avoids ~4s import on startup
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts and return a list of float vectors."""
    model = _load_model()
    embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query])[0]
