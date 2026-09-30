"""
Experiment 1 -- Loop vs graph
==============================
Objective  : same SRE on-call question, once through Week 3's AgentLoop,
             once through Week 4's GraphAgent -- diff the two traces.
Setup      : one SRE question this project's fixtures can actually
             support an answer for (see assistant/tools/docs/*.md and
             assistant/tools/seed_db.py for what's available -- e.g. the
             checkout-service / connection-pool-exhaustion incident from
             Week 3).
             Week 5: those fixture docs are retired. EVAL_CASES[2] is now
             a real-corpus question (KubePodCrashLooping + OOM kills), so
             rerunning this needs Week 5's retrieval implemented first.
Teaches    : the graph doesn't change WHAT the system does -- it changes
             what you can inspect and control (per-node output, not just
             a flat tool-call trace).

Run: python experiments/01_loop_vs_graph.py
"""
import uuid

import _bootstrap  # noqa: F401

from agent.graph import GraphAgent
from agent.loop import AgentLoop
from eval_cases import EVAL_CASES
import eval_checks as eval

_case = EVAL_CASES[2]

# TODO: an SRE question your search_docs/search_vendor_docs/sqlite_query fixtures
# can actually support an answer for.
QUESTION = _case.question


def run_loop() -> None:
    print("=== AgentLoop (Week 3) ===")
    for event in AgentLoop().run(QUESTION):
        print(event)
    print()


def run_graph() -> None:
     print("=== GraphAgent (Week 4) ===")
     thread_id = str(uuid.uuid4())
     trace = list(GraphAgent().run(user_message=QUESTION, thread_id=thread_id))
     for event in trace:
        print(event)
     print(eval.check_tool_sequence(trace, _case))
     print(eval.check_retry_bound(trace, max_retries=2))
     print(eval.check_parallel_evidence_complete(trace))
     print()


def main() -> None:
    # run_loop()
    run_graph()


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Same final recommendation from both? Which trace made it easier to see
# WHERE the evidence for that recommendation came from -- the flat
# AgentLoop trace, or the graph's per-node updates?
