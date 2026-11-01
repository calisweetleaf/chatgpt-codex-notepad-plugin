#!/usr/bin/env python3
"""
docsnag2.py — evolved docsnag for sites whose nav does NOT mirror the URL path.

What changed vs docsnag.py (v1):
  1. HIERARCHICAL llms.txt parsing. v1 only read `## Section` headers, so a site
     like antigravity.google — whose llms.txt is `## Documentation` with
     `### Get Started` / `### Antigravity CLI` / ... subsections — collapsed
     into 4 junk sections (Core Pages / Products / Use Cases / Documentation,
     108 "pages" including the homepage and pricing). v2 parses ## AND ###,
     and when a ## group contains ### subsections, the ### level is the folder.
     That matches how Daeron actually organizes these by hand:
         <out>/<section-as-subfolder>/<one-md-per-page>.md
  2. DOCS-PREFIX FILTER. Only URLs under the target path (/docs) are kept in
     hierarchical mode, so marketing pages from the same llms.txt don't leak in.
  3. SECTION EXCLUSIONS. --exclude <regex> (repeatable) drops whole sections,
     e.g. --exclude sdk when the SDK docs aren't wanted.
  4. FLAT SECTION FOLDERS. Nested URL sub-paths inside a section are flattened
     into the filename with '-' ( /docs/cli/commands/agents ->
     antigravity-cli/commands-agents.md ), and a leading path segment that just
     repeats the section's own slug token (cli/, ide/, sdk/) is dropped first.
     One folder level, one .md per page/tab — no deep URL-mirror trees.
  5. NO BROWSER REQUIRED UP FRONT. v1's fetch_from_index() launched Playwright
     before fetching anything and hard-crashed if Chromium wasn't installed,
     even when every page was available as raw .md. v2 tries tiers in order:
        a. raw markdown conventions (.md suffix, /index.md)
        b. plain HTTP GET + <main>/<article> extraction + markdownify
        c. Playwright render — launched LAZILY, only if a page actually
           reaches this tier, and skipped with a warning if unavailable.
     The "Copy/View Markdown" button in a site's UI is just a link to tier (a);
     nothing here depends on clicking it.
  6. INDEX.md + manifest.json written at the tree root (titles -> files ->
     source URLs) so a router skill can be built straight from the zip.
  7. UTF-8 FORCED when a response omits charset. Google's .md endpoints send
     no charset, requests defaults text/* to ISO-8859-1, and the first agy run
     came back with mojibake (â€™ / âœ…) on every page. Caught in QA, fixed
     in get(), re-ran clean.

Usage:
  python3 docsnag2.py https://antigravity.google/docs/ -o agy-10-19 --exclude sdk
"""
import argparse
import json
import os
import re
import sys
import zipfile
import shutil
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as html2md

UA = "Mozilla/5.0 (X11; Linux x86_64) docsnag/2.0 (+personal archival tool)"
TIMEOUT = 25


def get(url, **kw):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, **kw)
    # Google's .md endpoints omit charset; requests then defaults text/* to
    # ISO-8859-1 and every curly quote / emoji turns into mojibake (â€™, âœ…).
    # These docs are UTF-8 — say so.
    if not r.encoding or r.encoding.lower().replace("_", "-") in ("iso-8859-1", "iso8859-1", "iso8859", "latin-1"):
        r.encoding = "utf-8"
    return r


# ---------------------------------------------------------------- llms.txt --

def try_llms_txt(base):
    """Same candidate hunt as v1: llms-full.txt / llms.txt under the docs
    prefix, then at the site root (antigravity only publishes it at root)."""
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    docs_prefix = parsed.path.rstrip("/")
    candidates, seen = [], set()
    for prefix in (docs_prefix, ""):
        for name in ("llms-full.txt", "llms.txt"):
            u = f"{root}{prefix}/{name}"
            if u not in seen:
                seen.add(u)
                candidates.append(u)
    for url in candidates:
        try:
            r = get(url, allow_redirects=True)
        except requests.RequestException:
            continue
        if r.status_code == 200 and "text" in r.headers.get("content-type", "") and len(r.text) > 200:
            return url, r.text
    return None, None


