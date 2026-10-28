"""Replay the current overlay without some of its hold clears, for tests of the hold logic.

Kenny's 28 Oct 2026 answers cleared nearly every held stock, so the live inventory no longer has an
example of each hold class. These tests rebuild the overlay as it stood before the named records,
in a temporary file, and point the parser at it. The canonical overlay is never changed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine import inventory_parser


def use_overlay_without(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, record_ids: dict[str, str | None]) -> None:
    """Drop each successor record in ``record_ids`` and restore the held record it superseded.

    ``None`` means the successor superseded no overlay record (it retired a V5 stock row), so the
    V5 row comes back as it was.
    """
    path = inventory_parser.CURRENT_USER_INVENTORY_OVERLAY_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["records"] = [r for r in payload["records"] if r["record_id"] not in record_ids]
    restored = {old for old in record_ids.values() if old}
    payload["superseded_record_ids"] = [i for i in payload["superseded_record_ids"] if i not in restored]
    replayed = tmp_path / path.name
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    replayed.write_text(text, encoding="utf-8")
    monkeypatch.setattr(inventory_parser, "CURRENT_USER_INVENTORY_OVERLAY_PATH", replayed)
    # The materialization cache keys on these files, so the replayed overlay gets its own entry.
    monkeypatch.setattr(
        inventory_parser,
        "_USER_OVERLAY_CHAIN_PATHS",
        tuple(replayed if p == path else p for p in inventory_parser._USER_OVERLAY_CHAIN_PATHS),
    )
    monkeypatch.setattr(
        inventory_parser,
        "CURRENT_USER_INVENTORY_OVERLAY_SHA256",
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )
