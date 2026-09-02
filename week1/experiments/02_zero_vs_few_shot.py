"""
Experiment 2 -- Zero-shot vs few-shot
======================================
Hypothesis : few-shot examples improve accuracy/format-consistency on tasks
             the model doesn't already nail zero-shot, at the cost of extra
             input tokens on every single call.
Setup      : a small classification task, run once with zero examples and
             once with a few hand-picked examples, scored against a labeled
             eval set.
Teaches    : few-shot has a real cost -- measure the lift before paying it.

Run: python experiments/02_zero_vs_few_shot.py
"""
import _bootstrap  # noqa: F401
from llm_client import chat

# The task: classify a support/ops message into one of these categories.
# Chosen deliberately ambiguous-ish (backend-flavored) so zero-shot won't be
# perfect -- if you swap in a trivial task you won't see a few-shot lift.
LABELS = ["outage", "feature-request", "billing", "how-to"]

EVAL_SET = [
    ("Our Kafka consumer group is stuck rebalancing and nothing is processing.", "outage"),
    ("Could you add pagination to the /orders endpoint?", "feature-request"),
    ("We were charged twice for last month's usage.", "billing"),
    ("How do I configure a dead-letter topic in Spring Kafka?", "how-to"),
    ("Prod checkout has been throwing 500s for 10 minutes.", "outage"),
    ("Any chance of a bulk-export API for invoices?", "feature-request"),
    ("My card on file expired, how do I update billing details?", "billing"),
    ("What's the recommended way to test a LangGraph node in isolation?", "how-to"),
    ("Our Redis cluster failover isn't happening and writes are timing out.", "outage"),
    ("Could you add webhook support for order status changes?", "feature-request"),
    ("We're being billed for a plan we downgraded from last month.", "billing"),
    ("What's the right way to mock an external API call in our test suite?", "how-to"),
]

# Balanced few-shot set: one example per label, so no category is favored
# by sheer demonstration count. (Previous version had 2 how-to + 1 outage
# and zero examples of billing/feature-request -- see OBSERVATIONS below
# for what that imbalance did to accuracy.)
FEW_SHOT_EXAMPLES: list[tuple[str, str]] = [
    ("Our database is down and we can't access our application.", "outage"),
    ("Can you add support for exporting reports as CSV?", "feature-request"),
    ("I was charged for a subscription I already cancelled.", "billing"),
    ("How do I set up a retry policy for my Kafka producer?", "how-to"),
]


def build_messages(user_message: str, *, few_shot: bool) -> list[dict]:
    system = (
        f"Classify the message into exactly one label: {', '.join(LABELS)}. "
        "Reply with only the label, nothing else."
    )
    messages = [{"role": "developer", "content": system}]
    if few_shot:
        # TODO: append each FEW_SHOT_EXAMPLES pair as a user/assistant message
        # pair (assistant's content = the correct label), before the real
        # user message.
        for example_message, example_label in FEW_SHOT_EXAMPLES:
            messages.append({"role": "user", "content": example_message})
            messages.append({"role": "assistant", "content": example_label})
    messages.append({"role": "user", "content": user_message})
    return messages


def run(few_shot: bool) -> float:
    correct = 0
    for message, expected in EVAL_SET:
        messages = build_messages(message, few_shot=few_shot)
        # TODO: call chat(messages, temperature=0.0), strip/lowercase the
        # result, compare to `expected`, print a per-example pass/fail line,
        # and increment `correct` on a match.
        chat_result = chat(model="gpt-4.1-nano", messages=messages, temperature=0.0)
        result = chat_result.strip().lower()
        if result == expected:
            correct += 1
            print(f"PASS: {message} -> {result}")
        else:
            print(f"FAIL: {message} -> {result} (expected: {expected})")
    return correct / len(EVAL_SET)


def main() -> None:
    print("=== zero-shot ===")
    zero_acc = run(few_shot=False)
    print(f"\naccuracy: {zero_acc:.0%}")

    print("\n=== few-shot ===")
    few_acc = run(few_shot=True)
    print(f"\naccuracy: {few_acc:.0%}")


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
#
#- Zero-shot: you give the model only an instruction ("classify into one of these 4 labels") 
# and the new input. It has to map your task description onto its pretrained knowledge with 
# no worked examples.
#- Few-shot: before the real question, you prepend a handful of example (input → correct output) 
# pairs as fake prior turns in the conversation. The model conditions on those demonstrations 
# — it's not learning weights, just using the examples as in-context pattern to imitate 
# for the new input.
#
# zero-shot accuracy: 100%
# few-shot accuracy:  100%
# Which specific examples flipped from wrong to right? Why do you think the
# few-shot examples fixed those particular cases?
#
# Was the lift worth the extra input tokens for this task? How would you
# decide that in a real system processing thousands of these a day?
#
#Real lesson: few-shot lift can't be measured on a task the model already nails 
# zero-shot — you'd need a harder eval set (more ambiguous messages, more categories, 
# or a model dumber than gpt-4.1-nano) to see a genuine before/after difference.
