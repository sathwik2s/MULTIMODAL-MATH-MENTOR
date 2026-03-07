"""
Frontend — Visualization Panel Component

Displays the Manim-generated animation video and the script source.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_visualization_panel() -> None:
    """Render the Manim animation video and script."""
    pr = st.session_state.get("pipeline_result")
    if pr is None or pr.visualization is None:
        return

    viz = pr.visualization

    st.divider()
    st.subheader("🎬 Animated Explanation")

    if viz.success and viz.video_path and Path(viz.video_path).exists():
        st.video(viz.video_path)
        st.caption(f"Rendered from: {Path(viz.script_path).name}")
    elif viz.success and viz.video_path:
        st.warning("Video was rendered but the file is not accessible.", icon="⚠️")
    else:
        st.info(
            "Animation could not be generated for this problem. "
            "This is normal for some problem types.",
            icon="ℹ️",
        )
        if viz.error:
            with st.expander("Details"):
                st.code(viz.error, language="text")

    # Show the Manim script source
    if viz.script_content:
        with st.expander("📜 View Manim Script", expanded=False):
            st.code(viz.script_content, language="python")
