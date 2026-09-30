"""FastAPI service exposing the project over streaming endpoints.

Carried over from week2/main.py's /chat skeleton (still your TODO to
finish, same as before), plus one new endpoint this week: POST /research,
backed by AgentLoop. Build the rest of this project first -- this file
has nothing of its own to test until llm_client.chat_with_tools,
tools/registry.to_openai_tools, and agent/loop.AgentLoop all work.

Run (from inside assistant/, with fastapi + uvicorn installed):
    uvicorn main:app --reload

Then in another terminal:
    curl -N -X POST localhost:8000/research \\
        -H "Content-Type: application/json" \\
        -d '{"message": "What incidents happened on checkout-service?"}'
"""
from __future__ import annotations

import json
import uuid
from typing import Iterator

import tools  # noqa: F401 -- importing this registers all 6 tools
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.graph import GraphAgent
from conversation import ConversationState, truncate_sliding_window
from events import Event, EventType
from llm_client import DEFAULT_MODEL, chat_with_tools
from tools.registry import ToolError, dispatch, to_openai_tools

app = FastAPI()

# A real app would key this per session/user; one shared state is fine
# for this exercise, since there's only ever one caller (you, via curl).
_state = ConversationState()

CHAT_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the available tools when they help "
    "answer the user's question."
)
CHAT_MAX_TOOL_ITERATIONS = 6  # same safety-guard idea as AgentLoop's max_iterations
CHAT_TRUNCATE_MAX_TOKENS = 3000  # arbitrary budget -- keeps _state.messages bounded


class ChatRequest(BaseModel):
    message: str


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


def run_turn(user_message: str) -> Iterator[Event]:
    """One /chat turn against the shared, module-level `_state`.

    Unlike /research (a brand-new question every call), /chat is
    genuinely multi-turn: `_state.messages` persists across calls, so
    this reuses the exact same tool-calling loop shape as
    agent/loop.py's AgentLoop, just against that persistent history
    instead of a fresh messages list -- and with truncation applied
    first, which is the whole reason ConversationState/truncate_sliding_
    window exist. Reusing them here is the missing piece that actually
    exercises that Week 2 code.
    """
    yield Event(EventType.STARTED, {})

    if not _state.messages:
        _state.add("developer", CHAT_SYSTEM_PROMPT)
    _state.add("user", user_message)
    _state.messages = truncate_sliding_window(_state.messages, CHAT_TRUNCATE_MAX_TOKENS)

    tools_list = to_openai_tools()

    for _ in range(CHAT_MAX_TOOL_ITERATIONS):
        message = chat_with_tools(_state.messages, tools_list, model=DEFAULT_MODEL)

        if not message.tool_calls:
            _state.add("assistant", message.content)
            yield Event(EventType.COMPLETED, {"content": message.content})
            return

        _state.messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            yield Event(EventType.TOOL_CALL, {"name": name, "args": args})
            try:
                result = dispatch(name, args)
            except ToolError as e:
                result = f"error: {e}"
                yield Event(EventType.ERROR, {"name": name, "message": str(e)})
            else:
                yield Event(EventType.TOOL_RESULT, {"name": name, "result": result})
            _state.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    yield Event(EventType.COMPLETED, {
        "content": "I wasn't able to finish within the allowed number of steps.",
    })


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Wraps run_turn the same way /research is meant to wrap
    AgentLoop().run(...): convert each yielded Event into one SSE
    message and stream it back."""
    def event_stream() -> Iterator[str]:
        for event in run_turn(req.message):
            yield event.to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/research")
async def research_endpoint(req: ChatRequest):
    """Backed by GraphAgent (Week 4) -- AgentLoop (Week 3) is retired as
    the top-level control flow here; it still exists standalone for the
    week3/week4 loop-vs-graph comparisons, but production /research now
    runs the graph instead. Each call is a brand-new investigation, so
    no ConversationState -- but it DOES need a fresh thread_id per call
    (generated here, inside the request handler, not once at module
    import time), since the graph's checkpointer keys all state
    (including a possible pause at apply_fix_node) by thread_id.
    """
    thread_id = str(uuid.uuid4())
    print(f"thread_id: {thread_id} req.message: {req.message}")
    def event_stream() -> Iterator[str]:
        for event in GraphAgent().run(req.message, thread_id=thread_id):
            yield event.to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/research/resume")
async def research_resume_endpoint(req: ResumeRequest):
    """Resumes a /research run that paused at GraphAgent's apply_fix_node
    interrupt(), waiting on a human decision. req.thread_id comes from
    whatever PAUSED event /research emitted when the original run
    suspended -- agent/graph.py's GraphAgent.run() puts thread_id in that
    event's data for exactly this reason.
    """
    def event_stream() -> Iterator[str]:
        for event in GraphAgent().resume(req.thread_id, {"approved": req.approved}):
            yield event.to_sse()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
