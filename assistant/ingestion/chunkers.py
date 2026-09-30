"""chunkers.py -- SourceDoc -> list[Chunk], in three strategies. These
are exercise 2's comparison.

All three measure size in TOKENS, using the embedding model's tokenizer:
    encoding_name="cl100k_base"
langchain's from_tiktoken_encoder() and TokenTextSplitter DEFAULT TO
"gpt2" (verified, langchain-text-splitters 1.1.2). That's a different
tokenizer from the embedding model's, so without the argument your
"500-token chunks" would silently be measured in the wrong unit.

---------------------------------------------------------------------
TODO (yours) -- one function per strategy
---------------------------------------------------------------------
fixed_chunks(doc, size, overlap)
    TokenTextSplitter(encoding_name="cl100k_base", chunk_size=size,
                      chunk_overlap=overlap).split_text(doc.text)
    Cuts every `size` tokens no matter what: mid-sentence, mid-code-
    block, mid-table-row (verified). The baseline exercise 2 expects to
    lose.

recursive_chunks(doc, size, overlap)
    RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base", chunk_size=size, chunk_overlap=overlap)
    Tries its separators in order ["\\n\\n", "\\n", " ", ""]: paragraphs
    first, then lines, then words, then characters. The size is a TARGET,
    not a guarantee. With a custom separator list that lacks "", an
    unsplittable run stays whole (verified: a 5,000-character line with
    no spaces stayed 5,000 characters).

markdown_header_chunks(doc, size, overlap)
    MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False).split_text(doc.text)
    Splits at headings and records them in each piece's metadata
    ({"h1": ..., "h2": ...}). It's code-fence-aware: a "# comment" line
    inside ``` is NOT treated as a heading (verified).
    - It has NO size limit, so run recursive_chunks' splitter over any
      oversized section. split_documents() keeps the heading metadata
      on every piece (verified).
    - strip_headers=False keeps the heading line inside the chunk text,
      so the embedding "sees" which section the text came from. The
      default is True.
    - Joined lines come out as "text  \\n" (two trailing spaces, markdown's
      line-break syntax). Harmless.

Every strategy returns Chunks (vectorstore.Chunk) where:
    chunk_id = f"{doc.doc_id}#{position}"   -- position counts from 0.
               Stable as long as the document, strategy and size don't
               change, which golden-set citations depend on.
    section  = " › ".join(heading values) for markdown_header_chunks,
               "" for the other two.
    every other field is copied from the SourceDoc.
Never emit an empty or whitespace-only chunk: the embeddings API rejects
"" with a 400.

What exercise 2 should make visible: which strategy splits a code block
or a config table in half (runbooks have kubectl snippets; the Kafka
config tables and Postgres pages have long tables), and how that changes
what top-3 retrieval returns for the same golden questions.
"""
from __future__ import annotations

from vectorstore import Chunk

from .loaders import SourceDoc

ENCODING = "cl100k_base"
DEFAULT_SIZE = 500
DEFAULT_OVERLAP = 50


def fixed_chunks(doc: SourceDoc, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def recursive_chunks(doc: SourceDoc, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def markdown_header_chunks(doc: SourceDoc, size: int = DEFAULT_SIZE, overlap: int = DEFAULT_OVERLAP) -> list[Chunk]:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


STRATEGIES = {
    "fixed": fixed_chunks,
    "recursive": recursive_chunks,
    "markdown_header": markdown_header_chunks,
}
