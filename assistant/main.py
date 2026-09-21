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

from typing import Iterator

import tools  # noqa: F401 -- importing this registers all 6 tools
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent.graph import GraphAgent
from agent.loop import AgentLoop
from conversation import ConversationState
from events import Event, EventType
from llm_client import DEFAULT_MODEL, chat
from tools.registry import ToolError, dispatch

app = FastAPI()

# A real app would key this per session/user; one shared state is fine
# for this exercise, since there's only ever one caller (you, via curl).
_state = ConversationState()


class ChatRequest(BaseModel):
    message: str


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


def run_turn(user_message: str) -> Iterator[Event]:
    """Carried over from week2 -- still your TODO if you haven't done it
    yet. See week2/main.py's original docstring for the step-by-step."""
    raise NotImplementedError


@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Carried over from week2 -- still your TODO if you haven't done it
    yet."""
    raise NotImplementedError


@app.post("/research")
async def research_endpoint(req: ChatRequest):
    """New this week.

    TODO: wrap AgentLoop().run(req.message) the same way chat_endpoint is
    meant to wrap run_turn -- call `.to_sse()` on each yielded Event and
    return StreamingResponse(that_generator(), media_type=
    "text/event-stream"). Unlike /chat, this doesn't need ConversationState
    -- each research question is independent, no multi-turn history.
    """
    raise NotImplementedError


@app.post("/research/resume")
async def research_resume_endpoint(req: ResumeRequest):
    """New in Week 4 -- resumes a /research run that paused at
    GraphAgent's apply_fix_node interrupt(), waiting on a human decision.

    TODO: wrap GraphAgent().resume(req.thread_id, {"approved": req.approved})
    the same way /research wraps AgentLoop().run(...) -- stream Events
    over SSE identically. The client needs req.thread_id from whatever
    "paused" event /research emitted when the original run suspended, so
    that event's payload has to carry it -- decide that shape in
    agent/graph.py's GraphAgent.run() before this endpoint can work.
    """
    raise NotImplementedError
