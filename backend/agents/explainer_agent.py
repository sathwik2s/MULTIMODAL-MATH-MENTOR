"""
Multimodal Math Mentor — Explainer Agent

Generates a beginner-friendly, step-by-step explanation of the solution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

from backend.config import get_llm_client
from backend.agents.parser_agent import ParsedProblem
from backend.agents.solver_agent import SolverResult
from backend.agents.verifier_agent import VerificationResult
from backend.utils.json_utils import robust_json_loads
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a friendly and patient math tutor specialised in JEE-level problems.

Given:
1. The original problem.
2. The solver's answer and computation steps.
3. The verifier's assessment.

Your job:
- Produce a clear, step-by-step explanation that a student can follow.
- Use simple language (beginner friendly).
- Explain *why* each step works — cite formulas/rules.
- Highlight key insights or tricks.
- If the verifier found issues, address them.

IMPORTANT: You MUST respond with ONLY valid JSON and nothing else.
No explanations before or after the JSON. No markdown fences.

Return this exact JSON structure:
{
  "title": "Short title for the solution",
  "steps": [
    {"step_number": 1, "description": "explanation of step", "formula_used": "formula", "result": "intermediate result"}
  ],
  "final_answer": "clean final answer",
  "key_concepts": ["concept 1", "concept 2"],
  "common_mistakes": ["mistake 1"],
  "tips": "extra tips"
}

Field rules:
- "title": short descriptive string
- "steps": array of step objects, each with step_number, description, formula_used, result
- "final_answer": plain text final answer (REQUIRED, must not be empty)
- "key_concepts": array of strings
- "common_mistakes": array of strings
- "tips": string
"""


@dataclass
class Explanation:
    """Structured step-by-step explanation."""

    title: str = ""
    steps: list = field(default_factory=list)  # list of dicts
    final_answer: str = ""
    key_concepts: list = field(default_factory=list)
    common_mistakes: list = field(default_factory=list)
    tips: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        """Render as Markdown for the UI."""
        lines: list[str] = [f"## {self.title}\n"]

        for step in self.steps:
            n = step.get("step_number", "?")
            desc = step.get("description", "")
            formula = step.get("formula_used", "")
            result = step.get("result", "")
            lines.append(f"**Step {n}:** {desc}")
            if formula:
                lines.append(f"  *Formula:* `{formula}`")
            if result:
                lines.append(f"  *Result:* {result}")
            lines.append("")

        lines.append(f"### Final Answer\n**{self.final_answer}**\n")

        if self.key_concepts:
            lines.append("### Key Concepts")
            for c in self.key_concepts:
                lines.append(f"- {c}")
            lines.append("")

        if self.common_mistakes:
            lines.append("### Common Mistakes to Avoid")
            for m in self.common_mistakes:
                lines.append(f"- {m}")
            lines.append("")

        if self.tips:
            lines.append(f"### Tips\n{self.tips}\n")

        return "\n".join(lines)


def _parse_explainer_response(response: str, solver_result: SolverResult) -> dict:
    """Parse explainer LLM output, with fallback heuristics for non-JSON."""
    try:
        return robust_json_loads(response)
    except ValueError:
        pass

    # Fallback: extract structured info from free-text
    logger.warning("Explainer returned non-JSON — extracting heuristically.")
    import re as _re

    text = response.strip()

    # Extract title from first line or heading
    title = "Solution"
    title_m = _re.search(r"(?:^|\n)#*\s*(.+?)(?:\n|$)", text)
    if title_m:
        title = title_m.group(1).strip().lstrip("#").strip()

    # Extract steps from numbered lines
    steps = []
    for m in _re.finditer(r"(?:^|\n)\s*(?:step\s*)?(\d+)[.):]\s*(.+)", text, _re.IGNORECASE):
        steps.append({
            "step_number": int(m.group(1)),
            "description": m.group(2).strip(),
            "formula_used": "",
            "result": "",
        })

    # Extract final answer
    final_answer = solver_result.answer  # safe fallback
    for pattern in [
        r"(?:final\s+answer|the\s+answer\s+is|answer\s*[:=])\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"\\boxed\{(.+?)\}",
    ]:
        m = _re.search(pattern, text, _re.IGNORECASE)
        if m:
            final_answer = m.group(1).strip().rstrip(".")
            break

    return {
        "title": title,
        "steps": steps,
        "final_answer": final_answer,
        "key_concepts": [],
        "common_mistakes": [],
        "tips": "",
    }


def explain(
    parsed: ParsedProblem,
    solver_result: SolverResult,
    verification: VerificationResult,
) -> Explanation:
    """Generate a beginner-friendly explanation."""
    user_payload = json.dumps(
        {
            "problem": parsed.to_dict(),
            "answer": solver_result.answer,
            "computation_steps": solver_result.computation_steps,
            "verification": verification.to_dict(),
        },
        indent=2,
    )

    try:
        llm = get_llm_client()
        response = llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_payload,
            temperature=0.3,
        )

        data = _parse_explainer_response(response, solver_result)

        explanation = Explanation(
            title=data.get("title", "Solution"),
            steps=data.get("steps", []),
            final_answer=data.get("final_answer", solver_result.answer),
            key_concepts=data.get("key_concepts", []),
            common_mistakes=data.get("common_mistakes", []),
            tips=data.get("tips", ""),
        )
        logger.info("Explanation generated: '%s' with %d steps", explanation.title, len(explanation.steps))
        return explanation

    except Exception as exc:
        logger.error("Explainer agent error: %s", exc)
        # Fallback: return raw solver steps
        return Explanation(
            title="Solution (raw)",
            steps=[
                {"step_number": i + 1, "description": s, "formula_used": "", "result": ""}
                for i, s in enumerate(solver_result.computation_steps)
            ],
            final_answer=solver_result.answer,
            tips=f"Explanation generation encountered an error: {exc}",
        )
