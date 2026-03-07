"""
Frontend — Global CSS Theme Injection

Call inject_custom_styles() once at the top of app.py.
Provides the full dark professional color system for Math Mentor.
"""
from __future__ import annotations
import streamlit as st


def inject_custom_styles() -> None:
    st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════════
   MULTIMODAL MATH MENTOR — Professional Dark UI Theme
   ═══════════════════════════════════════════════════════════════ */

/* ── Hide Streamlit chrome ──────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Root background ────────────────────────────────────────── */
.stApp { background-color: #0f1117 !important; }
.block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 1140px !important;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12152b 0%, #1a1d2e 60%, #131525 100%) !important;
    border-right: 1px solid #2a2d4a !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown { color: #cbd5e1 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #f1f5f9 !important; }

/* ── Typography ──────────────────────────────────────────────── */
p, li { color: #94a3b8; }
h2 { color: #e2e8f0 !important; font-weight: 700 !important; }
h3 {
    color: #c4b5fd !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding-bottom: 0.4rem !important;
    border-bottom: 1px solid #2a2d4a;
    margin-bottom: 0.75rem !important;
}

/* ── Divider ─────────────────────────────────────────────────── */
hr { border-color: #2a2d4a !important; margin: 1rem 0 !important; }

/* ════════════════════════════════════════════════════════════════
   BUTTONS — Full Color System
   ════════════════════════════════════════════════════════════════ */

/* Base for ALL buttons */
.stButton > button,
div[data-testid="stButton"] > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
    letter-spacing: 0.3px !important;
    border: 1px solid transparent !important;
    cursor: pointer !important;
}

/* ── PRIMARY (Solve button) — Purple gradient ──────────────── */
button[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #7c3aed 0%, #5b21b6 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 15px rgba(124,58,237,0.45) !important;
    border-color: transparent !important;
}
button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%) !important;
    box-shadow: 0 6px 22px rgba(124,58,237,0.65) !important;
    transform: translateY(-2px) !important;
}
button[data-testid="baseButton-primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 8px rgba(124,58,237,0.4) !important;
}
button[data-testid="baseButton-primary"]:disabled {
    background: #2d2d4a !important;
    color: #4a4a6a !important;
    box-shadow: none !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* ── SECONDARY (default) — Dark indigo ─────────────────────── */
button[data-testid="baseButton-secondary"] {
    background: #1e2130 !important;
    color: #a5b4fc !important;
    border: 1px solid #3730a3 !important;
}
button[data-testid="baseButton-secondary"]:hover {
    background: #2d2463 !important;
    color: #c4b5fd !important;
    border-color: #7c3aed !important;
    transform: translateY(-1px) !important;
}

/* ── GREEN — Correct feedback ───────────────────────────────── */
.btn-success .stButton > button,
.btn-success div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #059669, #047857) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 12px rgba(5,150,105,0.4) !important;
}
.btn-success .stButton > button:hover,
.btn-success div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #10b981, #059669) !important;
    box-shadow: 0 6px 18px rgba(5,150,105,0.55) !important;
    transform: translateY(-2px) !important;
}

/* ── RED — Incorrect feedback ───────────────────────────────── */
.btn-danger .stButton > button,
.btn-danger div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 12px rgba(220,38,38,0.4) !important;
}
.btn-danger .stButton > button:hover,
.btn-danger div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #ef4444, #dc2626) !important;
    box-shadow: 0 6px 18px rgba(220,38,38,0.55) !important;
    transform: translateY(-2px) !important;
}

/* ── BLUE — Recheck / Submit / Ingest ──────────────────────── */
.btn-info .stButton > button,
.btn-info div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 12px rgba(37,99,235,0.4) !important;
}
.btn-info .stButton > button:hover,
.btn-info div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 6px 18px rgba(37,99,235,0.55) !important;
    transform: translateY(-2px) !important;
}

