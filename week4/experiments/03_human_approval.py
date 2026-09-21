"""
Experiment 3 -- Human-approval interrupt
==========================================
Objective  : prove the graph genuinely SUSPENDS at apply_fix_node's
             interrupt() call and later RESUMES with the right state --
             not just a synchronous confirm() call standing in for it.
Setup      : run a question that reaches an approved synthesis (so the
             graph actually gets to apply_fix_node), confirm the run
             pauses there, then resume two separate runs -- one with
             approval, one with rejection -- and confirm each produces
             the expected, DIFFERENT final state.
Teaches    : the mechanics of a real approval gate for a tool with side
             effects, and that resuming re-enters the paused node from
             the top (see apply_fix_node.py's own docstring for why that
             matters).

Run: python experiments/03_human_approval.py
"""
import uuid

import _bootstrap  # noqa: F401

from agent.graph import GraphAgent

# TODO: a question your fixtures can carry all the way to an "approved"
# synthesis, so the run actually reaches apply_fix_node.
QUESTION = "..."


def run_and_pause() -> str:
    thread_id = str(uuid.uuid4())
    print("=== initial run (expect it to pause) ===")
    for event in GraphAgent().run(QUESTION, thread_id=thread_id):
        print(event)
    return thread_id


def resume(thread_id: str, approved: bool) -> None:
    print(f"=== resume(approved={approved}) ===")
    for event in GraphAgent().resume(thread_id, {"approved": approved}):
        print(event)
    print()


def main() -> None:
    thread_id = run_and_pause()
    resume(thread_id, approved=True)

    # A second, independent thread so rejecting doesn't need to re-pause
    # the same (already-resumed) run.
    thread_id_2 = run_and_pause()
    resume(thread_id_2, approved=False)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did the initial run's trace end with a paused/interrupt signal instead
# of a normal COMPLETED event? Did the approved resume actually show the
# fix being "applied," and the rejected resume show it being skipped?
