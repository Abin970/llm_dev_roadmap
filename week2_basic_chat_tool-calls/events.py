"""Typed events for LLM/tool activity.

Why this exists: instead of a function that just returns a final string,
every meaningful step (call started, a text fragment arrived, a tool was
called, a tool returned, the whole thing finished, something errored) gets
modeled as its own typed object. That's what lets main.py stream progress
to a client over SSE, and it's the same shape Week 7's tracing will consume
-- build the habit now.

Backend lens: this is the same shape as a domain event in an event-sourced
system (think Kafka event types) -- nothing LLM-specific about the pattern
itself, only about which event types exist.

TODO: fill in EventType and Event below.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


# TODO: one member per meaningful step in a /chat request's lifecycle.
# At minimum: STARTED, TOKEN_DELTA, TOOL_CALL, TOOL_RESULT, COMPLETED, ERROR.
class EventType(str, Enum):
  STARTED = "STARTED"
  TOKEN_DELTA = "TOKEN_DELTA"
  TOOL_CALL = "TOOL_CALL"
  TOOL_RESULT = "TOOL_RESULT"
  COMPLETED = "COMPLETED"
  ERROR = "ERROR"


@dataclass
class Event:
    """
    TODO:
      - two fields: `type: EventType` and `data: dict[str, Any]` (the
        payload shape differs per type -- e.g. TOKEN_DELTA carries the
        text fragment, TOOL_CALL carries {"name": ..., "args": ...},
        ERROR carries {"message": ...} -- that's fine, `data` is
        deliberately loose so one Event shape covers every type)
      - a `to_sse(self) -> str` method that formats this event as one
        Server-Sent-Events message. SSE wire format is:
            event: <type>\\ndata: <json>\\n\\n
        (two trailing newlines terminate the message). Use
        `json.dumps(self.data)` for the data line.
    """
    type: EventType
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Format this event as a Server-Sent-Events message."""
        return f"event: {self.type.value}\ndata: {json.dumps(self.data)}\n\n"
