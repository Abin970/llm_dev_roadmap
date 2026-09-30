"""
Experiment 5 -- "Lost in the middle"
========================================
Hypothesis : a fact buried in the middle of a long context is recalled less
             reliably than the same fact placed at the start or end, even
             though all positions are well within the context window limit.
Setup      : build a long filler document, insert one unique "needle" fact at
             three different positions (start / middle / end), ask a question
             that can only be answered from the needle.
Teaches    : "it fits in the context window" != "the model will use it well" --
             this is the concept RAG retrieval quality (Week 5) has to reckon
             with.

Run: python experiments/05_context_window.py
"""
import _bootstrap  # noqa: F401
from llm_client import chat, count_tokens

# TODO: write one clearly artificial, unmistakable fact that couldn't be
# guessed or already known by the model -- e.g. a made-up config value.
# It needs to be specific enough that "the model guessed right by luck"
# is implausible.
NEEDLE = "The internal codename for the Q3 checkout-latency project is 'PROJECT_QUIETRIVER'."
QUESTION = "What is the internal codename for the Q3 checkout-latency project?"

# Reusable filler text -- doesn't need to be meaningful, just needs bulk.
FILLER_PARAGRAPH = (
    "The team continued its regular sprint cadence, reviewing backlog items, "
    "triaging bug reports, and syncing with adjacent squads on shared "
    "infrastructure concerns unrelated to the topic at hand. "
)


def build_context(needle_position: str, filler_paragraphs: int = 60) -> str:
    """needle_position: 'start' | 'middle' | 'end'"""
    filler = [FILLER_PARAGRAPH] * filler_paragraphs
    # TODO: insert NEEDLE as its own paragraph at the requested position:
    #   'start'  -> index 0
    #   'middle' -> len(filler) // 2
    #   'end'    -> len(filler) (i.e. appended)
    # then "\n\n".join(...) the list into one string and return it.
    if needle_position == "start":
        filler.insert(0, NEEDLE)
    elif needle_position == "middle":
        filler.insert(len(filler) // 2, NEEDLE)
    elif needle_position == "end":
        filler.append(NEEDLE)
    return "\n\n".join(filler)


def ask(position: str) -> None:
    context = build_context(position)
    messages = [
        {"role": "developer", "content": "Answer using only the provided context. Be concise."},
        {"role": "user", "content": f"{context}\n\n---\n\nQuestion: {QUESTION}"},
    ]
    print(f"[{position}] context is {count_tokens(context)} tokens")
    # TODO: call chat(messages, temperature=0.0) and print whether the
    # answer actually contains "PROJECT_QUIETRIVER".
    result = chat(messages=messages, temperature=0.0)
    print(f"[{position}] answer: {result}")


def main() -> None:
    for position in ["start", "middle", "end"]:
        ask(position)
        print()


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# start:  recalled correctly? ...
# middle: recalled correctly? ...
# end:    recalled correctly? ...
# Did the result match the "lost in the middle" hypothesis? If every position
# recalled correctly, what would you do to make the experiment harder
# (bigger haystack? multiple similar-looking needles?) -- and why does that
# matter for how you'll design RAG retrieval later?
