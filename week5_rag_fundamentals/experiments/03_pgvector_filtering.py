"""
Experiment 3 -- Migrate to pgvector, with metadata filters
===========================================================
Objective  : the artifact's exercise 3. Move the same data into Postgres
             with metadata columns, then see that a filter is often a
             bigger precision win than a better embedding model. It
             also shows where filtering and an approximate index
             interact badly.
Setup      : docker compose up -d pgvector      (repo root)
             the full corpus (Phase A + B) in PgVectorStore, using
             whichever chunker won experiment 2:
                 python -m ingestion.fetch
                 python -m ingestion.pipeline --strategy <winner> --store pgvector

TODO:
  1. Consistency check. For the Phase A golden questions, FaissStore
     (flat) and PgVectorStore (no index yet) are both EXACT search, so
     for the same chunks and vectors their top-5 ids must match. Any
     difference is an ingestion or normalization bug; fix it before
     trusting anything else.
  2. Filtered vs unfiltered, on an ambiguous question such as "how long
     are idle connections kept open?" Run it with no filter, then with
     layer = database, app_server and gateway_lb: Postgres
     idle_in_transaction_session_timeout vs uvicorn/Gunicorn keep-alive
     vs nginx keepalive_timeout. Then run the golden set once per graph
     branch filter (doc_type in {runbook, postmortem} vs vendor_doc).
     That's the filter each search tool will use.
  3. HNSW and the fewer-than-k effect:
       CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops);
     Pick a SELECTIVE filter (count rows per doc_type and layer first;
     postmortem chunks are a small share). Then:
       SET enable_seqscan = off;       -- on a small table the planner may skip the index
       SET hnsw.ef_search = 10;        -- small candidate list, so the effect is visible
     run LIMIT 5 filtered queries and count the rows returned. Then
       SET hnsw.iterative_scan = relaxed_order;
     and count again. EXPLAIN each one to see which plan actually ran.
     (Verified on 2026-09-30 with synthetic data: 1 row came back for
     LIMIT 5, and 5 with iterative scan, identical to exact search.)
  4. Save the report under experiment_results/.

Observe    : how much the right filter improves top-3 on ambiguous
             questions, compared with anything a chunking tweak did in
             experiment 2; and the fewer-than-k rows, a result that is
             silently incomplete.
Teaches    : metadata you keep at load time (the artifact's warning
             about dropping it) is what makes filtering possible. An
             approximate index plus a filter is a correctness question,
             not just a speed knob.

Run: python experiments/03_pgvector_filtering.py      (from week5_rag_fundamentals/)
"""
import _bootstrap  # noqa: F401

from golden_retrieval import for_phase
import retrieval_checks as rc


def main() -> None:
    raise NotImplementedError("TODO: see the module docstring")


if __name__ == "__main__":
    main()
