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


# one member per meaningful step in a /chat request's lifecycle.
# At minimum: STARTED, TOKEN_DELTA, TOOL_CALL, TOOL_RESULT, COMPLETED, ERROR.
class EventType(str, Enum):
  STARTED = "STARTED"
  TOKEN_DELTA = "TOKEN_DELTA"
  TOOL_CALL = "TOOL_CALL"
  TOOL_RESULT = "TOOL_RESULT"
  NODE_UPDATE = "NODE_UPDATE"
  PAUSED = "PAUSED"
  COMPLETED = "COMPLETED"
  ERROR = "ERROR"


@dataclass
class Event:

    type: EventType
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Format this event as a Server-Sent-Events message."""
        def _default(obj):
           if hasattr(obj, "model_dump"):
              return obj.model_dump()
           return str(obj)
        return f"event: {self.type.value}\ndata: {json.dumps(self.data, default=_default)}\n\n"
