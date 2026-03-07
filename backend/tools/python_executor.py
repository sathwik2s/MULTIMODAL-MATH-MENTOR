"""
Multimodal Math Mentor — Sandboxed Python Executor

Executes a restricted subset of Python for numerical computation.
Only math / numpy / sympy are available — no file I/O, no networking.
"""

from __future__ import annotations

import math
import threading
import traceback
from typing import Any, Dict

import numpy as np
import sympy as sp

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# White-listed names available inside the sandbox
_SAFE_GLOBALS: dict[str, Any] = {
    "__builtins__": {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "range": range,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "tuple": tuple,
        "dict": dict,
        "set": set,
        "True": True,
        "False": False,
        "None": None,
        "sorted": sorted,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "pow": pow,
        "print": print,  # will be captured
    },
    "math": math,
    "np": np,
    "numpy": np,
    "sp": sp,
    "sympy": sp,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
    "inf": math.inf,
    "factorial": math.factorial,
    "comb": math.comb,
    "perm": math.perm,
    "gcd": math.gcd,
}


def execute_python(code: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """Execute a code snippet in a restricted sandbox.

    Returns
    -------
    dict with keys: success (bool), output (str), error (str | None)
    """
    # Basic sanity checks
    _forbidden = ["import os", "import sys", "open(", "exec(", "eval(", "__import__",
                   "subprocess", "shutil", "pathlib", "io.", "socket"]
    for token in _forbidden:
        if token in code:
            return {
                "success": False,
                "output": "",
                "error": f"Forbidden operation detected: {token}",
            }

    captured: list[str] = []

    def _capture_print(*args, **kwargs):
        captured.append(" ".join(str(a) for a in args))

    sandbox = {**_SAFE_GLOBALS}
    sandbox["__builtins__"]["print"] = _capture_print  # type: ignore[index]

    result_container: list = [None]

    def _run() -> None:
        try:
            exec(code, sandbox)  # noqa: S102
            result_val = sandbox.get("result", None)
            output_lines = "\n".join(captured)
            if result_val is not None and not captured:
                output_lines = str(result_val)
            elif result_val is not None:
                output_lines += f"\nresult = {result_val}"
            result_container[0] = {"success": True, "output": output_lines, "error": None}
        except Exception:
            tb = traceback.format_exc()
            logger.error("Python executor error:\n%s", tb)
            result_container[0] = {"success": False, "output": "", "error": tb}

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        logger.warning("Python executor timed out after %ds", timeout_seconds)
        return {
            "success": False,
            "output": "",
            "error": f"Execution timed out after {timeout_seconds} seconds",
        }

    return result_container[0]
