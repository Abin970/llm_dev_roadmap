"""eval_checks -- graph-specific verification, so "did this run actually
do the right thing" is something you run, not something you eyeball.

Week 3's 03_break_it exercise ended with manual verification: was the
question even answerable with the available tools, did the tool-call
sequence make sense. Week 4's graph adds failure modes that are even
less eyeball-friendly (branching, bounded retries, parallel fan-out,
checkpoint/resume), so this module codifies those checks instead of
re-eyeballing a trace by hand every time.

TODO:(completed) each function below takes whatever data it needs (a captured trace
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
from dataclasses import dataclass
from typing import Any
from events import Event, EventType
from eval_cases import EvalCase


@dataclass
class CheckResult:
    ok: bool
    reason: str


def _tool_result_sequence(trace: list[Event]) -> list[str]:
    return  [e.data["name"] for e in trace if e.type == EventType.TOOL_RESULT]

def _tool_result_names(trace: list[Event]) -> list[str]:
    return [e.data["name"] for e in trace if e.type == EventType.TOOL_RESULT]

def _node_updates(trace: list[Event], node: str) ->list[dict]:
    return [
        e.data["update"]
        for e in trace if e.type == EventType.NODE_UPDATE and e.data.get("node") == node
    ]

# Event(EventType.NODE_UPDATE, {"node": "planner", "update": {"plan": "...", "retry_count": 1}})
# Event(EventType.TOOL_RESULT, {"name": "search_vendor_docs", "result": ["[search_vendor_docs] ..."]})
# Event(EventType.TOOL_RESULT, {"name": "search_docs", "result": ["[search_docs] ..."]})
# Event(EventType.NODE_UPDATE, {"node": "merge", "update": {}})


def check_tool_sequence(trace: list[Event], case: EvalCase) -> CheckResult:
     """Were the tools that ran (search_docs / search_vendor_docs) the ones this
     EvalCase expects, called before synthesis started (not after), and
     did the evidence they returned actually mention what this specific
     question needed? Same manual check from Week 3's 03_break_it,
     codified against a reference answer instead of eyeballed."""

     called = set(_tool_result_sequence(trace))
     if called != case.expected_tools: #set comparison
        return CheckResult(False, f"expected tools{case.expected_tools}, tools actaully called {called}")

     tool_indices = [ 
         i for i,e in enumerate(trace) if e.type == EventType.TOOL_RESULT
     ]
     synth_indices = [
          i for i,e in enumerate(trace) if e.type == EventType.NODE_UPDATE and e.data["node"] == "synthesizer"
     ]

     if tool_indices and synth_indices and max(tool_indices) > min(synth_indices):
         return CheckResult(False,"a tool result arrived after synthesis had already started")

     if case.expected_evidence_keywords:
         evidence_text = " ".join(
             str(item)
             for e in trace if e.type == EventType.TOOL_RESULT
             for item in e.data.get("result",[])
         ).lower()

         missing = [kw for kw in case.expected_evidence_keywords if kw.lower() not in evidence_text]
         if missing:
            return CheckResult(False, f"evidence never mentions: {missing}")
         
     return CheckResult(True, "tool usage and evidence content match this case's expectations")
     

import re

_WORD_RE = re.compile(r"\w+")


def _significant_words(text: str) -> set[str]:
    """Same 'what counts as a meaningful word' rule used in
    search_docs.py / reviewer.py -- kept as an
    independent copy on purpose, so a bug in reviewer_node's own
    grounding logic can't hide behind this external check reusing the
    exact same code."""
    words = _WORD_RE.findall(text.lower())
    return {w for w in words if any(c.isdigit() for c in w) or len(w) > 4}



def check_grounding(synthesis_text: str, evidence: list) -> Any:
     """Does every factual claim in `synthesis_text` trace back to
     something actually present in `evidence`, or did it fabricate a
     detail not supported by anything retrieved? This is the same check
     reviewer_node (assistant/agent/nodes/reviewer.py) makes INSIDE the
     graph -- this version verifies it from the OUTSIDE, after the fact,
     with its own independent implementation, so a bug in reviewer_node's
     own grounding logic doesn't go unnoticed just because the graph
     "worked" (i.e. reached an approved verdict).

     `synthesis_text` is the prose field -- if synthesizer_node returns a
     structured ApplyFixesArgs, pass its `.response_message` (or
     `["response_message"]` if it's already been through model_dump()),
     not the whole object.
     """

     if not synthesis_text:
        return CheckResult(False, "synthesis is empty")
     if "[search_docs]" not in synthesis_text and "[search_vendor_docs]" not in synthesis_text:
        return CheckResult(False, "synthesis cites no evidence source")

     evidence_words = _significant_words(" ".join(evidence))
     synthesis_words = _significant_words(synthesis_text)
     if not synthesis_words:
        return CheckResult(False, "synthesis has no substantive content to check")

     overlap_ratio = len(synthesis_words & evidence_words) / len(synthesis_words)
     MIN_OVERLAP = 0.5
     if overlap_ratio < MIN_OVERLAP:
        return CheckResult(
            False,
            f"only {overlap_ratio:.0%} of the synthesis's significant terms "
            f"appear anywhere in the retrieved evidence",
        )
     return CheckResult(True, f"{overlap_ratio:.0%} of synthesis's terms are grounded in evidence")
     


def check_retry_bound(trace: list[Event], max_retries: int) -> Any:
     """Count how many times planner_node re-ran in `trace` and confirm
    it never exceeds `max_retries` -- the artifact's edge-case test (a
    Reviewer-always-rejects stub, see 02_retry_guard.py, must
    force-terminate, not loop forever)."""
     planner_runs = len(_node_updates(trace, "planner"))
     if planner_runs > max_retries:
        return CheckResult(
            False, f"planner ran {planner_runs} times, exceeding max_retries={max_retries}"
        )
     return CheckResult(True, f"planner ran {planner_runs} time(s), within max_retries={max_retries}")


def check_parallel_evidence_complete(trace: list[Event]) -> CheckResult:
     """After the search_docs_node / search_vendor_docs_node fan-out, does
    state["evidence"] actually contain contributions from BOTH branches?
    With the reducer in place this should always hold -- without one,
    the graph wouldn't even run (LangGraph raises InvalidUpdateError for
    a field two parallel nodes both write with no reducer, verified
    directly, rather than silently letting one overwrite the other).
    This check is a regression guard on the reducer staying correctly
    declared, not a defense against a silent runtime failure."""
     names = _tool_result_names(trace)
     docs_count = names.count("search_docs")
     web_count = names.count("search_vendor_docs")
     if docs_count == 0 or web_count == 0:
        return CheckResult(
            False,
            f"one branch never contributed evidence (search_docs={docs_count}, search_vendor_docs={web_count})",
        )
     if docs_count != web_count:
        return CheckResult(
            False,
            f"branches ran an uneven number of times (search_docs={docs_count}, "
            f"search_vendor_docs={web_count}) -- a retry may have dropped one",
        )
     return CheckResult(True, f"both branches contributed evidence {docs_count} time(s) each")


def check_resume_consistency(pre_synthesis: str, post_synthesis: str, approved: bool) -> CheckResult:
    """Does a checkpoint-and-resume run (03_human_approval.py) produce a
    continuation consistent with the human decision it was given -- i.e.
    resuming with approved=True actually shows the fix as applied in the
    post-resume state, and approved=False shows it as skipped. The
    artifact's Week 4 acceptance criterion, made runnable instead of
    eyeballed."""
    marker = "(fix applied" if approved else "(fix not applied"
    if marker not in post_synthesis:
        return CheckResult(False, f"expected {marker!r} in post-resume synthesis, got: {post_synthesis!r}")
    if pre_synthesis not in post_synthesis:
        return CheckResult(False, "post-resume synthesis doesn't build on the pre-interrupt synthesis")
    return CheckResult(True, "resume produced a continuation consistent with the given decision")
