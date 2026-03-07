"""
Multimodal Math Mentor — Intent Router Agent

Classifies the parsed problem's math domain and decides which solver
strategy / tools to route to.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import List

from backend.config import get_llm_client
from backend.agents.parser_agent import ParsedProblem
from backend.utils.json_utils import robust_json_loads
from backend.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """\
You are a math problem router. Given a structured math problem, classify it and
decide the solving strategy.

Return a JSON object:
{
  "domain": "<algebra|calculus|probability|linear_algebra|trigonometry|number_theory|geometry|other>",
  "sub_topic": "<e.g. quadratic_equations, definite_integrals, bayes_theorem, etc.>",
  "tools_needed": ["<sympy_solve|sympy_diff|sympy_integrate|sympy_limit|sympy_matrix|python_eval|rag_only>"],
  "difficulty": "<easy|medium|hard>",
  "strategy": "<brief 1-2 sentence description of the solving approach>"
}

Only return valid JSON.
"""


@dataclass
class RoutingDecision:
    """Output of the intent router."""

    domain: str = "other"
    sub_topic: str = ""
    tools_needed: List[str] = field(default_factory=lambda: ["sympy_solve"])
    difficulty: str = "medium"
    strategy: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def route_problem(parsed: ParsedProblem) -> RoutingDecision:
    """Classify the problem and decide routing / tools."""
    prompt = json.dumps(parsed.to_dict(), indent=2)

    try:
        llm = get_llm_client()
        response = llm(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.1,
        )

        data = robust_json_loads(response)
        decision = RoutingDecision(
            domain=data.get("domain", parsed.topic),
            sub_topic=data.get("sub_topic", ""),
            tools_needed=data.get("tools_needed", ["sympy_solve"]),
            difficulty=data.get("difficulty", "medium"),
            strategy=data.get("strategy", ""),
        )
        logger.info(
            "Routed problem → domain=%s, sub_topic=%s, tools=%s",
            decision.domain, decision.sub_topic, decision.tools_needed,
        )
        return decision

    except Exception as exc:
        logger.error("Router agent error: %s", exc)
        return RoutingDecision(
            domain=parsed.topic,
            strategy=f"Fallback routing due to error: {exc}",
        )
