# Week 5 — RAG plan: decisions, pipeline, corpus

Distilled from the Week 5 planning session (Sep 29–30, 2026), with numbers
and tool choices updated to what was actually built. What got built is in
`rag_to_know.md`; the step-by-step TODO order is in
`week5_rag_fundamentals/README.md`.

## Why this week exists

Before Week 5, both evidence branches of the Week 4 graph ran keyword
matching over made-up fixtures:
- `search_docs`: 7 fictional incident notes, 484 words in total.
- `search_web`: 3 fictional "web pages" (PoolGuard, BackoffKit, PulseQueue).

That's small enough to paste into every prompt, so retrieval could never
fail in an interesting way. And the Week 4 eval cases were written to fit
those fixtures.

Week 5 replaces this with real retrieval, built on three principles:
- Every data source is real and authoritative.
- Together the sources cover a typical production stack end to end.
- The golden questions come from the corpus, never the corpus from the
  questions.

## Decisions

- **Use case: stay on the SRE/on-call copilot**, not banking or insurance.
  - Week 5's milestone is retrieval running inside the Week 4 graph. A new
    domain would fork the project that Weeks 6–8 build on.
  - The roadmap asks for a corpus you can judge. With infra docs you can
    tell a right chunk from a wrong one.
  - Infra docs are full of exact names (alert names, error codes, config
    keys). Plain vector search tends to miss those, which is the problem
    Week 6's hybrid search fixes.
  - What insurance would teach instead (messy PDFs, tables, clause
    exclusions) can come back later as one side experiment.
- **The web branch became a vendor-docs index.** `search_web` is now
  `search_vendor_docs`: real retrieval over official docs, repeatable, so
  golden-set scores stay stable. A live web-search API was the
  alternative; its results change over time, so any eval touching it
  wouldn't be repeatable.
- **The fictional incident notes were replaced by real public postmortems.**
- **Embeddings: OpenAI `text-embedding-3-small` now, a local model later**
  (reasons below). Verified working with the project key
  (`OPENAI_API_KEY_LLM_PRJ`) on 2026-09-30.
- **pgvector over Qdrant.** The roadmap's final architecture already uses
  Postgres + pgvector, and the same Postgres can later hold LangGraph
  checkpoints (FUTURE_SCOPE, "Real checkpointer").

## The pipeline

```
OFFLINE: ingestion (run once; re-run when sources change)
  fetch  (manifest → data/corpus/, gitignored; third-party text never committed)
   → load  (md/html → clean markdown + metadata {source, layer, doc_type, url, title})
   → chunk (sized in tokens, three strategies to compare)
   → embed (text-embedding-3-small, batched)
   → store (FAISS file for exercises 1–2 → one pgvector table for exercise 3 + the project)

ONLINE: per /research request (Week 4 graph shape unchanged)
  planner ─┬─ search_docs        → top-k where doc_type ∈ {runbook, postmortem}  "what happened / what to do"
           └─ search_vendor_docs → top-k where doc_type = vendor_doc            "what the tool supports"
                  ▼
                merge → synthesizer (answer + [chunk_id] citations)
                      → reviewer (grounded? is every cited chunk actually in evidence?) → apply_fix (human gate)
```

Both branches search the same index with different `doc_type` filters,
which puts the roadmap's metadata-filtering lesson into real use. The
graph keeps Week 4's split: the incident side ("why it happened") and the
vendor-docs side ("what the tool supports"), which the synthesizer
combines.

## The corpus

**One scope rule, fixed before any question was written.** For each
technology, include only the pages an on-call engineer actually opens:
configuration reference, operations/admin, monitoring/metrics,
troubleshooting, and failure/high-availability behavior. No tutorials,
install guides, client API references, release notes or contributor docs.

