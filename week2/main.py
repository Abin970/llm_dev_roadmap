"""FastAPI service exposing the Week 2 primitives over one streaming
endpoint.

Not an "exercise" with a hypothesis to test -- this is the actual service
skeleton the roadmap describes: a single POST /chat endpoint that streams
typed events (events.py) over SSE, backed by conversation state
(conversation.py) and the tool registry (tools/). Build this last, after
events.py, conversation.py, and tools/ are all working -- it has nothing
of its own to test until those pieces exist.

Run (from inside week2/, with fastapi + uvicorn installed):
    uvicorn main:app --reload

Then in another terminal:
    curl -N -X POST localhost:8000/chat \\
        -H "Content-Type: application/json" \\
        -d '{"message": "What incidents happened on checkout-service?"}'
"""
from __future__ import annotations

from typing import Iterator

import tools  # noqa: F401 -- importing this registers all 4 tools
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from conversation import ConversationState
from events import Event, EventType
from llm_client import DEFAULT_MODEL, chat
from tools.registry import ToolError, dispatch

app = FastAPI()

# TODO: a real app would key this per session/user; one shared state is
# fine for this exercise, since there's only ever one caller (you, via
# curl).
_state = ConversationState()


class ChatRequest(BaseModel):
    message: str


def run_turn(user_message: str) -> Iterator[Event]:
    """
    TODO:
      1. yield Event(EventType.STARTED, {})
      2. _state.add("user", user_message)
      3. Call chat(_state.messages, model=DEFAULT_MODEL). This week's
         llm_client.py doesn't do real tool-calling (that's the SDK's
         `tools=` param, not covered until you wire it in yourself) --
         for this exercise it's fine to fake the tool step: if the user's
         message looks like it's asking for one of your 4 tools (e.g.
         contains "calculate" or "search"), call dispatch() directly and
         yield TOOL_CALL / TOOL_RESULT events around it, wrapping
         ToolError into an ERROR event instead of letting it crash the
         generator.
      4. Get the model's final text reply, _state.add("assistant", reply)
      5. yield Event(EventType.COMPLETED, {"content": reply})
    Wrap step 3 in try/except Exception and yield an ERROR event on
    failure instead of raising -- a broken turn should end the stream
    cleanly, not kill the server process.
    """
    yield Event(EventType.STARTED, {})
    _state.add("user", user_message)

    try:
        # Simulate tool call if the message contains a tool keyword
        if "calculate" in user_message.lower():
            tool_name = "calculator"
            tool_args = {"expression": user_message.split("calculate")[-1].strip()}
            yield Event(EventType.TOOL_CALL, {"name": tool_name, "args": tool_args})
            try:
                result = dispatch(tool_name, tool_args)
                yield Event(EventType.TOOL_RESULT, {"result": result})
            except ToolError as e:
                yield Event(EventType.ERROR, {"message": str(e)})
                return
        elif "search" in user_message.lower():
            tool_name = "search"
            tool_args = {"query": user_message.split("search")[-1].strip()}
            yield Event(EventType.TOOL_CALL, {"name": tool_name, "args": tool_args})
            try:
                result = dispatch(tool_name, tool_args)
                yield Event(EventType.TOOL_RESULT, {"result": result})
            except ToolError as e:
                yield Event(EventType.ERROR, {"message": str(e)})
                return

        # Call the chat model
        response = chat(_state.messages, model=DEFAULT_MODEL)
        reply = response["content"]
        _state.add("assistant", reply)
        yield Event(EventType.COMPLETED, {"content": reply})

    except Exception as e:
        yield Event(EventType.ERROR, {"message": str(e)})


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """
    TODO: wrap run_turn(req.message) in a generator that calls
    `.to_sse()` on each Event and yields the resulting string, then
    return StreamingResponse(that_generator(), media_type="text/event-stream").
    """
    def event_generator():
        for event in run_turn(req.message):
            yield event.to_sse()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
