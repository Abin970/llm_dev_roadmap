"""loaders.py -- manifest line -> clean markdown text + metadata (the
"load" step).

Loaders never touch git or the network: fetch.py already put every file
on disk and described it in data/corpus/manifest.jsonl (see fetch.py
for one line's exact fields). `SourceDoc` below is GIVEN, the shape
chunkers.py consumes. The two functions are yours.

---------------------------------------------------------------------
TODO (yours)
---------------------------------------------------------------------
  iter_manifest(phase=None) -> Iterator[dict]
      one dict per manifest line, optionally only one phase ("A"/"B")
  load(entry) -> SourceDoc | None
      None = nothing usable (log a line and skip; don't crash the run)

Different formats need different parsers (the artifact's point). In
this corpus that means four cases:

1. fmt == "md": kubernetes, runbooks, redis, docker, fluentbit,
   prometheus(-docs), otel, gunicorn, uvicorn, and kafka's pages.
   Mostly Hugo/mkdocs sites, so there's real cruft to strip:
   - YAML front matter between the leading `---` lines. Take `title:`
     from it and drop the rest. MarkdownHeaderTextSplitter does NOT
     understand front matter (verified: it comes out as its own
     heading-less section).
   - Hugo shortcodes, both {{< ... >}} and {{% ... %}}. Kubernetes uses
     {{< glossary_tooltip text="Pod" term_id="pod" >}} inline, so keep
     the text= value and drop the rest of the tag.
   - GitBook template tags: {% hint style="..." %} ... {% endhint %}
     (Fluent Bit). Keep the text between them and drop the tags.
   - HTML comments <!-- ... --> (every Kafka page opens with a license
     comment).
   - Kafka's operations/monitoring.md embeds raw HTML <table> markup
     for its metric tables. Stripping the tags keeps the cell text, which
     is enough to retrieve on.
   - stray inline HTML: <img ...> tracking pixels (Fluent Bit),
     <span id="..."></span> anchors (Gunicorn), <br/>.
   - No front-matter title? Use the first "# " heading, then the file name.

2. fmt == "html" with a content_selector: postgres ("#docContent") and
   nginx ("#content").
       el = BeautifulSoup(html, "html.parser").select_one(entry["content_selector"])
       markdownify(str(el), heading_style="ATX", escape_underscores=False,
                   escape_asterisks=False)
   - heading_style="ATX": the default ("underlined") writes an H2 as
     "Title\\n-----", which the markdown-header chunker can't see.
   - escape_underscores=False: the default turns max_connections into
     max\\_connections (verified), which breaks exact-identifier matching.
   - Remove Postgres's .navheader / .navfooter elements inside
     #docContent BEFORE converting. Otherwise every page starts with a
     "Prev | Up | Next" table (verified).
   - title: the page's <title> (Postgres prefixes "PostgreSQL:
     Documentation: 18: ", which you can strip).

3. fmt == "html", no selector, source == "kafka": the generated config
   tables (kafka_config.html etc.). They're fragments, not pages, so run
   the whole file through markdownify with the same options.

4. fmt == "html", no selector: the postmortems, from 40 different sites,
   so nothing site-specific works. Use a generic article extractor:
       trafilatura.extract(html, url=entry["url"], output_format="markdown",
                           include_comments=False, include_tables=True,
                           favor_recall=True)
   - include_comments defaults to True, and blog comment threads aren't
     the postmortem.
   - It drops the ``` fences around code blocks (verified). That's fine
     for narrative write-ups, and it's why it ISN'T used for vendor docs.
   - title: trafilatura.extract_metadata(html).title, falling back to <title>.
   - Some pages open with site boilerplate (GitLab's starts with a
     login/marketing blurb). Leave it: that's realistic noise retrieval
     has to live with.

Reference numbers from a rough dry run over the full manifest
(2026-09-30): 308 docs and ~898k tokens (cl100k_base) after roughly
this cleaning. Postgres, Kafka and Kubernetes are ~150k each; the 108
runbooks are only ~25k in total, since they're short by nature.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

CORPUS_DIR = Path(__file__).resolve().parents[2] / "data" / "corpus"
RAW_DIR = CORPUS_DIR / "raw"
MANIFEST = CORPUS_DIR / "manifest.jsonl"


@dataclass(frozen=True)
class SourceDoc:
    doc_id: str       # manifest doc_id -- chunk ids are built from it
    text: str         # clean markdown
    title: str
    source: str
    doc_type: str
    layer: str
    url: str


def iter_manifest(phase: str | None = None) -> Iterator[dict]:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")


def load(entry: dict) -> SourceDoc | None:
    raise NotImplementedError("Week 5 TODO -- see this module's docstring")