| Layer | Source (official) | Format | Docs | Phase |
|---|---|---|---:|:---:|
| Database | PostgreSQL 18: runtime config, connections, vacuum, locks, WAL, replication, monitoring | HTML | 23 | A |
| Orchestration (+ Ingress, logging, ConfigMaps/Secrets) | Kubernetes: debug tasks, pod lifecycle, probes, resources, eviction, autoscaling, Services | md | 33 | A |
| Alert runbooks | prometheus-operator/runbooks (Apache-2.0) | md | 108 | A |
| API gateway / load balancer | NGINX: proxy, upstream, load balancing, rate limiting, logging | HTML | 11 | B |
| App server | Gunicorn (settings, design, signals, FAQ) + Uvicorn (settings, deployment) | md | 14 | B |
| Cache | Redis: eviction, persistence, replication, memory, latency | md | 13 | B |
| Message queue | Kafka 4.3: operations, design, monitoring, plus the generated config tables | md + HTML | 10 | B |
| Container (+ log drivers) | Docker: resource limits, restart policies, runtime metrics, daemon troubleshooting, logging drivers | md | 11 | B |
| Logs & config | Fluent Bit: pipeline, buffering, backpressure, tail input, monitoring | md | 14 | B |
| Monitoring & observability | Prometheus (alerting practices, PromQL, storage) + OpenTelemetry (concepts, collector) | md | 31 | B |
| Incidents | 40 real public postmortems spanning the layers above (from danluu/post-mortems) | blog HTML | 40 | B |
| **Total** | | | **308** | |

- **Size:** about 898k tokens in total. Phase A is 164 docs (~330k
  tokens). Embedding everything costs a few cents.
- **Fetched, never committed.** `data/` is gitignored and
  `python -m ingestion.fetch` re-creates it. Git sources are shallow,
  sparse clones that download only the listed files. Web pages are
  fetched politely, with robots.txt respected.
- **Pinned versions** where the source is versioned (PostgreSQL 18,
  Kafka 4.3), so golden answers don't drift. Git sources record their
  exact commit, and citation URLs point at it.
- **Real-world mess, on purpose.** The loaders have to deal with Hugo
  front matter and `{{< shortcodes >}}`, GitBook `{% hint %}` tags, HTML
  comments, navigation tables inside page content, and Kafka config
  tables that exist only as generated HTML.
- **Some candidates didn't make it:** JavaScript-only status pages, a
  parked domain, and a Korean-only duplicate. The reasons are noted in
  `sources.py`.

## The golden set

37 questions, written after the corpus was fetched by reading the real
pages. 16 of them work on the Phase A index.
- **Kinds:**
  - 15 *identifier*: names the exact alert or setting.
  - 15 *symptom*: describes what you see, not the name.
  - 3 *cross_source*: needs passages from two sources.
  - 4 *not_in_corpus*: the right answer is "not covered".
- **Each question records** its expected page and section, layer, kind and
  key facts, plus short verbatim "marker" phrases from the answering
  passage. Every marker was machine-checked against the fetched text.
- **Scoring:** a retrieved chunk counts only if it comes from the expected
  page AND contains a marker. So hit@k measures "the answering passage was
  retrieved", which makes it sensitive to how text was chunked.
- **Answer correctness** is the user's to verify.

## What we use, and where

| Stage | Library | Lives in |
|---|---|---|
| Fetch | `git` sparse checkout + `requests` | `assistant/ingestion/sources.py`, `fetch.py` |
| Load | plain Python (md); `beautifulsoup4` + `markdownify` (vendor HTML); `trafilatura` (postmortems) | `assistant/ingestion/loaders.py` |
| Chunk | `langchain-text-splitters` + `tiktoken` | `assistant/ingestion/chunkers.py` |
| Embed | `openai` → `text-embedding-3-small` (1536 dims) | `assistant/embeddings.py` |
| Store | `faiss-cpu`; Postgres + pgvector (`psycopg`, `pgvector`) | `assistant/vectorstore.py`, `docker-compose.yml` |
| Retrieve | both stores behind one `VectorStore.search()` | `assistant/retrieval.py`, `tools/search_docs.py`, `tools/search_vendor_docs.py` |
| Cite | `chat_structured()` + `ApplyFixesArgs.citations` | `agent/state.py`, `agent/nodes/synthesizer.py`, `agent/nodes/reviewer.py` |
| Measure | the golden set + scoring checks | `week5_rag_fundamentals/experiments/` |
| Later | BM25 + a cross-encoder reranker (Week 6), RAGAS (Week 7) | — |

