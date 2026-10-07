"""retrieval.py -- question text -> ranked chunks, shared by both search
tools so the embed + search + format logic exists once:

    search_docs         -> retrieve(q, k=5, doc_types=("runbook", "postmortem"))
    search_vendor_docs  -> retrieve(q, k=5, doc_types=("vendor_doc",))

TODO (yours):

1. get_embedder() / get_store() -- create each once per process, the
   same pattern as llm_client.get_client(). The store depends on the
   VECTOR_STORE env var:
     "faiss"    (default, Phase A)  FaissStore.load(INDEX_DIR / <name>)
     "pgvector" (exercise 3 on)     PgVectorStore(dim=embedder.dim)
   Queries must be embedded by the SAME model that built the index.

2. retrieve(query, *, k, doc_types, layer=None) -> list[Hit]:
   embed the query, then store.search(query_vec, k, filters={...}).

3. format_hits(hits) -> str -- the evidence text the graph passes
   around. THE FORMAT IS A CONTRACT: synthesizer_node cites chunk ids,
   and reviewer_node + retrieval_checks.check_citations() verify that
   every cited id appears in the evidence as "[<chunk_id>]". One block
   per hit, with a blank line between blocks:

       [postgres:runtime-config-client#12] PostgreSQL 18 › 19.11.1. Statement Behavior (https://www.postgresql.org/docs/18/runtime-config-client.html)
       <chunk text>

   For an empty list, return "(no relevant results)". An empty string
   makes the synthesizer guess.

Deliberately NOT here yet: a minimum-similarity cutoff. The artifact's
Week 6 point is that top-k with no threshold always returns k chunks,
even when none of them are relevant. The golden set's "not in the
corpus" questions will show you that happening; fix it in Week 6, after
you've seen it.
"""
from __future__ import annotations

import vectorstore, embeddings
from vectorstore import Hit
import os
import functools
DEFAULT_K = 5

@functools.lru_cache(maxsize=1)
def get_store():
     kind = os.environ.get("VECTOR_STORE", "faiss")
     folder = os.environ.get(
          "FAISS_INDEX_DIR", "faiss-recursive-500-A")#on changing FAISS_INDEX_DIR 
                                                    #call get_store.cache_clear() or new process
     return vectorstore.open_store(kind, vectorstore.INDEX_DIR / folder)

@functools.lru_cache(maxsize=1)
def get_embedder():
     return embeddings.get_embedder("openai-embedder")



def retrieve(query: str, *, k: int = DEFAULT_K, doc_types: tuple[str, ...],
             layer: str | None = None) -> list[Hit]:

     vector_store = get_store()
     embedder = get_embedder()
     query_vector = embedder.embed_query(query)
     filters = {"doc_type": doc_types}
     if layer is not None:
          filters["layer"] = (layer,)

     hits = vector_store.search(query_vector, k, filters)
     return hits



def format_hits(hits: list[Hit]) -> str:
     
     if not hits:
         return "(no relevant results)"
     blocks = []
     for hit in hits:
        chk = hit.chunk
        heading = f"{chk.title} › {chk.section}" if chk.section else chk.title
        blocks.append(f"[{chk.chunk_id}] {heading} ({chk.url})\n{chk.text}")
     return "\n\n".join(blocks)