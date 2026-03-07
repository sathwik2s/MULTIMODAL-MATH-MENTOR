"""
Multimodal Math Mentor — Audio ASR Pipeline

Converts uploaded audio to text using OpenAI Whisper (local model).
Applies math-phrase normalisation after transcribing.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Union

from backend.utils.confidence import ConfidenceResult
from backend.utils.logger import get_logger
from backend.multimodal.text_input import normalize_math_text

logger = get_logger(__name__)

# Lazy-loaded Whisper model
_model = None


def _get_whisper_model(size: str = "base"):
    """Lazy-load a Whisper model (default: base for speed)."""
    global _model
    if _model is None:
        import whisper
        logger.info("Loading Whisper model (%s) …", size)
        _model = whisper.load_model(size)
    return _model


def transcribe_audio(
    audio_input: Union[str, Path, bytes],
    whisper_size: str = "base",
) -> ConfidenceResult:
    """Transcribe audio to text and return with confidence score.

    Parameters
    ----------
    audio_input : File path (str/Path) or raw bytes of an audio file.
    whisper_size : Whisper model size (tiny/base/small/medium/large).

    Returns
    -------
    ConfidenceResult with value=transcript, score=heuristic_confidence.
    """
    model = _get_whisper_model(whisper_size)

    # If bytes, write to a temp file
    file_path: str
    if isinstance(audio_input, bytes):
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.write(audio_input)
        tmp.flush()
        file_path = tmp.name
    else:
        file_path = str(audio_input)

    if not Path(file_path).exists():
        return ConfidenceResult(value="", score=0.0, reason="Audio file not found")

    try:
        result = model.transcribe(file_path, language="en")
    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        return ConfidenceResult(value="", score=0.0, reason=f"ASR error: {exc}")

    raw_text: str = result.get("text", "").strip()
    if not raw_text:
        return ConfidenceResult(value="", score=0.0, reason="No speech detected")

    # Normalise math phrases
    cleaned = normalize_math_text(raw_text)

    # Whisper doesn't directly expose a single confidence; use
    # average log-probability from segments as a proxy.
    segments = result.get("segments", [])
    if segments:
        avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
        # Map log-prob (typically -0.1 … -1.5) to 0–1 range heuristically
        confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
    else:
        confidence = 0.5  # default fallback

    logger.info(
        "ASR transcript (%d chars, conf=%.2f): %s",
        len(cleaned),
        confidence,
        cleaned[:80],
    )

    return ConfidenceResult(
        value=cleaned,
        score=round(confidence, 4),
        reason="asr_ok" if confidence >= 0.6 else "asr_low_confidence",
    )
