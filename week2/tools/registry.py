"""One dispatch path for every tool.

Why this exists: the LLM only ever emits a tool name + a JSON args blob --
it never executes anything itself (Week 1's roadmap notes this explicitly:
"the model doesn't run tools, it proposes them"). Your code is the one
deciding whether that name is real, whether those args are well-formed,
and whether to actually run the handler. This file is that decision point,
built once so every tool goes through the same checks -- no tool gets to
skip validation because it "seems safe."

TODO: fill in `register` and `dispatch` below.
"""
from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Raised when a tool call can't be executed: unknown tool name,
    args that fail schema validation, or the handler itself failing."""


_REGISTRY: dict[str, tuple[type[BaseModel], Callable]] = {}

#
#@dataclass
#class ToolSpec:
#    schema: type[BaseModel]
#    handler: Callable
#    needs_context: bool = False      # does the handler want server-side info (user id, session)?
#    requires_approval: bool = False  # should this pause for a human "yes" before running?
#    retry_policy: RetryPolicy | None = None  # None = no retries, or (max_attempts, base_delay)
#
#
#


def register(name: str, schema: type[BaseModel]):
    """
    TODO: a decorator factory. Usage looks like:

        @register("calculator", CalculatorArgs)
        def calculator(args: CalculatorArgs) -> str:
            ...

    Implementation:
      1. define an inner `decorator(func)` that stores
         _REGISTRY[name] = (schema, func) and returns `func` unchanged
         (so the function is still directly callable/testable on its own,
         not just through dispatch)
      2. return `decorator` from `register(...)`
    """
    def decorator(func: Callable) -> Callable:
        _REGISTRY[name] = (schema, func)
        return func
    return decorator


def dispatch(name: str, raw_args: dict) -> str:
    """
    TODO:
      1. look up `name` in _REGISTRY; if it's not there, raise
         ToolError(f"unknown tool: {name}") -- the model can ask for a
         tool that was never registered, and that's not a bug, it's an
         input you must handle.
      2. validate raw_args against the tool's schema:
             try:
                 validated = schema(**raw_args)
             except ValidationError as e:
                 raise ToolError(str(e)) from e
      3. call the handler with the validated args object, wrapped in a
         try/except that turns any exception the handler raises into a
         ToolError too (wrap it, don't let it propagate raw) -- exercise 3
         is specifically about this path.
      4. return the handler's string result.
    """
    if name not in _REGISTRY:
        raise ToolError(f"unknown tool: {name}")

    schema, handler = _REGISTRY[name]

    try:
        validated_args = schema(**raw_args)
    except ValidationError as e:
        raise ToolError(str(e)) from e

    try:
        result = handler(validated_args)
    except Exception as e:
        raise ToolError(f"handler error: {str(e)}") from e

    return result