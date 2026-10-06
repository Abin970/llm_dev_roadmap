import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from vectorstore import Chunk, FaissStore

# Everything here is made up: random vectors, fake chunks. No API calls, no cost.
DIM = 16
rng = np.random.default_rng(0)


def make_vectors(n: int) -> np.ndarray:
    v = rng.random((n, DIM)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)      # length 1, like real embeddings


def make_chunk(i: int, doc_type: str = "vendor_doc", layer: str = "database") -> Chunk:
    return Chunk(chunk_id=f"doc{i}#0", doc_id=f"doc{i}", text=f"text of chunk {i}", source="test",
                 doc_type=doc_type, layer=layer, url=f"https://example.com/{i}", title=f"Doc {i}", section="")


# ---- 1. add + count -------------------------------------------------------
N = 20
vectors = make_vectors(N)
chunks = [make_chunk(i, doc_type="runbook" if i % 4 == 0 else "vendor_doc",
                     layer="orchestration" if i % 2 == 0 else "database") for i in range(N)]
store = FaissStore(DIM)
store.add(chunks, vectors)
assert store.count() == N
print(f"ok: add + count -> {store.count()}")

# ---- 2. add rejects mismatched lengths ------------------------------------
try:
    FaissStore(DIM).add(chunks[:5], vectors[:3])
    raise SystemExit("FAIL: mismatched chunks/vectors were accepted")
except ValueError as e:
    print(f"ok: mismatched lengths rejected ({type(e).__name__}: {e})")

# ---- 3. a stored vector finds itself first, best-first order ---------------
hits = store.search(vectors[7], k=5)
assert len(hits) == 5
assert hits[0].chunk.chunk_id == "doc7#0", hits[0].chunk.chunk_id
assert abs(hits[0].score - 1.0) < 1e-4, hits[0].score
scores = [h.score for h in hits]
assert scores == sorted(scores, reverse=True), scores
print(f"ok: vector 7 finds chunk 7 first (score {hits[0].score:.4f}); scores best-first {np.round(scores, 3)}")

# ---- 4. the row-to-chunk mapping holds for EVERY stored vector --------------
for i in range(N):
    assert store.search(vectors[i], k=1)[0].chunk.chunk_id == f"doc{i}#0", i
print(f"ok: all {N} vectors map back to their own chunk")

# ---- 5. k larger than the index: all chunks, no -1 rows, no crash ------------
all_hits = store.search(vectors[0], k=100)
assert len(all_hits) == N and len({h.chunk.chunk_id for h in all_hits}) == N
print(f"ok: k=100 on a {N}-vector index returns {len(all_hits)} hits (no -1 slots leaked)")

# ---- 6. filters ---------------------------------------------------------------
runbooks = store.search(vectors[1], k=10, filters={"doc_type": ("runbook",)})
assert runbooks and all(h.chunk.doc_type == "runbook" for h in runbooks)
both = store.search(vectors[1], k=10, filters={"doc_type": ("runbook", "vendor_doc"), "layer": ("orchestration",)})
assert both and all(h.chunk.layer == "orchestration" for h in both)
assert store.search(vectors[1], k=5, filters={"doc_type": ("postmortem",)}) == []
print(f"ok: filters work (single field, two fields, no-match -> []): {len(runbooks)} runbooks, {len(both)} orchestration")

# ---- 7. the post-filter effect: a rare filter can return FEWER than k ----------
# FAISS can't filter, so search() fetches k*10 candidates and filters afterwards.
# 3 "rare" chunks hidden among 200; ask for 5 of them.
big_v = make_vectors(200)
big_chunks = [make_chunk(i, doc_type="rare" if i >= 197 else "common") for i in range(200)]
big = FaissStore(DIM)
big.add(big_chunks, big_v)
rare = big.search(big_v[0], k=5, filters={"doc_type": ("rare",)})
assert len(rare) <= 3 and all(h.chunk.doc_type == "rare" for h in rare)
print(f"ok: asked for k=5 'rare' hits, 3 exist, got {len(rare)} (only 50 candidates were examined before filtering)")

# ---- 8. save / load round trip ---------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    target = Path(tmp) / "nested" / "faiss-test-500"           # folders that don't exist yet
    store.save(target)
    assert (target / "index.faiss").exists() and (target / "chunks.jsonl").exists()
    loaded = FaissStore.load(target)
    assert loaded.count() == store.count()
    assert loaded.chunks == store.chunks, "chunks changed in the round trip"
    for i in (0, 7, 13):
        before, after = store.search(vectors[i], k=5), loaded.search(vectors[i], k=5)
        assert [h.chunk.chunk_id for h in before] == [h.chunk.chunk_id for h in after]
        assert np.allclose([h.score for h in before], [h.score for h in after], atol=1e-6)
    store.save(target)                                            # saving again into the same folder must not fail
print("ok: save -> load gives identical chunks and identical search results (and re-saving works)")

print("\nall vectorstore checks passed")
