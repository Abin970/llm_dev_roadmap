import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "week5_rag_fundamentals" / "experiments"))

from golden_retrieval import GOLDEN
from retrieval_checks import is_hit, hit_at_k, evaluate
from vectorstore import Chunk, Hit

# Everything here is hand-built: fake chunks and hits where the right answer is known in advance.
# No API calls, no index loaded, no cost.
by_id = {q.qid: q for q in GOLDEN}


def hit(doc_id: str, text: str, score: float = 0.5) -> Hit:
    return Hit(chunk=Chunk(chunk_id=f"{doc_id}#0", doc_id=doc_id, text=text, source="test",
                           doc_type="vendor_doc", layer="database", url="https://example.com",
                           title="t", section=""), score=score)


def good(qid: str, i: int = 0, score: float = 0.9) -> Hit:
    """A hit that IS the answering passage for question `qid` (expected entry i): right doc + a marker."""
    e = by_id[qid].expected[i]
    return hit(e.doc_id, f"...context before... {e.markers[0]} ...context after...", score)


def wrong_doc(qid: str, score: float = 0.8) -> Hit:
    """Contains the marker text, but from the WRONG document -- must not count."""
    e = by_id[qid].expected[0]
    return hit("some:other-doc", e.markers[0], score)


def right_doc_no_marker(qid: str, score: float = 0.7) -> Hit:
    """Right document, but a chunk that doesn't hold the answer -- must not count."""
    return hit(by_id[qid].expected[0].doc_id, "an unrelated part of the same page", score)


# ---- is_hit: document AND marker, ignoring case/whitespace ---------------------
e = by_id["db-01"].expected[0]
assert is_hit(good("db-01").chunk, e)
assert not is_hit(wrong_doc("db-01").chunk, e), "marker from the wrong doc counted as a hit"
assert not is_hit(right_doc_no_marker("db-01").chunk, e), "right doc without a marker counted as a hit"
messy = hit(e.doc_id, e.markers[0].upper().replace(" ", "  \n"))
assert is_hit(messy.chunk, e), "case / whitespace differences should not matter"
print("ok: is_hit needs the right document AND a marker, ignoring case and whitespace")

# ---- hit_at_k: the k cutoff, any-vs-all, empty input -----------------------------
q = by_id["orch-01"]
ranked = [wrong_doc("orch-01", 0.9), right_doc_no_marker("orch-01", 0.8), good("orch-01", score=0.7)]
assert not hit_at_k(q, ranked, 1) and not hit_at_k(q, ranked, 2) and hit_at_k(q, ranked, 3)
assert hit_at_k(q, ranked, 10), "k larger than the hit list must not crash"
assert not hit_at_k(q, [], 3), "no hits -> miss"
print("ok: hit_at_k respects the cutoff (answer at rank 3: miss at k=1,2, hit at k=3), and handles k>len and empty")

x = by_id["xl-01"]                                    # cross_source, needs BOTH passages
assert x.needs_all and len(x.expected) == 2
assert not hit_at_k(x, [good("xl-01", 0)], 3), "needs_all with only one of two passages must be a miss"
assert hit_at_k(x, [good("xl-01", 0), good("xl-01", 1)], 3)
assert not hit_at_k(x, [good("xl-01", 0), good("xl-01", 1)], 1), "the second passage is beyond k=1"
print("ok: needs_all questions need every passage inside the top k")

# ---- evaluate: grouping, rates, misses, not-in-corpus ----------------------------
results = {
    "db-01":   [good("db-01")],                                                   # identifier, database      -> HIT
    "db-02":   [wrong_doc("db-02"), right_doc_no_marker("db-02")],                # symptom,    database      -> MISS
    "orch-01": [wrong_doc("orch-01", 0.9), right_doc_no_marker("orch-01", 0.8), good("orch-01", score=0.7)],  # identifier, orchestration: hit at k=3, miss at k=1
    "xl-01":   [good("xl-01", 0)],                                                # cross_source, gateway_lb  -> MISS (needs both)
    "xl-02":   [good("xl-02", 0, 0.9), good("xl-02", 1, 0.8)],                    # cross_source, app_server  -> HIT at k>=2
    "na-01":   [hit("x", "irrelevant", 0.4), hit("y", "irrelevant", 0.3)],        # not in corpus: excluded, top score recorded
    "na-02":   [],                                                                # not in corpus, nothing returned -> 0.0
}

r = evaluate(results, k=3)
assert r.k == 3
assert abs(r.hit_rate - 3 / 5) < 1e-9, r.hit_rate                                 # db-01, orch-01, xl-02 of 5 answerable
assert r.by_kind == {"identifier": 1.0, "symptom": 0.0, "cross_source": 0.5}, r.by_kind
assert r.by_layer == {"database": 0.5, "orchestration": 1.0, "gateway_lb": 0.0, "app_server": 1.0}, r.by_layer
assert set(r.misses) == {"db-02", "xl-01"}, r.misses
assert r.misses["db-02"] == [("some:other-doc", 0.8), (by_id["db-02"].expected[0].doc_id, 0.7)], r.misses["db-02"]
assert r.not_in_corpus_top_scores == {"na-01": 0.4, "na-02": 0.0}, r.not_in_corpus_top_scores
assert "na-01" not in r.misses and "na-02" not in r.misses
print(f"ok: evaluate at k=3 -> hit_rate {r.hit_rate:.2f}, by_kind {r.by_kind}")
print(f"                      by_layer {r.by_layer}, misses {sorted(r.misses)}, not-in-corpus {r.not_in_corpus_top_scores}")

r1 = evaluate(results, k=1)                           # only db-01 still hits at k=1
assert abs(r1.hit_rate - 1 / 5) < 1e-9, r1.hit_rate
assert set(r1.misses) == {"db-02", "orch-01", "xl-01", "xl-02"}, r1.misses
print(f"ok: evaluate at k=1 -> hit_rate {r1.hit_rate:.2f} (orch-01 and xl-02 now miss), misses {sorted(r1.misses)}")

assert evaluate({}, k=3).hit_rate == 0.0
assert evaluate({"na-01": [hit("x", "y", 0.5)]}, k=3).hit_rate == 0.0, "only not-in-corpus questions -> 0.0, not a crash"
print("ok: empty results and not-in-corpus-only results give 0.0 instead of dividing by zero")

print("\nall retrieval_checks checks passed")



# - is_hit:
#   - A chunk with the marker text but from the wrong document is not a hit.
#   - A chunk from the right document without a marker is not a hit.
#   - Case and whitespace differences don't matter.
# - hit_at_k:
#   - An answer at rank 3 is a miss at k=1 and k=2 and a hit at k=3.
#   - A k larger than the hit list doesn't crash, and an empty list is a miss.
#   - Cross-source questions need both passages inside the top k: one of two is a miss, and a second passage at rank 2 doesn't count at k=1.
# - evaluate at k=3: five answerable questions where I know 3 should hit. It checks the overall rate (0.60), the by-kind split (identifier 1.0, symptom 0.0, cross-source 0.5) and the by-layer split. It also checks that the misses list holds exactly db-02 and xl-01, with the right (doc_id, score) pairs.
# - Not-in-corpus questions: they're excluded from the rate, and their top-1 scores are recorded (0.4, and 0.0 for the empty result).
# - evaluate at k=1: the same fake results drop to 0.20, and the misses grow to four, confirming that k really changes the score.
# - Edge cases: empty results, and results with only not-in-corpus questions, return 0.0 instead of dividing by zero.