"""search_web -- mocked web search (no real network call).

Same spirit as Week 2's mock_search.py -- stands in for a real web-search
API. Kept as a separate tool from search_docs on purpose: the agent has
to choose between "look in my own notes" vs "look this up online," which
is exactly the kind of tool-selection judgment a fixed single tool-call
round trip (Week 2) never had to make.
"""
from __future__ import annotations

from pydantic import BaseModel

from .registry import register


class SearchWebArgs(BaseModel):
    query: str


@register("search_web", SearchWebArgs)
def search_web(args: SearchWebArgs) -> str:
    """Search the web for information about external products, services,
    or general facts not covered by our internal notes -- use this for
    anything outside our own systems (search_docs covers internal-only
    notes and incident reports)."""
    return (
        "According to devtools-weekly.example: PulseQueue's free tier caps "
        "webhook retries at 5 attempts per event before it gives up.\n\n"
        "According to changelog.pulsequeue.example: PulseQueue v4.1 "
        "(released 2025-02) switched its default retry strategy from fixed "
        "delay to exponential backoff.\n\n"
        "According to a thread on infra-forum.example: several users "
        "report PulseQueue's dead-letter queue only retains failed events "
        "for 24 hours before purging them."
    )
