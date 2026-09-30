"""search_docs_node / search_vendor_docs_node -- the parallel evidence-gathering
branch of the graph (fan-out from planner_node, fan-in at merge_node).

TODO: each node calls the SAME tool machinery Week 3 already built
(`tools.registry.dispatch`), not a redefinition of search logic -- reuse
`dispatch("search_docs", {"query": ...})` / `dispatch("search_vendor_docs",
{"query": ...})`, building the query from state["plan"] (or
state["question"]).

Confirmed via LangGraph API research: for a FIXED, known-in-advance pair
of parallel branches like this one (as opposed to a dynamic/variable
number of branches, which would need `langgraph.types.Send`), plain graph
topology is enough -- graph.py just adds two edges out of planner_node
(one to each of these) and two edges from these into merge_node;
LangGraph runs both in the same step automatically, no extra code here.
The one thing that ISN'T automatic: state["evidence"] needs the reducer
from state.py, or LangGraph raises `InvalidUpdateError` and refuses to
run at all (verified directly) the moment both nodes try to write it in
the same step -- not a silent loss of one branch's contribution, a hard
stop.

    def search_docs_node(state: GraphState) -> dict:
        try:
            result = dispatch("search_docs", {"query": ...})
        except ToolError as e:
            result = f"error: {e}"
        return {"evidence": [f"[search_docs] {result}"]}   # one-item list --
            # the reducer in state.py is what appends this to the other
            # branch's contribution instead of replacing it

Tag each evidence string with its source (as above) -- reviewer_node and
synthesizer_node need to tell a postmortem doc apart from a tool-config
doc when deciding whether a claim is actually grounded.

Week 5: nothing in these two nodes changes. `search_web` was renamed to
`search_vendor_docs` (it now searches the real vendor docs, not three
made-up web pages), and both tools' handlers become real retrieval. The
node code keeps calling dispatch(...) exactly as before, which is the
Week 2 tool registry paying off: the implementation behind a tool name
changed, and no caller had to change with it. The result string now
holds several retrieved chunks, each starting with "[<chunk_id>]" (see
retrieval.format_hits); that is what synthesizer_node cites and
reviewer_node checks.
"""
from __future__ import annotations

from tools.registry import ToolError, dispatch

from ..state import GraphState


def search_docs_node(state: GraphState) -> dict:
     try:
         result = dispatch("search_docs",{"query":state["plan"]})
     except ToolError as e:
         result = f"error:{e}"
         
     return {"evidence": [f"[search_docs] {result}"]}
         
         

def search_vendor_docs_node(state: GraphState) -> dict:
     try:
         result = dispatch("search_vendor_docs", {"query":state["plan"]})
     except ToolError as e:
          result = f"error: {e}"

     return {"evidence": [f"[search_vendor_docs] {result}"]}