"""
Experiment 1 -- FAISS vs the Week 3 keyword scorer, on a real corpus
=====================================================================
Objective  : does dense retrieval actually beat keyword matching, and
             on WHICH questions? The artifact's exercise 1 ("FAISS over
             a real corpus you understand"), measured against a baseline
             instead of eyeballed.
Setup      : Phase A index: postgres + kubernetes + runbooks.
                 python -m ingestion.fetch --phase A          (from assistant/)
                 python -m ingestion.pipeline --phase A --strategy recursive --store faiss
             Questions: golden_retrieval.for_phase("A"), 12 answerable
             + 4 not in the corpus.

TODO:
  1. Load the Phase A FaissStore (vectorstore.FaissStore.load) and an
     OpenAIEmbedder. The same model must embed the questions.
  2. Dense: for each golden question, embed it and search top-5 with NO
     doc_type filter. This experiment asks "can it find the passage at
     all"; the per-branch filters come with the graph.
  3. Keyword baseline: tools.search_docs.keyword_rank(question, texts,
     k=5) over the SAME chunk texts (the store's chunks), mapped back to
     Hit objects. Put its raw score in Hit.score, since it isn't a cosine.
  4. retrieval_checks.evaluate() on both, at k = 1, 3 and 5. Print hit@k
     overall and split by kind (identifier vs symptom).
  5. For the not_in_corpus questions, print what dense retrieval returned
     anyway: doc_ids and scores next to the scores of real hits.
  6. Save the printed report under experiment_results/.

Observe    : where keyword WINS (questions that name an exact alert or
             setting, e.g. orch-01, db-01) and where it collapses
             (symptom questions that share no words with the answer).
             What similarity do "not in corpus" questions still get?
             Could any cutoff separate them from the real hits?
Teaches    : what "good enough" retrieval looks like, as a number. It
             also shows both failures Week 6 exists for: exact
             identifiers (hybrid search) and the lack of a threshold
             (top-k always returns k chunks, even irrelevant ones).

Run: python experiments/01_faiss_vs_keyword.py      (from week5_rag_fundamentals/)
"""
import _bootstrap  # noqa: F401

from golden_retrieval import for_phase
from retrieval import get_store, get_embedder
import retrieval_checks as rc
from tools.search_docs import keyword_rank
from vectorstore import Chunk, Hit



K_VALUES = (1, 3, 5)

# keyword_rank returns (position, score) pairs, where position indexes into the texts list.
# Because texts is built from chunks in the same order, chunks[position] is the matching chunk.
# The score is a word-weight COUNT (an int), not a cosine, so it is never compared with dense scores.
def keyword_hits(question: str, chunks: list[Chunk], k: int)->list[Hit]:
    ranked = keyword_rank(question, [c.text for c in chunks], k)
    return [Hit(chunk=chunks[i], score=float(score)) for i,score in ranked]

def main() -> None:
    questions = for_phase("A")
    faiss_store = get_store()
    embedder = get_embedder()

    # the SAME chunks the vectors were built from, so both searchers search identical text
    chunks = faiss_store.chunks

    # one API call for all the questions (about 500 tokens in total)
    query_vectors = embedder.embed([q.question for q in questions])
    dense_search: dict[str,list[Hit]]= {q.qid: faiss_store.search(vec, k=5) 
                    for q,vec in zip(questions, query_vectors)}
    # both searchers now give {qid: [Hit, ...]} ranked best-first, so one evaluate() scores both
    keyword_search: dict[str,list[Hit]] = {q.qid: keyword_hits(q.question, chunks, 5) for q in questions}

   
    # one entry per k: evaluate() scores each searcher by whether the answering passage is in its top k
    report_comparison = [
          {f"dense_{k}":rc.evaluate(dense_search, k),
            f"keyword_{k}":rc.evaluate(keyword_search, k)} 
            for k in K_VALUES]

    # ---- 1. hit rate at each k, overall and by question kind
    # Only the RANK is compared (is the answer inside the top k?), never the raw scores.
    for k, row in zip(K_VALUES, report_comparison):
        dense_report = row[f"dense_{k}"]
        keyword_report = row[f"keyword_{k}"]
        
        print(f"k={k}  overall: dense {dense_report.hit_rate:.0%}   keyword {keyword_report.hit_rate:.0%}")
        for kind in dense_report.by_kind:
            # the groups are small, so show how many questions of this kind there are
            # (one question can move a percentage by 10 points or more)
            kind_total = 0
            for q in questions:
                if q.kind == kind:
                    kind_total += 1
            dense_found = round(dense_report.by_kind[kind] * kind_total)
            keyword_found = round(keyword_report.by_kind[kind] * kind_total)
            print(f"      {kind} ({kind_total} questions): "
                  f"dense {dense_found}/{kind_total} = {dense_report.by_kind[kind]:.0%}   "
                  f"keyword {keyword_found}/{kind_total} = {keyword_report.by_kind[kind]:.0%}")

    # ---- 2. question by question at k=3: did each searcher find the answering passage?
    # The rows where dense and keyword differ are the interesting ones.
    print("\nper question at k=3:")
    for q in questions:
        if q.kind == "not_in_corpus":
            continue   # nothing to find, these are covered in section 3
        dense_hit = rc.hit_at_k(q, dense_search[q.qid], 3)
        keyword_hit = rc.hit_at_k(q, keyword_search[q.qid], 3)
        print(f"  {q.qid:8s} {q.kind:10s} dense={dense_hit}   keyword={keyword_hit}")

    # ---- 3. questions the corpus cannot answer: top-k still returns chunks
    print("\nnot in corpus (best dense result anyway):")
    for q in questions:
        if q.kind != "not_in_corpus":
            continue
        best = dense_search[q.qid][0]
        print(f"  {q.qid}: score {best.score:.3f}  ->  {best.chunk.doc_id}")

    # for comparison: how high do the best results score on questions the corpus CAN answer?
    answerable_scores = []
    for q in questions:
        if q.kind != "not_in_corpus":
            answerable_scores.append(dense_search[q.qid][0].score)
    print(f"  answerable questions' best dense score: lowest {min(answerable_scores):.3f}, highest {max(answerable_scores):.3f}")

    # ---- 4. the misses at k=3: what each searcher returned INSTEAD of the answering passage
    # (evaluate() keeps the top 3 results of every question it missed)
    for k, row in zip(K_VALUES, report_comparison):
        if k != 3:
            continue
        for name in ("dense", "keyword"):
            report = row[f"{name}_{k}"]
            print(f"\n{name} misses at k=3:")
            for qid in report.misses:
                print(f"  {qid}:")
                if not report.misses[qid]:
                    print("      (nothing returned)")
                for doc_id, score in report.misses[qid]:
                    print(f"      {score:7.3f}  {doc_id}")

if __name__ == "__main__":
    main()
