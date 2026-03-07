"""
Multimodal Math Mentor — Streamlit UI

Run with:
    streamlit run frontend/app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Ensure project root is on sys.path so `backend.*` imports work ───────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Disable OpenTelemetry SDK (avoids Python 3.13 hang with chromadb) ────────
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

import streamlit as st

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Multimodal Math Mentor",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ───────────────────────────────────────────────────
for key, default in {
    "pipeline_result": None,
    "extracted_text": "",
    "input_confidence": 1.0,
    "input_type": "text",
    "show_agent_trace": False,
    "rag_ingested": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Import and render all UI components ──────────────────────────────────────
from frontend.components.sidebar import render_sidebar
from frontend.components.input_panel import render_input_panel
from frontend.components.preview_panel import render_preview_panel
from frontend.components.agent_trace import render_agent_trace
from frontend.components.result_panel import render_result_panel
from frontend.components.visualization_panel import render_visualization_panel
from frontend.components.feedback_panel import render_feedback_panel

# ── API key health-check banner ───────────────────────────────────────────────
import os as _os

def _api_key_ok() -> bool:
    provider = _os.environ.get("LLM_PROVIDER", "openai")
    key = _os.environ.get(
        {"openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider, "OPENAI_API_KEY"), ""
    )
    return bool(key) and not key.strip().endswith("...")

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

render_sidebar()

st.header("🧮 Multimodal Math Mentor")
st.markdown("Upload a **math question** via text, image, or audio and get a verified, step-by-step solution.")

if not _api_key_ok():
    st.warning(
        "**API key not configured.** "
        "Open the sidebar → 🔑 API Configuration and enter your real API key to enable solving.",
        icon="⚠️",
    )

render_input_panel()
render_preview_panel()
render_agent_trace()
render_result_panel()
render_visualization_panel()
render_feedback_panel()
