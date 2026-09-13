# Week 2 — LLM Application Primitives

From "calling an LLM" to an actual backend service: conversation state,
tool-calling done end to end, reliability, and typed events.

## Setup (one-time)

1. From the repo root, activate the same venv week1 used:
   ```
   source ../.venv/bin/activate
   ```
2. Install the two new dependencies this week needs (FastAPI + uvicorn,
   for `main.py`):
   ```
   pip install -r ../requirements.txt
   ```
3. Seed the sample database the `sqlite_query` tool reads from:
   ```
   python tools/seed_db.py
   ```
   This creates `tools/sample.db` with two small tables (`incidents`,
   `deploys`). Complete and runnable as-is — nothing to implement there.

## Order of operations

Unlike week1, these files depend on each other, so build them in this
order:

1. **`tools/registry.py`** first — every tool and every experiment needs
   `register`/`dispatch` to exist.
2. **The four tool files** (`tools/calculator.py`, `file_reader.py`,
   `sqlite_tool.py`, `mock_search.py`) — each is independent of the
   others, do them in any order.
3. **`experiments/01_tool_dispatcher.py`** — first real checkpoint; if
   this doesn't run clean, don't move on yet.
4. **`experiments/03_malformed_tool_call.py`** — same registry/tools,
   testing the failure path instead of the happy path.
5. **`conversation.py`**, then **`experiments/02_truncation_comparison.py`**.
6. **`events.py`**, then **`experiments/04_rate_limit_backoff.py`** (this
   one doesn't actually depend on `events.py` — it's independent, do it
   whenever).
7. **`main.py`** last — it pulls in everything above.

Each file has its own `TODO`s. Experiment files also have an
`OBSERVATIONS` block at the bottom — fill it in after running, same
discipline as week1.

## What "done" looks like for Week 2

Cross-check against the roadmap artifact's Week 2 → Completion criteria.
In short: `tools/registry.py` and all 4 tools implemented with no
`NotImplementedError` left, all 4 experiments run with `OBSERVATIONS`
filled in, and `main.py` serves a working `POST /chat` that streams
events over SSE end to end (test it with `curl -N`, not just by reading
the code).
