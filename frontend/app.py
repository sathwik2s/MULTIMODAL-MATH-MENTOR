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

import threading as _threading
import streamlit as st

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Multimodal Math Mentor",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Background pre-warm: load heavy singletons once while UI renders ─────────
def _prewarm() -> None:
    """Load embedding model + ChromaDB in a background thread so the first
    'Solve' click is instant instead of waiting 5-8 s for cold initialisation."""
    try:
        from backend.rag.embeddings import _load_model
        _load_model()
        from backend.rag.ingest import get_collection
        get_collection()
    except Exception:
        pass  # non-fatal — models will still lazy-load on first use

if not st.session_state.get("_prewarmed"):
    st.session_state["_prewarmed"] = True
    _threading.Thread(target=_prewarm, daemon=True).start()

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
from frontend.components.styles import inject_custom_styles
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
        {
            "openai": "OPENAI_API_KEY",
            "groq": "GROQ_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }.get(provider, "OPENAI_API_KEY"), ""
    )
    return bool(key) and not key.strip().endswith("...")

# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

inject_custom_styles()
render_sidebar()

st.markdown("""
<div style="
    background: linear-gradient(135deg, rgba(124,58,237,0.14) 0%, rgba(91,33,182,0.07) 100%);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 16px;
    padding: 1.75rem 2rem;
    margin-bottom: 1.25rem;
">
    <h1 style="
        background: linear-gradient(135deg, #a78bfa, #7c3aed);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0 0 0.4rem 0;
        line-height: 1.2;
    ">🧮 Multimodal Math Mentor</h1>
    <p style="color:#94a3b8;font-size:0.97rem;margin:0 0 1rem 0;">
        Upload a <strong style="color:#c4b5fd;">math question</strong> via
        text&nbsp;✏️, image&nbsp;📷, or audio&nbsp;🎤 and get a verified,
        step&#8209;by&#8209;step solution powered by multi&#8209;agent AI.
    </p>
    <div style="display:flex;gap:0.6rem;flex-wrap:wrap;">
        <span style="background:rgba(124,58,237,0.18);color:#c4b5fd;font-size:0.72rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:999px;border:1px solid rgba(124,58,237,0.35);">🤖 Multi-Agent Pipeline</span>
        <span style="background:rgba(5,150,105,0.15);color:#6ee7b7;font-size:0.72rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:999px;border:1px solid rgba(5,150,105,0.3);">📚 RAG Knowledge Base</span>
        <span style="background:rgba(37,99,235,0.15);color:#93c5fd;font-size:0.72rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:999px;border:1px solid rgba(37,99,235,0.3);">👁️ LLM Vision OCR</span>
        <span style="background:rgba(217,119,6,0.14);color:#fcd34d;font-size:0.72rem;font-weight:700;padding:0.2rem 0.65rem;border-radius:999px;border:1px solid rgba(217,119,6,0.3);">🎬 Manim Visualizations</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not _api_key_ok():
    provider = _os.environ.get("LLM_PROVIDER", "openai")
    key_name = {
        "openai": "OPENAI_API_KEY (sk-...)",
        "groq": "GROQ_API_KEY (gsk_...)",
        "anthropic": "ANTHROPIC_API_KEY (sk-ant-...)",
        "gemini": "GEMINI_API_KEY (AIza...)",
    }.get(provider, "OPENAI_API_KEY")
    st.error(
        f"""**🔑 API key required — app will not solve problems without one.**

"""
        f"**Step 1:** In the **sidebar on the left**, find **🔑 API Configuration**  \n"
        f"**Step 2:** Choose your provider (currently: `{provider}`)  \n"
        f"**Step 3:** Paste your real `{key_name}` into the password field and press Enter  \n\n"
        "The key is active for this session immediately — no restart needed.  \n"
        "*For permanent setup on Render: add the key in **Render dashboard → Environment** tab.*"
    )

render_input_panel()
render_preview_panel()
render_agent_trace()
render_result_panel()
render_visualization_panel()
render_feedback_panel()
