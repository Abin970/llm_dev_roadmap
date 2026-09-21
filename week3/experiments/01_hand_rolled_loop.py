"""
Experiment 1 -- Hand-roll the ReAct loop
==============================================
Objective  : run AgentLoop on a real research question and watch the
             reason -> act -> observe cycle happen for real, not just on
             paper.
Setup      : ask a question that genuinely needs a tool (not something
             the model already knows), print every event as it streams
             out -- the sequence of TOOL_CALL/TOOL_RESULT events IS the
             scratchpad.
Teaches    : termination isn't automatic -- max_iterations is doing real
             work, not just a paranoid safety net.

Prerequisite: run `python tools/seed_db.py` once first (from inside
assistant/), if you haven't already.

Run: python experiments/01_hand_rolled_loop.py
"""
import _bootstrap  # noqa: F401
from agent.loop import AgentLoop

# TODO: pick a question that requires at least one tool call to answer
# correctly -- e.g. something needing your sqlite `incidents` table, a
# calculation, or a lookup in tools/docs/. A question the model could
# just answer from its own knowledge won't exercise the loop at all.
QUESTION1 = """How many incidents in the incidents table are still unresolved? 
        Multiply that count by the retry cap Aurora added after incident INC-4821, 
        then tell me whether the result exceeds PulseQueue's free-tier webhook retry limit."""


QUESTION2 = """Is PulseQueue's free-tier webhook retry cap higher 
            or lower than the retry cap Aurora added after incident INC-4821?"""


def main() -> None:
    agent = AgentLoop(max_iterations=6, model="gpt-4.1-nano")
    for event in agent.run(QUESTION2):
        # TODO: print each event as it arrives -- at minimum the event
        # type and its data (event.type, event.data). Watching this
        # print in order is the point of the exercise.
        print(f"Event: {event.type}, Data: {event.data}")


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# How many iterations did it actually take? Now try max_iterations=1 --
# does it fail gracefully or just cut off mid-thought? Then try a very
# high max_iterations with a question that has no good answer -- did it
# loop pointlessly, or stop on its own?
#
#
# the question I asked was one that needed 3 different tool calls
# the real challenge here is get right tool result espeically with
# doc_search where llm-natural-language substring can't be matched 
# with doc string(RAG and embedding is the solution for this problem)
#
# now as for high max_iterations, didn't exaclty try but still
# found the tedency to loop pointlessly, so the max_iterations is a good safety net. 
#
#