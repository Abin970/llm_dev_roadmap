"""
Experiment 2 -- Retry guard actually trips
===========================================
Objective  : prove the Planner<->Reviewer retry loop is bounded, not
             infinite -- the same "no max_iterations guard" incident
             from Week 3, now expressed as graph topology instead of a
             while loop. Two complementary tests, since they check
             different things:

  (a) patched reviewer_node, always rejects -- a DETERMINISTIC test of
      the retry-cap TOPOLOGY itself, with the LLM's own judgment removed
      from the picture entirely. Proves the graph structure can't loop
      forever, full stop, regardless of what any reviewer decides.
  (b) a genuinely unanswerable question (EVAL_CASES[3]), run through the
      REAL, LLM-judged reviewer -- a realistic end-to-end test of
      whether the actual grounding check does its job. Not guaranteed
      deterministic (the LLM might approve a weak synthesis anyway --
      that's exactly the kind of unreliability this project has been
      probing all along), but it's the only one of the two that
      exercises reviewer_node's actual judgment.

Setup      : (a) needs GraphAgent() instantiated INSIDE the
             `with patch.object(...)` block -- agent/graph.py rebuilds
             the graph fresh in __init__ specifically so this patch can
             take effect (see _build_compiled_graph's docstring there
             for why building once at import time would have prevented
             this entirely).

Run: python experiments/02_retry_guard.py
"""
import uuid
from unittest.mock import patch

import _bootstrap  # noqa: F401

import agent.graph as graph_module
from agent.graph import GraphAgent
from events import EventType
from eval_cases import EVAL_CASES
import eval_checks as ec

UNANSWERABLE_CASE = EVAL_CASES[3]


def always_reject(state: dict) -> dict:
    return {"review_verdict": "rejected: forced for this experiment"}


def _final_review_verdict(trace: list) -> str | None:
    verdicts = [
        e.data["update"]["review_verdict"]
        for e in trace
        if e.type == EventType.NODE_UPDATE and e.data.get("node") == "reviewer"
    ]
    return verdicts[-1] if verdicts else None


def run_patched_reviewer() -> None:
    print("=== (a) patched reviewer_node, always rejects ===")
    with patch.object(graph_module, "reviewer_node", always_reject):
        thread_id = str(uuid.uuid4())
        trace = list(GraphAgent().run(UNANSWERABLE_CASE.question, thread_id=thread_id))

    for event in trace:
        print(event)
    print(ec.check_retry_bound(trace, max_retries=2))
    print()


def run_unanswerable_question() -> None:
    print("=== (b) real reviewer, genuinely unanswerable question ===")
    thread_id = str(uuid.uuid4())
    trace = list(GraphAgent().run(UNANSWERABLE_CASE.question, thread_id=thread_id))

    for event in trace:
        print(event)
    print(ec.check_retry_bound(trace, max_retries=2))

    approved = _final_review_verdict(trace) == "approved"
    if approved == UNANSWERABLE_CASE.expect_approved:
        print(f"expect_approved matched: got approved={approved}")
    else:
        print(f"MISMATCH: expected expect_approved={UNANSWERABLE_CASE.expect_approved}, got approved={approved}")
    print()


def main() -> None:
    run_patched_reviewer()
    run_unanswerable_question()


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# (a) Did the patched run stop at exactly MAX_RETRIES (2) planner calls,
# never more? This should be 100% repeatable across runs.
# (b) Did the REAL reviewer correctly refuse to approve a synthesis with
# no real evidence behind it, or did it hallucinate a plausible-sounding
# answer anyway? Either outcome is informative here -- that's the whole
# point of testing the actual judgment instead of just the topology.
