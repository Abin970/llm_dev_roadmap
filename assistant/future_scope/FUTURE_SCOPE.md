# Future scope — beyond the Week 3/4 curriculum exercise

A living list of what the AgentLoop/Graph-based SRE copilot could grow into,
past what the Week 3-4 curriculum exercises actually required. Nothing here
is scheduled — revisit and reprioritize whenever picking this back up,
whether that's mid-roadmap or after finishing it end to end.

Context for why this exists: the roadmap is breadth-first by design (new
concepts every week, skeletons not full implementations) — nothing forces a
"go back and harden what you built" pass, so quality stays wherever it was
when you moved on. This is where that gets tracked instead of lost.

## Graph topology — evolving beyond the fixed shape

- **Agent-inside-a-node.** `planner → {search_docs, search_vendor_docs}` is
  currently rigid: always exactly two tools, exactly once each. Collapse
  this into a single `investigate` node running a bounded ReAct loop
  internally (reusing `AgentLoop` from `assistant/agent/loop.py` almost
  as-is) so the number and choice of lookups can respond to what's
  actually found, while the outer graph (synthesize once, review once,
  retry capped, gate the risky action) stays deterministic and testable.
- **Dynamic fan-out.** Once the number of parallel branches isn't fixed
  at graph-definition time (e.g. "investigate every downstream service
  this incident touched," N unknown until `planner` runs), the current
  plain `add_edge` fan-out needs to become `langgraph.types.Send`.

## State and memory — beyond one run

- **Cross-run memory / pattern library.** `GraphState` is purely
  within-run working memory today — nothing persists across separate
  incidents. A real copilot wants to notice "we've seen this
  pool-exhaustion shape twice now." That's genuinely a RAG concern
  (Week 5/6), not a graph concern — retrieval over accumulated incident
  history, read at the start of a run, not crammed into `GraphState`.
- **Smarter evidence merging.** The `evidence` reducer is plain list
  concatenation (`operator.add`). Worth a custom reducer later — dedup
  near-identical entries, confidence-weighted ranking.
- **Full retry audit trail.** Currently only the latest `synthesis`/
  `review_verdict` survive a retry (last-write-wins, no reducer, by
  design — fine given the retry cap is only 2). A parallel
  `attempt_history: Annotated[list[dict], operator.add]` field would
  keep every attempt and its rejection reason, useful for debugging or
  for a future audit-trail feature.

## Production-hardening — beyond a demo

- **Real checkpointer.** `InMemorySaver` → `PostgresSaver`/`SqliteSaver`
  — state survives a restart and becomes queryable/auditable outside the
  running process, not just resumable within it.
- **`thread_id` ownership.** Currently a bare random UUID, no real
  session/auth boundary. Needs actual ownership enforcement before this
  is safe for more than one caller.
- **Checkpoint branching / time-travel.** `get_state_history()` lets you
  fork a run from an earlier checkpoint ("what if reviewer had approved
  on attempt 1?") — genuinely powerful for audit/debugging a long-lived
  incident, but a real complexity jump (a `thread_id` stops mapping to
  one linear history) — only worth it if actually needed.
- **Multiple simultaneous interrupts.** Only one pending interrupt per
  thread is supported today. If a later version gates more than one
  risky action in parallel branches, resuming needs the dict-keyed
  `Command(resume={interrupt_id: decision, ...})` form instead of the
  single-decision form `GraphAgent.resume()` uses now.
- **Real remediation, sandboxed.** Replace the mocked `apply_fix` tool
  (`assistant/tools/apply_fix.py`) with a fix actually applied to a
  minimal, deliberately-unhealthy Docker service, verified against real
  health-check signal — closes the loop on whether the LLM's fix
  actually *works*, not just that the tool call succeeded. Needs
  infrastructure the roadmap hasn't built yet (health-check/observability
  signal, safety rails around letting an LLM touch even a sandboxed
  container) — natural fit for Week 8 (production/system design) or a
  capstone stretch, not before `apply_fix_node`'s human-approval
  mechanics are solid.

## Long-running, independent operation

If this ever runs unsupervised (reacting to incoming alerts, not a human
hitting `/research`), two things matter most:

- **A global "done," not just a local one.** `MAX_RETRIES=2` bounds one
  review cycle, not the whole investigation. An unsupervised agent needs
  explicit terminal states (resolved / escalated / timed out /
  abandoned) and a run-level cost budget, not just a step count — same
  bounded-not-hoped-for principle as the retry cap, generalized to
  dollars, since unbounded wall-clock time is the real long-running risk.
- **Scoped prompts stop staying cheap as state grows.** Each node's
  advantage today is a small prompt built from specific fields, not a
  replayed history — but `evidence` (or a future `attempt_history`) can
  grow unbounded over a long investigation. Past some size it needs
  periodic summarization before every subsequent prompt, same idea as
  Week 2's truncation, just triggered by state size instead of turn
  count.

## Reviewer robustness

- `reviewer_node` (`assistant/agent/nodes/reviewer.py`) currently picks
  *either* the LLM judge or the keyword-overlap heuristic. A more robust
  design: heuristic as a cheap pre-filter, LLM judge only when the
  heuristic result is ambiguous — better cost profile and (likely)
  better reliability than either alone.

## Observability & eval maturity

- `eval_checks.py` (`week4/experiments/`) is run by hand against 4
  golden cases (`eval_cases.py`). Growing past 4 cases and wiring this
  into something that runs automatically on every change (not only when
  remembered) is the natural next step — connects to Week 7's
  tracing/eval work rather than being a separate concern.
- No real tracing yet — just the ad hoc `Event` stream. Proper
  per-node/per-run tracing is Week 7 territory.

## AgentLoop's own gaps (Week 3, still alive for comparisons)

Even though `AgentLoop` is retired as the *top-level* control flow, it
lives on standalone (`week3/experiments/`, `week4/experiments/01_loop_vs_graph.py`)
and potentially as the internal engine for the "agent-inside-a-node"
idea above. Worth remembering it has no persistence, no cost accounting,
and coarse-grained events — gaps that matter more if it graduates from
"comparison baseline" to "the thing inside a real node."
