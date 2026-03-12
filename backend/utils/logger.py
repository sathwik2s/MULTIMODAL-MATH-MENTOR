"""
Multimodal Math Mentor — Application Logger

Provides a pre-configured logger with console + optional file output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from backend.config import LOG_LEVEL, DATA_DIR

_LOG_FILE = DATA_DIR / "app.log"


def get_logger(name: str = "math_mentor") -> logging.Logger:
    """Return a named logger with console and file handlers."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (best-effort)
    try:
        _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(str(_LOG_FILE), encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        logger.warning("Could not create log file at %s", _LOG_FILE)

    return logger
