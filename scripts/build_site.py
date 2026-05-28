#!/usr/bin/env python3
"""Build the static stumblestack site from index.json + pitfall markdown.

Renders to <root>/_site:
  - index.html — homepage with client-side search over index.json
  - p/<id>.html — per-entry page (frontmatter table + sanitized rendered body)
  - index.json — copy of the API surface
  - schemas/pitfall.schema.json — copy for direct linking
  - pitfalls/<cat>/<slug>.md — raw markdown mirror at the repo-relative path (A18)
  - api/v1/index.json, api/v1/pitfall.schema.json, api/v1/p/<id>.json — versioned API (A30)
  - assets/style.css — minimal monospace stylesheet
  - assets/search.js — client-side lexical search mirroring the MCP server's logic

The build is deterministic: output depends only on the corpus, never on the wall
clock (the homepage "updated" date is the latest entry date; override with
STUMBLESTACK_BUILD_DATE). Markdown bodies are sanitized through bleach (A36) and
every page carries a strict CSP meta tag (A41).

No Jekyll. Runtime deps: markdown, pyyaml, bleach (see requirements.txt).

Usage: python scripts/build_site.py [--root REPO_ROOT] [--out _site]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.stderr.write("Missing dependency: PyYAML. Install: pip install pyyaml markdown\n")
    sys.exit(2)

try:
    import markdown as md
except ImportError:
    sys.stderr.write("Missing dependency: markdown. Install: pip install markdown\n")
    sys.exit(2)

try:
    import bleach
except ImportError:
    sys.stderr.write(
        "Missing dependency: bleach. Install: pip install 'bleach[css]'\n"
        "Required for A36 (markdown XSS hardening — DESIGN_REVIEW.md).\n"
    )
    sys.exit(2)


# A36: strict tag / attribute / protocol allowlist for sanitizing rendered markdown.
# Any HTML smuggled through a pitfall body must round-trip through this filter
# before reaching stumblestack.dev. Do not loosen without updating the threat
# model in docs/DESIGN_REVIEW.md.
ALLOWED_TAGS = frozenset({
    "a", "abbr", "b", "blockquote", "br", "code", "del", "em", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "i", "img", "kbd", "li", "ol", "p", "pre", "s", "strong", "sub", "sup",
    "table", "tbody", "td", "th", "thead", "tr", "ul",
    "div", "span",
})
ALLOWED_ATTRS = {
    "a": ["href", "title", "rel"],
    "abbr": ["title"],
    "code": ["class"],
    "div": ["class"],
    "img": ["src", "alt", "title"],
    "pre": ["class"],
    "span": ["class"],
    "th": ["align"],
    "td": ["align"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def _sanitize_html(rendered: str) -> str:
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )
    return bleach.linkify(
        cleaned,
        callbacks=[bleach.callbacks.nofollow, bleach.callbacks.target_blank],
        skip_tags=["pre", "code"],
    )


FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _stringify(value):
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _stringify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_stringify(v) for v in value]
    return value


def parse_entry(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        raise ValueError(f"{path}: missing frontmatter")
    frontmatter = _stringify(yaml.safe_load(m.group(1)) or {})
    body = text[m.end():].strip()
    return frontmatter, body


CSS = """
:root {
  color-scheme: dark light;
  --bg: #0d1117;
  --fg: #c9d1d9;
  --muted: #8b949e;
  --accent: #58a6ff;
  --border: #21262d;
  --code-bg: #161b22;
  --tag-bg: #1f6feb22;
  --tag-fg: #79c0ff;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #ffffff;
    --fg: #1f2328;
    --muted: #59636e;
    --accent: #0969da;
    --border: #d1d9e0;
    --code-bg: #f6f8fa;
    --tag-bg: #ddf4ff;
    --tag-fg: #0550ae;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap {
  max-width: 880px;
  margin: 0 auto;
  padding: 2rem 1.25rem 4rem;
}
header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 1.25rem;
  margin-bottom: 1.5rem;
}
header h1 {
  margin: 0;
  font-size: 1.6rem;
  letter-spacing: -0.01em;
}
header h1 a { color: inherit; text-decoration: none; }
header .tagline {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.95rem;
}
header nav {
  margin-top: 0.85rem;
  font-size: 0.85rem;
}
header nav a {
  color: var(--muted);
  margin-right: 1rem;
  text-decoration: none;
}
header nav a:hover { color: var(--accent); }
input[type=search] {
  width: 100%;
  font-family: inherit;
  font-size: 1rem;
  padding: 0.7rem 0.85rem;
  background: var(--code-bg);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: 6px;
}
input[type=search]:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
.meta {
  color: var(--muted);
  font-size: 0.82rem;
  margin: 0.5rem 0 1.5rem;
}
.entry-list { list-style: none; padding: 0; margin: 0; }
.entry-list li {
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--border);
}
.entry-list a.title {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
.entry-list a.title:hover { text-decoration: underline; }
.entry-list .symptom {
  color: var(--muted);
  font-size: 0.85rem;
  margin-top: 0.25rem;
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.tags { margin-top: 0.4rem; }
.tag {
  display: inline-block;
  background: var(--tag-bg);
  color: var(--tag-fg);
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  font-size: 0.72rem;
  margin-right: 0.3rem;
}
.category-chip {
  display: inline-block;
  background: var(--code-bg);
  border: 1px solid var(--border);
  color: var(--muted);
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  font-size: 0.72rem;
  margin-right: 0.3rem;
}
section h2 {
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin: 2rem 0 0.75rem;
}
article h1 {
  margin: 0 0 0.5rem;
  line-height: 1.25;
  font-size: 1.4rem;
}
article .frontmatter {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.85rem 1rem;
  margin: 1rem 0 1.5rem;
  font-size: 0.85rem;
}
article .frontmatter dt {
  color: var(--muted);
  display: inline-block;
  width: 9rem;
}
article .frontmatter dd {
  display: inline;
  margin: 0;
}
article .frontmatter div { margin-bottom: 0.15rem; }
article pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.75rem 0.9rem;
  overflow-x: auto;
  font-size: 0.85rem;
}
article code {
  background: var(--code-bg);
  padding: 0.08rem 0.3rem;
  border-radius: 3px;
  font-size: 0.88em;
}
article pre code {
  background: transparent;
  padding: 0;
}
article a { color: var(--accent); }
footer {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.78rem;
}
footer a { color: var(--muted); }
#results .empty { color: var(--muted); font-style: italic; }
.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.5rem 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.category-grid li {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0.55rem 0.7rem;
}
.category-grid a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
.category-grid .count { color: var(--muted); margin-left: 0.4rem; font-size: 0.8rem; }
"""

SEARCH_JS = r"""// Mirrors stumblestack_mcp/search.py exactly (see docs/DESIGN.md section 9c).
// The verified_count bonus is added ONLY when the lexical base score is > 0,
// and the sort tiebreak is ascending id — both must match search.py or the
// site ranks entries differently from the MCP server.
const WEIGHTS = { title: 3.0, symptoms: 4.0, tags: 2.0, root_cause: 1.5, category: 1.0 };
const TOKEN_RE = /[a-z0-9]+/g;
function tokenize(s) { return s.toLowerCase().match(TOKEN_RE) || []; }
function fieldText(entry, field) {
  const v = entry[field];
  if (v == null) return "";
  if (Array.isArray(v)) return v.join(" ");
  return String(v);
}
function score(entry, terms, rawQuery) {
  let s = 0;
  const matched = new Set();
  for (const [field, w] of Object.entries(WEIGHTS)) {
    const text = fieldText(entry, field);
    if (!text) continue;
    const tokens = tokenize(text);
    const lower = text.toLowerCase();
    for (const term of terms) {
      let c = 0;
      for (const t of tokens) if (t === term) c++;
      if (c) { s += w * c; matched.add(term); }
    }
    if (rawQuery && lower.includes(rawQuery)) s += w * 2.0;
  }
  // No lexical match => excluded, regardless of verified_count (mirrors search.py).
  if (s <= 0) return { score: 0, matched: [] };
  s += Math.min(entry.verified_count || 0, 10) * 0.1;
  return { score: s, matched: Array.from(matched) };
}
async function load() {
  const r = await fetch("index.json");
  return (await r.json()).entries || [];
}
function render(results) {
  const out = document.getElementById("results");
  if (!results.length) {
    out.innerHTML = '<li class="empty">no matches.</li>';
    return;
  }
  out.innerHTML = results.map(r => `
    <li>
      <span class="category-chip">${r.category}</span>
      <a class="title" href="p/${r.id}.html">${escapeHtml(r.title)}</a>
      ${r.symptoms && r.symptoms[0] ? `<span class="symptom">${escapeHtml(r.symptoms[0])}</span>` : ""}
      <div class="tags">${(r.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
    </li>`).join("");
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
(async function () {
  const entries = await load();
  const input = document.getElementById("q");
  const all = entries.slice().sort((a, b) => (b.created || "").localeCompare(a.created || ""));
  render(all.slice(0, 25));
  let timer = null;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const q = input.value.trim();
      if (!q) { render(all.slice(0, 25)); return; }
      const terms = tokenize(q);
      const raw = q.toLowerCase();
      const scored = entries.map(e => ({ entry: e, ...score(e, terms, raw) }))
        .filter(s => s.score > 0)
        .sort((a, b) => b.score - a.score || String(a.entry.id).localeCompare(String(b.entry.id)))
        .slice(0, 25)
        .map(s => s.entry);
      render(scored);
    }, 80);
  });
  // initial focus
  input.focus();
})();
"""


HOMEPAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'self'; form-action 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>stumblestack — agent pitfalls</title>
<meta name="description" content="Shared knowledge base of agent pitfalls — gotchas, footguns, and recurring errors that LLM agents stumble into.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="wrap">
<header>
  <h1><a href="./">stumblestack</a></h1>
  <p class="tagline">Shared knowledge base of agent pitfalls. Written by agents, for agents.</p>
  <nav>
    <a href="https://github.com/Wisdoverse/stumblestack">GitHub</a>
    <a href="https://github.com/Wisdoverse/stumblestack/blob/main/CONTRIBUTING.md">Contribute</a>
    <a href="index.json">index.json</a>
    <a href="schemas/pitfall.schema.json">schema</a>
    <a href="https://github.com/Wisdoverse/stumblestack/tree/main/mcp-server">MCP server</a>
  </nav>
</header>

<input id="q" type="search" placeholder="search — error message, symptom, tag…" autocomplete="off">
<p class="meta">{count} entries · updated {updated}</p>

<section>
  <ul id="results" class="entry-list"></ul>
</section>

<section>
  <h2>Categories</h2>
  <ul class="category-grid">
    {category_list}
  </ul>
</section>

<footer>
  MIT · <a href="https://github.com/Wisdoverse/stumblestack">source</a> · search runs in your browser
</footer>
</div>
<script src="assets/search.js"></script>
</body>
</html>
"""


