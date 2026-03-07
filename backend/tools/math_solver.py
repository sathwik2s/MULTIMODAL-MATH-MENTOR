"""
Multimodal Math Mentor — SymPy Math Solver

Provides functions for symbolic math solving using SymPy:
  - equation solving
  - differentiation / integration
  - simplification
  - limit computation
  - matrix operations
"""

from __future__ import annotations

from typing import Any, Dict

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Common symbol pre-definitions
x, y, z, t, n, k = sp.symbols("x y z t n k")
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def safe_parse(expr_str: str) -> sp.Expr:
    """Parse a string into a SymPy expression with sensible transformations."""
    return parse_expr(expr_str, transformations=TRANSFORMATIONS)


def solve_equation(equation_str: str, variable: str = "x") -> Dict[str, Any]:
    """Solve an equation (e.g. 'x**2 - 4 = 0') for a variable.

    If the string contains '=', we move everything to the LHS.
    """
    try:
        var = sp.Symbol(variable)
        if "=" in equation_str:
            lhs_str, rhs_str = equation_str.split("=", 1)
            lhs = safe_parse(lhs_str.strip())
            rhs = safe_parse(rhs_str.strip())
            expr = lhs - rhs
        else:
            expr = safe_parse(equation_str)

        solutions = sp.solve(expr, var)
        return {
            "success": True,
            "solutions": [str(s) for s in solutions],
            "latex": [sp.latex(s) for s in solutions],
        }
    except Exception as exc:
        logger.error("solve_equation failed: %s", exc)
        return {"success": False, "error": str(exc)}


def differentiate(expr_str: str, variable: str = "x", order: int = 1) -> Dict[str, Any]:
    """Compute the nth derivative of an expression."""
    try:
        var = sp.Symbol(variable)
        expr = safe_parse(expr_str)
        result = sp.diff(expr, var, order)
        return {
            "success": True,
            "result": str(result),
            "simplified": str(sp.simplify(result)),
            "latex": sp.latex(result),
        }
    except Exception as exc:
        logger.error("differentiate failed: %s", exc)
        return {"success": False, "error": str(exc)}


def integrate(expr_str: str, variable: str = "x", limits: tuple | None = None) -> Dict[str, Any]:
    """Compute indefinite or definite integral.

    Parameters
    ----------
    limits : optional (lower, upper) for definite integration.
    """
    try:
        var = sp.Symbol(variable)
        expr = safe_parse(expr_str)
        if limits:
            lo = safe_parse(str(limits[0]))
            hi = safe_parse(str(limits[1]))
            result = sp.integrate(expr, (var, lo, hi))
        else:
            result = sp.integrate(expr, var)
        return {
            "success": True,
            "result": str(result),
            "latex": sp.latex(result),
        }
    except Exception as exc:
        logger.error("integrate failed: %s", exc)
        return {"success": False, "error": str(exc)}


def simplify_expression(expr_str: str) -> Dict[str, Any]:
    """Simplify a mathematical expression."""
    try:
        expr = safe_parse(expr_str)
        simplified = sp.simplify(expr)
        return {
            "success": True,
            "result": str(simplified),
            "latex": sp.latex(simplified),
        }
    except Exception as exc:
        logger.error("simplify failed: %s", exc)
        return {"success": False, "error": str(exc)}


def compute_limit(expr_str: str, variable: str = "x", point: str = "oo") -> Dict[str, Any]:
    """Compute limit of an expression as variable → point."""
    try:
        var = sp.Symbol(variable)
        expr = safe_parse(expr_str)
        pt = sp.oo if point in ("oo", "inf", "infinity") else safe_parse(point)
        result = sp.limit(expr, var, pt)
        return {
            "success": True,
            "result": str(result),
            "latex": sp.latex(result),
        }
    except Exception as exc:
        logger.error("compute_limit failed: %s", exc)
        return {"success": False, "error": str(exc)}


def matrix_operations(matrix_str: str, operation: str = "det") -> Dict[str, Any]:
    """Perform matrix operations: det, inverse, eigenvalues, rank.

    matrix_str should be a valid Python nested list, e.g. '[[1,2],[3,4]]'.
    """
    try:
        import ast
        mat_list = ast.literal_eval(matrix_str)
        M = sp.Matrix(mat_list)

        if operation == "det":
            result = M.det()
        elif operation == "inverse":
            result = M.inv()
        elif operation == "eigenvalues":
            result = M.eigenvals()
        elif operation == "rank":
            result = M.rank()
        elif operation == "rref":
            result = M.rref()
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

        return {
            "success": True,
            "result": str(result),
            "latex": sp.latex(result) if hasattr(result, "__class__") else str(result),
        }
    except Exception as exc:
        logger.error("matrix_operations failed: %s", exc)
        return {"success": False, "error": str(exc)}
