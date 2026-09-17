"""calculator -- evaluate a basic arithmetic expression.

Deliberately not using bare eval() on model-supplied text -- that's a code
execution hole even in a toy project (the model's output is untrusted
input, same as any other user input). Use Python's `ast` module instead:
parse the expression into a syntax tree and only walk arithmetic node
types, rejecting anything else (name lookups, function calls, attribute
access, etc).
"""
from __future__ import annotations

import ast
import operator

from pydantic import BaseModel

from .registry import register

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


class CalculatorArgs(BaseModel):
    expression: str  # e.g. "2 + 2 * 3"


def _eval_node(node: ast.AST) -> float:
    """
    TODO: recursively evaluate an AST node, supporting only:
      - ast.Constant (a plain number) -> return node.value
      - ast.BinOp -> _eval_node(node.left) OP _eval_node(node.right),
        using _OPS[type(node.op)]
      - ast.UnaryOp (for e.g. "-5") -> _OPS[type(node.op)](_eval_node(node.operand))
    Anything else (Call, Name, Attribute, ...) should raise ValueError --
    that's the whole point, it's the allowlist that keeps this safe.
    """
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op_func = _OPS[type(node.op)]
        return op_func(left, right)
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand)
        op_func = _OPS[type(node.op)]
        return op_func(operand)
    else:
        raise ValueError(f"Unsupported AST node type: {type(node).__name__}")


@register("calculator", CalculatorArgs)
def calculator(args: CalculatorArgs) -> str:
    """ Evalutate a basic arithmetic expression, returning the result as a string."""
    
    tree = ast.parse(args.expression, mode="eval")
    result = _eval_node(tree.body)
    return str(result)
