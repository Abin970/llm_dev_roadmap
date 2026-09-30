"""search_docs -- search the on-call knowledge base: per-alert runbooks
and real incident postmortems (doc_type in {"runbook", "postmortem"}).

Weeks 3-4: keyword matching over 7 made-up incident notes in tools/docs/.
Week 5 retires those notes and makes this real retrieval over the fetched
corpus (ingestion/sources.py lists exactly what's in it).

The Week 3 keyword scorer isn't thrown away. `keyword_rank()` below keeps
the same scoring rule (identifier-looking words count double, long words
count once, short words not at all) but ranks ANY list of texts. It's
experiment 01's baseline: dense retrieval has to beat it on the golden
set to justify itself. Where it doesn't (questions that name an exact
alert or config key) is exactly the gap Week 6's hybrid search closes.

TODO (yours, once retrieval.py works). The handler body:

    hits = retrieve(args.query, k=TOP_K, doc_types=("runbook", "postmortem"))
    return format_hits(hits)

Same note as search_vendor_docs.py: the handler's docstring is the
LLM-facing tool description (registry.to_openai_tools() sends it).
"""
from __future__ import annotations

import re

from pydantic import BaseModel

from .registry import register

TOP_K = 5
_WORD_RE = re.compile(r"\w+")


def _word_weight(word: str) -> int:
    """Specific identifiers (contain a digit) outweigh long words, which
    outweigh short/common ones -- the Week 3 stand-in for relevance."""
    if any(c.isdigit() for c in word):
        return 2
    if len(word) > 4:
        return 1
    return 0


def keyword_rank(query: str, texts: list[str], k: int) -> list[tuple[int, int]]:
    """Rank `texts` by the Week 3 keyword score. Returns up to k
    (index into texts, score) pairs, best first, with zero scores
    dropped. Whole-word matching, the same as the old `\\b...\\b` regex:
    `\\w+` tokens split on the same boundaries, so max_connections stays
    one token. Plumbing for experiment 01's baseline."""
    query_words = {w for w in _WORD_RE.findall(query.lower()) if _word_weight(w)}
    scored = []
    for i, text in enumerate(texts):
        present = set(_WORD_RE.findall(text.lower()))
        score = sum(_word_weight(w) for w in query_words if w in present)
        if score:
            scored.append((i, score))
    scored.sort(key=lambda pair: -pair[1])
    return scored[:k]


class SearchDocsArgs(BaseModel):
    query: str


@register("search_docs", SearchDocsArgs)
def search_docs(args: SearchDocsArgs) -> str:
    """Search our on-call knowledge base: per-alert runbooks (what an
    alert means, its impact, how to diagnose and mitigate it) and real
    incident postmortems from other companies (what went wrong, how it
    was found and fixed). Use it for "what does this alert mean / what
    should I do" and "has this kind of failure happened before"
    questions. For how a specific technology behaves or is configured,
    use search_vendor_docs instead."""
    raise NotImplementedError(
        "Week 5 TODO: retrieve(args.query, doc_types=('runbook', 'postmortem')) -- see this module's docstring"
    )
