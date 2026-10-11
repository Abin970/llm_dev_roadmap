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
from vectorstore import FaissStore, INDEX_DIR
from retrieval import get_embedder

STRATEGIES = ("fixed", "recursive", "markdown_header")
SIZE, OVERLAP = 500, 50
K_VALUES = (1, 3, 5)


def main() -> None:
    stores = {}
    for strategy in STRATEGIES:
        stores[strategy] = FaissStore.load(INDEX_DIR / f"faiss-{strategy}-{SIZE}-A")

    questions = for_phase("A")
    query_vectors = get_embedder().embed([q.question for q in questions])

    results = {}
    for strategy, store in stores.items():
        results[strategy] = {q.qid: store.search(vec, k=5) for q,vec in zip(questions, query_vectors)}

    # one report per (strategy, k), kept in ONE dictionary so it can be looked up by its key
    strategy_report_over_k = {
            f"{strategy}_k:{k}": rc.evaluate(results[strategy], k)
            for k in K_VALUES for strategy in STRATEGIES
            }


    # ---- hit rate for every strategy at every k (all 9 combinations)
    answerable = 0
    for q in questions:
        if q.kind != "not_in_corpus":
            answerable += 1

    print(f"\n== hit rate, {answerable} answerable questions ==")
    for k in K_VALUES:
        for strg in STRATEGIES:
            report = strategy_report_over_k[f"{strg}_k:{k}"]
            hits_total = round(report.hit_rate * answerable)
            print(f"k={k}  {strg:16s} {hits_total:2d}/{answerable} = {report.hit_rate:4.0%}")

            for kind in report.by_kind:
                # the groups are small, so show how many questions of this kind there are
                # (one question can move a percentage by 10 points or more)
                kind_total = 0
                for q in questions:
                    if q.kind == kind:
                        kind_total += 1
                hits_by_kind = round(report.by_kind[kind] * kind_total)
                print(f"        {kind:11s} {hits_by_kind}/{kind_total} = {report.by_kind[kind]:4.0%}")
        print()



    print("== per question at k=3 ==")
    print(f"{'question':9s} {'kind':11s}" + "".join(f"{s:>17s}" for s in STRATEGIES))
    
    for q in questions:
        if q.kind == "not_in_corpus":
            continue                                   # nothing to find, so no hit/miss
        row = f"{q.qid:9s} {q.kind:11s}"
        marks = []
        for strategy in STRATEGIES:
            got = rc.hit_at_k(q, results[strategy][q.qid], 3)     # strategy first, then qid
            marks.append(got)
            row += f"{'hit' if got else 'MISS':>17s}"
        if len(set(marks)) > 1:                        # the strategies disagree on this question
            row += "   <-- differs"
        print(row)

    # ---- top-1 chunk under each strategy, for a few questions
    # db-04 and orch-02 were "right page, wrong chunk" misses in experiment 1, so they are the
    # ones chunking should be able to change. db-01 and orch-05 were hits, as a comparison.
    # hit_at_k(..., 1) is True only when the TOP result holds the answering passage.
    print("\n== top-1 chunk under each strategy ==")
    by_id = {q.qid: q for q in questions}
    for qid in ("db-04", "orch-02", "db-01", "orch-05"):
        q = by_id[qid]
        print(f"\n===== {qid} ({q.kind}): {q.question}")
        for strategy in STRATEGIES:
            hits = results[strategy][qid]
            top = hits[0]
            top_is_answer = rc.hit_at_k(q, hits, 1)
            print(f"--- {strategy}: score {top.score:.3f}, top-1 {'HIT' if top_is_answer else 'miss'}, {top.chunk.chunk_id}")
            if top.chunk.section:
                print(f"    section: {top.chunk.section}")
            print("    " + top.chunk.text[:250].replace("\n", " "))
    
            
    
if __name__ == "__main__":
    main()