LINK_RE = re.compile(r"^-\s*\[([^\]]+)\]\(([^)]+)\)")


def parse_llms_hier(text, root):
    """Parse llms.txt into an ordered tree:
    {h2_title: {"pages": [(title, url)], "subs": {h3_title: [(title, url)]}}}
    """
    tree = {}
    cur_h2, cur_h3 = "General", None
    for line in text.splitlines():
        h3 = re.match(r"^###\s+(.+)$", line)
        h2 = re.match(r"^##\s+(.+)$", line)
        if h3:
            cur_h3 = h3.group(1).strip()
            tree.setdefault(cur_h2, {"pages": [], "subs": {}})["subs"].setdefault(cur_h3, [])
            continue
        if h2:
            cur_h2 = h2.group(1).strip()
            cur_h3 = None
            tree.setdefault(cur_h2, {"pages": [], "subs": {}})
            continue
        m = LINK_RE.match(line.strip())
        if m:
            title, url = m.group(1).strip(), m.group(2).strip()
            if url.startswith("/"):
                url = root + url
            node = tree.setdefault(cur_h2, {"pages": [], "subs": {}})
            if cur_h3:
                node["subs"].setdefault(cur_h3, []).append((title, url))
            else:
                node["pages"].append((title, url))
    return tree


def select_sections(tree, docs_prefix, root):
    """Pick the folder level: if any ## group has ### subs whose pages live
    under docs_prefix, those ### subs are the sections. Otherwise fall back to
    the ## level (v1 behaviour). Returns ordered {section: [(title, url)]}."""
    def under_docs(url):
        return urlparse(url).path.startswith(docs_prefix) if docs_prefix else True

    sub_sections = {}
    for h2, node in tree.items():
        for h3, pages in node["subs"].items():
            kept = [(t, u) for t, u in pages if under_docs(u)]
            if kept:
                sub_sections[h3] = kept
    if sub_sections:
        return sub_sections

    flat = {}
    for h2, node in tree.items():
        kept = [(t, u) for t, u in node["pages"] if under_docs(u)]
        if kept:
            flat[h2] = kept
    return flat


# ------------------------------------------------------------------ naming --

def kebab(name):
    name = re.sub(r"\(.*?\)", "", name)  # drop parentheticals
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return name or "section"


# Section-slug tokens that pages repeat as a leading URL segment.
SECTION_PREFIX_TOKENS = {
    "antigravity-cli": {"cli"},
    "antigravity-for-ides": {"ide", "ides"},
    "antigravity-sdk": {"sdk"},
    "antigravity-app": {"app"},
}


def page_filename(section_slug, url, docs_prefix):
    path = urlparse(url).path
    rel = path[len(docs_prefix):].strip("/") if docs_prefix and path.startswith(docs_prefix) else path.strip("/")
    parts = [p for p in rel.split("/") if p]
    if not parts:
        return "index.md"
    tokens = SECTION_PREFIX_TOKENS.get(section_slug, set()) | {section_slug, section_slug.split("-")[-1]}
    if len(parts) > 1 and parts[0] in tokens:
        parts = parts[1:]
    return "-".join(parts) + ".md"


# ------------------------------------------------------------- orphan sweep --

# First URL segment -> section slug, for docs pages a site's llms.txt forgot
# to list under its Documentation tree (antigravity: /docs/ide/extensions is
# only listed as a "Product", yet it's the IDE Extensions overview page).
ORPHAN_SEGMENT_MAP = {
    "cli": "antigravity-cli",
    "ide": "antigravity-for-ides",
    "sdk": "antigravity-sdk",
    "commands": "antigravity-app",
}

# Full-URL overrides for legacy pages whose first segment matches no section
# (antigravity: /docs/agent and /docs/tools are App-era pages dropped from the
# current nav and from llms.txt, but still live in the sitemap).
ORPHAN_URL_MAP = {
    "/agent": "antigravity-app",
    "/tools": "antigravity-app",
}


