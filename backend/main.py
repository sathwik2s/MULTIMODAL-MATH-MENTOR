"""
Multimodal Math Mentor — Main Orchestration Pipeline

Ties all agents and modules together into a single solve() pipeline
that the UI calls.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

from backend.agents.parser_agent import parse_problem, ParsedProblem
from backend.agents.router_agent import route_problem, RoutingDecision
from backend.agents.solver_agent import solve as solver_solve, SolverResult
from backend.agents.verifier_agent import verify, VerificationResult
from backend.agents.explainer_agent import explain, Explanation
from backend.visualization.visualization_agent import (
    generate_visualization,
    VisualizationResult,
)
from backend.hitl.human_review import (
    create_review,
    ReviewTrigger,
    ReviewRequest,
)
from backend.memory.memory_store import store_record, MemoryRecord
from backend.memory.similarity_search import index_record, find_similar
from backend.utils.confidence import ConfidenceResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """Full result of the orchestration pipeline."""

    # Input stage
    input_type: str = "text"
    raw_input: str = ""
    input_confidence: float = 1.0

    # Parsing
    parsed: Optional[ParsedProblem] = None

    # Routing
    routing: Optional[RoutingDecision] = None

    # Solving
    solver_result: Optional[SolverResult] = None

    # Verification
    verification: Optional[VerificationResult] = None

    # Explanation
    explanation: Optional[Explanation] = None

    # Visualization
    visualization: Optional[VisualizationResult] = None

    # HITL
    review_request: Optional[ReviewRequest] = None
    needs_human_review: bool = False

    # Memory
    memory_record_id: Optional[int] = None

    # Similar past problems
    similar_problems: list = field(default_factory=list)

    # Timing
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "input_type": self.input_type,
            "raw_input": self.raw_input,
            "input_confidence": self.input_confidence,
            "needs_human_review": self.needs_human_review,
            "memory_record_id": self.memory_record_id,
            "elapsed_seconds": self.elapsed_seconds,
        }
        if self.parsed:
            d["parsed"] = self.parsed.to_dict()
        if self.routing:
            d["routing"] = self.routing.to_dict()
        if self.solver_result:
            d["solver_result"] = self.solver_result.to_dict()
        if self.verification:
            d["verification"] = self.verification.to_dict()
        if self.explanation:
            d["explanation"] = self.explanation.to_dict()
        return d


def run_pipeline(
    text: str,
    input_type: str = "text",
    input_confidence: float = 1.0,
) -> PipelineResult:
    """Execute the full multi-agent pipeline.

    Parameters
    ----------
    text : The (possibly pre-processed) question text.
    input_type : "text", "image", or "audio".
    input_confidence : Confidence from OCR / ASR pre-processing.
    """
    t0 = time.time()
    result = PipelineResult(
        input_type=input_type,
        raw_input=text,
        input_confidence=input_confidence,
    )

    # ── 0. Check for similar past problems ──────────────────────────────
    try:
        result.similar_problems = find_similar(text, top_k=3)
    except Exception as exc:
        logger.warning("Similarity search failed: %s", exc)

    # ── 1. Parse ────────────────────────────────────────────────────────
    parsed = parse_problem(text)
    result.parsed = parsed

    if parsed.needs_clarification:
        result.needs_human_review = True
        result.review_request = create_review(
            trigger=ReviewTrigger.PARSER_AMBIGUITY,
            original_text=text,
            suggested_text=parsed.problem_text,
            metadata={"clarification_reason": parsed.clarification_reason},
        )
        # Still continue solving with best-effort parsed text

    # ── 2. Route ────────────────────────────────────────────────────────
    routing = route_problem(parsed)
    result.routing = routing

    # ── 3. Solve ────────────────────────────────────────────────────────
    solver_result = solver_solve(parsed, routing)
    result.solver_result = solver_result

    # ── 4. Verify ───────────────────────────────────────────────────────
    verification = verify(parsed, solver_result)
    result.verification = verification

    if verification.needs_human_review:
        result.needs_human_review = True
        if not result.review_request:
            result.review_request = create_review(
                trigger=ReviewTrigger.VERIFIER_UNCERTAIN,
                original_text=text,
                answer=solver_result.answer,
                metadata={"issues": verification.issues},
            )

    # ── 5. Explain ──────────────────────────────────────────────────────
    explanation = explain(parsed, solver_result, verification)
    result.explanation = explanation

    # ── 6. Visualize (best-effort — does not block the pipeline) ─────
    try:
        viz = generate_visualization(parsed, solver_result, explanation)
        result.visualization = viz
        if viz.success:
            logger.info("Visualization generated: %s", viz.video_path)
        else:
            logger.warning("Visualization skipped: %s", viz.error)
    except Exception as exc:
        logger.warning("Visualization failed (non-fatal): %s", exc)

    # ── 7. Store to memory ──────────────────────────────────────────────
    try:
        record = MemoryRecord(
            input_type=input_type,
            raw_input=text,
            parsed_problem=json.dumps(parsed.to_dict()),
            topic=parsed.topic,
            retrieved_context=solver_result.rag_context,
            solution=solver_result.answer,
            explanation=explanation.to_markdown(),
            verifier_confidence=verification.confidence,
        )
        record_id = store_record(record)
        result.memory_record_id = record_id

        # Update review request with memory id
        if result.review_request:
            result.review_request.memory_record_id = record_id

        # Index for similarity search
        record.id = record_id
        index_record(record)
    except Exception as exc:
        logger.error("Memory storage failed: %s", exc)

    result.elapsed_seconds = round(time.time() - t0, 2)
    logger.info("Pipeline completed in %.2fs", result.elapsed_seconds)
    return result
