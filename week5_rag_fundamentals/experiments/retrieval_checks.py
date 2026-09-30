"""retrieval_checks -- score retrieval against golden_retrieval.GOLDEN, so
"is retrieval good enough?" is a number you run, not an impression.

Same idea as week4's eval_checks.py, for the retrieval half of the
pipeline. It's used by all three experiments, and Week 6 reruns it
unchanged to measure MMR, hybrid search and reranking against today's
baseline.

---------------------------------------------------------------------
TODO (yours)
---------------------------------------------------------------------
is_hit(chunk, expected) -> bool
    chunk.doc_id == expected.doc_id AND at least one marker appears in
    chunk.text. Compare case-insensitively with whitespace collapsed on
    both sides (" ".join(s.lower().split())), since loaders and chunkers
    re-flow whitespace.

hit_at_k(question, hits, k) -> bool
    - normal questions: some chunk in hits[:k] hits SOME Expected
    - needs_all questions (cross_source): EVERY Expected is hit by some
      chunk in hits[:k]
    - not_in_corpus: not scored here, since there's nothing to hit.
      Report their top scores instead (see evaluate).

evaluate(results, k) -> RetrievalReport
    results: {qid: list[Hit]} for one retrieval setup
    - hit@k over the answerable questions, overall AND per kind and per
      layer. The per-kind split is the interesting one: identifier vs
      symptom is where dense and keyword retrieval differ.
    - misses: for each missed qid, what came back instead (doc_id +
      score of the top 3). The misses are the part to actually read.
    - not_in_corpus: the top-1 score for each. Compare those numbers with
      the top-1 scores of real hits: is there a similarity cutoff that
      would separate them? (That's Week 6's threshold question, answered
      with your own data.)

check_citations(citations, evidence) -> CheckResult
    Every cited chunk id appears in the evidence as "[<chunk_id>]": the
    same rule reviewer_node applies inside the graph, checked here from
    outside it (Week 4's check_grounding pattern). Fail on an empty list,
    unless the answer says the evidence doesn't cover the question.

Acceptance (the artifact's bar): >= 80% top-3 hit rate on the
answerable questions, for the setup you'd ship.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import _bootstrap  # noqa: F401
from golden_retrieval import Expected, GoldenQuestion
from vectorstore import Chunk, Hit


@dataclass
class CheckResult:
    ok: bool
    reason: str


@dataclass
class RetrievalReport:
    k: int
    hit_rate: float                                         # answerable questions only
    by_kind: dict[str, float] = field(default_factory=dict)
    by_layer: dict[str, float] = field(default_factory=dict)
    misses: dict[str, list[tuple[str, float]]] = field(default_factory=dict)   # qid -> [(doc_id, score)]
    not_in_corpus_top_scores: dict[str, float] = field(default_factory=dict)   # qid -> top-1 score


def is_hit(chunk: Chunk, expected: Expected) -> bool:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def hit_at_k(question: GoldenQuestion, hits: list[Hit], k: int) -> bool:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def evaluate(results: dict[str, list[Hit]], k: int) -> RetrievalReport:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def check_citations(citations: list[str], evidence: list[str]) -> CheckResult:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")