def try_sitemap_urls(base, docs_prefix):
    parsed = urlparse(base)
    root = f"{parsed.scheme}://{parsed.netloc}"
    for sm in (f"{root}{docs_prefix}/sitemap.xml", f"{root}/sitemap.xml"):
        try:
            r = get(sm)
        except requests.RequestException:
            continue
        if r.status_code != 200:
            continue
        urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
        urls = [u for u in urls if urlparse(u).path.startswith(docs_prefix)] if docs_prefix else urls
        if urls:
            return urls
    return []


# ---------------------------------------------------------------- fetching --

def try_raw_markdown(url):
    for a in (url.rstrip("/") + ".md", url.rstrip("/") + "/index.md"):
        try:
            r = get(a)
        except requests.RequestException:
            continue
        ct = r.headers.get("content-type", "")
        if r.status_code == 200 and ("markdown" in ct or "text/plain" in ct or "text/markdown" in ct):
            if "<html" not in r.text[:500].lower() and len(r.text.strip()) > 40:
                return r.text
    return None


def fetch_via_http(url):
    """Tier (b): plain GET + main-content extraction. No browser, no button."""
    try:
        r = get(url)
    except requests.RequestException:
        return None
    if r.status_code != 200 or "<html" not in r.text[:1000].lower():
        return None
    soup = BeautifulSoup(r.text, "lxml")
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"}) or soup.body
    if main is None:
        return None
    title_tag = soup.find("h1") or soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else url
    md = html2md(str(main), heading_style="ATX", bullets="-")
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    if len(md) < 40:
        return None
    return f"# {title}\n\nSource: {url}\n\n{md}\n"


