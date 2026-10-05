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
import json
import re
from pathlib import Path
from typing import Iterator

import trafilatura
from bs4 import BeautifulSoup
from markdownify import markdownify

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


# data/corpus/manifest.jsonl
def iter_manifest(phase: str | None = None) -> Iterator[dict]:
   
   with open(MANIFEST, "r", encoding="utf-8") as manifest:
       for line in manifest:
            file_entry = json.loads(line)
            if phase is None or file_entry["phase"] == phase:
                yield file_entry
# phase A
# {"doc_id": "postgres:runtime-config-connection", "source": "postgres", 
# "doc_type": "vendor_doc", "layer": "database", "fmt": "html", 
# "path": "postgres/runtime-config-connection.html", "url": "https://www.postgresql.org/docs/18/...", 
# "content_selector": "#docContent", "phase": "A"}
# phase B 
#  {"doc_id": "redis:content/operate/.../latency.md", "source": "redis", 
# "doc_type": "vendor_doc", "layer": "cache", "fmt": "md", "path": "redis/content/operate/.../latency.md", 
# "url": "https://github.com/redis/docs/blob/...", "content_selector": null, "phase": "B"}




_FRONT_MATTER = re.compile(r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*\n", re.S)
_TITLE_LINE = re.compile(r"^title:\s*(.+?)\s*$", re.M)
_H1 = re.compile(r"^#\s+(.+?)\s*$", re.M)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_REF_LINK = re.compile(r"\[([^\]]*)\]\(\{\{[<%]\s*ref\b.*?[>%]\}\}\)", re.S)
_GLOSSARY = re.compile(r"\{\{[<%]\s*glossary_tooltip\b(.*?)[>%]\}\}", re.S)
_HUGO_TAG = re.compile(r"\{\{[<%].*?[>%]\}\}", re.S)       # {{< ... >}} and {{% ... %}}
_GITBOOK_TAG = re.compile(r"\{%.*?%\}", re.S)               # {% hint ... %} / {% endhint %}
_BR = re.compile(r"<br\s*/?>", re.I)
# Only these tags are stripped. A blanket "<...>" rule would also eat
# placeholders in runbook commands like `kubectl -n <namespace>`.
_HTML_NOISE = re.compile(
    r"</?(?:img|span|details|summary|div|table|thead|tbody|tr|th|td|sup|sub)\b[^>]*>", re.I
)


def _glossary_text(match: re.Match) -> str:
    """{{< glossary_tooltip text="node" term_id="node" >}} -> node"""
    args = match.group(1)
    found = re.search(r'\btext=["\']([^"\']*)["\']', args) or re.search(
        r'\bterm_id=["\']([^"\']*)["\']', args
    )
    return found.group(1) if found else ""


def _parse_markdown(raw: str) -> tuple[str, str]:
    """Markdown from Hugo / MkDocs / GitBook sites -> (title, clean markdown).

    Cleanup, in this order (each rule is here because the real corpus
    has it; the counts are from a scan of all 230 markdown docs):
      1. YAML front matter (197 docs): read `title:`, then drop the block.
      2. HTML comments (37 docs; every Kafka page opens with a license one).
      3. Hugo links to other pages, `[label]({{< ref "x.md" >}})` (runbooks):
         keep the label, drop the link, which points nowhere outside Hugo.
      4. `{{< glossary_tooltip text="node" ... >}}` (Kubernetes, 137 uses):
         replaced by the word it stands for.
      5. Every other Hugo shortcode, `{{< note >}}`, `{{% code_sample %}}`...
         (86 docs): the tag is deleted and anything BETWEEN an opening and
         closing tag stays. Known loss: `code_sample` pulls its code from
         another file at build time, so that code isn't in the page.
      6. GitBook tags `{% hint %}` / `{% endhint %}` (Fluent Bit).
      7. Layout HTML: img, span anchors, details/summary, table tags;
         `<br>` becomes a newline. Other `<...>` stays, because
         placeholders like `<namespace>` are content.
      8. Runs of blank lines collapse to one.
    Title: front matter `title:`, else the first `# ` heading, else "".
    """
    title = ""
    front = _FRONT_MATTER.match(raw)
    if front:
        found = _TITLE_LINE.search(front.group(1))
        if found:
            title = found.group(1).strip("\"'")
        raw = raw[front.end():]

    text = _COMMENT.sub("", raw)
    text = _REF_LINK.sub(r"\1", text)
    text = _GLOSSARY.sub(_glossary_text, text)
    text = _HUGO_TAG.sub("", text)
    text = _GITBOOK_TAG.sub("", text)
    text = _BR.sub("\n", text)
    text = _HTML_NOISE.sub("", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if not title:
        heading = _H1.search(text)
        title = heading.group(1) if heading else ""
    return title, text



_PERMALINK = re.compile(r"\s*\[#\]\(#[^)]*\)")   # Postgres heading/term anchors: "[#](#GUC-PORT)"

def _parse_vendor_html(raw: str, content_selector: str) -> tuple[str, str]:
    """Vendor doc page (PostgreSQL, NGINX) -> (title, markdown).

    1. Keep only the element matching `content_selector` (the manifest
       carries it per source), which drops site menus, search boxes and
       footers.
    2. Remove Postgres's "Prev | Up | Next" bars, which sit INSIDE that
       element (.navheader / .navfooter).
    3. markdownify with heading_style="ATX" (default writes "Title\\n----",
       which the header chunker can't see) and escape_underscores=False
       (default writes max\\_connections, breaking exact-name matching).
    4. Drop Postgres's "[#](#ANCHOR)" permalinks.
    Title: the page's <title>, minus Postgres's "PostgreSQL: Documentation:
    18: " prefix; "" if missing (load() falls back to the file name).
    Empty text when the selector matches nothing.
    """
    soup = BeautifulSoup(raw, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = " ".join(soup.title.string.split())   # also turns Postgres's non-breaking spaces into plain ones
        title = re.sub(r"^PostgreSQL: Documentation: \d+: ", "", title)

    content = soup.select_one(content_selector)
    if content is None:
        return title, ""
    for nav in content.select(".navheader, .navfooter"):
        nav.decompose()

    text = markdownify(
        str(content), heading_style="ATX", escape_underscores=False, escape_asterisks=False
    )
    text = _PERMALINK.sub("", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return title, text



def _parse_html_fragment(raw: str) -> tuple[str, str]:
    """Kafka's generated config tables (kafka_config.html, producer_config.html,
    consumer_config.html, topic_config.html) -> ("", markdown).

    These are HTML fragments, not pages: no <title>, no site chrome, just
    one <li> per setting holding an <h4> (the setting's name), a <p>
    (description) and a <table> of Type / Default / Valid Values / Importance
    rows. Converting the file as-is would give one huge table soup, so each
    setting becomes its own section, which is how people search ("what does
    min.insync.replicas do"), and the header chunker can split on it:

        ## min.insync.replicas
        <description, code spans kept>
        - Type: int
        - Default: 1

    The title is "" on purpose; load() falls back to the file name.
    """
    soup = BeautifulSoup(raw, "html.parser")
    sections = []
    for item in soup.select("li:has(> h4)"):          # skip bullet lists nested inside descriptions
        name = item.find("h4").get_text(strip=True)
        description = " ".join(
            markdownify(str(p), escape_underscores=False, escape_asterisks=False).strip()
            for p in item.find_all("p", recursive=False)
        )
        facts = [
            f"- {row.th.get_text(strip=True).rstrip(':')}: {row.td.get_text(' ', strip=True)}"
            for row in item.select("tr")
            if row.th and row.td
        ]
        sections.append("\n".join([f"## {name}", description, *facts]))
    return "", "\n\n".join(sections)



def parse_article(raw: str, url: str) -> tuple[str, str]:
    """A blog post / incident write-up from any website -> (title, markdown).

    The 40 postmortems come from ~30 different sites, so nothing site-specific
    (like a CSS selector) can work. trafilatura finds the main article text on
    its own. include_comments=False drops reader comment threads;
    favor_recall=True keeps borderline paragraphs rather than risk losing
    part of the story. Code fences are lost (trafilatura's behavior), which
    is fine for narrative write-ups.
    Title: trafilatura's page metadata, else the <title> tag, else "".
    """
    text = trafilatura.extract(
        raw, url=url, output_format="markdown", include_comments=False,
        include_tables=True, favor_recall=True,
    ) or ""
    text = re.sub(r"</?su[bp]>", "", text)    # "18<sup>th</sup>" -> "18th"

    meta = trafilatura.extract_metadata(raw, default_url=url)
    title = " ".join((meta.title or "").split()) if meta else ""
    if not title:
        soup = BeautifulSoup(raw, "html.parser")
        title = " ".join(soup.title.string.split()) if soup.title and soup.title.string else ""
    return title, text.strip()



def load(entry: dict) -> SourceDoc | None:

   raw = (RAW_DIR / entry["path"]).read_text(encoding ="utf-8", errors="ignore")

   if entry["fmt"] == "md":
       title, text = _parse_markdown(raw)
   elif entry["content_selector"]:
       title, text = _parse_vendor_html(raw, entry["content_selector"])
   elif entry["source"] == "kafka":
       title, text = _parse_html_fragment(raw)
   else:
       title, text = parse_article(raw, entry["url"])

   if not text.strip():
        return None

   title = title or Path(entry["path"]).stem   # e.g. uvicorn's lifespan.md has no heading at all

   return SourceDoc(
        doc_id=entry["doc_id"], text=text, title=title,
        source=entry["source"], doc_type=entry["doc_type"],
        layer=entry["layer"], url=entry["url"]
   )

