# Week 3 — Agents (Project V1 begins)

Understand the loop before you let a framework hide it. This week the
project gets a name for real: `assistant/` — an AI Research/Engineering
Assistant. It's the same codebase weeks 4-8 keep building on, all the way
to the capstone.

## Setup (one-time)

1. From the repo root, activate the venv:
   ```
   source ../.venv/bin/activate
   ```
2. Install this week's new dependency (LangChain + the OpenAI integration):
   ```
   pip install -r ../requirements.txt
   ```
3. If you haven't already for Week 2, seed the sample database:
   ```
   cd ../assistant && python tools/seed_db.py && cd -
   ```

## Order of operations

1. **`assistant/llm_client.py` → `chat_with_tools()`** — everything else
   in this file is carried over from Week 2, already working. This one
   function is new.
2. **`assistant/tools/registry.py` → `to_openai_tools()`** — turns your
   existing registered tools into something the model can actually call.
3. **`assistant/tools/search_docs.py`** and **`search_web.py`** — two new
   tools, same TODO pattern as Week 2's tools.
4. **`assistant/agent/loop.py` → `AgentLoop`** — the hand-rolled ReAct
   loop. This is the heart of the week.
5. **`week3/experiments/01_hand_rolled_loop.py`** — first real checkpoint.
   Don't move on until this runs clean.
6. **`assistant/agent/langchain_agent.py` → `LangChainAgent`** — same
   tools, via LangChain's `create_agent`.
7. **`week3/experiments/02_langchain_diff.py`**, then
   **`03_break_it.py`**.
8. **`assistant/main.py` → `/research`** endpoint — last, once
   `AgentLoop` works standalone. (`/chat` is still open from Week 2 if
   you haven't finished it — not required for this week's exercises, but
   worth closing out eventually.)

Each file has its own `TODO`s; experiment files have an `OBSERVATIONS`
block at the bottom, same discipline as weeks 1-2.

## What "done" looks like for Week 3

Cross-check against the roadmap artifact's Week 3 → Completion criteria.
In short: `AgentLoop` reliably terminates (either with a real answer or a
clear "couldn't finish"), you can explain the agent-vs-workflow
distinction with a real example, `LangChainAgent` reproduces the same
behavior and you can say what it automated for you, and Project V1
answers a real technical question end-to-end with visible intermediate
tool-call events.
