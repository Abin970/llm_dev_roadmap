"""apply_fix_node -- the human-approval-gated action, wired via
LangGraph's interrupt().

TODO: this is the "risky tool" from the artifact's Week 3 preview and
Week 4's human-approval exercise, made concrete for an SRE copilot: once
reviewer_node approves a synthesis, offer to actually apply the
recommended fix via the mocked `apply_fix` tool (tools/apply_fix.py) --
but pause and wait for a human "yes" first, since it's the one node in
this graph that (pretends to) touch production.

Confirmed via LangGraph API research (this framework's human-in-the-loop
surface has changed across versions -- don't rely on older tutorials
that reference a `NodeInterrupt` exception; current LangGraph builds HITL
entirely around the `interrupt()` function + `Command(resume=...)`):

    from langgraph.types import interrupt

    def apply_fix_node(state: GraphState) -> dict:
        decision = interrupt({
            "action": "apply_fix",
            "proposed_fix": state["synthesis"],
        })
        # Execution PAUSES here on first entry -- interrupt() raises
        # internally, the graph suspends via its checkpointer, and
        # graph.stream()/.invoke() surface a distinct
        # {"__interrupt__": (Interrupt(value=..., id=...),)} chunk/key
        # instead of a normal node-output chunk. This function does NOT
        # return on that first pass -- the whole run is suspended.
        #
        # Resuming (from graph.py's GraphAgent.resume(), driven by
        # main.py's new /research/resume endpoint) re-enters this SAME
        # function from the top via:
        #     graph.invoke(Command(resume=decision_value), config)
        # and this time interrupt(...) returns decision_value instead of
        # pausing again.
        if not decision.get("approved"):
            return {"synthesis": state["synthesis"] + "\n\n(fix not applied -- human declined)"}
        result = dispatch("apply_fix", {...})
        return {"synthesis": state["synthesis"] + f"\n\n(fix applied: {result})"}

IMPORTANT (confirmed, not obvious): on resume, this node's function
RESTARTS FROM THE TOP -- any code placed before the `interrupt()` call
re-runs too. Never put a non-idempotent side effect (like the real
`dispatch("apply_fix", ...)` call) before the interrupt() line -- only
after it, once you actually have the human's decision. Also never wrap
the `interrupt()` call in a bare `try/except` -- it works by raising
internally, and a bare catch swallows the pause.

Requires a checkpointer to work at all -- `interrupt()`/`Command(resume=...)`
raise a RuntimeError without one, so graph.py's `compile(checkpointer=...)`
call is not optional once this node is wired in.
"""
from __future__ import annotations

from langgraph.types import interrupt

from tools.registry import ToolError, dispatch

from ..state import GraphState



def apply_fix_node(state: GraphState) -> dict:
     # any line of code above interrupt() will be executed twice[idemtopency for side effects]
     decision = interrupt({
            "action": "apply_fix",
            "proposed_fix": state["synthesis"],
    })

     fix = state["synthesis"]
     if not decision.get("approved"):
                 updated = fix.model_copy(update={
                     "response_message": fix.response_message + "\n\n(fix not applied -- human declined)"
                 })
                 return {"synthesis": updated}
     result = dispatch(
                 "apply_fix", {
                                "service":fix.service,
                                "config_key":fix.config_key,
                                "config_value":fix.config_value
                            }
                        )
     updated = fix.model_copy(update={
         "response_message": fix.response_message + f"\n\n(fix applied: {result})"
     })
     return {"synthesis": updated}