"""GraphState -- the typed state shared across every node in the SRE
on-call graph (graph.py).

LangGraph state is a schema (TypedDict or a pydantic.BaseModel -- both
are supported, confirmed against the pinned `langgraph` version) with
each node returning only the fields it changes (a PARTIAL state dict) --
LangGraph merges that partial update into the running state for you
between each node; nodes never mutate the incoming state directly.

The one thing that ISN'T automatic: when two nodes can run in the same
step and both write to the SAME field -- this graph's parallel
`search_docs_node` / `search_web_node` both need to add to `evidence` --
plain assignment is last-write-wins: whichever branch's partial update is
applied second silently clobbers the other's. Fix: mark that field with a
reducer, confirmed syntax:

    from typing_extensions import TypedDict, Annotated
    import operator

    class GraphState(TypedDict):
        evidence: Annotated[list[str], operator.add]   # merged, not overwritten

Without the `Annotated[..., operator.add]`, a state field two parallel
nodes both write is exactly the artifact's own called-out mistake: "no
reducer on a field two parallel nodes both write -- one branch's result
silently overwrites the other's."

TODO: fill in the field types below (most don't need a reducer -- only
`evidence` is written by more than one node in the same step) --

  - question       : str -- the on-call question this run is investigating
  - plan           : str -- planner_node's decision about what to look up
  - evidence       : list[str], WRITTEN BY BOTH search_docs_node and
                     search_web_node in the same step -- needs the
                     reducer above, or one branch's contribution vanishes
  - synthesis      : str -- synthesizer_node's proposed root cause + fix
  - review_verdict : str -- reviewer_node's "approved" or "rejected: ..."
  - retry_count    : int -- bumped by planner_node on every (re)plan;
                     read by the conditional edge after reviewer_node to
                     enforce the max-retries cap (see graph.py)
  - pending_action : dict | None -- the risky action (if any) currently
                     awaiting human approval via apply_fix_node's
                     interrupt() call
"""
from __future__ import annotations

from typing_extensions import Annotated, TypedDict


class GraphState(TypedDict):
    question: str
    plan: str
    evidence: list  # TODO: needs a reducer -- see the module docstring above
    synthesis: str
    review_verdict: str
    retry_count: int
    pending_action: dict | None
