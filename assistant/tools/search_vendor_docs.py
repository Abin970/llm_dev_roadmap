"""search_vendor_docs -- search the official documentation for the
technologies in our stack (doc_type == "vendor_doc").

Weeks 3-4: this was `search_web`, a keyword mock over three made-up "web
pages" (PoolGuard, BackoffKit, PulseQueue). Week 5 retires that fixture.
This tool now searches the real vendor docs that ingestion/fetch.py
downloads: NGINX, Gunicorn, Uvicorn, Redis, PostgreSQL, Kafka, Docker,
Kubernetes, Fluent Bit, Prometheus and OpenTelemetry.

The split with search_docs keeps Week 4's design:
  - search_docs answers "what happened / what do I do" (runbooks,
    postmortems)
  - this tool answers "what does the tool actually support / how is it
    configured"
The synthesizer has to combine the two instead of reading a fix off
either one.

TODO (yours, once retrieval.py works). The body is the same call as
search_docs.py, with a different filter:

    hits = retrieve(args.query, k=TOP_K, doc_types=("vendor_doc",))
    return format_hits(hits)

The handler's DOCSTRING below isn't documentation for you. It's the tool
description the LLM reads when choosing tools: registry.py's
to_openai_tools() sends `handler.__doc__`. Keep it accurate if you
change what this tool searches.
"""
from __future__ import annotations

from pydantic import BaseModel

from .registry import register

TOP_K = 5


class SearchVendorDocsArgs(BaseModel):
    query: str


@register("search_vendor_docs", SearchVendorDocsArgs)
def search_vendor_docs(args: SearchVendorDocsArgs) -> str:
    """Search the official documentation for the technologies in our
    stack: NGINX (load balancing, proxying, rate limiting), Gunicorn and
    Uvicorn (app servers), Redis (cache), PostgreSQL (database), Kafka
    (message queue), Docker (containers), Kubernetes (orchestration),
    Fluent Bit (log shipping), Prometheus and OpenTelemetry (monitoring).
    Use it to find how a component behaves, what a setting, metric or
    error means, and which configuration options exist. For alert
    runbooks and past incidents, use search_docs instead."""
    raise NotImplementedError(
        "Week 5 TODO: retrieve(args.query, doc_types=('vendor_doc',)) -- see this module's docstring"
    )
