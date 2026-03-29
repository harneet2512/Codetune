"""Safe arithmetic evaluation tool."""

from __future__ import annotations

import ast
import operator
from typing import Any

ALLOWED_OPERATORS: dict[type[ast.AST], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
        return ALLOWED_OPERATORS[type(node.op)](_eval_node(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return ALLOWED_OPERATORS[type(node.op)](left, right)
    raise ValueError("Unsupported expression")


def run(expression: str) -> str:
    try:
        parsed = ast.parse(expression, mode="eval")
        result = _eval_node(parsed.body)
    except ZeroDivisionError:
        return '{"error": "Invalid expression: division by zero"}'
    except Exception:
        return '{"error": "Invalid expression"}'
    if result.is_integer():
        return str(int(result))
    return str(round(result, 4))
