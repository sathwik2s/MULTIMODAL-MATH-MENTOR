"""
Multimodal Math Mentor — Robust JSON Utilities

LLMs sometimes return Python-style output (single quotes, True/False/None)
instead of strict JSON. This module provides a tolerant parser.
"""

from __future__ import annotations

import ast
import json
import re


def robust_json_loads(text: str) -> dict:
    """Parse JSON from LLM output tolerantly.

    Strategy:
    1. Extract the outermost {...} block.
    2. Try standard json.loads.
    3. Fall back to ast.literal_eval (handles single quotes, Python booleans).
    4. If both fail, attempt light sanitisation then retry.
    """
    # Step 1 – extract the first {...} block
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group()
    else:
        candidate = text.strip()

    # Step 2 – standard JSON
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Step 3 – Python literal eval (handles 'key': 'value', True/False/None)
    try:
        result = ast.literal_eval(candidate)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass

    # Step 4 – light sanitisation: replace Python booleans / None, trailing commas
    sanitised = candidate
    sanitised = re.sub(r'\bTrue\b', 'true', sanitised)
    sanitised = re.sub(r'\bFalse\b', 'false', sanitised)
    sanitised = re.sub(r'\bNone\b', 'null', sanitised)
    # convert single-quoted strings to double-quoted (simple heuristic)
    sanitised = re.sub(r"(?<![\\])'", '"', sanitised)
    # remove trailing commas before } or ]
    sanitised = re.sub(r',\s*([}\]])', r'\1', sanitised)

    try:
        return json.loads(sanitised)
    except json.JSONDecodeError:
        pass

    # Step 5 – last resort: raise so callers can fall back gracefully
    raise ValueError(f"Could not parse LLM output as JSON:\n{text[:300]}")
