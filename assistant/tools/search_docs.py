"""search_docs -- keyword search over a local folder of technical notes.

Stands in for real retrieval (Week 5 replaces this with actual RAG --
chunking, embeddings, vector search). For now: plain keyword/substring
matching over the files in tools/docs/. No ranking, no relevance scoring
-- presence or absence of the keyword is the whole point at this stage.
"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from .registry import register

DOCS_DIR = (Path(__file__).resolve().parent / "docs").resolve()


class SearchDocsArgs(BaseModel):
    query: str


def _word_weight(word: str) -> int:
    """Specific identifiers (contain a digit) outweigh long words, which
    outweigh short/common ones -- a stand-in for real relevance scoring."""
    if any(c.isdigit() for c in word):
        return 2
    if len(word) > 4:
        return 1
    return 0


@register("search_docs", SearchDocsArgs)
def search_docs(args: SearchDocsArgs) -> str:
    """Search ONLY our own internal engineering notes and incident
    reports. Has no knowledge of external products, services, or
    third-party companies -- use search_web for anything outside our own
    systems."""
    query_words = re.findall(r"\w+", args.query.lower())

    best_file = None
    best_score = 0
    best_text = ""
    for file_path in DOCS_DIR.glob("*"):
        text = file_path.read_bytes().decode(errors="ignore")
        text_lower = text.lower()
        score = sum(
            _word_weight(w)
            for w in set(query_words)
            if re.search(rf"\b{re.escape(w)}\b", text_lower)
        )
        if score > best_score:
            best_score = score
            best_file = file_path
            best_text = text

    if best_file is None or best_score < 2:
        return "(no matching docs)"

    text_lower = best_text.lower()
    present_words = [
        w for w in query_words if re.search(rf"\b{re.escape(w)}\b", text_lower)
    ]
    keyword = max(present_words, key=_word_weight)

    index = re.search(rf"\b{re.escape(keyword)}\b", text_lower).start()
    start = max(0, index - (100 - len(keyword)) // 2)
    end = min(len(best_text), start + 100)
    snippet = best_text[start:end].replace("\n", " ")

    return f"{best_file.name}: ...{snippet}..."
