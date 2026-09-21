"""graph.py -- the SRE on-call copilot reborn as a graph (Project V2).

Retires AgentLoop (Week 3) as the top-level control flow: instead of one
implicit while-loop deciding everything, control flow is now explicit
graph topology --

    planner -> {search_docs ‖ search_web} -> merge -> synthesizer -> reviewer
                                                                        |
                              approved -----------------------> apply_fix -> END
                              rejected, retries left -----------------> planner
                              rejected, retries exhausted --------------> END

TODO, following the confirmed LangGraph API (verified against the
pinned `langgraph` version, not assumed from memory -- this framework's
surface has drifted before, see langchain_agent.py's own header comment
from Week 3 for why that matters):

  from langgraph.graph import StateGraph, START, END
  from langgraph.checkpoint.memory import InMemorySaver

  from .state import GraphState
  from .nodes.planner import planner_node
  from .nodes.search import search_docs_node, search_web_node
  from .nodes.merge import merge_node
  from .nodes.synthesizer import synthesizer_node
  from .nodes.reviewer import reviewer_node
  from .nodes.apply_fix_node import apply_fix_node

  MAX_RETRIES = 2

  builder = StateGraph(GraphState)
  builder.add_node("planner", planner_node)
  builder.add_node("search_docs", search_docs_node)
  builder.add_node("search_web", search_web_node)
  builder.add_node("merge", merge_node)
  builder.add_node("synthesizer", synthesizer_node)
  builder.add_node("reviewer", reviewer_node)
  builder.add_node("apply_fix", apply_fix_node)

  builder.add_edge(START, "planner")
  builder.add_edge("planner", "search_docs")
  builder.add_edge("planner", "search_web")   # fan-out: both run in the
                                               # same step -- a FIXED pair
                                               # of branches needs nothing
                                               # beyond plain multi-edges,
                                               # no langgraph.types.Send
  builder.add_edge("search_docs", "merge")
  builder.add_edge("search_web", "merge")     # fan-in: merge waits for
                                               # BOTH edges before running
  builder.add_edge("merge", "synthesizer")
  builder.add_edge("synthesizer", "reviewer")

  def route_after_review(state: GraphState) -> str:
      if state["review_verdict"] == "approved":
          return "apply_fix"
      if state["retry_count"] >= MAX_RETRIES:
          return "give_up"
      return "planner"

  builder.add_conditional_edges(
      "reviewer", route_after_review,
      {"apply_fix": "apply_fix", "planner": "planner", "give_up": END},
  )
  builder.add_edge("apply_fix", END)

  checkpointer = InMemorySaver()
  compiled = builder.compile(checkpointer=checkpointer)

A wrapper CLASS around this compiled graph should expose the SAME
interface AgentLoop and LangChainAgent already use, so main.py and the
experiments can treat all three agent variants interchangeably --
plus the one thing neither of those needed: a `thread_id`, since
interrupts/resume are only meaningful per-conversation-thread, via the
checkpointer.

    class GraphAgent:
        def __init__(self, *, max_iterations: int = MAX_RETRIES) -> None: ...

        def run(self, user_message: str, *, thread_id: str) -> Iterator[Event]:
            '''Starts a NEW run on this thread_id. Confirmed streaming
            shape (v1/default `stream_mode`, no `version=` kwarg --
            LangGraph 1.1+ also offers an opt-in v2/v3 streaming contract
            with cleaner interrupt access via `result.interrupts`, but
            this project targets the default shape for consistency with
            LangChainAgent's own stream_mode=["updates"] handling from
            Week 3):

                config = {"configurable": {"thread_id": thread_id}}
                for mode, chunk in compiled.stream(
                    {"question": user_message, "retry_count": 0},
                    config, stream_mode=["updates"],
                ):
                    if "__interrupt__" in chunk:
                        ...  # the run just paused -- surface this somehow
                        return
                    for node_name, update in chunk.items():
                        ...  # map node_name/update -> an Event; there's
                             # no 1:1 "tool call" concept at the graph
                             # level the way there was in Week 3, so this
                             # mapping is your own design decision
            '''
            raise NotImplementedError

        def resume(self, thread_id: str, decision: dict) -> Iterator[Event]:
            '''Resumes a run PAUSED at apply_fix_node's interrupt() call.
            Same thread_id as the original .run() call -- the
            checkpointer is what makes that resumable at all.

                from langgraph.types import Command
                config = {"configurable": {"thread_id": thread_id}}
                for mode, chunk in compiled.stream(
                    Command(resume=decision), config, stream_mode=["updates"],
                ):
                    ...
            '''
            raise NotImplementedError

main.py's new /research/resume endpoint needs to receive and pass through
whatever thread_id /research handed back when a run paused -- decide how
that gets communicated across the SSE boundary (e.g. as a field in the
Event.data of whatever "paused" event you emit) before wiring the
endpoint.
"""
from __future__ import annotations

from typing import Iterator

from events import Event, EventType

MAX_RETRIES = 2


class GraphAgent:
    def __init__(self, *, max_iterations: int = MAX_RETRIES) -> None:
        self.max_iterations = max_iterations

    def run(self, user_message: str, *, thread_id: str) -> Iterator[Event]:
        raise NotImplementedError

    def resume(self, thread_id: str, decision: dict) -> Iterator[Event]:
        raise NotImplementedError
