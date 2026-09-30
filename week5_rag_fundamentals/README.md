# Week 5 — RAG Fundamentals (Project V3)

Until now the SRE copilot's two evidence branches ran keyword matching over
made-up fixtures: 7 fictional incident notes (484 words in total) and 3
fake "web pages". That's small enough to paste into every prompt, so
retrieval never had a chance to fail in an interesting way. This week the
fixtures are retired. Both branches now search a **real corpus** covering a
typical production stack end to end, through a real pipeline:
load → chunk → embed → store → retrieve. Answers cite the exact chunks they
came from.

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

`search_web` was renamed `search_vendor_docs`. The graph's nodes didn't
change. They still call `dispatch(tool_name, ...)`, and only what's behind
the tool names changed. That's the Week 2 tool registry paying off.

## The corpus

**One scope rule, fixed before any question was written.** For each
technology, include only the pages an on-call engineer actually opens:
configuration reference, operations/admin, monitoring/metrics,
troubleshooting, failure/HA behavior. No tutorials, install guides or
client API docs. `assistant/ingestion/sources.py` lists every page.

| Layer | Source | Docs | ~Tokens | Phase |
|---|---|---:|---:|:---:|
| Database | PostgreSQL 18 docs (HTML) | 23 | 153k | A |
| Orchestration (+ Ingress, logging, ConfigMaps) | Kubernetes docs | 33 | 149k | A |
| Alert runbooks | prometheus-operator/runbooks | 108 | 25k | A |
| API gateway / load balancer | NGINX docs (HTML) | 11 | 63k | B |
| App server | Gunicorn + Uvicorn docs | 14 | 36k | B |
| Cache | Redis docs | 13 | 67k | B |
| Message queue | Kafka 4.3 docs + generated config tables | 10 | 151k | B |
| Container (+ log drivers) | Docker docs | 11 | 24k | B |
| Logs & config | Fluent Bit docs | 14 | 52k | B |
| Monitoring & observability | Prometheus (2 repos) + OpenTelemetry docs | 31 | 95k | B |
| Incidents | 40 real public postmortems (danluu/post-mortems) | 40 | 85k | B |
| **Total** | | **308** | **~898k** | |

- **Phase A** (164 docs, ~330k tokens) is the first slice: one HTML
  source, one markdown source, and one runbook source. It's enough to run
  exercises 1–2 end to end before touching the other 144 documents.
- **Fetched, never committed.** `data/` is gitignored, and
  `python -m ingestion.fetch` re-creates it from `sources.py`. Git sources
  are shallow, blobless, sparse clones (only the listed files). Web pages
  are fetched politely: 1s apart per host, robots.txt respected.
- **Versions are pinned** where the source is versioned (PostgreSQL 18,
  Kafka 4.3), so the golden answers don't drift. Git sources record their
  exact commit in the manifest, and citation URLs point at that commit.
- **Pages that didn't make it**, and why, are noted in `sources.py`:
  JavaScript-only status pages, a parked domain, and a Korean-only
  duplicate. The first pass of that check extracted every page and
  flagged the ones that came out nearly empty.

## What we use, and where

| Stage | Library | Lives in |
|---|---|---|
| Fetch | `git` sparse checkout + `requests` | `assistant/ingestion/sources.py`, `fetch.py` *(done)* |
| Load | plain Python (md), `beautifulsoup4` + `markdownify` (vendor HTML), `trafilatura` (postmortems) | `assistant/ingestion/loaders.py` |
| Chunk | `langchain-text-splitters` + `tiktoken` | `assistant/ingestion/chunkers.py` |
| Embed | `openai` → `text-embedding-3-small` (1536 dims) | `assistant/embeddings.py` |
| Store | `faiss-cpu`; Postgres + pgvector (`psycopg`, `pgvector`) | `assistant/vectorstore.py` |
| Retrieve + format | both stores behind `VectorStore.search()` | `assistant/retrieval.py`, `tools/search_docs.py`, `tools/search_vendor_docs.py` |
| Cite + check | `chat_structured()` + `ApplyFixesArgs.citations` | `agent/state.py`, `agent/nodes/synthesizer.py`, `agent/nodes/reviewer.py` |
| Measure | the golden set + checks | `experiments/golden_retrieval.py` *(done)*, `experiments/retrieval_checks.py` |

## Setup (one-time)

```bash
.venv/bin/pip install -r requirements.txt      # already done on 2026-09-30
cd assistant && ../.venv/bin/python -m ingestion.fetch --phase A   # ~1 min; everything: ~3 min
docker compose up -d pgvector                  # from the repo root, when you reach exercise 3
```

Embeddings run on the same key as everything else (`OPENAI_API_KEY_LLM_PRJ`
via `llm_client.get_client()`). `text-embedding-3-small` was verified
working with it on 2026-09-30. Embedding the whole corpus costs a few
cents; each chunking variant in exercise 2 costs about a third of that.

