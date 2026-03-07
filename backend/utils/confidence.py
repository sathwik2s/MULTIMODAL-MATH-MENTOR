"""
Multimodal Math Mentor — Confidence Utilities

Helpers for computing and classifying confidence scores across modules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    """Encapsulates a value with an associated confidence score."""

    value: object
    score: float  # 0.0 – 1.0
    reason: str = ""

    @property
    def is_high(self) -> bool:
        return self.score >= 0.75

    @property
    def is_medium(self) -> bool:
        return 0.5 <= self.score < 0.75

    @property
    def is_low(self) -> bool:
        return self.score < 0.5

    def needs_human_review(self, threshold: float = 0.7) -> bool:
        """Return True when confidence is below the given threshold."""
        return self.score < threshold


def average_confidence(scores: list[float]) -> float:
    """Compute the mean of a list of confidence scores."""
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def weighted_confidence(scores: list[float], weights: list[float]) -> float:
    """Compute a weighted mean of confidence scores."""
    if not scores or not weights or len(scores) != len(weights):
        return 0.0
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    return sum(s * w for s, w in zip(scores, weights)) / total_weight


def classify_confidence(score: float) -> str:
    """Return a human-readable label for a confidence score."""
    if score >= 0.9:
        return "very_high"
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.25:
        return "low"
    return "very_low"
