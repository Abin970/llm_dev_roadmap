"""vectorstore.py -- the "store" and "search" steps: one interface, two
backends (the artifact's Project V3 module).

    FaissStore     exercises 1-2   in-process, exact search, vectors only
    PgVectorStore  exercise 3 on   a Postgres table: vectors + metadata columns

Both return the same Hit objects, so retrieval.py and the experiments
don't care which one is live.

`Chunk` and `Hit` (below) are GIVEN, not TODO: they're the record shapes
every module shares. chunkers.py produces Chunks, stores keep them, and
retrieval.format_hits() renders Hits into evidence text. Pinning the
field names once keeps loaders, chunkers, stores, tools and the
experiments agreeing with each other.

Everything below marked "verified" was checked against the installed
libraries and the running docker-compose container on 2026-09-30:
faiss-cpu 1.15.1, pgvector 0.8.6 (image pgvector/pgvector:0.8.6-pg18),
pgvector-python 0.5.0, psycopg 3.3.6.

---------------------------------------------------------------------
TODO (yours) -- FaissStore
---------------------------------------------------------------------
    index = faiss.IndexFlatIP(dim)   # "Flat" = exact, brute-force search;
                                     # IP = inner product, which IS cosine
                                     # similarity when rows are L2-normalized
  - index.add(x) / index.search(q, k) need float32, C-contiguous arrays.
    faiss.normalize_L2(x) normalizes IN PLACE and raises TypeError on
    float64 (verified).
  - index.search(q.reshape(1, -1), k) -> (scores, ids), each shaped
    (1, k). If k > index.ntotal, the extra slots come back as id -1 with
    score -inf (verified), so drop those.
  - FAISS stores vectors only, with no metadata at all. Keep
    `self.chunks: list[Chunk]` where position i <-> vector i.
  - filters: FAISS can't filter. Over-fetch (say k * 10, or everything
    at this corpus size), then filter in Python, and notice when fewer
    than k survive. That's the same trade-off pgvector's HNSW index hits
    with a WHERE clause (see below and exercise 3).
  - save(dir) / load(dir): faiss.write_index(index, str(path)) +
    faiss.read_index(...) (verified round-trip), plus the chunks as JSONL
    next to it, so the positions line up again after loading.

---------------------------------------------------------------------
TODO (yours) -- PgVectorStore
---------------------------------------------------------------------
  - DSN: os.environ.get("PGVECTOR_DSN", DEFAULT_DSN) -- DEFAULT_DSN
    matches docker-compose.yml (`docker compose up -d pgvector` first).
  - conn = psycopg.connect(dsn, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)            # from pgvector.psycopg
    ORDER MATTERS: register_vector() before the extension exists raises
    ProgrammingError "vector type not found in the database" (verified).
  - one table, metadata as real columns so filters are plain SQL:
      chunk_id text PRIMARY KEY, doc_id, source, doc_type, layer, url,
      title, section, text  (all text), embedding vector(<dim>)
    Inserting a vector of the wrong length raises DataException
    "expected 1536 dimensions, not N" (verified).
  - bulk insert: COPY is much faster than executemany for thousands of
    rows (both verified):
      with cur.copy("COPY chunks (...) FROM STDIN WITH (FORMAT BINARY)") as copy:
          copy.set_types(["text", ..., "vector"])
          copy.write_row([...])            # numpy arrays accepted as-is
  - search -- named parameters, so the query vector is passed once:
      SELECT chunk_id, ..., 1 - (embedding <=> %(q)s) AS score
      FROM chunks WHERE doc_type = ANY(%(doc_types)s)
      ORDER BY embedding <=> %(q)s LIMIT %(k)s
    `<=>` is cosine DISTANCE (0 = identical), hence score = 1 - distance.
    Selected embeddings come back as pgvector.Vector objects;
    .to_numpy() converts them (verified).
  - No index = an exact sequential scan: fine at this corpus size (a few
    thousand rows), and exact means it must return the SAME top-k as
    FaissStore (this week's consistency check). Exercise 3 then adds
      CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
    and observes the filter problem: HNSW collects hnsw.ef_search
    candidates (default 40) FIRST and filters AFTER, so a selective
    WHERE can return fewer than k rows. Verified with 5% matching rows
    and ef_search=10: LIMIT 5 returned 1 row. After
    `SET hnsw.iterative_scan = relaxed_order` it returned 5 rows, the
    same ids as exact search. On a small table the planner may skip the
    index entirely; `SET enable_seqscan = off` forces it for the
    experiment, and EXPLAIN shows which plan actually ran.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = REPO_ROOT / "data" / "index"     # gitignored, like data/corpus
DEFAULT_DSN = "postgresql://copilot:copilot@127.0.0.1:5433/copilot"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str      # f"{doc_id}#{position}" -- what citations point at
    doc_id: str        # manifest doc_id, e.g. "postgres:runtime-config-connection"
    text: str          # what gets embedded AND what the LLM reads
    source: str        # "postgres", "kubernetes", "runbooks", ...
    doc_type: str      # "vendor_doc" | "runbook" | "postmortem"
    layer: str         # one of ingestion.sources.LAYERS
    url: str           # the manifest's citation URL
    title: str         # document title
    section: str       # "H1 › H2 › H3" for header-aware chunks, else ""


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float       # cosine similarity, higher = closer


class VectorStore(Protocol):
    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        """vectors: (len(chunks), dim) float32, L2-normalized rows."""
        ...

    def search(self, query_vec: np.ndarray, k: int, filters: dict | None = None) -> list[Hit]:
        """query_vec: (dim,) float32, normalized. filters maps a Chunk
        field name to the allowed values, e.g.
        {"doc_type": ("runbook", "postmortem"), "layer": ("database",)}.
        Returns at most k hits, best first."""
        ...

    def count(self) -> int:
        ...


class FaissStore:
    """TODO (yours): see "FaissStore" in the module docstring."""

    def __init__(self, dim: int) -> None:
        raise NotImplementedError

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        raise NotImplementedError

    def search(self, query_vec: np.ndarray, k: int, filters: dict | None = None) -> list[Hit]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError

    def save(self, directory: Path) -> None:
        raise NotImplementedError

    @classmethod
    def load(cls, directory: Path) -> "FaissStore":
        raise NotImplementedError


class PgVectorStore:
    """TODO (yours): see "PgVectorStore" in the module docstring."""

    def __init__(self, dim: int, dsn: str | None = None, table: str = "chunks") -> None:
        self.dsn = dsn or os.environ.get("PGVECTOR_DSN", DEFAULT_DSN)
        raise NotImplementedError

    def add(self, chunks: list[Chunk], vectors: np.ndarray) -> None:
        raise NotImplementedError

    def search(self, query_vec: np.ndarray, k: int, filters: dict | None = None) -> list[Hit]:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError
