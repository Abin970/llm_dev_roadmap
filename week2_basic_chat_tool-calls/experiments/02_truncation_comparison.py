"""
Experiment 2 -- Truncation strategy comparison
====================================================
Hypothesis : sliding-window truncation is cheap but can silently drop a
             fact that summarization would have preserved -- at the cost
             of an extra LLM call every time summarization kicks in.
Setup      : build a synthetic ~30-turn conversation with one specific,
             unmistakable fact planted early on, truncate it down with
             both strategies to a small token budget, then ask a question
             that can only be answered using that fact.
Teaches    : truncation is a lossy tradeoff, not a solved problem -- sets
             up Week 6's memory design.

Run: python experiments/02_truncation_comparison.py
"""
import _bootstrap  # noqa: F401
from conversation import truncate_sliding_window, truncate_summarize
from llm_client import chat

# TODO: build ~30 messages of generic back-and-forth filler (alternating
# {"role": "user", ...} / {"role": "assistant", ...}), with ONE early
# message containing a specific, made-up fact (similar in spirit to
# week1 exp5's NEEDLE -- something the model can't guess). Set QUESTION to
# something answerable only from that fact.
CONVERSATION: list[dict] = [
    {"role": "user", "content": "Hey, I need help planning a trip to Portugal next month."},
    {"role": "assistant", "content": "Happy to help! How many days are you thinking, and which cities are on your list?"},
    {"role": "user", "content": "About 10 days total. I just booked an Airbnb in Lisbon for the first four nights -- confirmation code TRV-8842-QZ, in case I need it later."},
    {"role": "assistant", "content": "Got it, noted. Lisbon is a great home base for the first few days. Want neighborhood recommendations?"},
    {"role": "user", "content": "Sure, I've heard Alfama and Baixa are popular."},
    {"role": "assistant", "content": "Both are great. Alfama has narrow streets and fado bars, Baixa is flatter and easier to walk everywhere."},
    {"role": "user", "content": "What about day trips from Lisbon?"},
    {"role": "assistant", "content": "Sintra is the classic one -- palaces and castles, about 40 minutes by train. Cascais is good for a beach day."},
    {"role": "user", "content": "How many days should I budget for Porto?"},
    {"role": "assistant", "content": "3-4 days is usually enough, plus a day trip to the Douro Valley for wine tasting."},
    {"role": "user", "content": "Is the train between Lisbon and Porto easy to book?"},
    {"role": "assistant", "content": "Yes, the CP Alfa Pendular is about 3 hours, easy to book online a few weeks ahead."},
    {"role": "user", "content": "Any food recommendations for Lisbon?"},
    {"role": "assistant", "content": "Try pastéis de nata from Pastéis de Belém -- and bacalhau dishes are everywhere."},
    {"role": "user", "content": "What's the weather usually like there that time of year?"},
    {"role": "assistant", "content": "Generally mild, 60s-70s F during the day, cooler at night -- pack layers."},
    {"role": "user", "content": "Should I rent a car for the Douro Valley trip?"},
    {"role": "assistant", "content": "A car gives more flexibility, but a guided day tour from Porto is common too."},
    {"role": "user", "content": "Do I need any special outlet adapters?"},
    {"role": "assistant", "content": "Portugal uses the European two-pin plug (type C/F), so a standard EU adapter works fine."},
]
QUESTION = "What is the confirmation code for my Lisbon Airbnb booking?"
FACT_VALUE = "TRV-8842-QZ"


# TODO: pick a max_tokens budget small enough that most of CONVERSATION
# has to be truncated away, but the question can still be answered if the
# fact survives truncation.
MAX_TOKENS_BUDGET = 200


def run(strategy_name: str, truncate_fn) -> None:
    # TODO:
    #   1. truncated = truncate_fn(CONVERSATION, MAX_TOKENS_BUDGET)
    #   2. messages = truncated + [{"role": "user", "content": QUESTION}]
    #   3. answer = chat(messages, temperature=0.0)
    #   4. print the strategy name, the resulting token count, and whether
    #      the fact appears in `answer`
    if strategy_name == "sliding-window":
        truncated = truncate_sliding_window(CONVERSATION, MAX_TOKENS_BUDGET,model="gpt-4.1-nano")
    elif strategy_name == "summarization":
        truncated = truncate_summarize(CONVERSATION, MAX_TOKENS_BUDGET,model="gpt-4.1-nano")
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    messages = truncated + [{"role": "user", "content": QUESTION}]
    answer = chat(messages, temperature=0.0, model="gpt-4.1-nano")
    token_count = sum(len(m["content"].split()) for m in messages)
    passed = FACT_VALUE.lower() in answer.lower()
    print(f"[{strategy_name}] answer: {answer}")
    print(f"[{strategy_name}] fact recalled: {passed}")  



def main() -> None:
    run("sliding-window", truncate_sliding_window)
    run("summarization", truncate_summarize)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Which strategy kept the fact, which lost it? What did summarization cost
# you (extra LLM calls, latency) for that reliability?
#
# Is there a conversation shape where sliding-window would actually be the
# better choice despite the risk? (Hint: think about what's in the most
# recent turns vs the oldest ones.)
#
#
# at max_token=500 both strategies kept the fact,
# but at max_token=200 sliding-window lost the fact while summarization kept it.
