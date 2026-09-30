"""EvalCase -- a small golden/labeled dataset for eval_checks.py's
question-specific checks.

Most of eval_checks.py's checks (retry bound, grounding, parallel
evidence completeness, resume consistency) verify the GRAPH'S MACHINERY
and hold no matter what question was asked. check_tool_sequence is
different: "was the right evidence actually found" only means something
relative to what a specific question needed -- so it needs a reference
answer to compare against, not just a trace on its own.

Week 5 rewrite (2026-09-30): these cases used to be built against Week
3-4's made-up fixtures (tools/docs/*.md, search_web's three fake pages),
which Week 5 retired. They're now built on real passages in the fetched
corpus, the same ones week5_rag_fundamentals/experiments/golden_retrieval.py
points at (db-02, xl-03, orch-01/orch-02, na-01). Each index keeps its
old role, because the experiments pick cases by position:
    [1] 03_human_approval.py -- needs a config-style fix for apply_fix
    [2] 01_loop_vs_graph.py
    [3] 02_retry_guard.py    -- the unanswerable one
They only produce real evidence once Week 5's retrieval is implemented.
Until then both search tools return "error: ... TODO" and these cases
fail check_tool_sequence's keyword part, which is expected.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalCase:
    question: str
    expected_tools: set[str]
    expected_evidence_keywords: list[str]
    expect_approved: bool


EVAL_CASES = [
    EvalCase(
        question=(
            "Postgres started rejecting all writes with a hint to run a "
            "database-wide VACUUM, while reads still work -- what's the "
            "root cause and how do we recover?"
        ),
        expected_tools={"search_docs", "search_vendor_docs"},
        # search_docs: Sentry / Mandrill transaction-ID-wraparound postmortems
        # search_vendor_docs: postgres routine-vacuuming, 24.1.5
        expected_evidence_keywords=["wraparound", "vacuum"],
        expect_approved=True,
    ),
    EvalCase(
        question=(
            "Our Postgres schema migrations keep blocking every query on "
            "busy tables until they finish -- what should we change?"
        ),
        expected_tools={"search_docs", "search_vendor_docs"},
        # search_docs: GoCardless postmortem ("Set lock_timeout in your
        #   migration scripts...")
        # search_vendor_docs: postgres runtime-config-client (lock_timeout),
        #   explicit-locking (ACCESS EXCLUSIVE)
        # A config-style fix -- service=postgres, config_key=lock_timeout --
        # which is what 03_human_approval.py's apply_fix gate needs.
        expected_evidence_keywords=["lock_timeout", "migration"],
        expect_approved=True,
    ),
    EvalCase(
        question=(
            "KubePodCrashLooping keeps firing for our API pods and kubectl "
            "describe shows the containers were OOM killed -- what's the "
            "root cause and what should we change?"
        ),
        expected_tools={"search_docs", "search_vendor_docs"},
        # search_docs: runbooks/kubernetes/KubePodCrashLooping.md
        # search_vendor_docs: kubernetes manage-resources-containers
        #   ("memory limits are enforced by the kernel with out of memory
        #   (OOM) kills")
        expected_evidence_keywords=["crashloop", "memory"],
        expect_approved=True,
    ),
    EvalCase(
        # Nothing in the corpus covers MongoDB (verified: zero mentions of
        # MongoDB or WiredTiger). Same role as Week 3's 03_break_it
        # "unanswerable question": the reviewer should REJECT rather than
        # approve a plausible-sounding fix. New since real retrieval: with
        # no similarity floor yet (Week 6), the retriever still returns k
        # chunks, most likely Redis eviction or Postgres memory pages. A
        # synthesis built on those can be "grounded in the evidence" while
        # answering about the wrong system -- watch whether the reviewer
        # catches that.
        question=(
            "Our MongoDB replica set's WiredTiger cache keeps filling up and "
            "evicting hot data -- what should we change?"
        ),
        expected_tools={"search_docs", "search_vendor_docs"},
        expected_evidence_keywords=[],
        expect_approved=False,
    ),
]
