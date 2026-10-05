
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.loaders import iter_manifest, load, RAW_DIR, _parse_markdown, _parse_vendor_html

# --- markdown: before vs after
entry = next(e for e in iter_manifest() if e["doc_id"] == "kubernetes:content/en/docs/concepts/workloads/pods/probes.md")
raw = (RAW_DIR / entry["path"]).read_text(errors="ignore")
title, text = _parse_markdown(raw)
print(title)
print(raw[:600])     # before
print("-----")
print(text[:600])    # after

# --- vendor html: before vs after (Postgres + NGINX)
for doc_id in ("postgres:runtime-config-connection", "nginx:ngx_http_upstream_module"):
    entry = next(e for e in iter_manifest() if e["doc_id"] == doc_id)
    raw = (RAW_DIR / entry["path"]).read_text(errors="ignore")
    title, text = _parse_vendor_html(raw, entry["content_selector"])
    print("\n=====", doc_id, "| title:", repr(title), "|", len(raw), "->", len(text), "chars")
    print(text[:700])

# --- every vendor-html doc through load(): none empty, no leftovers
import re
n = 0
for e in iter_manifest():
    if e["fmt"] == "html" and e["content_selector"]:
        d = load(e); n += 1
        assert d is not None, f"empty: {e['doc_id']}"
        assert not re.search(r"\\_|\[#\]\(#|Prev\s*\|", d.text), f"leftover markup: {e['doc_id']}"
        assert re.search(r"^#{1,6} ", d.text, re.M), f"no ATX headings: {e['doc_id']}"
print(f"\n{n} vendor-html docs load clean")


# --- kafka config fragments: one section per setting
from ingestion.loaders import _parse_html_fragment
frag = [e for e in iter_manifest() if e["fmt"] == "html" and e["source"] == "kafka"]
for e in frag:
    raw = (RAW_DIR / e["path"]).read_text(errors="ignore")
    expected = raw.count("<h4>")
    _, text = _parse_html_fragment(raw)
    got = len(re.findall(r"^## ", text, re.M))
    print(f"{e['doc_id'].split(':')[1][-22:]:22s} settings in html: {expected:3d} -> sections: {got:3d}")
    assert got == expected and not re.search(r"</?(li|ul|p|table|tbody|tr|td|th|a|h4|br)\b", text), e["doc_id"]
e = next(e for e in frag if "topic_config" in e["doc_id"])
print("\n" + load(e).text[:900])
print("title fallback:", repr(load(e).title))


# --- the whole corpus through load(): every doc, every format
import collections
from ingestion.loaders import parse_article
per_source, empty = collections.Counter(), []
for e in iter_manifest():
    d = load(e)
    if d is None or not d.title:
        empty.append(e["doc_id"])
    else:
        per_source[e["source"]] += 1
print(f"\nALL: {sum(per_source.values())} of 308 docs loaded with text + title; problems: {empty}")
pm = [load(e) for e in iter_manifest() if e["source"] == "postmortems"]
assert not any("<sup>" in d.text for d in pm), "leftover <sup>"
assert not empty
