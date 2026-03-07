"""
Multimodal Math Mentor — Verifier Agent

Validates the solver's answer for mathematical correctness, domain constraints,
and edge cases. Outputs a confidence assessment and any issues found.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List

from backend.config import get_llm_client, VERIFIER_CONFIDENCE_THRESHOLD
from backend.agents.parser_agent import ParsedProblem
from backend.agents.solver_agent import SolverResult
from backend.tools.python_executor import execute_python
from backend.utils.json_utils import robust_json_loads
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a meticulous math verifier for JEE-level problems.

Given:
1. The original parsed problem.
2. The solver's answer, steps, and tool outputs.

Your job:
- CHECK the answer for mathematical correctness.
- VERIFY domain constraints (e.g. x > 0, denominators ≠ 0).
- DETECT edge cases (division by zero, negative square roots, etc.).
- If possible, verify by substitution or an alternative method.
- Assign a confidence score (0.0–1.0).

IMPORTANT: You MUST respond with ONLY valid JSON and nothing else.
No explanations before or after the JSON. No markdown fences.

Return this exact JSON structure:
{
  "is_correct": true,
  "confidence": 0.9,
  "issues": [],
  "verification_method": "Verified by substitution",
  "alternative_answer": "",
  "verification_code": ""
}

Field rules:
- "is_correct": must be true, false, or "uncertain"
- "confidence": number from 0.0 to 1.0
- "issues": array of strings (empty array if no issues)
- "verification_method": short string describing how you verified
- "alternative_answer": string (empty if same answer)
- "verification_code": optional Python code string (empty if none)
"""


@dataclass
class VerificationResult:
    """Output of the verifier agent."""

    is_correct: bool | str = "uncertain"
    confidence: float = 0.5
    issues: List[str] = field(default_factory=list)
    verification_method: str = ""
    alternative_answer: str = ""
    needs_human_review: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def verify(parsed: ParsedProblem, solver_result: SolverResult) -> VerificationResult:
    """Verify the solver's answer using LLM + optional code execution."""
    user_payload = json.dumps(
        {
            "problem": parsed.to_dict(),
            "answer": solver_result.answer,
            "latex_answer": solver_result.latex_answer,
            "computation_steps": solver_result.computation_steps,
            "tool_outputs": {k: str(v) for k, v in solver_result.tool_outputs.items()},
            "solver_confidence": solver_result.confidence,
        },
        indent=2,
    )

    try:
        llm = get_llm_client()
        response = llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_payload,
            temperature=0.1,
        )

        data = _parse_verifier_response(response)

        # Run verification code if provided
        code = data.get("verification_code", "")
        if code:
            exec_result = execute_python(code)
            if exec_result["success"]:
                logger.info("Verification code output: %s", exec_result["output"])

        is_correct = data.get("is_correct", "uncertain")
        confidence = float(data.get("confidence", 0.5))
        needs_review = confidence < VERIFIER_CONFIDENCE_THRESHOLD or is_correct == "uncertain"

        result = VerificationResult(
            is_correct=is_correct,
            confidence=confidence,
            issues=data.get("issues", []),
            verification_method=data.get("verification_method", ""),
            alternative_answer=data.get("alternative_answer", ""),
            needs_human_review=needs_review,
        )

        logger.info(
            "Verification: correct=%s, conf=%.2f, issues=%d, needs_review=%s",
            result.is_correct, result.confidence, len(result.issues), result.needs_human_review,
        )
        return result

    except Exception as exc:
        logger.error("Verifier agent error: %s", exc)
        return VerificationResult(
            is_correct="uncertain",
            confidence=0.3,
            issues=[f"Verification failed: {exc}"],
            needs_human_review=True,
        )


def _parse_verifier_response(response: str) -> dict:
    """Parse verifier LLM output, with fallback heuristics for non-JSON."""
    # Try structured JSON first
    try:
        return robust_json_loads(response)
    except ValueError:
        pass

    # Fallback: extract structured info from free-text response
    logger.warning("Verifier returned non-JSON — extracting heuristically.")
    text = response.lower()

    # Heuristic: detect correctness
    is_correct: bool | str = "uncertain"
    if any(w in text for w in ["is correct", "the answer is correct", "verified", "confirms"]):
        is_correct = True
    elif any(w in text for w in ["incorrect", "is wrong", "does not hold", "error in"]):
        is_correct = False

    # Heuristic: estimate confidence from tone
    confidence = 0.65  # default for free-text
    if is_correct is True:
        confidence = 0.80
    elif is_correct is False:
        confidence = 0.60

    return {
        "is_correct": is_correct,
        "confidence": confidence,
        "issues": [],
        "verification_method": "LLM free-text analysis (JSON parse fallback)",
        "alternative_answer": "",
        "verification_code": "",
    }