Vendor HTML goes through BeautifulSoup + markdownify rather than
trafilatura because trafilatura drops the fences around code blocks, and
the chunking exercise needs to see code blocks intact.

## Embeddings: OpenAI now, local later

- **Time:** neither is meaningfully faster here. Embedding the whole
  corpus takes minutes either way and only reruns when the sources change.
  Per question, a local model skips about 0.1–0.3s of network time, which
  disappears next to the multi-second LLM calls.
- **Input length is the real difference.** The local default
  (`bge-small-en-v1.5`) reads at most 512 tokens of a chunk and cuts off
  the rest; OpenAI's model reads up to 8,192. Exercise 2 compares chunk
  sizes, and that cutoff would quietly skew the comparison.
- **Local wins later:** it keeps text on your own machine (which matters
  once real internal postmortems are involved), and Week 6 brings in the
  same library (`fastembed`) for reranking anyway. Then the same golden
  set can be run through both models to compare them.

## Phases

- **Phase A (short feedback loop):** PostgreSQL + Kubernetes + runbooks go
  through load → chunk → embed → FAISS. Experiments 1–2 run on this slice.
- **Phase B:** the remaining sources and postmortems, pgvector (experiment
  3), graph wiring, citations, and the full golden set.
- The corpus work makes this week bigger than the roadmap's 19-hour
  budget; Phase A keeps the first results quick.

## The three experiments

- **01 FAISS vs keyword:** top-3 hit rate of dense retrieval against the
  Week 3 keyword scorer, split by layer and question kind.
- **02 Chunking comparison:** fixed vs recursive vs markdown-header
  chunking, on the same questions and embedding model.
- **03 pgvector filtering:** filtered vs unfiltered search, and exact
  search vs an HNSW index.

## Reading list (~2h)

Must-read:
1. LlamaIndex, [Introduction to RAG](https://developers.llamaindex.ai/python/framework/understanding/rag/):
   the five stages (skip their API).
2. The [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings).
   Its FAQ explains that the vectors have length 1, so cosine similarity
   equals the dot product.
3. The [pgvector README](https://github.com/pgvector/pgvector): distance
   operators, exact vs HNSW search, and "Iterative Index Scans" (filters
   apply after an approximate search, so a filtered query can return fewer
   than k rows).
4. [FAISS Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started):
   the flat index only.
5. LangChain's text-splitter docs (recursive and markdown-header).

Optional:
- Barnett et al. 2024, *Seven Failure Points When Engineering a RAG
  System* (arXiv 2401.05856)
- Liu et al. 2023, *Lost in the Middle* (arXiv 2307.03172)
- Anthropic 2024, [Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- Lewis et al. 2020, the original RAG paper (arXiv 2005.11401): abstract
  and Figure 1 only

Skip for now: the HNSW, DPR and ColBERT papers, and RAGAS (Week 7).

## What success looks like

- At least 80% top-3 hit rate on the golden set's answerable questions on
  the pgvector path (the roadmap's bar), broken down by layer and question
  kind, and compared with the keyword baseline.
- FAISS (flat) and pgvector (no index) return the same top-k for every
  golden question. Both are exact search, so a mismatch means an ingestion
  or normalization bug. Only then add HNSW and compare.
- The edge cases behave: an out-of-corpus question gets no invented
  citation; an answer split across a chunk boundary; near-duplicate
  runbooks in the top-k.
- End-to-end `/research`: both branches return real chunks, every cited
  chunk id appears in the evidence, Week 4's graph-mechanics checks still
  pass (retry bound, parallel evidence, resume), and the rewritten Week 4
  cases pass.
