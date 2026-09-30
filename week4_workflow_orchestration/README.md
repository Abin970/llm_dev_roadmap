# Week 4 — Workflow Orchestration with LangGraph (Project V2)

> **Changed in Week 5:** `search_web` is now `search_vendor_docs`, and
> both search tools do real retrieval over a real corpus instead of
> reading the made-up fixtures this page mentions (`tools/docs/*.md`,
> PoolGuard/BackoffKit). The graph's shape is unchanged. `eval_cases.py`
> was rewritten against the real corpus, keeping each case's position.
> This README describes the graph as it was built in Week 4; see
> `week5_rag_fundamentals/README.md` for what changed.

Why agent loops alone don't survive production. Week 3's `AgentLoop`
answers a question with an implicit while-loop; this week the same
assistant becomes an explicit, inspectable graph — and gets grounded in
something more concrete than a generic "research agent": an **SRE/on-call
copilot** that investigates an incident, proposes a fix, checks its own
answer is actually grounded in evidence before trusting it, and pauses
for a human's sign-off before it (pretends to) touch anything.

## Graph flow

How one `/research` call moves through the graph, and which tool each
node touches:

```
POST /research  (new thread_id)
        │
        ▼
     [START]
        │
        ▼
   ┌──────────┐
   │ planner  │   retry_count += 1; decides what to search for
   └────┬─────┘
        │  fan-out — both run in the SAME step
   ┌────┴─────────────────┐
   ▼                      ▼
┌────────────────┐  ┌────────────────┐
│ search_docs_node│  │ search_web_node│
│ → dispatch(     │  │ → dispatch(    │
│   "search_docs")│  │   "search_web")│
└────────┬────────┘  └────────┬───────┘
         │                    │
         └─────────┬──────────┘   fan-in — waits for BOTH branches
                    ▼
              ┌───────────┐
              │   merge   │   evidence = docs-evidence + web-evidence
              └─────┬─────┘
                    ▼
             ┌──────────────┐
             │ synthesizer  │   chat(): root cause + fix, citing evidence
             └──────┬───────┘
                    ▼
               ┌──────────┐
               │ reviewer │   grounding check on the synthesis
               └────┬─────┘
                    │
        ┌───────────┴────────────────┐
     approved                     rejected
        │                             │
        ▼                       retry_count >= 2 ?
  ┌─────────────┐                 │          │
  │ apply_fix_  │                no          yes
  │ node        │                 │          │
  │             │                 ▼          ▼
  │ interrupt() │           back to      [END] —
  │  ⏸ PAUSES   │            planner     forced best-effort
  │  the graph  │           (loop)        answer
  └──────┬──────┘
         │   ⋯ suspended, thread_id checkpointed ⋯
         │
         │   POST /research/resume {thread_id, approved}
         ▼
   decision.approved?
     │no  → synthesis += "(fix not applied)"  ──► [END]
     │yes → dispatch("apply_fix", ...)         ──► [END]
```

Tools touched, by node:

| Node               | Tool called                    | Gated behind approval? |
|  ---               |    ---                         |        ---             |
| `search_docs_node` | `dispatch("search_docs", ...)` | no — read-only |
| `search_web_node`  | `dispatch("search_web", ...)`  | no — read-only |
| `apply_fix_node`   | `dispatch("apply_fix", ...)`   | **yes** — only after `interrupt()` resumes with `approved=True`|

The only cycle in the graph is `reviewer → planner`, capped at
`retry_count >= 2`. Everything else is a straight line, including the
fan-out/fan-in — the parallelism is just topology (two nodes both fed by
`planner`, both feeding `merge`), not a loop.

## Setup (one-time)

1. From the repo root, activate the venv:
   ```
   source ../.venv/bin/activate
   ```
2. Install this week's new dependency (LangGraph):
   ```
   pip install -r ../requirements.txt
   ```
3. If you haven't already, seed the sample database (unchanged since
   Week 2/3):
   ```
   cd ../assistant && python tools/seed_db.py && cd -
   ```

## Order of operations

1. **`assistant/tools/apply_fix.py`** — one new tool, same TODO pattern
   as every other tool in this project. Mocked/no-op on purpose: it's
   the first tool in the registry that changes something (even if only
   pretend), which is exactly why it's the one this week's human-approval
   exercise gates.
2. **`assistant/agent/state.py`** — the graph's shared state schema. The
   one real decision here: `evidence` needs a reducer, or the parallel
   search step in point 4 will silently lose one branch's result.
3. **`assistant/agent/nodes/`** — six node functions: `planner.py`,
   `search.py` (both `search_docs_node` and `search_web_node`),
   `merge.py`, `synthesizer.py`, `reviewer.py`, `apply_fix_node.py`. Each
   is a pure function (state in → partial state out) and independently
   testable without a real LLM call if you mock its inputs — build and
   sanity-check them roughly in this order, since `reviewer_node` is
   where the retry loop and `apply_fix_node` is where the interrupt live.
4. **`assistant/agent/graph.py`** — wires the six nodes into a
   `StateGraph`: the fixed two-branch fan-out/fan-in, the bounded
   Planner↔Reviewer retry loop, the checkpointer, and a `GraphAgent`
   wrapper exposing the same `.run(...) -> Iterator[Event]` shape
   `AgentLoop`/`LangChainAgent` already use (plus `.resume(...)` for the
   human-approval flow). This is the heart of the week.
5. **`assistant/main.py` → `POST /research/resume`** — new endpoint,
   resumes a `/research` run that paused waiting on a human decision.
6. **`week4/experiments/eval_checks.py`** — the graph-specific
   verification harness (tool-sequence validity, grounding, retry bound,
   parallel-evidence completeness, resume consistency). Write this
   before the experiments below so they can call it instead of relying
   on you eyeballing each trace by hand.
7. **`week4/experiments/01_loop_vs_graph.py`**, then
   **`02_retry_guard.py`**, then **`03_human_approval.py`**.

Each file has its own `TODO`s; experiment files have an `OBSERVATIONS`
block at the bottom, same discipline as weeks 1-3.

## What "done" looks like for Week 4

Cross-check against the roadmap artifact's Week 4 → Completion criteria.
In short: you can explain why LangGraph over a bare agent loop with a
concrete failure the loop couldn't handle, explain what a reducer does
and why the parallel search branches need one, have implemented real
branching + a bounded retry loop + true parallel fan-out/fan-in, have a
working human-approval interrupt with resume, and can say when you'd
choose agent vs. workflow vs. agent-inside-a-node for a new requirement
— using this project's own Planner/Reviewer/apply_fix as your concrete
example of each, not an abstract one.
