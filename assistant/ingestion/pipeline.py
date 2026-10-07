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
import statistics
import time
from collections import Counter

from llm_client import count_tokens

# from .chunkers import DEFAULT_OVERLAP, DEFAULT_SIZE, STRATEGIES
from . import chunkers, loaders
import embeddings
import vectorstore

DEFAULT_OVERLAP = chunkers.DEFAULT_OVERLAP
DEFAULT_SIZE  = chunkers.DEFAULT_SIZE
STRATEGIES = chunkers.STRATEGIES



def _print_chunk_stats(chunks) -> int:
    """Chunk report printed BEFORE any money is spent. Returns total tokens."""
    sizes = [count_tokens(c.text, model=embeddings.EMBED_MODEL) for c in chunks]
    print(f"chunks: {len(chunks)}")
    print("  by doc_type:", dict(sorted(Counter(c.doc_type for c in chunks).items())))
    print("  by layer:   ", dict(sorted(Counter(c.layer for c in chunks).items())))
    print(f"  tokens per chunk: min/median/max = {min(sizes)}/{int(statistics.median(sizes))}/{max(sizes)}")
    print(f"  total tokens to embed: {sum(sizes):,}")
    return sum(sizes)


def build_index(phase: str | None, strategy: str, size: int, overlap: int,
                store_kind: str, dry_run: bool = False) -> None:
    started = time.time()

    # 1) load
    docs, skipped = [], 0
    for entry in loaders.iter_manifest(phase):
        doc = loaders.load(entry)
        if doc is None:
            skipped += 1
            continue
        docs.append(doc)
    print(f"loaded {len(docs)} docs, skipped {skipped}")

    # 2) chunk (all documents first, so embedding can batch across them)
    all_chunks = []
    for doc in docs:
        all_chunks.extend(STRATEGIES[strategy](doc, size, overlap))
    
    if not all_chunks:
        print("no chunks produced -- nothing to do")
        return
    
    print(f"\nstrategy={strategy} size={size} overlap={overlap}")
    _print_chunk_stats(all_chunks)

    if dry_run:
        return

    # 3) embed -- the only step that costs money
    embedder = embeddings.get_embedder("openai-embedder")
    vector_store = vectorstore.new_store(store_kind, embedder.dim)
    vectors = embedder.embed([chunk.text for chunk in all_chunks])

    # 4) store
    vector_store.add(all_chunks, vectors)
    if store_kind == "faiss":
        # phase in the name, so a Phase A index never overwrites (or is mistaken for) a full one
        name = f"faiss-{strategy}-{size}" + (f"-{phase}" if phase else "")
        target = vectorstore.INDEX_DIR / name
        vector_store.save(target)
        print(f"\nsaved index -> {target}")

    print(f"embedded {getattr(embedder, 'tokens_used', '?')} tokens, "
          f"{vector_store.count()} vectors stored, {time.time() - started:.1f}s total")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Build a vector index from data/corpus/manifest.jsonl.")
    ap.add_argument("--phase", choices=["A", "B"], help="only this phase's documents (default: all)")
    ap.add_argument("--strategy", choices=sorted(STRATEGIES), default="recursive")
    ap.add_argument("--size", type=int, default=DEFAULT_SIZE, help="target chunk size in tokens")
    ap.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help="overlap in tokens")
    ap.add_argument("--store", choices=["faiss", "pgvector"], default="faiss")
    ap.add_argument("--dry-run", action="store_true", help="load + chunk + print stats, then stop BEFORE embedding")
    args = ap.parse_args(argv)
    build_index(args.phase, args.strategy, args.size, args.overlap, args.store, args.dry_run)


if __name__ == "__main__":
    main()
