"""
Experiment 2 -- Chunking strategy comparison
=============================================
Objective  : show that chunking is a precision lever, not a formatting
             detail (the artifact's exercise 2): same documents, same
             questions, same embedding model, and only the chunker
             changes.
Setup      : the Phase A documents, chunked three ways at the same target
             size (500 tokens, 50 overlap), giving three FAISS indexes:
                 python -m ingestion.pipeline --phase A --strategy fixed --store faiss
                 python -m ingestion.pipeline --phase A --strategy recursive --store faiss
                 python -m ingestion.pipeline --phase A --strategy markdown_header --store faiss
             Each one embeds the ~330k tokens of Phase A text, plus the
             overlap. That costs cents, but it isn't free. Check chunk
             statistics (the pipeline's --dry-run idea) BEFORE embedding.

TODO:
  1. Chunk statistics per strategy, WITHOUT embedding: chunk count,
     min/median/max tokens, and how many chunks cut a code block in half
     (an odd number of ``` fences in one chunk means a fence opened or
     closed in a different chunk).
  2. hit@3 per strategy on golden_retrieval.for_phase("A"), using
     retrieval_checks.evaluate().
  3. Side by side, for 2-3 questions (db-01, orch-05 and a symptom
     question are good picks): the top-1 chunk under each strategy. Is
     the answering passage whole, cut in half, or buried in noise?
  4. Optional: rerun one strategy at 250 and 1000 tokens. The runbooks
     are ~50-600 tokens each, while many Postgres and Kubernetes pages
     run to thousands. That's the artifact's "one global chunk size for a
     corpus mixing short entries and long reference pages" mistake,
     happening in your own corpus.
  5. Save the report under experiment_results/.

Observe    : where fixed-size splits a kubectl snippet or a config table
             in half; where the markdown-header chunker keeps a section
             whole but produces a chunk too big to be precise; whether
             hit@3 moves in the direction you predicted before running it.
Teaches    : chunk boundaries decide what CAN be retrieved. A passage cut
             in two can lose its marker, and a chunk mixing three topics
             embeds as the average of all three.

Run: python experiments/02_chunking_comparison.py      (from week5_rag_fundamentals/)
"""
import _bootstrap  # noqa: F401

from golden_retrieval import for_phase
import retrieval_checks as rc

STRATEGIES = ("fixed", "recursive", "markdown_header")
SIZE, OVERLAP = 500, 50


def main() -> None:
    raise NotImplementedError("TODO: see the module docstring")


if __name__ == "__main__":
    main()
