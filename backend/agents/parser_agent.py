"""
Multimodal Math Mentor — Parser Agent

Converts raw (possibly noisy) input text into a structured math problem.
Detects ambiguity and flags problems that need human clarification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List

from backend.config import get_llm_client
from backend.utils.json_utils import robust_json_loads
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a math problem parser specialised in JEE-style questions.

Given a raw text (possibly from OCR or speech-to-text, so it may contain errors),
produce a JSON object with the following fields:

{
  "problem_text": "<cleaned, unambiguous version of the problem>",
  "topic": "<one of: algebra, calculus, probability, linear_algebra, trigonometry, number_theory, geometry, other>",
  "variables": ["<list of variable names>"],
  "constraints": ["<list of constraints like 'x > 0'>"],
  "equation": "<if an equation is present, write it in standard form e.g. x^2 - 4 = 0>",
  "needs_clarification": <true|false>,
  "clarification_reason": "<why clarification is needed, or empty string>"
}

Rules:
- Fix obvious OCR errors (e.g. "l" → "1", "O" → "0" when in numeric context).
- If the problem is ambiguous or incomplete, set needs_clarification = true.
- Detect missing numbers, unclear operators, or garbled expressions.
- Always return valid JSON — nothing else.
"""


@dataclass
class ParsedProblem:
    """Structured representation of a math problem."""

    problem_text: str = ""
    topic: str = "other"
    variables: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    equation: str = ""
    needs_clarification: bool = False
    clarification_reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def parse_problem(raw_text: str) -> ParsedProblem:
    """Use the LLM to parse raw input into a structured problem."""
    if not raw_text.strip():
        return ParsedProblem(
            needs_clarification=True,
            clarification_reason="Input is empty.",
        )

    try:
        llm = get_llm_client()
        response = llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=raw_text,
            temperature=0.1,
        )

        data = robust_json_loads(response)
        parsed = ParsedProblem(
            problem_text=data.get("problem_text", raw_text),
            topic=data.get("topic", "other"),
            variables=data.get("variables", []),
            constraints=data.get("constraints", []),
            equation=data.get("equation", ""),
            needs_clarification=data.get("needs_clarification", False),
            clarification_reason=data.get("clarification_reason", ""),
        )
        logger.info("Parsed problem — topic=%s, needs_clarification=%s", parsed.topic, parsed.needs_clarification)
        return parsed

    except (ValueError, KeyError) as exc:
        logger.warning("Parser LLM returned invalid JSON: %s", exc)
        return ParsedProblem(
            problem_text=raw_text,
            needs_clarification=True,
            clarification_reason="Could not parse the input into structured form.",
        )
    except Exception as exc:
        logger.error("Parser agent error: %s", exc)
        return ParsedProblem(
            problem_text=raw_text,
            needs_clarification=True,
            clarification_reason=f"Parser error: {exc}",
        )
