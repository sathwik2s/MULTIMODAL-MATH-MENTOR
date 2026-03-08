"""
Multimodal Math Mentor — Audio ASR Pipeline

Engine priority (configurable via ASR_ENGINE env var):
  auto     — Groq cloud Whisper → OpenAI cloud Whisper → local Whisper
  groq     — Groq Whisper API  (whisper-large-v3, free tier, fast)
  openai   — OpenAI Whisper API (whisper-1)
  local    — local openai-whisper model (heavy, not suitable for Render)

For cloud deployments (Render) set ASR_ENGINE=groq or ASR_ENGINE=openai.
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Union

from backend.utils.confidence import ConfidenceResult
from backend.utils.logger import get_logger
from backend.multimodal.text_input import normalize_math_text

logger = get_logger(__name__)

# Lazy-loaded local Whisper model (only used when ASR_ENGINE=local)
_local_model = None


def _get_local_whisper_model(size: str = "base"):
    """Lazy-load the local Whisper model."""
    global _local_model
    if _local_model is None:
        import whisper
        logger.info("Loading local Whisper model (%s) …", size)
        _local_model = whisper.load_model(size)
    return _local_model


# ── Engine availability ───────────────────────────────────────────────────────

def _groq_whisper_available() -> bool:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return bool(key) and key not in {"", "your_groq_api_key"} and not key.endswith("...")


def _openai_whisper_available() -> bool:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return bool(key) and key not in {"", "your_openai_api_key"} and not key.endswith("...")


def _local_whisper_available() -> bool:
    try:
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _detect_asr_engine() -> str:
    """Return the engine to use: 'groq' | 'openai' | 'local'."""
    pref = os.environ.get("ASR_ENGINE", "auto").lower()
    if pref == "groq":
        return "groq"
    if pref == "openai":
        return "openai"
    if pref == "local":
        return "local"
    # Auto priority: Groq (free, fast, no model download) → OpenAI → local
    if _groq_whisper_available():
        return "groq"
    if _openai_whisper_available():
        return "openai"
    if _local_whisper_available():
        return "local"
    raise ImportError(
        "No ASR engine available.\n"
        "Option A — Groq Whisper API (free, fast): set GROQ_API_KEY in .env\n"
        "Option B — OpenAI Whisper API: set OPENAI_API_KEY in .env\n"
        "Option C — Local Whisper (offline): pip install openai-whisper  and set ASR_ENGINE=local"
    )


# ── Cloud Whisper via Groq ────────────────────────────────────────────────────

def _groq_transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> tuple[str, float]:
    """Transcribe using Groq's Whisper API (whisper-large-v3)."""
    from groq import Groq
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
    transcription = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model="whisper-large-v3",
        response_format="verbose_json",
        language="en",
    )
    text = getattr(transcription, "text", "") or ""
    # Groq verbose_json may include segments with avg_logprob
    segments = getattr(transcription, "segments", None) or []
    if segments:
        avg_logprob = sum(s.get("avg_logprob", -0.3) for s in segments) / len(segments)
        confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
    else:
        confidence = 0.90 if len(text.strip()) > 5 else 0.3
    logger.info("Groq Whisper: %d chars, conf=%.2f", len(text), confidence)
    return text.strip(), confidence


# ── Cloud Whisper via OpenAI ──────────────────────────────────────────────────

def _openai_transcribe(audio_bytes: bytes, filename: str = "audio.wav") -> tuple[str, float]:
    """Transcribe using OpenAI's Whisper API (whisper-1)."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=(filename, io.BytesIO(audio_bytes)),
        response_format="text",
        language="en",
    )
    text = transcription if isinstance(transcription, str) else str(transcription)
    confidence = 0.90 if len(text.strip()) > 5 else 0.3
    logger.info("OpenAI Whisper: %d chars", len(text))
    return text.strip(), confidence


# ── Local Whisper ─────────────────────────────────────────────────────────────

def _local_transcribe(audio_bytes: bytes, whisper_size: str = "base") -> tuple[str, float]:
    """Transcribe using local openai-whisper model."""
    model = _get_local_whisper_model(whisper_size)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(audio_bytes)
    tmp.flush()
    file_path = tmp.name
    result = model.transcribe(file_path, language="en")
    raw_text: str = result.get("text", "").strip()
    segments = result.get("segments", [])
    if segments:
        avg_logprob = sum(s.get("avg_logprob", -1.0) for s in segments) / len(segments)
        confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
    else:
        confidence = 0.5
    return raw_text, confidence


# ── Main entry point ──────────────────────────────────────────────────────────

def transcribe_audio(
    audio_input: Union[str, Path, bytes],
    whisper_size: str = "base",
) -> ConfidenceResult:
    """Transcribe audio to text and return with confidence score.

    Parameters
    ----------
    audio_input : File path (str/Path) or raw bytes of an audio file.
    whisper_size : Whisper model size — used only for the local engine.

    Returns
    -------
    ConfidenceResult with value=transcript, score=confidence.
    """
    # Normalise input to bytes
    if isinstance(audio_input, (str, Path)):
        fp = Path(audio_input)
        if not fp.exists():
            return ConfidenceResult(value="", score=0.0, reason="Audio file not found")
        audio_bytes = fp.read_bytes()
        filename = fp.name
    elif isinstance(audio_input, bytes):
        audio_bytes = audio_input
        filename = "audio.wav"
    else:
        return ConfidenceResult(value="", score=0.0, reason="Unsupported audio input type")

    try:
        engine = _detect_asr_engine()
    except ImportError as exc:
        return ConfidenceResult(value="", score=0.0, reason=str(exc))

    raw_text = ""
    confidence = 0.0

    try:
        if engine == "groq":
            raw_text, confidence = _groq_transcribe(audio_bytes, filename)
        elif engine == "openai":
            raw_text, confidence = _openai_transcribe(audio_bytes, filename)
        else:
            raw_text, confidence = _local_transcribe(audio_bytes, whisper_size)
    except Exception as exc:
        logger.error("ASR (%s) failed: %s", engine, exc)
        return ConfidenceResult(value="", score=0.0, reason=f"ASR error ({engine}): {exc}")

    if not raw_text.strip():
        return ConfidenceResult(value="", score=0.0, reason="No speech detected")

    # Normalise math phrases
    cleaned = normalize_math_text(raw_text)

    logger.info(
        "ASR transcript via %s (%d chars, conf=%.2f): %s",
        engine, len(cleaned), confidence, cleaned[:80],
    )

    return ConfidenceResult(
        value=cleaned,
        score=round(confidence, 4),
        reason="asr_ok" if confidence >= 0.6 else "asr_low_confidence",
    )
