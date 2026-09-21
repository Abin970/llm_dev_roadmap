"""
Experiment 2 -- Reimplement with LangChain, diff the two
===============================================================
Objective  : run the SAME question through LangChainAgent and compare its
             tool-call trace against AgentLoop's from experiment 1.
Setup      : same QUESTION, same tools, run both back to back.
Teaches    : the framework isn't magic -- it's the loop you already
             wrote, packaged. What's different is boilerplate (message
             formatting, provider adapters), not the underlying shape.

Run: python experiments/02_langchain_diff.py
"""
import _bootstrap  # noqa: F401
from agent.langchain_agent import LangChainAgent
from agent.loop import AgentLoop

# TODO: reuse the same QUESTION from experiment 1 (copy it, or refactor
# it into a shared constant if you'd rather -- your call).
QUESTION = """"notification-service is currently throwing 'connection pool exhausted' 
    errors under sustained load. Have we run into this pattern before, and if so, what fixed it?"""


def main() -> None:
    # print("=== AgentLoop (hand-rolled) ===")
    # for event in AgentLoop(max_iterations=6).run(QUESTION):
    #     print(event)

    print("\n=== LangChainAgent ===")
    for event in LangChainAgent(max_iterations=6).run(QUESTION):
        print(event)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Same tool calls in the same order? Same final answer? What did
# LangChain's abstraction handle for you that you had to write by hand in
# AgentLoop -- message formatting? tool-call parsing? something else?
#
# Did anything behave differently between the two (e.g. one recovered
# from a tool error more gracefully, or took more/fewer iterations)?

# genuinely good example of "what LangChain automated for you" 
# — AgentLoop needs you to hand-write the give-up message yourself 
# after the for loop exhausts; LangChainAgent gets one generated 
# for free by the middleware, you just had to know to route it into 
# final_content instead of silently discarding it as an unrecognized chunk source.
