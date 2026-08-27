"""CLI for the LLM response cache.

Subcommands:
    stats                 Aggregate hit rate + estimated savings.
    clear                 Remove cache entries (default: everything older than 0 days).
    inspect               Show recent entries (sorted newest first).

Run from the repository root so ``engine.llm_cache`` resolves.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

# Resolve repo root from this script's location so `engine` imports cleanly
# regardless of the caller's cwd. This matches the convention used by
# scripts/formula_release_gate.py.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engine.llm_cache import (  # noqa: E402
    CACHE_DB,
    clear_cache,
    get_stats,
    inspect_cache,
)


def _parse_older_than(s: str | None) -> int | None:
    if s is None:
        return None
    s = s.strip().lower()
    if s.endswith("d"):
        s = s[:-1]
    try:
        return int(s)
    except ValueError:
        raise SystemExit(f"--older-than expects an integer or 'Nd' form, got: {s!r}")


def cmd_stats(_args: argparse.Namespace) -> int:
    if not CACHE_DB.is_file():
        print(
            json.dumps(
                {
                    "cache_present": False,
                    "cache_path": str(CACHE_DB),
                    "note": "No cache yet — first LLM call will create it.",
                },
                indent=2,
            )
        )
        return 0

    stats = get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    older = _parse_older_than(args.older_than)
    removed = clear_cache(older_than_days=older, model=args.model, provider=args.provider)
    print(
        json.dumps(
            {
                "removed": removed,
                "filters": {
                    "older_than_days": older,
                    "model": args.model,
                    "provider": args.provider,
                },
            },
            indent=2,
        )
    )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    rows = inspect_cache(model=args.model, provider=args.provider, limit=args.limit)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="llm_cache_stats.py",
        description="Local LLM response cache maintenance CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("stats", help="Aggregate cache stats (hit rate, savings).")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("clear", help="Remove cache entries.")
    sp.add_argument(
        "--older-than",
        default=None,
        help="Remove rows older than N days (e.g. '30d' or '30'). Default: 0 (clear everything).",
    )
    sp.add_argument("--model", default=None, help="Restrict to model name.")
    sp.add_argument("--provider", default=None, help="Restrict to provider name.")
    sp.set_defaults(func=cmd_clear)

    sp = sub.add_parser("inspect", help="List recent cache entries (no response bodies).")
    sp.add_argument("--model", default=None, help="Filter by model.")
    sp.add_argument("--provider", default=None, help="Filter by provider.")
    sp.add_argument("--limit", type=int, default=20, help="Number of recent rows.")
    sp.set_defaults(func=cmd_inspect)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
