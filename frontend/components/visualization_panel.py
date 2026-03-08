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

    if viz.success and viz.video_path:
        video_file = Path(viz.video_path)
        if video_file.exists():
            # Read as bytes — most reliable way to serve local files in Streamlit
            st.video(video_file.read_bytes())
            st.caption(f"Rendered from: {video_file.name}")
        else:
            st.warning(
                f"Video was rendered but cannot be found at `{viz.video_path}`. "
                "Try solving again.",
                icon="⚠️",
            )
    else:
        st.error(
            "**Animation rendering failed.**  \n"
            "Make sure **Manim CE** and **ffmpeg** are installed, then click "
            "**🚀 Solve Problem** again to regenerate.",
            icon="🎬",
        )
        # Show the Manim error output so the user / developer can diagnose
        error_text = "\n\n".join(filter(None, [viz.error, viz.render_stderr]))
        if error_text:
            with st.expander("🔍 Manim Error Details", expanded=True):
                st.code(error_text, language="text")

    # Always show the generated script so users can tweak / inspect it
    if viz.script_content:
        with st.expander("📜 View Manim Script", expanded=False):
            st.code(viz.script_content, language="python")

