"""
Multimodal Math Mentor — Persistent Memory Store

Dual-layer memory:
  1. SQLite — structured records of every solved problem.
  2. ChromaDB — vector embeddings for similarity search.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import SQLITE_DB_PATH
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# ── SQLite schema ────────────────────────────────────────────────────────────

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS solved_problems (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       REAL    NOT NULL,
    input_type      TEXT    NOT NULL DEFAULT 'text',
    raw_input       TEXT    NOT NULL,
    parsed_problem  TEXT    NOT NULL,
    topic           TEXT    NOT NULL DEFAULT 'other',
    retrieved_context TEXT  DEFAULT '',
    solution        TEXT    NOT NULL,
    explanation     TEXT    DEFAULT '',
    verifier_confidence REAL DEFAULT 0.0,
    user_feedback   TEXT    DEFAULT '',
    corrections     TEXT    DEFAULT ''
);
"""


def _get_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite database and ensure the table exists."""
    db_path = Path(SQLITE_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn


@dataclass
class MemoryRecord:
    """A single memory record for a solved problem."""

    id: Optional[int] = None
    timestamp: float = 0.0
    input_type: str = "text"
    raw_input: str = ""
    parsed_problem: str = ""
    topic: str = "other"
    retrieved_context: str = ""
    solution: str = ""
    explanation: str = ""
    verifier_confidence: float = 0.0
    user_feedback: str = ""
    corrections: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ── CRUD operations ──────────────────────────────────────────────────────────

def store_record(record: MemoryRecord) -> int:
    """Insert a new record and return its row id."""
    record.timestamp = record.timestamp or time.time()
    conn = _get_connection()
    cur = conn.execute(
        """
        INSERT INTO solved_problems
            (timestamp, input_type, raw_input, parsed_problem, topic,
             retrieved_context, solution, explanation, verifier_confidence,
             user_feedback, corrections)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.timestamp,
            record.input_type,
            record.raw_input,
            record.parsed_problem,
            record.topic,
            record.retrieved_context,
            record.solution,
            record.explanation,
            record.verifier_confidence,
            record.user_feedback,
            record.corrections,
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    logger.info("Stored memory record id=%d, topic=%s", row_id, record.topic)
    return row_id


def update_feedback(record_id: int, feedback: str, corrections: str = "") -> None:
    """Update user feedback and corrections for an existing record."""
    conn = _get_connection()
    conn.execute(
        "UPDATE solved_problems SET user_feedback = ?, corrections = ? WHERE id = ?",
        (feedback, corrections, record_id),
    )
    conn.commit()
    conn.close()
    logger.info("Updated feedback for record id=%d", record_id)


def get_record(record_id: int) -> Optional[MemoryRecord]:
    """Fetch a single record by id."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM solved_problems WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    return _row_to_record(row)


def get_recent_records(limit: int = 20) -> List[MemoryRecord]:
    """Return the most recent records."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM solved_problems ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [_row_to_record(r) for r in rows]


def get_records_by_topic(topic: str, limit: int = 10) -> List[MemoryRecord]:
    """Return records matching a topic."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM solved_problems WHERE topic = ? ORDER BY timestamp DESC LIMIT ?",
        (topic, limit),
    ).fetchall()
    conn.close()
    return [_row_to_record(r) for r in rows]


def get_all_records() -> List[MemoryRecord]:
    """Return every record (be cautious with large datasets)."""
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM solved_problems ORDER BY timestamp DESC").fetchall()
    conn.close()
    return [_row_to_record(r) for r in rows]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_record(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        id=row["id"],
        timestamp=row["timestamp"],
        input_type=row["input_type"],
        raw_input=row["raw_input"],
        parsed_problem=row["parsed_problem"],
        topic=row["topic"],
        retrieved_context=row["retrieved_context"],
        solution=row["solution"],
        explanation=row["explanation"],
        verifier_confidence=row["verifier_confidence"],
        user_feedback=row["user_feedback"],
        corrections=row["corrections"],
    )
