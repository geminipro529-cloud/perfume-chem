"""Build the perfumery knowledge SQLite database (``data/perfumery_kb.db``).

The database is a generated artifact and is gitignored (``*.db``). Run this on a
fresh clone / CI before knowledge-base tests or rule queries that read the live
DB. ``tests/conftest.py`` also provisions it automatically when missing.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build data/perfumery_kb.db from source stores.")
    parser.add_argument(
        "--db",
        default=str(ROOT / "data" / "perfumery_kb.db"),
        help="output database path",
    )
    args = parser.parse_args(argv)

    from engine.kb_migrate import migrate

    path = migrate(args.db)
    print(f"built {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
