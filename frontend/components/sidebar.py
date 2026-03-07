"""
Frontend — Sidebar Component

Includes API key configuration, knowledge-base ingestion and recent problem history.
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from backend.rag.ingest import ingest_directory
from backend.memory.memory_store import get_recent_records

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

_PLACEHOLDER_PREFIXES = ("sk-...", "gsk_...", "sk-ant-...", "your_mathpix_app_id", "your_mathpix_app_key")


def _is_placeholder(key: str) -> bool:
    return not key or key.strip() in _PLACEHOLDER_PREFIXES or key.strip().endswith("...")


def _persist_key_to_env(env_var: str, value: str) -> bool:
    """Update or insert a key=value line in the .env file. Returns True on success."""
    # Sanitise: reject values containing newlines to prevent .env injection
    if "\n" in value or "\r" in value:
        logger.warning("Rejected .env write for %s: value contains newline", env_var)
        return False
    try:
        lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{env_var}="):
                lines[i] = f"{env_var}={value}"
                updated = True
                break
        if not updated:
            lines.append(f"{env_var}={value}")
        _ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return True
    except Exception as exc:
        logger.warning("Could not persist %s to .env: %s", env_var, exc)
        return False  # non-fatal — key is still set in os.environ for this session


def render_sidebar() -> None:
    """Render the sidebar with API config, KB ingestion and history."""
    with st.sidebar:
        st.title("🧮 Math Mentor")
        st.caption("AI-powered JEE Math Tutor")
        st.divider()

        # ── API Key Configuration ────────────────────────────────────────────
        st.subheader("🔑 API Configuration")

        provider_options = ["openai", "groq", "anthropic", "gemini"]
        current_provider = os.environ.get("LLM_PROVIDER", "openai")
        provider = st.selectbox(
            "LLM Provider",
            provider_options,
            index=provider_options.index(current_provider) if current_provider in provider_options else 0,
        )
        if provider != current_provider:
            os.environ["LLM_PROVIDER"] = provider
            _persist_key_to_env("LLM_PROVIDER", provider)

        if provider == "openai":
            key_env = "OPENAI_API_KEY"
            key_hint = "sk-..."
            key_label = "OpenAI API Key"
        elif provider == "groq":
            key_env = "GROQ_API_KEY"
            key_hint = "gsk_..."
            key_label = "Groq API Key"
        elif provider == "anthropic":
            key_env = "ANTHROPIC_API_KEY"
            key_hint = "sk-ant-..."
            key_label = "Anthropic API Key"
        else:  # gemini
            key_env = "GEMINI_API_KEY"
            key_hint = "AIza..."
            key_label = "Google Gemini API Key"

        current_key = os.environ.get(key_env, "")
        new_key = st.text_input(
            key_label,
            value="" if _is_placeholder(current_key) else current_key,
            type="password",
            placeholder=key_hint,
            help="Enter your real API key. It will be saved to .env for future sessions.",
        )
        if new_key and not _is_placeholder(new_key):
            clean_key = new_key.strip()
            os.environ[key_env] = clean_key
            _persist_key_to_env(key_env, clean_key)
            st.success("API key saved ✓", icon="✅")
        elif _is_placeholder(os.environ.get(key_env, "")):
            st.warning("No valid API key — set one above before solving.", icon="⚠️")

        st.divider()

        # ── Mathpix OCR Credentials ──────────────────────────────────────────
        with st.expander("📷 Mathpix OCR (Image→Math)", expanded=False):
            st.caption(
                "Mathpix is the best OCR for math equations. "
                "Get free credentials at [mathpix.com](https://mathpix.com)."
            )
            current_app_id = os.environ.get("MATHPIX_APP_ID", "")
            new_app_id = st.text_input(
                "Mathpix App ID",
                value="" if _is_placeholder(current_app_id) else current_app_id,
                placeholder="your_mathpix_app_id",
                help="From your Mathpix dashboard → Account → API Keys",
            )
            current_app_key = os.environ.get("MATHPIX_APP_KEY", "")
            new_app_key = st.text_input(
                "Mathpix App Key",
                value="" if _is_placeholder(current_app_key) else current_app_key,
                type="password",
                placeholder="your_mathpix_app_key",
                help="From your Mathpix dashboard → Account → API Keys",
            )
            if new_app_id and not _is_placeholder(new_app_id):
                os.environ["MATHPIX_APP_ID"] = new_app_id.strip()
                _persist_key_to_env("MATHPIX_APP_ID", new_app_id.strip())
            if new_app_key and not _is_placeholder(new_app_key):
                os.environ["MATHPIX_APP_KEY"] = new_app_key.strip()
                _persist_key_to_env("MATHPIX_APP_KEY", new_app_key.strip())
            if new_app_id and new_app_key and not _is_placeholder(new_app_id) and not _is_placeholder(new_app_key):
                st.success("Mathpix credentials saved ✓", icon="✅")
            elif os.environ.get("MATHPIX_APP_ID"):
                st.success("Mathpix active — best math OCR.", icon="✅")
            else:
                # Show which fallback engine will be used
                _provider = os.environ.get("LLM_PROVIDER", "openai").lower()
                _key_map = {
                    "openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY",
                    "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY",
                }
                _has_llm_key = not _is_placeholder(os.environ.get(_key_map.get(_provider, ""), ""))
                _vision_models = {
                    "openai": "gpt-4o", "groq": "llama-3.2-11b-vision",
                    "anthropic": "claude-3-haiku", "gemini": "gemini-1.5-flash",
                }
                if _has_llm_key:
                    st.info(
                        f"No Mathpix keys — **{_provider.title()} Vision OCR** "
                        f"(`{_vision_models.get(_provider, '')}`) will be used. "
                        "Good quality for JEE math.",
                        icon="✨",
                    )
                else:
                    st.warning(
                        "No Mathpix or LLM API key — **EasyOCR** (offline, basic) will be used. "
                        "Set an LLM key above for much better equation recognition.",
                        icon="⚠️",
                    )

        st.divider()

        # RAG Knowledge Base ingestion
        st.subheader("📚 Knowledge Base")
        if st.button("Ingest Knowledge Base", use_container_width=True):
            with st.spinner("Ingesting documents…"):
                try:
                    n = ingest_directory()
                    st.success(f"Ingested {n} new chunks.")
                    st.session_state.rag_ingested = True
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")

        st.divider()

        # Recent history
        st.subheader("📝 Recent Problems")
        try:
            recent = get_recent_records(limit=5)
            for rec in recent:
                with st.expander(f"#{rec.id} — {rec.topic}", expanded=False):
                    st.write(rec.raw_input[:120])
                    st.caption(f"Confidence: {rec.verifier_confidence:.2f}")
        except Exception:
            st.caption("No history yet.")

        st.divider()
        st.subheader("⚙️ Settings")
        st.session_state.show_agent_trace = st.toggle(
            "Show Agent Trace", value=st.session_state.get("show_agent_trace", False)
        )
