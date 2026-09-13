"""
Experiment 4 -- Rate-limit backoff
========================================
Hypothesis : fixed-delay retries cause a "thundering herd" -- every caller
             retries at the exact same instant, so they keep colliding --
             while jittered exponential backoff spreads retries out over
             time and clears a burst of failures faster overall.
Setup      : no real API call here -- simulate a flaky function that
             raises a rate-limit error for its first N calls, then
             succeeds. Run several "concurrent" callers against it under
             both retry strategies (a plain loop simulating callers is
             fine; true concurrency isn't the point of this exercise).
Teaches    : this isn't LLM-specific -- it's the same thundering-herd
             problem you'd design around for any flaky rate-limited
             upstream.

Run: python experiments/04_rate_limit_backoff.py
"""
import random
import time

import _bootstrap  # noqa: F401


class RateLimitError(Exception):
    """Simulated rate-limit error for this experiment."""
    pass


def flaky_call(attempts: list[int], fail_until: int) -> str:
    """
    TODO: attempts is a single-item list used as a mutable counter (so
    callers can track state across retries). Increment attempts[0]; if
    it's still <= fail_until, raise RateLimitError; otherwise return
    "ok".
    """
    attempts[0] += 1
    if attempts[0] <= fail_until:
        raise RateLimitError(f"Simulated rate limit error on attempt {attempts[0]}")
    return "ok"


def retry_fixed_delay(fail_until: int, delay: float = 1.0) -> float:
    """
    TODO: retry flaky_call in a loop, sleeping exactly `delay` seconds
    (no randomness) between each failed attempt, until it succeeds.
    Return total elapsed wall-clock time (time.perf_counter() diff).
    """
    attempts = [0]
    start_time = time.perf_counter()
    while True:
        try:
            flaky_call(attempts=attempts, fail_until=fail_until)
            break
        except RateLimitError:
            time.sleep(delay)
    elapsed_time = time.perf_counter() - start_time
    return elapsed_time


def retry_jittered_backoff(fail_until: int, base: float = 0.5) -> float:
    """
    TODO: retry flaky_call, sleeping `base * 2**attempt_number +
    random.uniform(0, base)` between attempts (exponential backoff with
    jitter) until it succeeds. Return total elapsed time.
    """
    attempts = [0]
    start_time = time.perf_counter()
    while True:
        try:
            flaky_call(attempts=attempts, fail_until=fail_until)
            break
        except RateLimitError:
            attempt_number = attempts[0]
            sleep_time = base * (2 ** attempt_number) + random.uniform(0, base)
            time.sleep(sleep_time)
    elapsed_time = time.perf_counter() - start_time
    return elapsed_time


def simulate_burst(strategy_fn, num_callers: int = 5, fail_until: int = 3) -> None:
    """
    TODO: call strategy_fn(fail_until) once per "caller" (a plain for
    loop -- each call already includes its own retry-until-success logic
    above) and print each caller's total elapsed time, plus the max
    across all callers (i.e. how long until the whole burst clears).
    """
    elapsed_times = []
    for i in range(num_callers):
        elapsed_time = strategy_fn(fail_until=fail_until)
        elapsed_times.append(elapsed_time)
        print(f"Caller {i + 1} elapsed time: {elapsed_time:.2f} seconds")
    max_elapsed_time = max(elapsed_times)
    print(f"Max elapsed time across all callers: {max_elapsed_time:.2f} seconds")


def main() -> None:
    print("=== fixed-delay retries ===")
    simulate_burst(retry_fixed_delay)
    print("\n=== jittered exponential backoff ===")
    simulate_burst(retry_jittered_backoff)


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# Did fixed-delay retries cluster (multiple callers retrying at the same
# moment)? Did jitter visibly spread them out?
#
# Which strategy cleared the whole simulated burst faster? Was that
# actually true for every run, or did it vary -- and if it varied, what
# does that tell you about testing retry logic with a single run?
