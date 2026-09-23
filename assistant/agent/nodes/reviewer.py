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

import re

from pydantic import BaseModel

from llm_client import chat_structured

from ..state import GraphState


class GroundingVerdict(BaseModel):
    grounded: bool
    reason: str


def llm_review(synthesis: str, evidence: list[str]) -> str:
    """LLM-judged grounding check: ask a model whether every claim in
    `synthesis` is actually supported by `evidence`. Uses
    chat_structured (schema-constrained output, Week 1) instead of
    parsing free text out of a plain chat() reply -- more reliable than
    regexing a yes/no out of prose, and it's exactly the kind of
    structured-output use case Week 1's exercises were building toward.
    """
    evidence_block = "\n".join(evidence) if evidence else "(no evidence retrieved)"
    messages = [
        {
            "role": "developer",
            "content": (
                "You are a strict fact-checker. Given a proposed "
                "root-cause/fix synthesis and the evidence it's supposed "
                "to be based on, decide whether EVERY factual claim in "
                "the synthesis is actually supported by the evidence. "
                "If the synthesis states anything the evidence doesn't "
                "support, it is NOT grounded, even if the claim sounds "
                "plausible."
            ),
        },
        {
            "role": "user",
            "content": f"Evidence:\n{evidence_block}\n\nSynthesis:\n{synthesis}",
        },
    ]
    verdict = chat_structured(messages, GroundingVerdict)
    if verdict is None:
        # Fail closed: no parseable verdict is treated as "not grounded"
        # rather than silently approving -- an unreviewable answer
        # shouldn't be able to reach apply_fix_node.
        return "rejected: llm judge returned no parseable verdict"
    if verdict.grounded:
        return "approved"
    return f"rejected: {verdict.reason}"


_WORD_RE = re.compile(r"\w+")


def _significant_words(text: str) -> set[str]:
    """Same 'what counts as a meaningful word' rule as search_docs.py /
    search_web.py's _word_weight -- digit-bearing or long (>4 chars)
    words carry the signal; short/common words are noise."""
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if any(c.isdigit() for c in w) or len(w) > 4}


def heuristic_review(synthesis: str, evidence: list[str]) -> str:
    """Deterministic grounding check, no LLM call: does the synthesis
    cite a source at all, and does it actually reuse enough of the
    evidence's own vocabulary? Cheaper and fully repeatable -- useful
    for 02_retry_guard.py, where you want rejections forceable without
    depending on a live model call.
    """
    if "[search_docs]" not in synthesis and "[search_web]" not in synthesis:
        return "rejected: synthesis cites no evidence source"

    evidence_words = _significant_words(" ".join(evidence))
    synthesis_words = _significant_words(synthesis)
    if not synthesis_words:
        return "rejected: synthesis has no substantive content to check"

    overlap_ratio = len(synthesis_words & evidence_words) / len(synthesis_words)

    MIN_OVERLAP = 0.5
    if overlap_ratio < MIN_OVERLAP:
        return (
            f"rejected: only {overlap_ratio:.0%} of the synthesis's "
            f"significant terms appear anywhere in the retrieved evidence"
        )
    return "approved"


def reviewer_node(state: GraphState) -> dict:
    # LLM-judged by default -- more faithful to what "grounding" means
    # than a keyword-overlap heuristic. Swap to heuristic_review(...) if
    # you want a fully deterministic reviewer (e.g. while isolating the
    # retry-loop topology itself from LLM variance). Whichever is live
    # here is the one eval_checks.check_grounding() should mirror.
    verdict = llm_review(state["synthesis"], state["evidence"])
    return {"review_verdict": verdict}
