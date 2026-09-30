"""Week 5 ingestion: turns the fetched corpus into chunks the retriever
can search.

    sources.py   WHAT is in the corpus                         (plumbing, done)
    fetch.py     downloads it + writes data/corpus/manifest.jsonl (plumbing, done)
    loaders.py   manifest line -> clean markdown + metadata     (TODO: yours)
    chunkers.py  document -> chunks, three strategies           (TODO: yours)
    pipeline.py  load -> chunk -> embed -> store, as a CLI       (TODO: yours)

Run everything from assistant/ (`python -m ingestion.fetch`, then
`python -m ingestion.pipeline ...`), the same way main.py is run.
"""