/* ── AMBER — OCR / Transcribe ───────────────────────────────── */
.btn-warning .stButton > button,
.btn-warning div[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #d97706, #b45309) !important;
    color: white !important;
    border-color: transparent !important;
    box-shadow: 0 4px 12px rgba(217,119,6,0.4) !important;
}
.btn-warning .stButton > button:hover,
.btn-warning div[data-testid="stButton"] > button:hover {
    background: linear-gradient(135deg, #f59e0b, #d97706) !important;
    box-shadow: 0 6px 18px rgba(217,119,6,0.55) !important;
    transform: translateY(-2px) !important;
}

/* ════════════════════════════════════════════════════════════════
   TABS
   ════════════════════════════════════════════════════════════════ */
[data-baseweb="tab-list"] {
    background: #1a1d2e !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid #2a2d4a !important;
}
[data-baseweb="tab"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: #94a3b8 !important;
    background: transparent !important;
    transition: all 0.2s !important;
    border: none !important;
}
[data-baseweb="tab"]:hover { color: #a78bfa !important; background: #252840 !important; }
[aria-selected="true"][data-baseweb="tab"] {
    background: linear-gradient(135deg, #7c3aed, #5b21b6) !important;
    color: white !important;
    box-shadow: 0 2px 10px rgba(124,58,237,0.4) !important;
}

/* ════════════════════════════════════════════════════════════════
   METRICS
   ════════════════════════════════════════════════════════════════ */
[data-testid="stMetric"] {
    background: #1a1d2e !important;
    border: 1px solid #2a2d4a !important;
    border-radius: 12px !important;
    padding: 0.85rem 1rem !important;
}
[data-testid="stMetricValue"] {
    color: #a78bfa !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ════════════════════════════════════════════════════════════════
   ALERTS
   ════════════════════════════════════════════════════════════════ */
div[data-baseweb="notification"],
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-size: 0.9rem !important;
}
.stSuccess, [data-testid="stAlert"][kind="success"] {
    background: rgba(5,150,105,0.12) !important;
    border: 1px solid rgba(5,150,105,0.4) !important;
    border-left: 4px solid #059669 !important;
}
.stWarning, [data-testid="stAlert"][kind="warning"] {
    background: rgba(217,119,6,0.12) !important;
    border: 1px solid rgba(217,119,6,0.4) !important;
    border-left: 4px solid #d97706 !important;
}
.stError, [data-testid="stAlert"][kind="error"] {
    background: rgba(220,38,38,0.12) !important;
    border: 1px solid rgba(220,38,38,0.4) !important;
    border-left: 4px solid #dc2626 !important;
}
.stInfo, [data-testid="stAlert"][kind="info"] {
    background: rgba(37,99,235,0.12) !important;
    border: 1px solid rgba(37,99,235,0.4) !important;
    border-left: 4px solid #2563eb !important;
}

/* ════════════════════════════════════════════════════════════════
   INPUTS & TEXTAREAS
   ════════════════════════════════════════════════════════════════ */
.stTextArea textarea,
.stTextInput input,
.stTextArea > div > div > textarea,
.stTextInput > div > div > input {
    background: #1a1d2e !important;
    border: 1px solid #2a2d4a !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.92rem !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextArea textarea:focus,
.stTextInput input:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.2) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #1a1d2e !important;
    border: 1px solid #2a2d4a !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
}

/* ════════════════════════════════════════════════════════════════
   EXPANDERS
   ════════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: #1a1d2e !important;
    border: 1px solid #2a2d4a !important;
    border-radius: 12px !important;
    margin-bottom: 0.75rem !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] > details > summary {
    font-weight: 600 !important;
    color: #c4b5fd !important;
    padding: 0.85rem 1rem !important;
}
[data-testid="stExpander"] > details > summary:hover { color: #a78bfa !important; }
[data-testid="stExpander"] > details[open] > summary {
    border-bottom: 1px solid #2a2d4a;
}

/* ════════════════════════════════════════════════════════════════
   FILE UPLOADER
   ════════════════════════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
    background: #1a1d2e !important;
    border: 2px dashed #3730a3 !important;
    border-radius: 12px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #7c3aed !important; }

/* ════════════════════════════════════════════════════════════════
   CODE / CAPTIONS / MISC
   ════════════════════════════════════════════════════════════════ */
code, .stCodeBlock pre {
    background: #0d1117 !important;
    border: 1px solid #2a2d4a !important;
    border-radius: 8px !important;
    color: #a5f3fc !important;
    font-size: 0.85rem !important;
}
.stCaption, [data-testid="stCaptionContainer"] {
    color: #64748b !important;
    font-size: 0.78rem !important;
}
[data-testid="stToggle"] span[aria-checked="true"] {
    background: #7c3aed !important;
}
.stSpinner > div { border-top-color: #7c3aed !important; }

/* ── Scrollbar ─────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #3730a3; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #7c3aed; }

/* ════════════════════════════════════════════════════════════════
   CUSTOM COMPONENT CARDS
   ════════════════════════════════════════════════════════════════ */

/* Answer card (used in result_panel) */
.answer-card {
    background: linear-gradient(135deg, rgba(5,150,105,0.15), rgba(4,120,87,0.07));
    border: 1px solid rgba(5,150,105,0.4);
    border-left: 4px solid #059669;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.5rem 0 1rem 0;
}
.answer-label {
    font-size: 0.75rem;
    font-weight: 700;
    color: #6ee7b7;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.5rem;
}
.answer-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #ecfdf5;
    font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    word-break: break-word;
}

/* Step card (used in result_panel steps) */
.step-card {
    background: #1a1d2e;
    border: 1px solid #2a2d4a;
    border-left: 3px solid #7c3aed;
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 0.6rem;
}
.step-num {
    font-size: 0.72rem;
    font-weight: 700;
    color: #7c3aed;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.25rem;
}
.step-desc { color: #e2e8f0; font-size: 0.9rem; margin: 0; }
.step-formula {
    background: #0d1117;
    color: #a5f3fc;
    font-family: monospace;
    font-size: 0.83rem;
    padding: 0.3rem 0.6rem;
    border-radius: 6px;
    margin-top: 0.35rem;
    display: inline-block;
}
.step-result { color: #6ee7b7; font-size: 0.82rem; margin-top: 0.3rem; }

/* Feedback section label */
.feedback-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)
