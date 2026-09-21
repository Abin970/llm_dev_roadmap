"""search_docs_node / search_web_node -- the parallel evidence-gathering
branch of the graph (fan-out from planner_node, fan-in at merge_node).

TODO: each node calls the SAME tool machinery Week 3 already built
(`tools.registry.dispatch`), not a redefinition of search logic -- reuse
`dispatch("search_docs", {"query": ...})` / `dispatch("search_web",
{"query": ...})`, building the query from state["plan"] (or
state["question"]).

Confirmed via LangGraph API research: for a FIXED, known-in-advance pair
of parallel branches like this one (as opposed to a dynamic/variable
number of branches, which would need `langgraph.types.Send`), plain graph
topology is enough -- graph.py just adds two edges out of planner_node
(one to each of these) and two edges from these into merge_node;
LangGraph runs both in the same step automatically, no extra code here.
The one thing that ISN'T automatic: state["evidence"] needs the reducer
from state.py, or whichever of these two nodes finishes last silently
overwrites the other's contribution.

    def search_docs_node(state: GraphState) -> dict:
        try:
            result = dispatch("search_docs", {"query": ...})
        except ToolError as e:
            result = f"error: {e}"
        return {"evidence": [f"[search_docs] {result}"]}   # one-item list --
            # the reducer in state.py is what appends this to the other
            # branch's contribution instead of replacing it

Tag each evidence string with its source (as above) -- reviewer_node and
synthesizer_node need to tell a postmortem doc apart from a tool-config
doc when deciding whether a claim is actually grounded.
"""
from __future__ import annotations

from tools.registry import ToolError, dispatch

from ..state import GraphState


def search_docs_node(state: GraphState) -> dict:
    raise NotImplementedError


def search_web_node(state: GraphState) -> dict:
    raise NotImplementedError
