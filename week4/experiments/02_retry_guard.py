"""
Experiment 2 -- Retry guard actually trips
===========================================
Objective  : prove the Planner<->Reviewer retry loop is bounded, not
             infinite -- the same "no max_iterations guard" incident from
             Week 3, now expressed as graph topology instead of a while
             loop, so it needs its own proof.
Setup      : stub reviewer_node to ALWAYS return
             review_verdict="rejected", then run the graph and confirm it
             still terminates at MAX_RETRIES instead of looping forever.
Teaches    : loop guards are graph topology now -- testable in isolation,
             without needing a real LLM call to force the failure case.

Run: python experiments/02_retry_guard.py
"""
import uuid
from unittest.mock import patch

import _bootstrap  # noqa: F401

import agent.graph as graph_module
from agent.graph import GraphAgent

# TODO: any question -- the point of this experiment is the Reviewer
# stub always rejecting, not the question's content.
QUESTION = "..."


def always_reject(state: dict) -> dict:
    return {"review_verdict": "rejected: forced for this experiment"}


def main() -> None:
    # NOTE: agent/graph.py does `from .nodes.reviewer import reviewer_node`,
    # which binds a NAME in agent.graph's own namespace at import time --
    # patching agent.nodes.reviewer.reviewer_node afterward won't affect a
    # graph that's already wired up with the original reference. Patch
    # the name as graph.py sees it (`agent.graph.reviewer_node`) instead,
    # BEFORE building/compiling the graph -- if GraphAgent builds its
    # graph once at import time rather than per-instance, you may need to
    # patch before importing agent.graph at all, or give GraphAgent a way
    # to rebuild after patching.
    with patch.object(graph_module, "reviewer_node", always_reject):
        thread_id = str(uuid.uuid4())
        for event in GraphAgent().run(QUESTION, thread_id=thread_id):
            print(event)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did the run actually stop at MAX_RETRIES (2), or keep looping? Count how
# many times planner_node re-ran in the trace above and confirm it
# matches -- feed the trace into eval_checks.check_retry_bound() once
# that's implemented.
