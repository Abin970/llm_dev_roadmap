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
from tools.registry import dispatch, to_langchain_tools
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langchain_openai import ChatOpenAI
import os

    
class LangChainAgent:
    def __init__(self, *, model: str = DEFAULT_MODEL, max_iterations: int = 6) -> None:
        self.model = model
        self.max_iterations = max_iterations

    def run(self, user_message: str) -> Iterator[Event]:
        """Run the same research question through LangChain's agent,
        yielding Events so it's directly comparable to AgentLoop.run().
        """
        tools = to_langchain_tools()

        

        yield Event(EventType.STARTED, {})
        final_content = None
        try:
            model = ChatOpenAI(model=self.model, api_key=os.environ["OPENAI_API_KEY_LLM_PRJ"],max_tokens=5000)
            agent = create_agent(
                         model=model,
                         tools=tools,
                         system_prompt=(
                             "You are a research/engineering assistant. Use the "
                             "available tools when they help answer the question."
                            ),
                         middleware=[ModelCallLimitMiddleware(
                                              run_limit=self.max_iterations, exit_behavior="end")],
                    )

            for mode, chunk_update in agent.stream(
                {"messages": [{"role": "user", "content": user_message}]},
                stream_mode=["updates"],
            ):
                print(f"stream chunk :{chunk_update}")
                for source, update in chunk_update.items():
                    if source == "ModelCallLimitMiddleware.before_model" and update and update.get("jump_to") == "end":
                        final_content = update["messages"][-1].content
                        continue
                    if source not in ("model","tools") or not update:
                        continue
                    last = update["messages"][-1]
                    if source == "tools":
                        yield Event(EventType.TOOL_RESULT,{"content": str(last.content)})
                    elif source == "model" and getattr(last,"tool_calls", None):
                        for tc in last.tool_calls:
                            yield Event(EventType.TOOL_CALL, {"name": tc["name"], "args": tc["args"]})
                    elif source == "model":
                        final_content = last.content
            yield Event(EventType.COMPLETED, {"content":final_content})
        except Exception as e:
            yield Event(EventType.ERROR, {"content": str(e)})
