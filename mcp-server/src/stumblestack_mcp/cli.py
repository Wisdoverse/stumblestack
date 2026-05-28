"""stumblestack command-line interface.

Subcommands:
  search   lexical search over the corpus (same ranker as the MCP server)
  get      print one pitfall by id
  new      print a frontmatter template for a new pitfall (pipe to a file)
  lint     validate the local checkout (delegates to scripts/validate.py)
  submit   build + (optionally) open a PR for a new pitfall

All reads honor the same env config as the MCP server (STUMBLESTACK_REPO,
STUMBLESTACK_MIRRORS, STUMBLESTACK_REMOTE, STUMBLESTACK_TTL). `submit` needs
GITHUB_TOKEN for a live (non-dry-run) submission.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .search import search
from .source import StumblestackSource
from .submit import SubmitError
from .submit import build as build_submission
from .submit import submit as submit_call

TEMPLATE = """\
---
id: {id}
title: "TODO: <system> <fails-when>"
category: TODO-kebab
tags:
  - TODO
symptoms:
  - "TODO: verbatim error or observable behavior"
root_cause: "TODO: one-sentence mechanism"
fix: "TODO: concrete corrective action"
verified_count: 0
created: {today}
---

## Reproduction

TODO: brief steps.

## Correct usage

TODO: minimal corrected example.
"""


def _source() -> StumblestackSource:
    return StumblestackSource.from_env()


def cmd_search(args: argparse.Namespace) -> int:
    src = _source()
    try:
        hits = search(src.entries(), args.query, category=args.category,
                      top_k=args.top_k, model=args.model)
    finally:
        src.close()
    if args.json:
        print(json.dumps([{"id": h.entry.get("id"), "title": h.entry.get("title"),
                           "category": h.entry.get("category"), "score": round(h.score, 3)}
                          for h in hits], indent=2))
    else:
        if not hits:
            print("no matches.")
        for h in hits:
            e = h.entry
            print(f"[{e.get('category','?')}] {e.get('title','')}")
            print(f"    id={e.get('id')}  score={round(h.score,3)}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    src = _source()
    try:
        record, body = src.entry_body(args.id)
    except KeyError:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    finally:
        src.close()
    print(json.dumps(record, indent=2) if args.json else body)
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    import uuid
    from datetime import date
    print(TEMPLATE.format(id=uuid.uuid4(), today=date.today().isoformat()))
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    # Single source of truth: delegate to scripts/validate.py in the checkout.
    repo = Path(args.root).resolve() if args.root else _find_repo()
    validator = repo / "scripts" / "validate.py"
    if not validator.exists():
        print(f"lint requires a stumblestack checkout; not found under {repo}", file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(validator), "--root", str(repo)]).returncode


def _find_repo() -> Path:
    # Walk up from CWD looking for scripts/validate.py.
    here = Path.cwd()
    for parent in (here, *here.parents):
        if (parent / "scripts" / "validate.py").exists():
            return parent
    return here


def cmd_submit(args: argparse.Namespace) -> int:
    src = _source()
    try:
        fix_code = None
        if args.fix_code:
            fix_code = {"code": args.fix_code}
            if args.fix_code_lang:
                fix_code["language"] = args.fix_code_lang
        applies_to = {}
        for k, v in (("product", args.product), ("tool", args.tool), ("surface", args.surface)):
            if v:
                applies_to[k] = v
        result = build_submission(
            src,
            title=args.title, category=args.category, tags=args.tag,
            symptoms=args.symptom, root_cause=args.root_cause, fix=args.fix,
            body=None, agent=args.agent, model_version=args.model_version,
            links=args.link, severity=args.severity,
            applies_to=applies_to or None, fix_code=fix_code, aliases=args.alias,
        )
        if result.errors:
            print("invalid pitfall:", file=sys.stderr)
            for e in result.errors:
                line = f"  - {e['field']}: {e['message']}"
                if e.get("suggestion"):
                    line += f"  (hint: {e['suggestion']})"
                print(line, file=sys.stderr)
            return 1
        if args.dry_run:
            print(result.markdown)
            if result.duplicates:
                print("\n# possible duplicates:", file=sys.stderr)
                for d in result.duplicates:
                    print(f"#   {d['id']}  {d['title']} (score {d['score']})", file=sys.stderr)
            return 0
        try:
            out = submit_call(src, result, dry_run=False)
        except SubmitError as exc:
            print(f"submit failed: {exc}", file=sys.stderr)
            return 1
        print(f"opened PR: {out.pr_url}")
        return 0
    finally:
        src.close()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="stumblestack", description="agent-pitfall knowledge base CLI")
    p.add_argument("--version", action="version", version=f"stumblestack {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("search", help="search the corpus")
    s.add_argument("query")
    s.add_argument("--category")
    s.add_argument("--model")
    s.add_argument("--top-k", type=int, default=5)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="print one pitfall by id")
    g.add_argument("id")
    g.add_argument("--json", action="store_true", help="print the index record instead of markdown")
    g.set_defaults(func=cmd_get)

    n = sub.add_parser("new", help="print a new-pitfall template")
    n.set_defaults(func=cmd_new)

    li = sub.add_parser("lint", help="validate the local checkout")
    li.add_argument("--root", help="repo root (default: discover from CWD)")
    li.set_defaults(func=cmd_lint)

    sb = sub.add_parser("submit", help="build/submit a pitfall (dry-run by default)")
    sb.add_argument("--title", required=True)
    sb.add_argument("--category", required=True)
    sb.add_argument("--tag", action="append", default=[], required=True)
    sb.add_argument("--symptom", action="append", default=[], required=True)
    sb.add_argument("--root-cause", required=True)
    sb.add_argument("--fix", required=True)
    sb.add_argument("--agent")
    sb.add_argument("--model-version")
    sb.add_argument("--link", action="append", default=[])
    sb.add_argument("--severity", choices=["blocker", "wrong-output", "wasted-cycles", "minor"])
    sb.add_argument("--product")
    sb.add_argument("--tool")
    sb.add_argument("--surface")
    sb.add_argument("--fix-code")
    sb.add_argument("--fix-code-lang")
    sb.add_argument("--alias", action="append", default=[])
    sb.add_argument("--dry-run", action="store_true", help="preview markdown, do not open a PR")
    sb.set_defaults(func=cmd_submit)

    return p


def cli_main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


def main() -> None:  # console_scripts entry point
    raise SystemExit(cli_main())


if __name__ == "__main__":
    main()
