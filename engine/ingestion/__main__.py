"""CLI entrypoint for the ingestion adapter: `python -m engine.ingestion`.

Importable-library invocation via existing command infrastructure — NOT a new
top-level pipeline script (AGENTS.md Rule 2 compliant).
"""

from __future__ import annotations

import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m engine.ingestion",
        description="Generic external reconstruction candidate ingestion adapter",
    )
    parser.add_argument("candidate", help="path to external candidate JSON")
    parser.add_argument(
        "--inventory-snapshot", default=None, help="inventory snapshot id (override)"
    )
    parser.add_argument(
        "--expected-total", type=float, default=None, help="expected formula total parts"
    )
    parser.add_argument(
        "--output-dir", required=True, help="output directory for canonical interchange + reports"
    )
    args = parser.parse_args(argv)

    with open(args.candidate, encoding="utf-8") as f:
        candidate = json.load(f)
    if args.inventory_snapshot:
        candidate["inventory_snapshot_id"] = args.inventory_snapshot

    from .ingest import ingest_external_candidate

    result = ingest_external_candidate(
        candidate, expected_total=args.expected_total, output_dir=args.output_dir
    )
    written = result.write()
    print(
        json.dumps(
            {
                "accepted": result.accepted,
                "candidate_id": result.candidate_id,
                "deterministic_hash": result.candidate_hash,
                "rejections": [r.to_dict() for r in result.rejections],
                "written": written,
            },
            indent=1,
        )
    )
    return 0 if result.accepted else 3


if __name__ == "__main__":
    sys.exit(main())
