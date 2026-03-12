"""
Frontend — Agent Trace Component

Shows internal agent outputs (parser, router, solver, verifier) in expandable sections.
"""

from __future__ import annotations

import streamlit as st


def render_agent_trace() -> None:
    """Render expandable agent trace panels (only when toggled on)."""
    if not st.session_state.get("show_agent_trace", False):
        return

    pr = st.session_state.get("pipeline_result")
    if pr is None:
        return

    st.subheader("🔍 Agent Trace")

    with st.expander("Parser Result", expanded=False):
        if pr.parsed:
            st.json(pr.parsed.to_dict())

    with st.expander("Router Decision", expanded=False):
        if pr.routing:
            st.json(pr.routing.to_dict())

    with st.expander("Solver Output", expanded=False):
        if pr.solver_result:
            st.json(pr.solver_result.to_dict())

    with st.expander("Verifier Result", expanded=False):
        if pr.verification:
            st.json(pr.verification.to_dict())
