from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.ingredient_catalog import write_ingredient_catalog


def main() -> int:
    path = write_ingredient_catalog()
    payload = json.loads(path.read_text(encoding="utf-8"))
    count = len(payload.get("ingredients", []))
    print(f"WROTE {path}")
    print(f"INGREDIENTS {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
