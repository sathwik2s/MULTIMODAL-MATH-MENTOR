"""
Multimodal Math Mentor — RAG Ingestion Pipeline

Reads documents from the knowledge_base directory, chunks them, computes
embeddings, and stores everything in a persistent ChromaDB collection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List

import chromadb
from chromadb.config import Settings as ChromaSettings

from backend.config import CHROMA_PERSIST_DIR, KNOWLEDGE_BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from backend.rag.embeddings import embed_texts
from backend.utils.logger import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "math_knowledge"


# ── Chunking ─────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


# ── ChromaDB helpers ─────────────────────────────────────────────────────────

def _get_chroma_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client."""
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection() -> chromadb.Collection:
    """Get or create the knowledge-base collection."""
    client = _get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Ingestion ────────────────────────────────────────────────────────────────

def _doc_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def ingest_directory(directory: Path | None = None) -> int:
    """Read all .txt / .md files in *directory*, chunk, embed, and store.

    Returns the number of chunks ingested.
    """
    directory = directory or KNOWLEDGE_BASE_DIR
    collection = get_collection()

    files = list(directory.glob("*.txt")) + list(directory.glob("*.md"))
    if not files:
        logger.warning("No .txt or .md files found in %s", directory)
        return 0

    all_chunks: list[str] = []
    all_ids: list[str] = []
    all_metas: list[dict] = []

    for fpath in files:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        chunks = _chunk_text(text)
        for idx, chunk in enumerate(chunks):
            cid = _doc_id(chunk)
            all_chunks.append(chunk)
            all_ids.append(cid)
            all_metas.append({"source": fpath.name, "chunk_index": idx})

    # Deduplicate by id
    existing = set(collection.get()["ids"])
    new_chunks, new_ids, new_metas = [], [], []
    for chunk, cid, meta in zip(all_chunks, all_ids, all_metas):
        if cid not in existing:
            new_chunks.append(chunk)
            new_ids.append(cid)
            new_metas.append(meta)

    if not new_chunks:
        logger.info("All chunks already present — nothing to ingest.")
        return 0

    logger.info("Embedding %d new chunks …", len(new_chunks))
    vectors = embed_texts(new_chunks)

    collection.add(
        ids=new_ids,
        embeddings=vectors,
        documents=new_chunks,
        metadatas=new_metas,
    )
    logger.info("Ingested %d chunks into ChromaDB.", len(new_chunks))
    return len(new_chunks)


def ingest_text(text: str, source: str = "manual") -> int:
    """Ingest a single piece of text (e.g. a solved example)."""
    collection = get_collection()
    chunks = _chunk_text(text)
    ids = [_doc_id(c) for c in chunks]
    metas = [{"source": source, "chunk_index": i} for i, _ in enumerate(chunks)]
    vecs = embed_texts(chunks)

    existing = set(collection.get()["ids"])
    new = [(c, i, m, v) for c, i, m, v in zip(chunks, ids, metas, vecs) if i not in existing]
    if not new:
        return 0

    collection.add(
        ids=[x[1] for x in new],
        embeddings=[x[3] for x in new],
        documents=[x[0] for x in new],
        metadatas=[x[2] for x in new],
    )
    return len(new)


# ── CLI helper ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    n = ingest_directory()
    print(f"Ingested {n} chunks.")
