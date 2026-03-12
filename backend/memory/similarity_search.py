"""
Multimodal Math Mentor — Similarity Search over Memory

Uses vector embeddings (via ChromaDB) to find previously solved problems
that are similar to a new query — enabling pattern reuse & learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import CHROMA_PERSIST_DIR
from backend.rag.embeddings import embed_texts, embed_query
from backend.memory.memory_store import MemoryRecord, get_all_records
from backend.utils.logger import get_logger

logger = get_logger(__name__)

MEMORY_COLLECTION = "solved_memory"


def _get_memory_collection() -> chromadb.Collection:
    """Get or create the memory vector collection."""
    from pathlib import Path
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=MEMORY_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


@dataclass
class SimilarProblem:
    """A previously solved problem similar to the current query."""

    record_id: int
    problem_text: str
    solution: str
    topic: str
    similarity: float  # 0–1


def index_record(record: MemoryRecord) -> None:
    """Add a solved problem's embedding to the memory vector store."""
    if not record.id:
        return
    collection = _get_memory_collection()
    text = f"{record.parsed_problem}\n{record.solution}"
    vec = embed_query(text)
    doc_id = f"mem_{record.id}"

    # Upsert — check only this specific ID (O(1) instead of fetching all IDs)
    existing = collection.get(ids=[doc_id])["ids"]
    if existing:
        collection.update(
            ids=[doc_id],
            embeddings=[vec],
            documents=[text],
            metadatas=[{"record_id": record.id, "topic": record.topic}],
        )
    else:
        collection.add(
            ids=[doc_id],
            embeddings=[vec],
            documents=[text],
            metadatas=[{"record_id": record.id, "topic": record.topic}],
        )
    logger.info("Indexed memory record id=%d", record.id)


def find_similar(query: str, top_k: int = 5) -> List[SimilarProblem]:
    """Find previously solved problems similar to *query*."""
    collection = _get_memory_collection()
    if collection.count() == 0:
        return []

    q_vec = embed_query(query)
    results = collection.query(
        query_embeddings=[q_vec],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    similar: list[SimilarProblem] = []
    if results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if results["distances"] else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, dists):
            similarity = round(1.0 - dist, 4)
            parts = doc.split("\n", 1)
            similar.append(
                SimilarProblem(
                    record_id=meta.get("record_id", 0),
                    problem_text=parts[0] if parts else "",
                    solution=parts[1] if len(parts) > 1 else "",
                    topic=meta.get("topic", ""),
                    similarity=similarity,
                )
            )

    logger.info("Found %d similar problems for query.", len(similar))
    return similar


def rebuild_index() -> int:
    """Re-index all records in the SQLite store into the vector collection."""
    records = get_all_records()
    count = 0
    for rec in records:
        index_record(rec)
        count += 1
    logger.info("Rebuilt memory index: %d records.", count)
    return count
