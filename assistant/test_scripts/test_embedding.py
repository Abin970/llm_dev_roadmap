import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from embeddings import OpenAIEmbedder, EMBED_DIM, MAX_TOKENS_PER_REQUEST

embedder = OpenAIEmbedder()

# ---------------------------------------------------------------------------
# Part 1 -- OFFLINE checks (no API call, no cost): bad input must raise.
# ---------------------------------------------------------------------------
for label, bad in [("empty string", [""]), ("whitespace only", ["   "]),
                   ("over 8192 tokens", ["word " * 9000])]:
    try:
        embedder.embed(["fine text", bad[0]])
        print(f"FAIL: {label} was accepted")
        sys.exit(1)
    except ValueError as e:
        print(f"ok: {label} -> ValueError: {e!r}")

empty = embedder.embed([])
assert empty.shape == (0, EMBED_DIM), empty.shape
print("ok: embed([]) returns an empty (0, 1536) array")

# ---------------------------------------------------------------------------
# Part 2 -- LIVE check: 3 short texts, ONE API call (~30 tokens, a tiny
# fraction of a cent).
# ---------------------------------------------------------------------------
texts = [
    "The pod keeps restarting after the memory limit is exceeded.",
    "KubePodCrashLooping",
    "max_connections controls how many clients can connect to PostgreSQL.",
]
vectors = embedder.embed(texts)

assert vectors.shape == (3, EMBED_DIM), f"shape {vectors.shape}"
assert vectors.dtype == np.float32, vectors.dtype
norms = np.linalg.norm(vectors, axis=1)
assert np.allclose(norms, 1.0, atol=1e-5), f"rows not normalized: {norms}"
assert embedder.tokens_used > 0
print(f"\nok: shape {vectors.shape}, dtype {vectors.dtype}, row lengths {norms.round(6)}")
print(f"ok: tokens_used = {embedder.tokens_used}")

# Same order in, same order out: embedding a text alone must match its row.
alone = embedder.embed([texts[2]])[0]
assert np.allclose(alone, vectors[2], atol=1e-3), "row 2 doesn't match embedding that text alone"
print("ok: row i really is the embedding of texts[i] (checked on row 2)")

# Similar meaning should score higher than unrelated text. Rows are length 1,
# so the dot product IS the cosine similarity.
sim = vectors @ vectors.T
print("\ncosine similarity matrix (rows/cols = the 3 texts):")
print(sim.round(3))
assert sim[0, 1] > sim[0, 2], "pod-restart text should be closer to KubePodCrashLooping than to the Postgres one"
print("ok: pod text is closer to KubePodCrashLooping than to the PostgreSQL text")

# ---------------------------------------------------------------------------
# Part 3 -- embed_query: one vector, same values as embed([text])[0].
# ---------------------------------------------------------------------------
q = embedder.embed_query("what restarts a crashing pod?")
assert q.shape == (EMBED_DIM,), q.shape
assert abs(np.linalg.norm(q) - 1.0) < 1e-5
print("\nok: embed_query returns one normalized (1536,) vector")

print("\nall embedding checks passed")
