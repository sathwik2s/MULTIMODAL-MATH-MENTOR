"""
Multimodal Math Mentor — Solver Agent

Orchestrates RAG retrieval + math tools to solve the parsed problem.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

from backend.config import get_llm_client
from backend.agents.parser_agent import ParsedProblem
from backend.agents.router_agent import RoutingDecision
from backend.rag.retriever import retrieve, RetrievalResult
from backend.tools.math_solver import (
    solve_equation,
    differentiate,
    integrate,
    simplify_expression,
    compute_limit,
    matrix_operations,
)
from backend.tools.python_executor import execute_python
from backend.utils.json_utils import robust_json_loads
from backend.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SolverResult:
    """Output of the solver agent."""

    answer: str = ""
    latex_answer: str = ""
    computation_steps: List[str] = field(default_factory=list)
    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    rag_context: str = ""
    rag_sources: List[str] = field(default_factory=list)
    confidence: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


SOLVER_SYSTEM_PROMPT = """\
You are an expert math solver for JEE-level problems.

You are given:
1. A structured math problem.
2. Routing information (domain, tools to use, strategy).
3. Relevant knowledge-base context from RAG.
4. Tool computation results (SymPy / Python).

Your job:
- Synthesise all the information and produce a final answer.
- Show your reasoning step by step.

IMPORTANT: You MUST respond with ONLY valid JSON and nothing else.
No explanations before or after the JSON. No markdown fences.

Return this exact JSON structure:
{
  "answer": "final answer as a string",
  "latex_answer": "answer in LaTeX notation",
  "computation_steps": ["step 1 description", "step 2 description"],
  "confidence": 0.9,
  "sympy_code": ""
}

Field rules:
- "answer": plain text final answer (REQUIRED, must not be empty)
- "latex_answer": LaTeX formatted answer string
- "computation_steps": array of strings describing each step
- "confidence": number from 0.0 to 1.0
- "sympy_code": optional Python/SymPy verification code (empty string if none)
"""


def _parse_solver_response(response: str) -> dict:
    """Parse solver LLM output, with fallback heuristics for non-JSON."""
    # Try structured JSON first
    try:
        return robust_json_loads(response)
    except ValueError:
        pass

    # Fallback: extract answer from free-text response
    logger.warning("Solver returned non-JSON — extracting heuristically.")
    import re as _re

    text = response.strip()

    # Try to extract answer from common patterns
    answer = ""
    # Pattern: "Final Answer: ..." or "The answer is ..."
    for pattern in [
        r"(?:final\s+answer|the\s+answer\s+is|answer\s*[:=])\s*[:\-]?\s*(.+?)(?:\n|$)",
        r"\\boxed\{(.+?)\}",
        r"(?:x\s*=\s*)([^\n,]+)",
        r"(?:solution|result)\s*[:=]\s*(.+?)(?:\n|$)",
    ]:
        m = _re.search(pattern, text, _re.IGNORECASE)
        if m:
            answer = m.group(1).strip().rstrip(".")
            break

    # If no pattern matched, take the last non-empty line as the answer
    if not answer:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            answer = lines[-1]

    # Extract computation steps from numbered lines
    steps = []
    for m in _re.finditer(r"(?:^|\n)\s*(?:step\s*)?(\d+)[.):]\s*(.+)", text, _re.IGNORECASE):
        steps.append(f"Step {m.group(1)}: {m.group(2).strip()}")
    if not steps:
        # Fall back to any lines that look like explanation
        steps = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 10][:5]

    # Extract LaTeX if present
    latex_answer = ""
    latex_m = _re.search(r"(\$\$.+?\$\$|\\\[.+?\\\]|\\boxed\{.+?\})", text, _re.DOTALL)
    if latex_m:
        latex_answer = latex_m.group(1)

    return {
        "answer": answer,
        "latex_answer": latex_answer,
        "computation_steps": steps,
        "confidence": 0.65,
        "sympy_code": "",
    }


def _run_tools(parsed: ParsedProblem, routing: RoutingDecision) -> Dict[str, Any]:
    """Execute the math tools specified by routing."""
    results: dict[str, Any] = {}

    for tool in routing.tools_needed:
        try:
            if tool == "sympy_solve" and parsed.equation:
                var = parsed.variables[0] if parsed.variables else "x"
                results["sympy_solve"] = solve_equation(parsed.equation, var)

            elif tool == "sympy_diff" and parsed.equation:
                var = parsed.variables[0] if parsed.variables else "x"
                results["sympy_diff"] = differentiate(parsed.equation, var)

            elif tool == "sympy_integrate" and parsed.equation:
                var = parsed.variables[0] if parsed.variables else "x"
                results["sympy_integrate"] = integrate(parsed.equation, var)

            elif tool == "sympy_limit" and parsed.equation:
                var = parsed.variables[0] if parsed.variables else "x"
                results["sympy_limit"] = compute_limit(parsed.equation, var)

            elif tool == "sympy_matrix":
                # Try to extract matrix from equation field
                results["sympy_matrix"] = matrix_operations(parsed.equation, "det")

            elif tool == "python_eval":
                # Signal to the LLM that it MUST provide executable SymPy/Python
                # code in the 'sympy_code' field of its JSON response.
                results["python_eval"] = {
                    "instruction": "Generate Python/SymPy code in the 'sympy_code' field to numerically or symbolically evaluate this problem."
                }

        except Exception as exc:
            logger.warning("Tool %s failed: %s", tool, exc)
            results[tool] = {"success": False, "error": str(exc)}

    return results


def solve(parsed: ParsedProblem, routing: RoutingDecision) -> SolverResult:
    """Run the full solver pipeline: RAG → tools → LLM synthesis."""

    # 1. RAG retrieval
    rag_result: RetrievalResult = retrieve(parsed.problem_text)
    rag_context = rag_result.as_context_string()
    rag_sources = [c.source for c in rag_result.chunks]

    # 2. Run math tools
    tool_outputs = _run_tools(parsed, routing)

    # 3. Ask LLM to synthesise
    user_payload = json.dumps(
        {
            "problem": parsed.to_dict(),
            "routing": routing.to_dict(),
            "rag_context": rag_context,
            "tool_results": {k: str(v) for k, v in tool_outputs.items()},
        },
        indent=2,
    )

    try:
        llm = get_llm_client()
        response = llm(
            system_prompt=SOLVER_SYSTEM_PROMPT,
            user_prompt=user_payload,
            temperature=0.2,
        )

        data = _parse_solver_response(response)

        # If the LLM produced sympy_code, try running it
        code = data.get("sympy_code", "")
        if code:
            exec_result = execute_python(code)
            if exec_result["success"]:
                tool_outputs["llm_code"] = exec_result["output"]

        result = SolverResult(
            answer=data.get("answer", ""),
            latex_answer=data.get("latex_answer", ""),
            computation_steps=data.get("computation_steps", []),
            tool_outputs=tool_outputs,
            rag_context=rag_context,
            rag_sources=rag_sources,
            confidence=float(data.get("confidence", 0.5)),
        )
        logger.info("Solver produced answer (conf=%.2f): %s", result.confidence, result.answer[:80])
        return result

    except Exception as exc:
        logger.error("Solver agent error: %s", exc)
        return SolverResult(
            error=str(exc),
            rag_context=rag_context,
            rag_sources=rag_sources,
            tool_outputs=tool_outputs,
        )
