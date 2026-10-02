What I built
- Corpus: 308 official documents, about 898k tokens, covering all nine layers you listed. It's PostgreSQL, Kubernetes, NGINX, Gunicorn/Uvicorn, Redis, Kafka, Docker, Fluent Bit, Prometheus and OpenTelemetry, plus 108 alert runbooks and 40 real postmortems. Pages are only on-call-relevant ones. Five dead or empty postmortem pages were dropped and four moved links replaced; sources.py notes why.
  - python -m ingestion.fetch recreates everything under data/, which git ignores, so no third-party text gets committed.
  - Phase A (PostgreSQL + Kubernetes + runbooks, 164 documents) is a smaller first slice so you get results quickly.
- Golden set: 37 questions written by reading the real pages, 16 of them usable on Phase A. Each one records short verbatim phrases from the answering passage. A script confirmed every phrase is really in the fetched text (0 missing).
- Rename: search_web → search_vendor_docs. The made-up notes and fake web pages are gone. The graph shape and node code are unchanged.
- Stubs: loaders, chunkers, embeddings, the FAISS/pgvector stores, retrieval, the scoring checks, three experiment scripts, and citation TODOs in state.py, synthesizer.py and reviewer.py.
- Also: docker-compose.yml for pgvector, the new libraries installed and pinned in requirements.txt, and Week 4's eval_cases.py rewritten against the real corpus with the same case positions.

I checked every library detail against the installed packages and the running database before writing the TODOs. Three findings you'd otherwise hit at runtime:
- LangChain's token splitters count tokens with the gpt2 tokenizer by default, not the embedding model's cl100k_base.
- trafilatura drops the fences around code blocks. That's why vendor HTML goes through BeautifulSoup + markdownify instead.
- With an HNSW index plus a filter in pgvector, LIMIT 5 returned only 1 row until hnsw.iterative_scan was turned on. Exercise 3 reproduces this on purpose.

Things to know
- Search is off until you build retrieval. Both search tools return a "TODO" error for now. The graph still runs, but with no evidence, so Week 4's experiments will fail their keyword checks until then.
- Existing synthesizer bug, not fixed. The fallback in synthesizer.py assigns to a misspelled respone and builds ApplyFixesArgs positionally, which raises TypeError. It's noted in that file's TODO.
- Git changes are staged but not committed. The rename and the deleted fixture notes are staged because I used git mv / git rm.
- pgvector is stopped. Its data volume is kept; start it with docker compose up -d pgvector when you reach exercise 3.
- One made-up data source remains. The Week 2 sqlite_query tool still serves ma_db.py. It isn't part of the graph, so I left it. Say if you want it retiredtoo.