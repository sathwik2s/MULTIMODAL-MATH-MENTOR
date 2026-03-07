"""
Multimodal Math Mentor — Central Configuration

Loads environment variables and exposes typed settings used across all modules.
"""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── Disable OpenTelemetry SDK (avoids Python 3.13 hang with chromadb) ────────
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# ── LLM ──────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# ── Vision OCR models (used by image_ocr.py, independent of the chat model) ──
OPENAI_VISION_MODEL: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")
GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
ANTHROPIC_VISION_MODEL: str = os.getenv("ANTHROPIC_VISION_MODEL", "claude-3-haiku-20240307")
GEMINI_VISION_MODEL: str = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash")

# ── Embeddings ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── OCR ──────────────────────────────────────────────────────────────────────
OCR_CONFIDENCE_THRESHOLD: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.7"))
# OCR_ENGINE: mathpix | easyocr | auto  (default: auto — prefers Mathpix if keys exist)
MATHPIX_APP_ID: str = os.getenv("MATHPIX_APP_ID", "")
MATHPIX_APP_KEY: str = os.getenv("MATHPIX_APP_KEY", "")

# ── Verifier ─────────────────────────────────────────────────────────────────
VERIFIER_CONFIDENCE_THRESHOLD: float = float(
    os.getenv("VERIFIER_CONFIDENCE_THRESHOLD", "0.75")
)

# ── RAG ──────────────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR: str = os.getenv(
    "CHROMA_PERSIST_DIR", str(_PROJECT_ROOT / "data" / "chroma_db")
)
RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "5"))
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

# ── Memory / SQLite ─────────────────────────────────────────────────────────
SQLITE_DB_PATH: str = os.getenv(
    "SQLITE_DB_PATH", str(_PROJECT_ROOT / "data" / "memory.db")
)

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR: Path = _PROJECT_ROOT / "data"
KNOWLEDGE_BASE_DIR: Path = DATA_DIR / "knowledge_base"
SOLVED_EXAMPLES_DIR: Path = DATA_DIR / "solved_examples"

# Ensure critical directories exist
for _d in (DATA_DIR, KNOWLEDGE_BASE_DIR, SOLVED_EXAMPLES_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _is_placeholder_key(key: str) -> bool:
    """Return True when the key looks like an unfilled placeholder."""
    return not key or key.strip().endswith("...") or key.strip() in ("", "sk-...", "gsk_...", "sk-ant-...", "AIza...")


def get_llm_client():
    """Return an LLM chat-completion callable based on configured provider.

    Reads API keys and provider from *os.environ* at call time so that
    keys entered via the sidebar UI take effect without restarting the app.
    """
    # Always read fresh from env so sidebar updates are picked up immediately
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER)

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
        if _is_placeholder_key(api_key):
            raise ValueError(
                "OpenAI API key is not configured. "
                "Enter your key in the sidebar (🔑 API Configuration)."
            )
        model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
        client = OpenAI(api_key=api_key)

        def _chat(system_prompt: str, user_prompt: str, **kwargs) -> str:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=kwargs.get("temperature", 0.2),
            )
            return resp.choices[0].message.content or ""

        return _chat

    elif provider == "groq":
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if _is_placeholder_key(api_key):
            raise ValueError(
                "Groq API key is not configured. "
                "Enter your key in the sidebar (🔑 API Configuration)."
            )
        model = os.getenv("GROQ_MODEL", GROQ_MODEL)
        client = Groq(api_key=api_key)

        def _chat(system_prompt: str, user_prompt: str, **kwargs) -> str:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=kwargs.get("temperature", 0.2),
            )
            return resp.choices[0].message.content or ""

        return _chat

    elif provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY)
        if _is_placeholder_key(api_key):
            raise ValueError(
                "Anthropic API key is not configured. "
                "Enter your key in the sidebar (🔑 API Configuration)."
            )
        model = os.getenv("ANTHROPIC_MODEL", ANTHROPIC_MODEL)
        client = Anthropic(api_key=api_key)

        def _chat(system_prompt: str, user_prompt: str, **kwargs) -> str:
            resp = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=kwargs.get("temperature", 0.2),
            )
            return resp.content[0].text  # type: ignore[union-attr]

        return _chat

    elif provider == "gemini":
        from google import genai
        from google.genai import types as genai_types

        api_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)
        if _is_placeholder_key(api_key):
            raise ValueError(
                "Gemini API key is not configured. "
                "Enter your key in the sidebar (\ud83d\udd11 API Configuration)."
            )
        model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)
        client = genai.Client(api_key=api_key)

        def _chat(system_prompt: str, user_prompt: str, **kwargs) -> str:
            temperature = kwargs.get("temperature", 0.2)
            response = client.models.generate_content(
                model=model_name,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=genai_types.GenerateContentConfig(
                    temperature=temperature,
                ),
            )
            return response.text or ""

        return _chat

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
