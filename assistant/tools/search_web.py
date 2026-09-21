"""search_web -- mocked web search (no real network call).

Same spirit as Week 2's mock_search.py -- stands in for a real web-search
API. Kept as a separate tool from search_docs on purpose: the agent has
to choose between "look in my own notes" vs "look this up online," which
is exactly the kind of tool-selection judgment a fixed single tool-call
round trip (Week 2) never had to make.

Holds external tool/library documentation, not incident-specific advice
-- the idea is the agent has to combine "why an incident happened" (from
search_docs) with "what this library/tool actually supports" (from here)
and reason out a fix itself, rather than reading a fix off either source
directly.
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from .registry import register


def _word_weight(word: str) -> int:
    """Same scale as search_docs._word_weight -- kept as a separate copy
    on purpose so this module doesn't depend on search_docs's internals."""
    if any(c.isdigit() for c in word):
        return 2
    if len(word) > 4:
        return 1
    return 0


# Each entry is a fake "web page": (title, body). No incident-specific
# advice here on purpose -- just what the tool/library itself supports.
_WEB_DOCS = [
    (
        "poolguard-docs.example/config",
        "PoolGuard connection pool -- configuration reference. "
        "max_idle_time (default 30s) controls how quickly an idle "
        "connection is recycled; raising it keeps connections alive "
        "longer under bursty traffic. prewarm(n) opens n connections "
        "ahead of time, useful right before an expected load spike "
        "(e.g. a scheduled sale) instead of waiting for demand to "
        "create them on the fly.",
    ),
    (
        "backoffkit-docs.example/retries",
        "BackoffKit retry client -- configuration reference. "
        "max_retries caps how many attempts a single call gets. "
        "backoff_strategy can be 'fixed' or 'exponential' -- exponential "
        "spreads retries out over time instead of hammering the same "
        "instant. respect_rate_limit(True) makes the client read a "
        "provider's rate-limit response headers and throttle itself "
        "instead of retrying blindly into a 429.",
    ),
    (
        "devtools-weekly.example/pulsequeue",
        "PulseQueue's free tier caps webhook retries at 5 attempts per "
        "event before it gives up. PulseQueue v4.1 (released 2025-02) "
        "switched its default retry strategy from fixed delay to "
        "exponential backoff. Its dead-letter queue only retains failed "
        "events for 24 hours before purging them.",
    ),
]


class SearchWebArgs(BaseModel):
    query: str


@register("search_web", SearchWebArgs)
def search_web(args: SearchWebArgs) -> str:
    """Search the web for information about external products, services,
    or general facts not covered by our internal notes -- use this for
    anything outside our own systems (search_docs covers internal-only
    notes and incident reports)."""
    query_words = re.findall(r"\w+", args.query.lower())

    best_title, best_body, best_score = None, "", 0
    for title, body in _WEB_DOCS:
        body_lower = body.lower()
        score = sum(
            _word_weight(w)
            for w in set(query_words)
            if re.search(rf"\b{re.escape(w)}\b", body_lower)
        )
        if score > best_score:
            best_title, best_body, best_score = title, body, score

    if best_title is None or best_score < 2:
        return "(no relevant results)"

    return f"According to {best_title}: {best_body}"
