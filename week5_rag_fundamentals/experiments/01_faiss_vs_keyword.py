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
import retrieval_checks as rc

K_VALUES = (1, 3, 5)


def main() -> None:
    questions = for_phase("A")
    raise NotImplementedError(f"TODO: see the module docstring ({len(questions)} Phase A questions ready)")


if __name__ == "__main__":
    main()
