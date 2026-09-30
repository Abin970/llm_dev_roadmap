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

from llm_client import chat

def planner_node(state: GraphState) -> dict:
    retry_count = state.get("retry_count", 0) + 1
    messages = None
    if state.get("question"):
        question = state.get("question")

        messages = [
            {"role": "developer", "content": (
                "You are the planning step of an SRE on-call copilot. Given an "
                "incident question, output a short investigation plan: what "
                "service and what keywords to search for. Do not answer the "
                "question yourself -- only say what to look up."
            )},
            {"role": "user", "content": question},
        ]
    if state.get("review_verdict", "").startswith("rejected"):
        review_verdict = state.get("review_verdict")
        messages.append({
            "role": "user",
            "content": f"Previous attempt was rejected: {review_verdict}.Revise the plan.",
        })
    
    response_message = chat(messages=messages,max_tokens=2000, model="gpt-4.1-nano")
    
    return {"plan":response_message, "retry_count":retry_count}