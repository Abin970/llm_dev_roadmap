"""reviewer_node -- the grounding/hallucination check, wired directly
into the graph as the artifact's Week 4 "bounded retry loop" exercise.

TODO: check whether every factual claim in state["synthesis"] actually
traces back to something present in state["evidence"] -- the same
grounding-check idea discussed at the end of Week 3's 03_break_it, now a
real graph node instead of a standalone eval script (and also exactly
what week4/experiments/eval_checks.py's check_grounding() verifies from
the outside, after the fact). A rejected synthesis routes back to
planner_node via the conditional edge in graph.py, capped at MAX_RETRIES
before a forced best-effort answer.

    def reviewer_node(state: GraphState) -> dict:
        ...
        return {"review_verdict": "approved"}   # or "rejected: <why>"

Can be LLM-judged (ask a model "does every claim below trace to the
evidence above?") or done with a cheaper heuristic (keyword/entity
overlap between synthesis and evidence). An LLM judge is more faithful
to what "grounding" actually means; a heuristic is fully deterministic,
which is genuinely useful for 02_retry_guard.py's experiment (you'll
stub this node out entirely there to force rejections regardless of
input). Pick one and note the choice -- eval_checks.py's
check_grounding() needs different code depending on which you pick.
"""
from __future__ import annotations

from ..state import GraphState


def reviewer_node(state: GraphState) -> dict:
    raise NotImplementedError
