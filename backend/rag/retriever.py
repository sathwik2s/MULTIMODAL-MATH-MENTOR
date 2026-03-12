"""
Multimodal Math Mentor — RAG Retriever

Queries ChromaDB for the top-K most relevant knowledge chunks given a query.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from backend.config import RAG_TOP_K
from backend.rag.embeddings import embed_query
from backend.rag.ingest import get_collection
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    """A single chunk returned by the retriever."""

    text: str
    source: str
    score: float  # cosine similarity (higher = better, 0–1 after conversion)
    chunk_index: int = 0


@dataclass
class RetrievalResult:
    """Aggregated retrieval output."""

    chunks: List[RetrievedChunk] = field(default_factory=list)
    query: str = ""

    @property
    def has_results(self) -> bool:
        return len(self.chunks) > 0

    def as_context_string(self) -> str:
        """Format chunks as a numbered context block for the LLM."""
        if not self.chunks:
            return "(No relevant knowledge-base documents found.)"
        lines: list[str] = []
        for i, c in enumerate(self.chunks, 1):
            lines.append(f"[{i}] (source: {c.source}, relevance: {c.score:.2f})\n{c.text}")
        return "\n\n".join(lines)


def retrieve(query: str, top_k: int = RAG_TOP_K) -> RetrievalResult:
    """Embed *query* and retrieve top-K chunks from ChromaDB.

    ChromaDB returns distances (lower = more similar for cosine).
    We convert to a similarity score: score = 1 - distance.
    """
    collection = get_collection()

    # Guard: empty collection
    if collection.count() == 0:
        logger.warning("Knowledge base is empty — run ingestion first.")
        return RetrievalResult(query=query)

    q_vec = embed_query(query)

    results = collection.query(
        query_embeddings=[q_vec],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if results["distances"] else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, dists):
            chunks.append(
                RetrievedChunk(
                    text=doc,
                    source=meta.get("source", "unknown"),
                    score=round(1 - dist, 4),  # cosine distance → similarity
                    chunk_index=meta.get("chunk_index", 0),
                )
            )

    logger.info("Retrieved %d chunks for query (top_k=%d).", len(chunks), top_k)
    return RetrievalResult(chunks=chunks, query=query)
