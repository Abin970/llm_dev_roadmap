"""merge_node -- joins the two parallel search branches' evidence before
synthesis.

TODO: with the `evidence` reducer in state.py already combining both
branches' contributions by the time this node runs, this node might not
need to do much beyond returning an empty/no-op partial update --
LangGraph guarantees merge_node only runs once BOTH search_docs_node and
search_web_node have completed (a node with multiple incoming edges
waits for all of them before its step runs; that's the graph's topology
in graph.py doing the actual guaranteeing, not this function's body).

Use this node for any extra shaping you want (dedup near-identical
evidence strings, truncate an overly long list before it hits the
Synthesizer's prompt) -- optional, not required for the graph to work.

    def merge_node(state: GraphState) -> dict:
        ...
"""
from __future__ import annotations

from ..state import GraphState


def merge_node(state: GraphState) -> dict:
     
     
     return {}