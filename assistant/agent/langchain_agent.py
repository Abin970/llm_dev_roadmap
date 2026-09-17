"""LangChainAgent -- same tools, same task, via LangChain's agent
abstraction.

Built to expose a comparable interface to AgentLoop (loop.py) --
`.run(user_message) -> Iterator[Event]` -- so experiment 2 can genuinely
diff the two traces, not just eyeball two differently-shaped outputs.

API confirmed via Context7 against LangChain's current docs (Sep 2026),
not from memory:

  - langchain.agents.create_agent(model=..., tools=[...], system_prompt=...,
        middleware=[...]) -> a runnable agent
  - agent.invoke({"messages": [{"role": "user", "content": ...}]})
        -> {"messages": [...]}; the final answer is result["messages"][-1]
  - agent.stream({"messages": [...]}, stream_mode=["updates"])
        yields dicts like {"model": {"messages": [...]}} or
        {"tools": {"messages": [...]}} as the agent progresses through
        each step -- this is what lets you emit Events incrementally
        instead of only getting the final result.
  - a hard cap on total model calls per run (this project's
    max_iterations equivalent) is set via:
        from langchain.agents.middleware import ModelCallLimitMiddleware
        middleware=[ModelCallLimitMiddleware(run_limit=N, exit_behavior="end")]

Needs `langchain` with the openai extra installed (see requirements.txt).
"""
from __future__ import annotations

from typing import Iterator

from events import Event, EventType
from llm_client import DEFAULT_MODEL
from tools.registry import dispatch

# TODO: one thin wrapper function per registered tool, reusing dispatch()
# so the actual tool logic isn't duplicated. LangChain's create_agent
# expects plain Python functions with type-hinted args and a docstring --
# the docstring becomes the tool's description, same as
# to_openai_tools()'s "description" field in registry.py. e.g.:
#
#   def calculator(expression: str) -> str:
#       """Evaluate a basic arithmetic expression."""
#       return dispatch("calculator", {"expression": expression})
#
# Write one of these for each of the 5 registered tools (calculator,
# file_reader, sqlite_query, search_docs, search_web), matching each
# function's argument names to that tool's Pydantic schema fields.


class LangChainAgent:
    def __init__(self, *, model: str = DEFAULT_MODEL, max_iterations: int = 6) -> None:
        self.model = model
        self.max_iterations = max_iterations

    def run(self, user_message: str) -> Iterator[Event]:
        """Run the same research question through LangChain's agent,
        yielding Events so it's directly comparable to AgentLoop.run().

        TODO:
          1. from langchain.agents import create_agent
             from langchain.agents.middleware import ModelCallLimitMiddleware
          2. tools = [calculator, file_reader, ...]  # the wrapper functions above
          3. agent = create_agent(
                 model=f"openai:{self.model}",
                 tools=tools,
                 system_prompt=(
                     "You are a research/engineering assistant. Use the "
                     "available tools when they help answer the question."
                 ),
                 middleware=[ModelCallLimitMiddleware(
                     run_limit=self.max_iterations, exit_behavior="end")],
             )
          4. yield Event(EventType.STARTED, {})
          5. final_content = None
             for chunk in agent.stream(
                 {"messages": [{"role": "user", "content": user_message}]},
                 stream_mode=["updates"],
             ):
                 for source, update in chunk.items():
                     last = update["messages"][-1]
                     if source == "tools":
                         yield Event(EventType.TOOL_RESULT, {"content": str(last.content)})
                     elif source == "model" and getattr(last, "tool_calls", None):
                         for tc in last.tool_calls:
                             yield Event(EventType.TOOL_CALL, {"name": tc["name"], "args": tc["args"]})
                     elif source == "model":
                         final_content = last.content
          6. yield Event(EventType.COMPLETED, {"content": final_content})

        Wrap this in try/except so an exception surfaced from inside
        LangChain still yields an ERROR event instead of crashing --
        same expectation as AgentLoop. The exact keys inside each stream
        chunk are worth printing/inspecting once by hand first (`print(chunk)`
        in the loop) -- treat the shape above as a strong starting point
        from the docs, not gospel, since streaming payload shapes are the
        part of any framework most likely to drift between versions.
        """
        raise NotImplementedError