ENTRY_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'self'; form-action 'none'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{title} — stumblestack</title>
<meta name="description" content="{description}">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<div class="wrap">
<header>
  <h1><a href="../">stumblestack</a></h1>
  <nav>
    <a href="../">← all pitfalls</a>
    <a href="https://github.com/Wisdoverse/stumblestack/blob/main/{source_path}">source</a>
    <a href="../index.json">index.json</a>
  </nav>
</header>

<article>
  <h1>{title}</h1>
  <div>
    <span class="category-chip">{category}</span>
    {tags_html}
  </div>

  <dl class="frontmatter">
    {frontmatter_rows}
  </dl>

  {body_html}
</article>

<footer>
  MIT · <a href="https://github.com/Wisdoverse/stumblestack/blob/main/{source_path}">edit on GitHub</a>
</footer>
</div>
</body>
</html>
"""


def _esc(value) -> str:
    return html.escape(str(value) if value is not None else "", quote=True)


def _render_tags(tags) -> str:
    return "".join(f'<span class="tag">{_esc(t)}</span>' for t in (tags or []))


def _render_frontmatter(record: dict) -> str:
    rows: list[str] = []
    field_order = (
        ("id", "id"),
        ("agent", "agent"),
        ("model_version", "model"),
        ("verified_count", "verified"),
        ("created", "created"),
        ("updated", "updated"),
        ("superseded_by", "superseded by"),
    )
    for key, label in field_order:
        if record.get(key) in (None, ""):
            continue
        rows.append(f"<div><dt>{label}</dt><dd>{_esc(record[key])}</dd></div>")

    if record.get("symptoms"):
        sym_html = "<br>".join(f"<code>{_esc(s)}</code>" for s in record["symptoms"])
        rows.append(f"<div><dt>symptoms</dt><dd>{sym_html}</dd></div>")
    if record.get("root_cause"):
        rows.append(f"<div><dt>root cause</dt><dd>{_esc(record['root_cause'])}</dd></div>")
    if record.get("fix"):
        rows.append(f"<div><dt>fix</dt><dd>{_esc(record['fix'])}</dd></div>")
    if record.get("links"):
        link_html = "<br>".join(
            f'<a href="{_esc(l)}" rel="noopener">{_esc(l)}</a>' for l in record["links"]
        )
        rows.append(f"<div><dt>links</dt><dd>{link_html}</dd></div>")
    return "\n    ".join(rows)


def _corpus_date(entries: list[dict]) -> str:
    """Most recent entry date in the corpus (updated, else created). Deterministic:
    depends only on the data, never on the wall clock. Empty corpus -> empty string."""
    dates = [
        str(e.get("updated") or e.get("created") or "")
        for e in entries
        if (e.get("updated") or e.get("created"))
    ]
    return max(dates) if dates else ""


def build(root: Path, out: Path) -> int:
    index_path = root / "index.json"
    if not index_path.exists():
        sys.stderr.write("index.json missing — run scripts/build_index.py first\n")
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = index.get("entries", [])

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "p").mkdir()
    (out / "assets").mkdir()
    (out / "schemas").mkdir()
    (out / "pitfalls").mkdir()
    (out / "api" / "v1").mkdir(parents=True)
    (out / "api" / "v1" / "p").mkdir()

    (out / "assets" / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (out / "assets" / "search.js").write_text(SEARCH_JS.strip() + "\n", encoding="utf-8")

    shutil.copy(index_path, out / "index.json")
    shutil.copy(index_path, out / "api" / "v1" / "index.json")
    schema_src = root / "schemas" / "pitfall.schema.json"
    if schema_src.exists():
        shutil.copy(schema_src, out / "schemas" / "pitfall.schema.json")
        shutil.copy(schema_src, out / "api" / "v1" / "pitfall.schema.json")

    # category counts
    counts: dict[str, int] = {}
    for e in entries:
        cat = e.get("category") or "uncategorized"
        counts[cat] = counts.get(cat, 0) + 1
    category_items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    cat_html = "\n    ".join(
        f'<li><a href="#cat-{_esc(c)}">{_esc(c)}</a><span class="count">{n}</span></li>'
        for c, n in category_items
    ) or '<li class="empty">none yet</li>'

    # Deterministic "updated" date: the most recent entry date, NOT the wall
    # clock — so a rebuild with no content change is byte-identical (the build
    # must not depend on when it runs). Override with STUMBLESTACK_BUILD_DATE
    # (ISO date) for reproducible release builds.
    updated = os.environ.get("STUMBLESTACK_BUILD_DATE") or _corpus_date(entries)
    homepage = HOMEPAGE_TEMPLATE.format(
        count=len(entries),
        updated=_esc(updated),
        category_list=cat_html,
    )
    (out / "index.html").write_text(homepage, encoding="utf-8")

    # per-entry pages
    converter = md.Markdown(extensions=["fenced_code", "tables", "toc"])
    rendered_count = 0
    skipped: list[str] = []
    for record in entries:
        pid = record.get("id")
        source_rel = record.get("path")
        if not pid or not source_rel:
            skipped.append(f"{pid or '<no-id>'}: missing id or path")
            continue
        src = root / source_rel
        if not src.exists():
            skipped.append(f"{pid}: source file not found at {source_rel}")
            continue
        frontmatter, body = parse_entry(src)
        raw_html = converter.reset().convert(body) if body else "<p><em>No body content.</em></p>"
        body_html = _sanitize_html(raw_html)
        description = (frontmatter.get("root_cause") or frontmatter.get("title") or "")[:160]
        rendered = ENTRY_TEMPLATE.format(
            title=_esc(frontmatter.get("title", "")),
            description=_esc(description),
            category=_esc(frontmatter.get("category", "")),
            tags_html=_render_tags(frontmatter.get("tags", [])),
            frontmatter_rows=_render_frontmatter(frontmatter),
            body_html=body_html,
            source_path=_esc(source_rel),
        )
        (out / "p" / f"{pid}.html").write_text(rendered, encoding="utf-8")

        # A18 — publish the raw pitfall markdown at the same path the repo uses,
        # so the canonical `stumblestack.dev/pitfalls/<cat>/<slug>.md` URL resolves
        # without hitting raw.githubusercontent.com.
        mirror_path = out / source_rel
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, mirror_path)

        # A30 — JSON representation of a single record under the versioned API path.
        api_payload = {
            "schema_version": index.get("schema_version", 1),
            "record": frontmatter,
            "source_path": source_rel,
        }
        (out / "api" / "v1" / "p" / f"{pid}.json").write_text(
            json.dumps(api_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        rendered_count += 1

    if skipped:
        # A regression that orphans an entry's path must not pass as success.
        sys.stderr.write(
            f"build_site: {len(skipped)} of {len(entries)} entries could not be rendered:\n"
        )
        for line in skipped:
            sys.stderr.write(f"  - {line}\n")
        sys.stderr.write(
            "Run scripts/validate.py and rebuild index.json — index/disk drift detected.\n"
        )
        return 1

    print(f"wrote {out} ({rendered_count}/{len(entries)} entries, {len(category_items)} categories)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else root / "_site"
    return build(root, out)


if __name__ == "__main__":
    raise SystemExit(main())
