"""
Experiment 4 -- Streaming vs non-streaming
=============================================
Hypothesis : streaming dramatically reduces time-to-first-token (TTFT) but
             does NOT reduce total generation time -- it changes perceived
             latency, not throughput.
Setup      : same prompt (long enough to generate a many-second response),
             timed both ways.
Teaches    : what streaming is actually buying you, and what it isn't.

Run: python experiments/04_streaming.py
"""
import time

import _bootstrap  # noqa: F401
from llm_client import chat, chat_stream

# TODO: pick a prompt that reliably produces a longish response (a few
# hundred tokens) -- the TTFT-vs-total gap is invisible on a one-line answer.
PROMPT = "Explain how Kafka consumer group rebalancing works, in about 300 words."


def run_non_streaming() -> None:
    messages = [{"role": "user", "content": PROMPT}]
    start = time.perf_counter()
    # TODO: call chat(messages) and capture the full result

    result = chat(messages=messages,model="gpt-4.1-nano")
    end = time.perf_counter()
    print(f"non-streaming: first-token-time == total-time == {end - start:.2f}s")


def run_streaming() -> None:
    messages = [{"role": "user", "content": PROMPT}]
    start = time.perf_counter()
    ttft = None
    # TODO: iterate chat_stream(messages); on the *first* non-empty delta,
    # record ttft = time.perf_counter() - start (only once). Print each
    # delta as it arrives (end="", flush=True) so you can watch it stream.
    for delta in chat_stream(messages=messages, model="gpt-4.1-nano"):
        if ttft is None:
            ttft = time.perf_counter() - start
        print(f"{ttft:.2f}s: {delta}\n", end="", flush=True)
    end = time.perf_counter()
    print(f"\nstreaming: TTFT={ttft:.2f}s, total={end - start:.2f}s")


def main() -> None:
    print("=== non-streaming ===")
    run_non_streaming()
    print("\n=== streaming ===")
    run_streaming()


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# non-streaming total time: 7.16s
# streaming TTFT: 2.31s      streaming total time: 4.75s
# Was total time roughly the same both ways, as hypothesized? If not, why
# might it differ (network variance, provider load)?
#
# In what kind of UI/product does the TTFT improvement actually matter, and
# in what kind of backend workflow does it not matter at all?
