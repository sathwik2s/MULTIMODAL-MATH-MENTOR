"""
Frontend — Preview Panel Component

Shows extracted text with editable area and confidence indicator.
"""

from __future__ import annotations

import os

import streamlit as st

from backend.utils.confidence import classify_confidence


def _api_key_ready() -> bool:
    """Return True when a non-placeholder API key is present in the environment."""
    provider = os.environ.get("LLM_PROVIDER", "openai")
    env_map = {
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    key = os.environ.get(env_map.get(provider, "OPENAI_API_KEY"), "")
    return bool(key) and not key.strip().endswith("...")


def render_preview_panel() -> None:
    """Render the extracted text preview, edit area, and Solve button."""
    if not st.session_state.get("extracted_text"):
        return

    st.subheader("2️⃣ Preview & Edit")

    col_preview, col_meta = st.columns([3, 1])
    with col_preview:
        edited_text = st.text_area(
            "Extracted / entered text (editable)",
            value=st.session_state.extracted_text,
            height=100,
            key="editable_text",
        )
    with col_meta:
        conf = st.session_state.input_confidence
        label = classify_confidence(conf)
        colour = "🟢" if conf >= 0.75 else "🟡" if conf >= 0.5 else "🔴"
        st.metric("Input Confidence", f"{conf:.0%}")
        st.caption(f"{colour} {label}")

    # ── SOLVE BUTTON ─────────────────────────────────────────────────────
    if not _api_key_ready():
        st.error(
            "**API key required.** "
            "Open the **sidebar → 🔑 API Configuration**, choose your provider, "
            "and paste your real API key before solving.",
            icon="🔑",
        )
        st.button("🚀 Solve Problem", type="primary", use_container_width=True, disabled=True)
        return

    if st.button("🚀 Solve Problem", type="primary", use_container_width=True):
        if not (edited_text or "").strip():
            st.warning("Please enter or extract a math question first.")
            return
        with st.spinner("Running multi-agent pipeline…"):
            try:
                from backend.main import run_pipeline  # lazy import — avoids circular import at module load
                pipeline_result = run_pipeline(
                    text=edited_text or "",
                    input_type=st.session_state.input_type,
                    input_confidence=st.session_state.input_confidence,
                )
                st.session_state.pipeline_result = pipeline_result
            except ValueError as exc:
                # API key or configuration error — show clear guidance
                st.error(
                    f"**🔑 Configuration error:** {exc}\n\n"
                    "Open the **sidebar → 🔑 API Configuration**, choose your provider, "
                    "and paste your real API key.",
                    icon="🔑",
                )
            except Exception as exc:
                st.error(
                    f"**Pipeline error:** {exc}\n\n"
                    "If this is an API authentication error, check your key in the sidebar.",
                    icon="❌",
                )
