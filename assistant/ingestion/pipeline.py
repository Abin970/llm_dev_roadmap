"""pipeline.py -- load -> chunk -> embed -> store, as one command.

    python -m ingestion.pipeline --phase A --strategy recursive --store faiss
    python -m ingestion.pipeline --strategy markdown_header --store pgvector

(run from assistant/, after `python -m ingestion.fetch`)

The argument parsing below is given; build_index() is yours.

---------------------------------------------------------------------
TODO (yours) -- build_index(phase, strategy, size, overlap, store_kind)
---------------------------------------------------------------------
  1. loaders.iter_manifest(phase) -> loaders.load(entry) for each; skip
     None, and count loaded vs skipped per source.
  2. chunkers.STRATEGIES[strategy](doc, size, overlap) for each doc.
  3. OpenAIEmbedder().embed([c.text for c in chunks]). It handles the
     token-based batching, so hand it everything at once.
  4. Store:
       faiss     FaissStore(dim).add(chunks, vectors), then .save() to
                 INDEX_DIR / f"faiss-{strategy}-{size}" -- one directory
                 per variant, so exercise 2 can keep all three side by side
       pgvector  PgVectorStore(dim).add(...). Decide what a re-run does
                 (drop + recreate the table, or upsert on chunk_id) and
                 write down why.
  5. Print a summary: docs loaded/skipped, chunk count by doc_type and
     layer, min/median/max chunk tokens, tokens embedded (the embedder's
     counter), and wall time.

Chunking and embedding are separate on purpose. Chunks are cheap to
re-make and embedding is the only step that costs money, so print chunk
statistics BEFORE embedding (a --dry-run flag that stops after step 2
is worth adding). A chunking bug caught there costs nothing.
"""
from __future__ import annotations

import argparse

from .chunkers import DEFAULT_OVERLAP, DEFAULT_SIZE, STRATEGIES


def build_index(phase: str | None, strategy: str, size: int, overlap: int, store_kind: str) -> None:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build a vector index from data/corpus/manifest.jsonl.")
    ap.add_argument("--phase", choices=["A", "B"], help="only this phase's documents (default: all)")
    ap.add_argument("--strategy", choices=sorted(STRATEGIES), default="recursive")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="target chunk size in tokens")
    ap.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="overlap in tokens")
    ap.add_argument("--store", choices=["faiss", "pgvector"], default="faiss")
    args = ap.parse_args(argv)
    build_index(args.phase, args.strategy, args.size, args.overlap, args.store)


if __name__ == "__main__":
    main()
