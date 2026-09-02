# Week 1 — LLM Fundamentals & Prompt Engineering

No framework. You're calling the raw OpenAI SDK and watching exactly what
goes over the wire.

## Setup (one-time)

1. Get an API key: https://platform.openai.com/api-keys — create a
   project-scoped key for this repo (not your main/org key) and set a spend
   limit on it. See the security note in `.env.example` for why.
2. From the repo root:
   ```
   cp .env.example .env
   chmod 600 .env
   ```
   then paste your key into `.env` as `OPENAI_API_KEY=sk-...`
3. The venv and dependencies are already installed at `../.venv`. Activate it:
   ```
   source ../.venv/bin/activate
   ```
4. Sanity-check your key and see what models your account can actually call:
   ```
   python -c "from openai import OpenAI; [print(m.id) for m in OpenAI().models.list()]"
   ```
   Compare that list against `OPENAI_MODEL` in `.env` and adjust per the
   tiering table there (cheap for Week 1-2, mid for Week 3-5, frontier for
   Week 6-8).

## Keeping your API key safe

`.gitignore` keeps `.env` out of commits, but that's not the whole story:

- `.env` is `chmod 600` (owner-only) so other local users/processes on this
  machine can't just read it off disk.
- A local git hook (`.git/hooks/pre-commit`) refuses any commit that stages
  `.env` or a diff shaped like a live key — a backstop for `git add -A`
  without looking. It's untracked, so it protects only this clone; it won't
  follow the repo if you clone it elsewhere.
- Use a project-scoped key with a spend limit (see Setup step 1), not your
  main account key — caps the damage if it ever does leak.
- Never print or log a raw client/response object; the key itself isn't in
  API responses, but don't build the habit of dumping SDK internals to
  stdout or screenshots.
- If a key leaks anyway (pasted somewhere, pushed, shared in a screenshot),
  revoke it on the OpenAI dashboard and issue a new one immediately —
  deleting the commit or message after the fact doesn't undo the exposure.

## Order of operations

1. **Implement `llm_client.py` first.** Every experiment imports from it.
   Fill in the four `TODO`-marked functions (`get_client`, `chat`,
   `chat_stream`, `chat_structured`, `count_tokens`) using the API shapes
   documented in the file's own docstrings — those were pulled from current
   SDK docs, not guessed.
2. Run the experiments **in order**, `01` through `06`:
   ```
   python experiments/01_temperature_sweep.py
   ```
   Each has its own `TODO`s (the experiment-design choices, not SDK
   mechanics — that's `llm_client.py`'s job) and an `OBSERVATIONS` block at
   the bottom. Fill that in after running it, before moving to the next one
   — the point of each experiment is the sentence you can write afterward,
   not the code.

## What "done" looks like for Week 1

Cross-check against the completion checklist in the roadmap artifact
(Week 1 → Completion criteria). In short: `llm_client.py` fully implemented
with no `NotImplementedError` left, all 6 experiments run successfully with
their `OBSERVATIONS` filled in, and you can explain *why* each result came
out the way it did — not just that it did.

## A note on staleness

Model names and the `"developer"` role name are what the SDK's own docs
used as of when this was last touched (Sep 2026), and both move fast.
`gpt-5-nano`/`gpt-5-mini` (used here through Week 5) are scheduled to sunset
2026-12-11 — check pricing and availability again if you're still on an
early week close to that date; the newer `gpt-5.6-*` family replaces them
but at a *higher* price per token (verified against the live pricing docs,
not assumed from the "compact"/"efficient" naming). If something in
`llm_client.py`'s docstrings looks off against what you're actually seeing,
trust the live API response over this file's comments.