class LazyBrowser:
    """Tier (c): Playwright, launched only on first actual need."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._failed = False

    def fetch(self, url):
        if self._failed:
            return None
        try:
            if self._browser is None:
                from playwright.sync_api import sync_playwright
                self._pw = sync_playwright().start()
                exe = "/opt/pw-browsers/chromium/chrome-linux/chrome"
                self._browser = self._pw.chromium.launch(
                    executable_path=exe if os.path.exists(exe) else None
                )
            page = self._browser.new_page(user_agent=UA)
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(500)
                html = page.content()
            finally:
                page.close()
        except Exception as e:
            print(f"    [!] render tier unavailable: {e}")
            self._failed = True
            return None
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.find(attrs={"role": "main"}) or soup.body
        if main is None:
            return None
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url
        md = html2md(str(main), heading_style="ATX", bullets="-")
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        return f"# {title}\n\nSource: {url}\n\n{md}\n"

    def close(self):
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass


# -------------------------------------------------------------------- main --

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="Docs base URL, e.g. https://antigravity.google/docs/")
    ap.add_argument("-o", "--out", default=None, help="Output folder name")
    ap.add_argument("--exclude", action="append", default=[],
                    help="Regex matched against section names to drop (repeatable), e.g. --exclude sdk")
    ap.add_argument("--dry-run", action="store_true", help="Print the planned tree, fetch nothing")
    args = ap.parse_args()

    parsed = urlparse(args.url if args.url.startswith("http") else "https://" + args.url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    docs_prefix = parsed.path.rstrip("/") or ""
    domain = parsed.netloc.replace("www.", "").split(".")[0]
    outname = args.out or f"{domain}_docs"
    outdir = Path(outname).resolve()

    print(f"[*] Target: {args.url}")
    print(f"[*] Output: {outdir}")

    src, text = try_llms_txt(args.url)
    if not src:
        print("[!] No llms.txt found — v2 currently handles llms.txt sites; use docsnag.py v1 sitemap mode.")
        sys.exit(1)
    print(f"[+] llms.txt: {src} ({len(text):,} chars)")

    tree = parse_llms_hier(text, root)
    sections = select_sections(tree, docs_prefix, root)

    excludes = [re.compile(p, re.I) for p in args.exclude]
    dropped = [s for s in sections if any(x.search(s) for x in excludes)]
    sections = {s: p for s, p in sections.items() if s not in dropped}
    if dropped:
        print(f"[*] Excluded sections: {', '.join(dropped)}")

    # Dedupe by URL across sections (changelog etc. can be listed twice).
    # Canonical form strips the trailing slash — sitemap URLs carry one,
    # llms.txt URLs don't, and the same page must not land twice.
    canon = lambda u: u.rstrip("/")
    seen_urls = set()
    plan = []  # (section_slug, title, url, filename)
    for section, pages in sections.items():
        slug = kebab(section)
        used = set()
        for title, url in pages:
            if canon(url) in seen_urls:
                continue
            seen_urls.add(canon(url))
            fname = page_filename(slug, url, docs_prefix)
            base, i = fname, 2
            while fname in used:
                fname = base[:-3] + f"-{i}.md"
                i += 1
            used.add(fname)
            plan.append((section, slug, title, url, fname))

    # Orphan sweep: docs URLs in the sitemap that llms.txt never listed.
    excluded_slugs = {kebab(s) for s in dropped}
    slug_by_name = {kebab(s): s for s in sections}
    used_by_slug = {}
    for _sec, _slug, _t, _u, _f in plan:
        used_by_slug.setdefault(_slug, set()).add(_f)
    for u in try_sitemap_urls(args.url, docs_prefix):
        if canon(u) in seen_urls or urlparse(u).path.rstrip("/") == docs_prefix:
            continue
        rel = urlparse(u).path[len(docs_prefix):].strip("/")
        first = rel.split("/")[0] if rel else ""
        slug = ORPHAN_URL_MAP.get("/" + rel) or ORPHAN_SEGMENT_MAP.get(first)
        if slug is None and first in slug_by_name:
            slug = first  # e.g. /docs/migration/... -> the migration/ section
        if slug is None or slug in excluded_slugs or slug not in slug_by_name:
            print(f"    [orphan-unfiled] {u}  (no section mapping — NOT skipped silently)")
            continue
        seen_urls.add(canon(u))
        fname = page_filename(slug, u, docs_prefix)
        used = used_by_slug.setdefault(slug, set())
        base, i = fname, 2
        while fname in used:
            fname = base[:-3] + f"-{i}.md"
            i += 1
        used.add(fname)
        plan.append((slug_by_name[slug], slug, fname[:-3], u, fname))
        print(f"    [orphan] {slug}/{fname}  <-  sitemap-only page")

    print(f"[+] Plan: {len(sections)} sections, {len(plan)} pages")
    for section, slug, title, url, fname in plan:
        print(f"    {slug}/{fname}  <-  {title}")
    if args.dry_run:
        return

    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    browser = LazyBrowser()
    manifest = {"source": args.url, "llms_txt": src, "sections": {}}
    ok = fail = 0
    total = len(plan)
    for i, (section, slug, title, url, fname) in enumerate(plan, 1):
        sdir = outdir / slug
        sdir.mkdir(parents=True, exist_ok=True)
        content, tier = None, None
        raw = try_raw_markdown(url)
        if raw:
            content, tier = raw, "raw-md"
        else:
            content = fetch_via_http(url)
            if content:
                tier = "http"
            else:
                content = browser.fetch(url)
                if content:
                    tier = "render"
        if not content:
            print(f"[{i}/{total}] FAILED  {slug}/{fname}  ({url})")
            fail += 1
            continue
        (sdir / fname).write_text(content.rstrip() + "\n", encoding="utf-8")
        manifest["sections"].setdefault(section, []).append(
            {"title": title, "file": f"{slug}/{fname}", "url": url, "tier": tier}
        )
        ok += 1
        print(f"[{i}/{total}] {tier:7} {slug}/{fname}")
    browser.close()

    # INDEX.md + manifest.json at the root — the router-skill on-ramp.
    idx = [f"# {outname} — docs index\n", f"Source: {args.url}  ", f"Export: {src}\n"]
    for section, entries in manifest["sections"].items():
        idx.append(f"\n## {section}\n")
        for e in entries:
            idx.append(f"- [{e['title']}]({e['file']}) — {e['url']}")
    (outdir / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    zip_path = str(outdir) + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for r, _, files in os.walk(outdir):
            for f in files:
                full = os.path.join(r, f)
                zf.write(full, os.path.relpath(full, outdir.parent))
    print(f"[+] Done: {ok} ok, {fail} failed, {len(sections)} sections")
    print(f"[+] Zipped: {zip_path}")


if __name__ == "__main__":
    main()
