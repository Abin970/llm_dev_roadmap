"""
Experiment 3 -- Free-form vs schema-constrained structured output
====================================================================
Hypothesis : asking for JSON via prompt instructions alone has a real,
             non-zero parse-failure rate; schema-constrained decoding
             (response_format) does not.
Setup      : same extraction task, run N times each way, count parse failures.
Teaches    : why the structured-output API exists instead of just prompting
             nicely for JSON.

Run: python experiments/03_structured_output.py
"""
import json

import _bootstrap  # noqa: F401
from llm_client import chat, chat_structured
from pydantic import BaseModel

N_RUNS = 5

INCIDENT_TEXT = (
    "At 14:32 UTC the checkout-service pods started OOMKilling after a deploy "
    "that bumped the JVM heap default down. Payment success rate dropped to 40%. "
    "Rolled back at 14:51 UTC, fully recovered by 14:55 UTC. No data loss."
)


# TODO: define the schema you want extracted from an incident writeup like the
# one above. Suggested fields: severity (an enum-like Literal, not a free
# string), affected_service: str, start_time: str, resolved: bool,
# summary: str. Use Pydantic's `Literal` for severity so the model is
# constrained to real values, not whatever it feels like writing.
class IncidentReport(BaseModel):
    severity: str
    affected_service: str
    start_time: str
    resolved: bool
    summary: str


FREE_FORM_PROMPT = (
    "Walk me through this incident and give me a JSON summary at the end.\n\n"
    f"{INCIDENT_TEXT}"
)


def run_free_form() -> None:
    failures = 0
    for i in range(N_RUNS):
        text = chat([{"role": "user", "content": FREE_FORM_PROMPT}], temperature=1.0)
        try:
            # TODO: json.loads(text) -- note the model may wrap it in
            # ```json fences or add a leading sentence; decide whether you
            # strip those or count it as a failure as-is (that's part of
            # the point).
            json.loads(text)
        except (json.JSONDecodeError, TypeError):
            failures += 1
            print(f"  run {i+1}: PARSE FAILURE -> {text[:80]!r}")
    print(f"free-form JSON: {failures}/{N_RUNS} parse failures")


def run_structured() -> None:
    failures = 0
    for i in range(N_RUNS):
        messages = [{"role": "user", "content": f"Extract the incident details:\n\n{INCIDENT_TEXT}"}]
        # TODO: call chat_structured(messages, IncidentReport, model=...);
        # count it as a failure if the result is None (a refusal).
        result = chat_structured(messages, IncidentReport, model="gpt-4.1-nano")
        if result is None:
            failures += 1
            print(f" run {i+1}: PARSE FAILURE (refusal)")
    print(f"structured output: {failures}/{N_RUNS} parse failures")


def main() -> None:
    print("=== free-form JSON (prompt only) ===")
    run_free_form()
    print("\n=== schema-constrained structured output ===")
    run_structured()


if __name__ == "__main__":
    main()

# --- OBSERVATIONS ------------------------------------------------------------
# free-form failure rate: 15/15
# structured-output failure rate: 15/15
# What did the free-form failures actually look like (markdown fences? extra
# prose? truncation?) -- would a regex have caught all of them reliably?
#
# same as previous experiment: model is too good generating JSON,
# it might be valid JSON but not the right schema (e.g. missing fields, wrong types).
#
# Even when structured output parses successfully, is the *data* always
# correct (e.g. is severity ever a plausible-sounding but wrong value)?
# What does that tell you about validation vs correctness?
