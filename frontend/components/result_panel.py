"""
Frontend — Result Panel Component

Displays the solution, RAG context, similar past problems, and confidence.
"""

from __future__ import annotations

import streamlit as st

from backend.utils.confidence import classify_confidence


def _confidence_badge(score: float) -> None:
    colour = "🟢" if score >= 0.75 else "🟡" if score >= 0.5 else "🔴"
    label = classify_confidence(score)
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Solution Confidence", f"{score:.0%}")
    with col2:
        st.caption(f"{colour} {label}")


def render_result_panel() -> None:
    """Render solution results, RAG sources, similar problems, and confidence."""
    pr = st.session_state.get("pipeline_result")
    if pr is None:
        return

    st.divider()
    st.subheader("3️⃣ Solution")

    # ── FINAL ANSWER — always show prominently first ──────────────────────
    final_answer = ""
    if pr.explanation and pr.explanation.final_answer:
        final_answer = pr.explanation.final_answer
    elif pr.solver_result and pr.solver_result.answer:
        final_answer = pr.solver_result.answer

    if final_answer:
        st.success(f"### ✅ Final Answer\n\n**{final_answer}**")
    else:
        st.warning("No answer was produced. Check the agent trace for details.")

    # ── CONFIDENCE ────────────────────────────────────────────────────────
    if pr.verification:
        vc = pr.verification.confidence
        _confidence_badge(vc)
        if pr.verification.issues:
            # Filter out raw API error noise — show clean messages
            clean_issues = [
                i for i in pr.verification.issues
                if not any(k in i for k in ("Error code:", "status_code", "traceback"))
            ]
            if clean_issues:
                st.warning("⚠️ Verifier notes:\n" + "\n".join(f"- {i}" for i in clean_issues))

    # ── STEP-BY-STEP EXPLANATION ─────────────────────────────────────────
    if pr.explanation and pr.explanation.steps:
        with st.expander("📋 Step-by-Step Explanation", expanded=True):
            # Title
            if pr.explanation.title:
                st.markdown(f"#### {pr.explanation.title}")

            for step in pr.explanation.steps:
                n = step.get("step_number", "?")
                desc = step.get("description", "")
                formula = step.get("formula_used", "")
                result = step.get("result", "")
                st.markdown(f"**Step {n}:** {desc}")
                if formula:
                    st.code(formula, language="text")
                if result:
                    st.caption(f"→ {result}")

            # Key concepts
            if pr.explanation.key_concepts:
                st.markdown("**Key Concepts:** " + " · ".join(f"`{c}`" for c in pr.explanation.key_concepts))

            # Common mistakes
            if pr.explanation.common_mistakes:
                with st.expander("⚠️ Common Mistakes to Avoid"):
                    for m in pr.explanation.common_mistakes:
                        st.markdown(f"- {m}")

            # Tips (only show if it doesn't look like an error message)
            if pr.explanation.tips and "error" not in pr.explanation.tips.lower()[:30]:
                st.info(f"💡 **Tip:** {pr.explanation.tips}")

    elif pr.solver_result and pr.solver_result.computation_steps:
        # Fallback: show raw solver steps when explanation not available
        with st.expander("📋 Computation Steps", expanded=True):
            for i, step in enumerate(pr.solver_result.computation_steps, 1):
                st.markdown(f"**Step {i}:** {step}")

    # ── RAG CONTEXT ───────────────────────────────────────────────────────
    if pr.solver_result and pr.solver_result.rag_sources:
        with st.expander("📚 Knowledge Sources Used", expanded=False):
            st.text(pr.solver_result.rag_context)
            st.caption("Sources: " + ", ".join(sorted(set(pr.solver_result.rag_sources))))
    
    # ── SIMILAR PAST PROBLEMS ────────────────────────────────────────────
    if pr.similar_problems:
        with st.expander("🧠 Similar Past Problems", expanded=False):
            for sp_item in pr.similar_problems:
                st.markdown(f"**Similarity:** {sp_item.similarity:.0%} — *{sp_item.topic}*")
                st.text(sp_item.problem_text[:200])
                st.divider()

    # ── HITL NOTICE ───────────────────────────────────────────────────────
    if pr.needs_human_review:
        st.info(
            "⚠️ **Human Review Recommended** — "
            "Confidence is below the threshold. Please review the steps above and use the feedback panel below.",
            icon="🔍",
        )
