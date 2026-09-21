"""One dispatch path for every tool.

Why this exists: the LLM only ever emits a tool name + a JSON args blob --
it never executes anything itself. Your code is the one deciding whether
that name is real, whether those args are well-formed, and whether to
actually run the handler. This file is that decision point, built once so
every tool goes through the same checks.

`register`/`dispatch` are carried over from week2, already implemented.
New this week: `to_openai_tools()`, so the agent loop can actually hand
your registered tools to the model.
"""
from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """Raised when a tool call can't be executed: unknown tool name,
    args that fail schema validation, or the handler itself failing."""


_REGISTRY: dict[str, tuple[type[BaseModel], Callable]] = {}


def register(name: str, schema: type[BaseModel]):
    """Decorator factory: @register("calculator", CalculatorArgs)."""
    def decorator(func: Callable) -> Callable:
        _REGISTRY[name] = (schema, func)
        return func
    return decorator


def dispatch(name: str, raw_args: dict) -> str:
    """Validate raw_args against the tool's schema, run its handler,
    return the string result. Raises ToolError for any failure."""
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


def to_openai_tools() -> list[dict[str, Any]]:
    """New this week: convert every registered tool into the shape the
    OpenAI API expects for its `tools=` parameter, so the LLM can
    actually see and call them (Week 1/2 never wired this up -- `chat()`
    never passed tools at all).
    `schema.model_json_schema()` is
    Pydantic's built-in method for turning a BaseModel into a JSON Schema
    dict -- this is exactly why every tool got a Pydantic schema back in
    Week 2, not just for validation.

    """
    tools_list: list[dict[str, Any]] = []
    for name, (schema, handler) in _REGISTRY.items():
        tool_dict = {
            "type": "function",
            "function": {
                "name": name,
                "description": (handler.__doc__ or "").strip(),
                "parameters": schema.model_json_schema(),
            },
        }
        tools_list.append(tool_dict)
    return tools_list


def to_langchain_tools() -> list:

    from langchain_core.tools import tool as lc_tool
    def _make(name, schema, handler):
        def run(**kwargs):
            try:
                return dispatch(name, kwargs)
            except ToolError as e:
                return f"error: {e}"
        run.__name__ = name
        run.__doc__ = (handler.__doc__ or "").strip()
        return lc_tool(run, args_schema=schema) 

    return [_make(name, schema, handler) for name,(schema, handler) in _REGISTRY.items()]