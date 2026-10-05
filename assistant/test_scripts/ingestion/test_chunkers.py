import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import statistics
import tiktoken

from ingestion.loaders import iter_manifest, load
from ingestion.chunkers import STRATEGIES

enc = tiktoken.get_encoding("cl100k_base")
tokens = lambda s: len(enc.encode(s))

# one doc per input format: markdown runbook, vendor HTML, postmortem
DOC_IDS = [
    "runbooks:content/runbooks/kubernetes/KubePodCrashLooping.md",
    "postgres:runtime-config-client",
    "postmortems:sentry-2015-xid-wraparound",
]
manifest = {e["doc_id"]: e for e in iter_manifest()}

SIZE, OVERLAP = 500, 50
for doc_id in DOC_IDS:
    doc = load(manifest[doc_id])                      # real SourceDoc, straight from the loaders
    print(f"\n######## {doc_id}  ({tokens(doc.text)} tokens in the document)")
    for name, fn in STRATEGIES.items():
        chunks = fn(doc, SIZE, OVERLAP)
        sizes = [tokens(c.text) for c in chunks]
        print(f"  {name:16s} {len(chunks):3d} chunks | tokens min/median/max = "
              f"{min(sizes)}/{int(statistics.median(sizes))}/{max(sizes)}")

        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), f"{name}: duplicate chunk ids"
        assert all(i.startswith(doc_id + "#") and i.removeprefix(doc_id + "#").isdigit() for i in ids), \
            f"{name}: malformed chunk id, e.g. {ids[0]}"
        assert all(c.text.strip() for c in chunks), f"{name}: empty chunk"
        assert all(c.doc_type == doc.doc_type and c.layer == doc.layer and c.url == doc.url for c in chunks)
        if name == "markdown_header":
            print(f"      sections: {sorted({c.section for c in chunks})[:3]} ...")
        else:
            assert all(c.section == "" for c in chunks)

print("\nall chunker checks passed")


# ---------------------------------------------------------------------------
# Marker check: can each chunker keep the answering passage whole?
#
# Each golden question lists the page that answers it plus short "marker"
# phrases copied word for word from the answering sentence. If NO chunk
# contains a marker, the chunker cut the answer apart and retrieval could
# never return it, however good the search is. No embeddings needed.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "week5_rag_fundamentals" / "experiments"))
from golden_retrieval import GOLDEN

norm = lambda s: " ".join(s.lower().split())      # ignore whitespace/case differences

for size in (250, 500, 1000):
    print(f"\n--- marker check, target size {size}, overlap 50 ---")
    for name, fn in STRATEGIES.items():
        total = whole = 0
        lost = []
        for q in GOLDEN:                          # not_in_corpus questions have no expected page
            for ex in q.expected:
                doc = load(manifest[ex.doc_id])
                chunks = fn(doc, size, 50)
                survived = any(norm(m) in norm(c.text) for c in chunks for m in ex.markers)
                total += 1
                whole += survived
                if not survived:
                    lost.append(q.qid)
        print(f"  {name:16s} answering passage whole in a chunk: {whole}/{total}  lost: {lost}")
        assert not lost, f"{name} at size {size} cut apart the passages for {lost}"
