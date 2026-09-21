"""planner_node -- decides what to investigate for an on-call question.

TODO: given state["question"] (and, on a retry, the previous
state["review_verdict"] telling you *why* the last synthesis was
rejected), produce a short investigation plan -- what service/incident
keywords to search for -- and return it as the `plan` state update. Also
responsible for bumping `retry_count` on every call (including the
first), since the conditional edge after reviewer_node reads this field
to enforce the max-retries cap (see graph.py).

Node function signature (confirmed LangGraph convention): a node is a
plain function, state in -> a PARTIAL state dict out (only the keys
you're changing) -- LangGraph merges it into the running state for you.
Never mutate the incoming `state` argument directly.

    def planner_node(state: GraphState) -> dict:
        retry_count = state.get("retry_count", 0) + 1
        ...
        return {"plan": ..., "retry_count": retry_count}

Can call the LLM directly (llm_client.chat -- no tools needed here, this
node only *plans*, it doesn't execute searches itself) or use a simple
heuristic (e.g. just echo the question as the plan) if that's enough to
unblock the rest of the graph while you're first getting the topology
working end to end -- upgrade to an LLM-written plan once the graph
shape itself is proven out.
"""
from __future__ import annotations

from ..state import GraphState


def planner_node(state: GraphState) -> dict:
    raise NotImplementedError