## Order of operations (TODOs are yours, in this order)

**Phase A: get one slice working end to end**

1. `ingestion/loaders.py`: four formats, each with its own cruft (listed
   in the docstring).
2. `ingestion/chunkers.py`: fixed / recursive / markdown-header, all in
   `cl100k_base` tokens.
3. `embeddings.py`: token-based batching, normalized rows, a token counter.
4. `vectorstore.py`: `FaissStore` (exact search, metadata kept beside the
   vectors).
5. `ingestion/pipeline.py`: `build_index()`, printing chunk stats before
   embedding.
6. `retrieval.py`: `retrieve()` + `format_hits()` (the evidence format is
   a contract).
7. `experiments/retrieval_checks.py`, then experiments **01** and **02**.

**Phase B: the whole stack, and the graph**

8. `ingestion.fetch` for everything, `PgVectorStore`, experiment **03**.
9. Both tool handlers: `search_docs` and `search_vendor_docs`, each one
   line calling `retrieve()`.
10. Citations: `ApplyFixesArgs.citations` (state.py), the synthesizer
    prompt, and the reviewer's deterministic citation check. The
    synthesizer docstring also flags an existing bug in its `None`
    fallback.
11. End to end: `/research` with a golden question, then Week 4's
    experiments rerun against the real corpus. Their `eval_cases.py` was
    rewritten with the same positions and roles.

## The golden set

`experiments/golden_retrieval.py` has 37 questions (16 usable on the
Phase A index), **written after the corpus was fetched, by reading the real
pages**. Every marker was machine-checked against the fetched text.

- **Kinds**:
  - 15 *identifier*: names the exact alert or setting, where keyword search
    should do well.
  - 15 *symptom*: describes what you see, not the name. This is what dense
    retrieval is for.
  - 3 *cross_source*: needs two passages. xl-02 is a keep-alive default
    mismatch that neither doc states on its own.
  - 4 *not_in_corpus*: the right answer is "not covered". na-04 (Kong vs
    NGINX rate limiting) is the strongest distractor.
- **Scoring**: a retrieved chunk counts only if it's from the expected
  page **and** contains one of the answer's verbatim marker phrases. So
  hit@k measures "the answering passage was retrieved", not "some chunk
  from the right page". That's what makes it sensitive to chunking.

## Verified gotchas (each is in the relevant docstring, with how it was checked)

- langchain's token splitters default to the `gpt2` tokenizer, not the
  embedding model's `cl100k_base`.
- `MarkdownHeaderTextSplitter` doesn't understand YAML front matter, and
  has no size limit.
- markdownify's defaults write headings the header splitter can't see, and
  escape underscores (`max\_connections`).
- trafilatura drops code-block fences, which is fine for postmortems and
  wrong for vendor docs.
- Embeddings: `""` gives a 400, and more than 8,192 tokens also gives a
  400. Vectors come back with norm ≈ 0.9997, so normalize them yourself.
- FAISS takes float32 only. Asking for k larger than the index returns ids
  of `-1` with scores of `-inf`.
- pgvector: calling `register_vector()` before `CREATE EXTENSION` fails.
  Selected vectors come back as `pgvector.Vector` objects. With HNSW plus a
  selective filter, LIMIT 5 returned 1 row until `hnsw.iterative_scan` was
  turned on.

## Reading (~2h)

- **Must-read:**
  - LlamaIndex, [Introduction to RAG](https://developers.llamaindex.ai/python/framework/understanding/rag/)
  - The [OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings)
    (read the FAQ on distance functions)
  - The [pgvector README](https://github.com/pgvector/pgvector) (read
    "Iterative Index Scans")
  - [FAISS Getting started](https://github.com/facebookresearch/faiss/wiki/Getting-started)
    (the flat index only)
  - LangChain's text-splitter docs (recursive and markdown-header)
- **Optional:**
  - Barnett et al. 2024, *Seven Failure Points When Engineering a RAG
    System* (arXiv 2401.05856)
  - Liu et al. 2023, *Lost in the Middle*: the paper behind your Week 1
    exercise 5
  - Anthropic, [Introducing Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval),
    which leads into Week 6

## What "done" looks like for Week 5

- [ ] Explain every pipeline stage without notes, and justify the chunking
  strategy you picked using experiment 2's numbers.
- [ ] ≥ 80% top-3 hit rate on the golden set's answerable questions (the
  artifact's bar). Report it by kind and layer, and against the keyword
  baseline.
- [ ] FAISS (flat) and pgvector (no index) return the same top-k. Both are
  exact search, so any difference is a bug.
- [ ] Exercise 3 reproduces the "fewer than k" effect with a real filter,
  and explains it.
- [ ] `/research` answers with citations, and every cited chunk id appears
  in the evidence.
- [ ] Not-in-corpus questions get "not covered", not a confident
  citation. (No similarity threshold yet: seeing that fail is the lead-in
  to Week 6.)
