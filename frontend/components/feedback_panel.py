"""
Frontend — Feedback Panel Component

Provides correct / incorrect / re-check buttons and a correction form.
"""

from __future__ import annotations

import streamlit as st

from backend.memory.memory_store import update_feedback
from backend.hitl.human_review import approve_review, correct_review, reject_review
from backend.main import run_pipeline


def render_feedback_panel() -> None:
    """Render the user-feedback section."""
    pr = st.session_state.get("pipeline_result")
    if pr is None:
        return

    st.subheader("4️⃣ Feedback")
    col_fb1, col_fb2, col_fb3 = st.columns(3)

    with col_fb1:
        if st.button("✅ Correct", use_container_width=True, key="fb_correct"):
            if pr.memory_record_id:
                update_feedback(pr.memory_record_id, "correct")
                st.success("Thanks! Marked as correct.")
            if pr.review_request:
                approve_review(pr.review_request.id)

    with col_fb2:
        if st.button("❌ Incorrect", use_container_width=True, key="fb_incorrect"):
            if pr.memory_record_id:
                update_feedback(pr.memory_record_id, "incorrect")
                st.warning("Marked as incorrect. Please provide the correct answer below.")
            if pr.review_request:
                reject_review(pr.review_request.id)

    with col_fb3:
        if st.button("🔄 Re-check", use_container_width=True, key="fb_recheck"):
            with st.spinner("Re-running pipeline…"):
                pipeline_result = run_pipeline(
                    text=st.session_state.extracted_text,
                    input_type=st.session_state.input_type,
                    input_confidence=st.session_state.input_confidence,
                )
                st.session_state.pipeline_result = pipeline_result
                st.rerun()

    # Correction box
    with st.expander("Provide correction / comment"):
        correction_text = st.text_area("Correct answer or comment", key="correction_box")
        if st.button("Submit Correction", key="submit_correction"):
            if pr.memory_record_id and correction_text:
                update_feedback(pr.memory_record_id, "corrected", correction_text)
                if pr.review_request:
                    correct_review(pr.review_request.id, corrected_answer=correction_text)
                st.success("Correction saved. The system will learn from this.")

    # Timing
    st.caption(f"⏱️ Pipeline completed in {pr.elapsed_seconds:.1f}s")
