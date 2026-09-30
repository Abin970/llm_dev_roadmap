"""GraphState -- the typed state shared across every node in the SRE
on-call graph (graph.py).

LangGraph state is a schema (TypedDict or a pydantic.BaseModel -- both
are supported, confirmed against the pinned `langgraph` version) with
each node returning only the fields it changes (a PARTIAL state dict) --
LangGraph merges that partial update into the running state for you
between each node; nodes never mutate the incoming state directly.

The one thing that ISN'T automatic: when two nodes can run in the same
step and both write to the SAME field -- this graph's parallel
`search_docs_node` / `search_vendor_docs_node` both need to add to `evidence` --
a plain field can only take ONE value per step. Verified directly (not
assumed): without a reducer, LangGraph doesn't silently pick a winner --
it raises `InvalidUpdateError: At key '<field>': Can receive only one
value per step. Use an Annotated key to handle multiple values.` and
refuses to run at all. Fix: mark that field with a reducer, confirmed
syntax:

    from typing_extensions import TypedDict, Annotated
    import operator

    class GraphState(TypedDict):
        evidence: Annotated[list[str], operator.add]   # merged, not overwritten

Without the `Annotated[..., operator.add]`, a state field two parallel
nodes both write is exactly the artifact's own called-out mistake: "no
reducer on a field two parallel nodes both write." The artifact frames
the risk as one branch silently overwriting the other -- in practice
(this LangGraph version, verified directly) it's a hard `InvalidUpdateError`
at runtime instead, which is a kinder failure mode than the artifact's
wording suggests, but the fix is the same either way: declare a reducer.

TODO: fill in the field types below (most don't need a reducer -- only
`evidence` is written by more than one node in the same step) --

  - question       : str -- the on-call question this run is investigating
  - plan           : str -- planner_node's decision about what to look up
  - evidence       : list[str], WRITTEN BY BOTH search_docs_node and
                     search_vendor_docs_node in the same step -- needs the
                     reducer above, or one branch's contribution vanishes
  - synthesis      : str -- synthesizer_node's proposed root cause + fix
  - review_verdict : str -- reviewer_node's "approved" or "rejected: ..."
  - retry_count    : int -- bumped by planner_node on every (re)plan;
                     read by the conditional edge after reviewer_node to
                     enforce the max-retries cap (see graph.py)
  - pending_action : dict | None -- the risky action (if any) currently
                     awaiting human approval via apply_fix_node's
                     interrupt() call

Week 5 TODO (yours): add `citations: list[str]` to ApplyFixesArgs. It
holds the chunk ids the answer relies on, written exactly as they
appear in the evidence ("[<chunk_id>]", without the brackets). Because
it's part of the structured-output schema, chat_structured() makes the
model fill it in, and reviewer_node can check it as data instead of
parsing citations out of prose. An empty list is only legitimate when
response_message says the evidence doesn't cover the question.
"""
from __future__ import annotations

from typing_extensions import Annotated, TypedDict
import operator
from pydantic import BaseModel

class ApplyFixesArgs(BaseModel):
     response_message: str
     service: str
     config_key: str
     config_value: str

class GraphState(TypedDict):
    question: str
    plan: str
    evidence: Annotated[list[str], operator.add]   # merged, not overwrittenbove
    synthesis: ApplyFixesArgs | None
    review_verdict: str
    retry_count: int
    pending_action: dict | None
