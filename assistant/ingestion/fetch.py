"""Fetch the corpus described in sources.py into data/corpus/.

Plumbing, not an exercise. The learning starts at loaders.py, which only
ever reads the manifest this script writes. Loaders never touch git or
the network.

Usage (from assistant/):
    python -m ingestion.fetch                  # every source
    python -m ingestion.fetch --phase A        # Postgres + Kubernetes + runbooks
    python -m ingestion.fetch --only nginx postmortems
    python -m ingestion.fetch --refresh        # re-download web pages already on disk

Writes:
    data/corpus/raw/<source>/...   git sparse checkouts / saved HTML pages
    data/corpus/manifest.jsonl     one JSON line per document on disk

One manifest line:
    {"doc_id": "kubernetes:content/en/docs/concepts/workloads/pods/pod-lifecycle.md",
     "source": "kubernetes", "doc_type": "vendor_doc", "layer": "orchestration",
     "fmt": "md", "path": "kubernetes/content/en/docs/.../pod-lifecycle.md",
     "url": "https://github.com/kubernetes/website/blob/<commit>/content/...",
     "content_selector": null, "phase": "A"}

`path` is relative to data/corpus/raw/. `url` is what a citation should
point at: the exact commit for git sources, and the final (post-redirect)
URL for web pages. The manifest is rebuilt from EVERYTHING on disk after
each run, so fetching phase B later never drops phase A's documents.

Git sources use a shallow, blobless, sparse clone, so only the listed
files' contents are downloaded, not the (large) repositories.

Web pages get one request each, 1s apart per host, with a descriptive
User-Agent, and robots.txt is respected. A page that fails is reported
and left out of the manifest instead of failing the whole run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.robotparser
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

from .sources import SOURCES, GitSource, PathGroup, WebSource

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "corpus"
RAW_DIR = CORPUS_DIR / "raw"
MANIFEST = CORPUS_DIR / "manifest.jsonl"

HEADERS = {"User-Agent": "llm-dev-roadmap-corpus-fetch/0.1 (personal learning project)"}
POLITE_DELAY_S = 1.0
PAGES_INDEX = "_pages.json"  # per web source: slug -> {url, final_url, fetched_at}

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_last_hit: dict[str, float] = {}


def _git(*args: str, cwd: Path | None = None) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def fetch_git(src: GitSource) -> None:
    dest = RAW_DIR / src.name
    if not (dest / ".git").exists():
        print(f"[{src.name}] cloning {src.repo} (shallow, blobless, sparse)")
        _git("clone", "--quiet", "--depth", "1", "--filter=blob:none", "--sparse", src.repo, str(dest))
    patterns = ["/" + p for group in src.groups for p in group.paths]
    _git("sparse-checkout", "set", "--no-cone", *patterns, cwd=dest)
    print(f"[{src.name}] {len(patterns)} paths checked out at {_git('rev-parse', '--short', 'HEAD', cwd=dest)}")


def _allowed(url: str) -> bool:
    """robots.txt check (RFC 9309): 200 -> obey it, 4xx -> no rules,
    5xx/unreachable -> treat as disallowed. Fetched with our own
    User-Agent, since the stdlib reader's default one gets 403s that it
    then misreads as "disallow everything"."""
    parts = urlparse(url)
    root = f"{parts.scheme}://{parts.netloc}"
    if root not in _robots:
        try:
            r = requests.get(root + "/robots.txt", headers=HEADERS, timeout=15)
        except requests.RequestException:
            _robots[root] = None
        else:
            if r.status_code >= 500:
                _robots[root] = None
            else:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
                _robots[root] = rp
    rp = _robots[root]
    return rp is not None and rp.can_fetch(HEADERS["User-Agent"], url)


def _polite_get(url: str) -> requests.Response:
    host = urlparse(url).netloc
    wait = POLITE_DELAY_S - (time.monotonic() - _last_hit.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    try:
        return requests.get(url, headers=HEADERS, timeout=30)
    finally:
        _last_hit[host] = time.monotonic()


def fetch_web(src: WebSource, refresh: bool) -> list[str]:
    dest = RAW_DIR / src.name
    dest.mkdir(parents=True, exist_ok=True)
    index_path = dest / PAGES_INDEX
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    failures = []
    for page in src.pages:
        out = dest / f"{page.slug}.html"
        if out.exists() and page.slug in index and not refresh:
            continue
        if not _allowed(page.url):
            failures.append(f"{page.slug}: disallowed by robots.txt (or robots.txt unreachable)")
            continue
        try:
            r = _polite_get(page.url)
        except requests.RequestException as e:
            failures.append(f"{page.slug}: {type(e).__name__}: {e}")
            continue
        ctype = r.headers.get("content-type", "")
        if r.status_code != 200 or "html" not in ctype:
            failures.append(f"{page.slug}: HTTP {r.status_code} {ctype!r} at {r.url}")
            continue
        out.write_bytes(r.content)
        index[page.slug] = {"url": page.url, "final_url": r.url,
                            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    print(f"[{src.name}] {sum(p.slug in index for p in src.pages)}/{len(src.pages)} pages on disk")
    return failures


def _expand(dest: Path, group: PathGroup) -> list[Path]:
    files: list[Path] = []
    for p in group.paths:
        target = dest / p
        if target.is_dir():
            files += sorted(f for f in target.rglob(f"*.{group.fmt}") if not f.name.startswith("_"))
        elif target.is_file():
            files.append(target)
        else:
            print(f"  ! {dest.name}: listed in sources.py but missing from the checkout: {p}")
    return files


def build_manifest() -> list[dict]:
    docs: list[dict] = []
    for src in SOURCES:
        dest = RAW_DIR / src.name
        if isinstance(src, GitSource):
            if not (dest / ".git").exists():
                continue
            commit = _git("rev-parse", "HEAD", cwd=dest)
            for group in src.groups:
                for f in _expand(dest, group):
                    rel = f.relative_to(dest).as_posix()
                    docs.append({
                        "doc_id": f"{src.name}:{rel}", "source": src.name,
                        "doc_type": src.doc_type, "layer": group.layer, "fmt": group.fmt,
                        "path": f"{src.name}/{rel}", "url": f"{src.repo}/blob/{commit}/{rel}",
                        "content_selector": None, "phase": src.phase,
                    })
        else:
            index_path = dest / PAGES_INDEX
            index = json.loads(index_path.read_text()) if index_path.exists() else {}
            for page in src.pages:
                if page.slug not in index or not (dest / f"{page.slug}.html").exists():
                    continue
                docs.append({
                    "doc_id": f"{src.name}:{page.slug}", "source": src.name,
                    "doc_type": src.doc_type, "layer": page.layer, "fmt": "html",
                    "path": f"{src.name}/{page.slug}.html", "url": index[page.slug]["final_url"],
                    "content_selector": src.content_selector, "phase": src.phase,
                })
    MANIFEST.write_text("".join(json.dumps(d) + "\n" for d in docs))
    return docs


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Fetch the Week 5 corpus into data/corpus/.")
    ap.add_argument("--phase", choices=["A", "B"], help="fetch only this phase's sources")
    ap.add_argument("--only", nargs="+", metavar="SOURCE", help="fetch only these sources")
    ap.add_argument("--refresh", action="store_true", help="re-download web pages already on disk")
    args = ap.parse_args(argv)

    unknown = set(args.only or ()) - {s.name for s in SOURCES}
    if unknown:
        ap.error(f"unknown source(s): {sorted(unknown)}")
    selected = [
        s for s in SOURCES
        if (args.phase is None or s.phase == args.phase) and (args.only is None or s.name in args.only)
    ]

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for src in selected:
        if isinstance(src, GitSource):
            try:
                fetch_git(src)
            except subprocess.CalledProcessError as e:
                failures.append(f"{src.name}: git {' '.join(e.cmd[1:3])} failed: {e.stderr.strip()[:200]}")
        else:
            failures += [f"{src.name}/{f}" for f in fetch_web(src, args.refresh)]

    docs = build_manifest()
    print(f"\nmanifest: {len(docs)} documents -> {MANIFEST.relative_to(REPO_ROOT)}")
    for key in ("doc_type", "layer"):
        print(f"  by {key}:", dict(sorted(Counter(d[key] for d in docs).items())))
    if failures:
        print(f"\n{len(failures)} failure(s), left out of the manifest:")
        for f in failures:
            print("  -", f)


if __name__ == "__main__":
    main()
