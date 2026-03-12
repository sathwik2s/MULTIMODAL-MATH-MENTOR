"""
Multimodal Math Mentor — Human-in-the-Loop (HITL) Module

Manages the lifecycle of human review requests:
  - Creating review requests when confidence is low.
  - Storing human corrections.
  - Feeding corrections back into the pipeline.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import SQLITE_DB_PATH
from backend.memory.memory_store import update_feedback
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── SQLite-backed review persistence ────────────────────────────────────────

_CREATE_REVIEWS_SQL = """\
CREATE TABLE IF NOT EXISTS review_requests (
    id              TEXT PRIMARY KEY,
    trigger         TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    original_text   TEXT DEFAULT '',
    suggested_text  TEXT DEFAULT '',
    corrected_text  TEXT DEFAULT '',
    answer          TEXT DEFAULT '',
    corrected_answer TEXT DEFAULT '',
    comment         TEXT DEFAULT '',
    memory_record_id INTEGER,
    timestamp       REAL NOT NULL,
    metadata        TEXT DEFAULT '{}'
);
"""


def _get_db() -> sqlite3.Connection:
    db_path = Path(SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_REVIEWS_SQL)
    conn.commit()
    return conn


def _save_review(req: "ReviewRequest") -> None:
    """Upsert a review request into SQLite."""
    conn = _get_db()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO review_requests
              (id, trigger, status, original_text, suggested_text, corrected_text,
               answer, corrected_answer, comment, memory_record_id, timestamp, metadata)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                req.id, req.trigger.value, req.status.value,
                req.original_text, req.suggested_text, req.corrected_text,
                req.answer, req.corrected_answer, req.comment,
                req.memory_record_id, req.timestamp,
                json.dumps(req.metadata),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _load_reviews() -> "List[ReviewRequest]":
    """Load all review requests from SQLite."""
    conn = _get_db()
    try:
        rows = conn.execute("SELECT * FROM review_requests ORDER BY timestamp DESC").fetchall()
    finally:
        conn.close()
    result = []
    for row in rows:
        result.append(ReviewRequest(
            id=row["id"],
            trigger=ReviewTrigger(row["trigger"]),
            status=ReviewStatus(row["status"]),
            original_text=row["original_text"],
            suggested_text=row["suggested_text"],
            corrected_text=row["corrected_text"],
            answer=row["answer"],
            corrected_answer=row["corrected_answer"],
            comment=row["comment"],
            memory_record_id=row["memory_record_id"],
            timestamp=row["timestamp"],
            metadata=json.loads(row["metadata"] or "{}"),
        ))
    return result


class ReviewTrigger(str, Enum):
    """Why a review was triggered."""

    OCR_LOW_CONFIDENCE = "ocr_low_confidence"
    ASR_LOW_CONFIDENCE = "asr_low_confidence"
    PARSER_AMBIGUITY = "parser_ambiguity"
    VERIFIER_UNCERTAIN = "verifier_uncertain"
    USER_RECHECK = "user_recheck"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CORRECTED = "corrected"
    REJECTED = "rejected"


@dataclass
class ReviewRequest:
    """A single review request queued for human attention."""

    id: str = ""
    trigger: ReviewTrigger = ReviewTrigger.USER_RECHECK
    status: ReviewStatus = ReviewStatus.PENDING
    original_text: str = ""
    suggested_text: str = ""
    corrected_text: str = ""
    answer: str = ""
    corrected_answer: str = ""
    comment: str = ""
    memory_record_id: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["trigger"] = self.trigger.value
        d["status"] = self.status.value
        return d


def create_review(
    trigger: ReviewTrigger,
    original_text: str,
    suggested_text: str = "",
    answer: str = "",
    memory_record_id: int | None = None,
    metadata: dict | None = None,
) -> ReviewRequest:
    """Create and persist a new human review request."""
    req = ReviewRequest(
        id=f"review_{int(time.time() * 1000)}",
        trigger=trigger,
        original_text=original_text,
        suggested_text=suggested_text or original_text,
        answer=answer,
        memory_record_id=memory_record_id,
        metadata=metadata or {},
    )
    _save_review(req)
    logger.info("Created review request %s (trigger=%s)", req.id, trigger.value)
    return req


def get_pending_reviews() -> List[ReviewRequest]:
    """Return all pending review requests from the persistent store."""
    return [r for r in _load_reviews() if r.status == ReviewStatus.PENDING]


def approve_review(review_id: str) -> Optional[ReviewRequest]:
    """Mark a review as approved (no changes needed)."""
    req = _find_review(review_id)
    if req:
        req.status = ReviewStatus.APPROVED
        _save_review(req)
        _persist_feedback(req)
        logger.info("Review %s approved.", review_id)
    return req


def correct_review(
    review_id: str,
    corrected_text: str = "",
    corrected_answer: str = "",
    comment: str = "",
) -> Optional[ReviewRequest]:
    """Apply human corrections to a review."""
    req = _find_review(review_id)
    if req:
        req.status = ReviewStatus.CORRECTED
        req.corrected_text = corrected_text or req.suggested_text
        req.corrected_answer = corrected_answer or req.answer
        req.comment = comment
        _save_review(req)
        _persist_feedback(req)
        logger.info("Review %s corrected.", review_id)
    return req


def reject_review(review_id: str, comment: str = "") -> Optional[ReviewRequest]:
    """Reject the solution entirely."""
    req = _find_review(review_id)
    if req:
        req.status = ReviewStatus.REJECTED
        req.comment = comment
        _save_review(req)
        _persist_feedback(req)
        logger.info("Review %s rejected.", review_id)
    return req


# ── Internals ────────────────────────────────────────────────────────────────

def _find_review(review_id: str) -> Optional[ReviewRequest]:
    for r in _load_reviews():
        if r.id == review_id:
            return r
    logger.warning("Review %s not found.", review_id)
    return None


def _persist_feedback(req: ReviewRequest) -> None:
    """Push feedback into the memory store if a record id is available."""
    if req.memory_record_id:
        feedback = req.status.value
        corrections = req.corrected_answer or req.corrected_text or ""
        update_feedback(req.memory_record_id, feedback, corrections)


def clear_queue() -> None:
    """Clear all reviews (for testing / reset)."""
    conn = _get_db()
    try:
        conn.execute("DELETE FROM review_requests")
        conn.commit()
    finally:
        conn.close()
