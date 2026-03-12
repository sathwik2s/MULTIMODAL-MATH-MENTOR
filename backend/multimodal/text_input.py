"""
Multimodal Math Mentor — Text Input Handler

Simple text preprocessing for direct typed input.
"""

from __future__ import annotations

import re

from backend.utils.confidence import ConfidenceResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Map spoken math phrases to symbolic equivalents
_MATH_PHRASE_MAP: list[tuple[str, str]] = [
    (r"\braised to the power(?: of)?\s*", "^"),
    (r"\bsquare root of\b", "sqrt"),
    (r"\bcube root of\b", "cbrt"),
    (r"\bintegral of\b", "∫"),
    (r"\bderivative of\b", "d/dx"),
    (r"\bsummation of\b", "Σ"),
    (r"\binfinity\b", "∞"),
    (r"\bpi\b", "π"),
    (r"\balpha\b", "α"),
    (r"\bbeta\b", "β"),
    (r"\bgamma\b", "γ"),
    (r"\btheta\b", "θ"),
    (r"\bdelta\b", "δ"),
    (r"\blambda\b", "λ"),
    (r"\bgreater than or equal to\b", "≥"),
    (r"\bless than or equal to\b", "≤"),
    (r"\bgreater than\b", ">"),
    (r"\bless than\b", "<"),
    (r"\bnot equal to\b", "≠"),
    (r"\bplus or minus\b", "±"),
    (r"\bdivided by\b", "/"),
    (r"\bmultiplied by\b", "*"),
    (r"\btimes\b", "*"),
    (r"\bsquared\b", "^2"),
    (r"\bcubed\b", "^3"),
]


def normalize_math_text(text: str) -> str:
    """Replace common verbal math phrases with symbolic equivalents."""
    result = text.strip()
    for pattern, replacement in _MATH_PHRASE_MAP:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    # Collapse multiple whitespace
    result = re.sub(r"\s+", " ", result).strip()
    return result


def process_text_input(text: str) -> ConfidenceResult:
    """Validate and normalise a text question.

    Returns a ConfidenceResult with the cleaned text and a heuristic score.
    """
    if not text or not text.strip():
        return ConfidenceResult(value="", score=0.0, reason="Empty input")

    cleaned = normalize_math_text(text)

    # Simple heuristic: longer, more "mathy" text → higher confidence
    has_math_symbols = bool(re.search(r"[+\-*/=^√∫Σπ(){}x]", cleaned))
    has_digits = bool(re.search(r"\d", cleaned))
    long_enough = len(cleaned) > 10

    score = 0.5
    if has_math_symbols:
        score += 0.2
    if has_digits:
        score += 0.15
    if long_enough:
        score += 0.15
    score = min(score, 1.0)

    logger.info("Text input processed (score=%.2f): %s", score, cleaned[:80])
    return ConfidenceResult(value=cleaned, score=score, reason="text_input")
