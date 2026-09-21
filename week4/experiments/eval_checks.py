"""eval_checks -- graph-specific verification, so "did this run actually
do the right thing" is something you run, not something you eyeball.

Week 3's 03_break_it exercise ended with manual verification: was the
question even answerable with the available tools, did the tool-call
sequence make sense. Week 4's graph adds failure modes that are even
less eyeball-friendly (branching, bounded retries, parallel fan-out,
checkpoint/resume), so this module codifies those checks instead of
re-eyeballing a trace by hand every time.

TODO: each function below takes whatever data it needs (a captured trace
-- the list of Events your experiment printed -- and/or graph state) and
returns SOME kind of pass/fail report (a bool, a small dataclass with a
`.ok` field and a `.reason` string, whatever's convenient to assert on or
print from the experiment scripts). The exact trace/state shapes depend
on how you designed GraphAgent.run()'s Event mapping in agent/graph.py --
these signatures are intentionally loose (`trace`, `state`) rather than
pinned to a specific type, since that mapping is your design decision to
make there, not here.
"""
from __future__ import annotations

from typing import Any


def check_tool_sequence(trace: list) -> Any:
    """Were the tools that ran (search_docs / search_web / sqlite_query)
    called in an order actually capable of answering the question --
    evidence gathered before synthesis, not after -- and was each call's
    args aimed at the right service/incident? Same manual check from
    Week 3's 03_break_it, codified instead of eyeballed."""
    raise NotImplementedError


def check_grounding(synthesis: str, evidence: list) -> Any:
    """Does every factual claim in `synthesis` trace back to something
    actually present in `evidence`, or did it fabricate a detail not
    supported by anything retrieved? This is the same check
    reviewer_node (assistant/agent/nodes/reviewer.py) makes INSIDE the
    graph -- this version verifies it from the OUTSIDE, after the fact,
    so a bug in reviewer_node's own grounding logic doesn't go unnoticed
    just because the graph "worked" (i.e. reached an approved verdict)."""
    raise NotImplementedError


def check_retry_bound(trace: list, max_retries: int) -> Any:
    """Count how many times planner_node re-ran in `trace` and confirm
    it never exceeds `max_retries` -- the artifact's edge-case test (a
    Reviewer-always-rejects stub, see 02_retry_guard.py, must
    force-terminate, not loop forever)."""
    raise NotImplementedError


def check_parallel_evidence_complete(state: dict) -> Any:
    """After the search_docs_node / search_web_node fan-out, does
    state["evidence"] actually contain contributions from BOTH branches,
    not just whichever one happened to finish last? Catches the
    artifact's called-out failure mode: a state field two parallel nodes
    both write with no reducer, where one silently overwrites the
    other."""
    raise NotImplementedError


def check_resume_consistency(state_before_interrupt: dict, state_after_resume: dict) -> Any:
    """Does a checkpoint-and-resume run (03_human_approval.py) produce a
    continuation consistent with the human decision it was given -- i.e.
    resuming with approved=True actually shows the fix as applied in the
    post-resume state, and approved=False shows it as skipped. The
    artifact's Week 4 acceptance criterion, made runnable instead of
    eyeballed."""
    raise NotImplementedError
