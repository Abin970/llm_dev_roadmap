"""
Experiment 3 -- Break it on purpose
=========================================
Objective  : see what AgentLoop actually does when a tool always fails,
             and when the question has no correct tool at all.
Setup      : (a) register a tiny always-failing tool, ask a question that
             can only be answered by calling it. (b) ask a genuinely
             unanswerable question with the normal toolset.
Teaches    : these are the failure modes you have to design against
             before shipping any agent -- a graceful "I can't do this"
             beats both a crash and a confident wrong answer.

Run: python experiments/03_break_it.py
"""
import _bootstrap  # noqa: F401
from pydantic import BaseModel

from agent.loop import AgentLoop
from tools.registry import register


class AlwaysFailsArgs(BaseModel):
    pass


@register("always_fails", AlwaysFailsArgs)
def always_fails(args: AlwaysFailsArgs) -> str:
    """A lookup tool that is always broken -- for testing failure recovery."""
    raise RuntimeError("this tool is broken on purpose")


# TODO: two questions --
#   FAILING_TOOL_QUESTION should be phrased so the model reaches for
#   "always_fails" specifically (mention "the broken lookup tool" or
#   similar so the model can't just avoid it and answer another way).
#   UNANSWERABLE_QUESTION should be something none of your tools or the
#   model's own knowledge can resolve (e.g. asking for live data no tool
#   here provides).
FAILING_TOOL_QUESTION = "..."
UNANSWERABLE_QUESTION = "..."


def run(label: str, question: str) -> None:
    print(f"=== {label} ===")
    for event in AgentLoop(max_iterations=4).run(question):
        print(event)
    print()


def main() -> None:
    run("always-failing tool", FAILING_TOOL_QUESTION)
    run("unanswerable question", UNANSWERABLE_QUESTION)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did the agent retry the failing tool, try a different approach, or give
# up cleanly? Did the unanswerable question get a forced/garbage answer
# at max_iterations, or an honest "I can't answer this"?


# Now as for experiment 03_break_it we have already seen both 
#     a) almost always failing tool-call 
#     b) unanswerable question with given tools, 
# instead of testing them by hand I want 
#     1] how do I identify and measure such deviation where llm-halucianates to fill the information gap 
#     2] how I design by keeping mind these failure modes.

# hallucination:=> Grounding checks: fact check againts tools call result
# unanswerable question and failing_tool_calls :=> llm admits that it can't answer(abstention check)


#Desgining for these failure modes
# - Make abstention an explict instruction
# - Make tool "no result" states loud and unabiguous
# - Ask for citations
# -Circuit-breaking on tool calls

