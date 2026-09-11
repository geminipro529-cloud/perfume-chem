"""Merge PerfumersWorld supplier fields into material_properties.json.

Idempotent; safe to re-run after any PW intake refresh. The generator
(``_generate_material_properties.py``) also calls the same merge so a full
regeneration preserves these fields.

Usage:
    python scripts/merge_pw_supplier_data.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.knowledge.pw_supplier import PW_FIELD_NAMES, merge_pw_supplier_fields  # noqa: E402

MP_PATH = ROOT / "data" / "knowledge_graph" / "material_properties.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=str(MP_PATH))
    args = parser.parse_args(argv)

    path = Path(args.path)
    entries = json.loads(path.read_text(encoding="utf-8"))
    stats = merge_pw_supplier_fields(entries)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")

    coverage = {
        field: sum(1 for e in entries if e.get(field) is not None)
        for field in PW_FIELD_NAMES
    }
    print(f"entries={stats['entries']} matched={stats['matched']} pw_records={stats['pw_records']}")
    for field, count in coverage.items():
        print(f"  {field}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
