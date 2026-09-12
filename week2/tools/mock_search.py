"""search -- canned/fake search results, no real network call.

This stands in for a real web-search tool (Week 3 wires up something
closer to the real thing). The point of including it here isn't realism --
it's making sure exercise 1's dispatcher is tested against a 4th tool
shape that isn't just "another calculator-like function," so the registry
design actually gets exercised, not just repeated on similar inputs.
"""
from __future__ import annotations

from pydantic import BaseModel

from .registry import register


class SearchArgs(BaseModel):
    query: str


@register("search", SearchArgs)
def search(args: SearchArgs) -> str:
    """
    TODO: return a small fixed set of fake "search results" as one string
    (e.g. 2-3 fake title/snippet pairs). It's fine for the content to
    always be the same regardless of args.query, or to lightly reference
    args.query in the fake results -- either is enough for this exercise.
    """
    raise NotImplementedError
