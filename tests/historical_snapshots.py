"""Test-only exact historical inputs; never rebind live evidence or inventory."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEPTEMBER_COMMIT = "9e501074"


@lru_cache(maxsize=1)
def gin_stock_contract_fixture():
    """Source-confirmed stock contracts for algorithm tests, not live inventory.

    The September text is not recoverable. This fixture therefore makes no
    historical replay claim; temporary test plans bind today's text hash and
    this separately verified stock-contract fixture explicitly.
    """
    from dataclasses import replace

    from engine import inventory_parser as inventory

    base = inventory.materialize_current_inventory(
        apply_user_overlay=False, apply_user_completions=False
    )
    path = inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_PATH
    assert hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == (
        inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256
    )
    overlay = inventory._load_20260908_romandolide_inventory_successor(
        json.loads(path.read_bytes()), require_live_inventory_binding=False
    )
    materialized = inventory._apply_current_user_inventory_overlay(base, overlay)
    return replace(materialized, overlay_sha256=inventory.ROMANDOLIDE_USER_INVENTORY_OVERLAY_SHA256)


def bind_gin_design_test_plan(payload: dict) -> dict:
    """Create fresh test-only inputs; never rebind a canonical design record."""
    materialized = gin_stock_contract_fixture()
    plan = dict(payload)
    plan.update(
        test_fixture="gin-vetiver-stock-contract-test-v1",
        historical_inventory_replay_verified=False,
        inventory_sha256=hashlib.sha256((ROOT / "inventory.txt").read_bytes()).hexdigest(),
        inventory_authority={key: getattr(materialized, key) for key in (
            "source_workbook_sha256", "snapshot_sha256", "overlay_sha256"
        )},
    )
    return plan


def assert_historical_source_pin(relative: str, expected: str, commit: str = SEPTEMBER_COMMIT):
    """Verify an original source pin against a frozen Git object, not today's code."""
    raw = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)
    variants = (raw, raw.replace(b"\r\n", b"\n"),
                raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    assert any(hashlib.sha256(item).hexdigest() == expected for item in variants), relative


@lru_cache(maxsize=128)
def historical_source_bytes(relative: str, expected: str) -> bytes:
    """Recover original source bytes only when an unchanged pin verifies them."""
    current = ROOT / relative
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == expected:
        return current.read_bytes()
    revisions = subprocess.check_output(
        ["git", "log", "--format=%H", "-100", "--", relative], cwd=ROOT, text=True
    ).splitlines()
    for revision in revisions:
        result = subprocess.run(["git", "show", f"{revision}:{relative}"], cwd=ROOT,
                                capture_output=True, check=False)
        if result.returncode:
            continue
        raw = result.stdout
        for candidate in (raw, raw.replace(b"\r\n", b"\n"),
                          raw.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")):
            if hashlib.sha256(candidate).hexdigest() == expected:
                return candidate
    raise AssertionError(f"Pinned historical source bytes unavailable: {relative} ({expected})")


def assert_historical_artifact(path: Path, expected: str, size: int | None = None):
    raw = historical_source_bytes(path.relative_to(ROOT).as_posix(), expected)
    assert hashlib.sha256(raw).hexdigest() == expected
    if size is not None:
        assert len(raw) == size


def historical_replay_status(path: Path, expected: str, size: int | None = None) -> str:
    """Verify original bytes, or an exact reviewed HOLD; never imply replay passed."""
    try:
        assert_historical_artifact(path, expected, size)
    except AssertionError:
        review = json.loads((ROOT / "data/governance/historical_source_replay_review_20261007.json").read_bytes())
        assert review["schema_version"] == "historical-source-replay-review-v1"
        assert review["decision"] == "HOLD_HISTORICAL_REPLAY_INCOMPLETE"
        assert review["historical_receipts_modified"] is False
        assert review["current_runtime_accepted_by_this_review"] is False
        assert not any(review["authority"].values())
        rows = [row for row in review["missing_sources"]
                if row["path"] == path.relative_to(ROOT).as_posix()
                and row["original_sha256"] == expected]
        assert len(rows) == 1, "Missing source pin has no exact replay-HOLD review"
        row = rows[0]
        assert row["state"] == "HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE"
        if size is not None:
            assert row["original_size_bytes"] == size
        assert path.stat().st_size == row["current_size_bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["current_sha256"]
        parent = next(item for item in review["parent_records"]
                      if item["path"] == row["parent_path"])
        assert hashlib.sha256((ROOT / parent["path"]).read_bytes()).hexdigest() == parent["sha256"]
        return row["state"]
    return "EXACT_ORIGINAL_BYTES_VERIFIED"


def copy_referenced_artifacts(destination: Path, sources: list[Path]) -> None:
    """Clone only locally referenced artifacts; never substitute current inventory."""
    pending = list(sources)
    visited = set()
    while pending:
        source = pending.pop()
        if source in visited:
            continue
        visited.add(source)
        target = destination / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if source.suffix != ".json":
            continue
        try:
            value = json.loads(source.read_bytes())
        except ValueError:
            continue

        def visit(item):
            if isinstance(item, str):
                # Prose strings are not paths; Linux raises OSError (ENAMETOOLONG)
                # on very long names, so probe only plausible candidates.
                if "\n" in item or len(item.encode("utf-8")) > 240:
                    return
                try:
                    path = (ROOT / item).resolve()
                    is_candidate = (path.is_relative_to(ROOT) and path.is_file()
                                    and path != ROOT / "inventory.txt")
                except OSError:
                    return
                if is_candidate:
                    pending.append(path)
            elif isinstance(item, dict):
                for child in item.values():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)
        visit(value)


def copy_checkpoint_snapshot(destination: Path) -> Path:
    """Clone referenced artifacts into test scratch without changing any pin."""
    copy_referenced_artifacts(
        destination, list((ROOT / "data/governance").glob("lavande_ambre_profond_*.json"))
    )
    inventory = destination / "inventory.txt"
    raw = (ROOT / "tests/fixtures/checkpoint_inventory_20260926.txt").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == (
        "1b4324da5a35cebe8c59959e58276d84ac8f2f0e0e6f3239fdef0a4250d8df71"
    )
    inventory.write_bytes(raw)
    return inventory


def copy_august_inventory_snapshot(destination: Path, sources: list[Path]) -> None:
    """Reconstruct the exact August text, retaining the original trailing space."""
    copy_referenced_artifacts(destination, sources)
    for source in sources:
        if source.suffix != ".json":
            continue
        payload = json.loads(source.read_bytes())
        if not isinstance(payload, dict):
            continue
        for parent in payload.get("parents", []):
            if parent["path"] == "inventory.txt":
                continue
            target = destination / parent["path"]
            if hashlib.sha256(target.read_bytes()).hexdigest() != parent["sha256"]:
                try:
                    raw = historical_source_bytes(parent["path"], parent["sha256"])
                except AssertionError:
                    assert historical_replay_status(ROOT / parent["path"], parent["sha256"],
                                                    parent["size_bytes"]) == (
                        "HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE"
                    )
                else:
                    target.write_bytes(raw)
    source = ROOT / "backend/tests/fixtures/inventory_v5_delta_20260811/inventory.txt"
    text = source.read_text(encoding="utf-8")
    needle = "- Myristic Acid Powder\n"
    assert text.count(needle) == 1
    raw = text.replace(needle, "- Myristic Acid Powder \n").replace("\n", "\r\n").encode()
    assert len(raw) == 17140
    assert hashlib.sha256(raw).hexdigest() == (
        "dc3c7ffc6e27711aa38d26bd3aef09b7046f1834353e7171eb78729fbd2cc4ec"
    )
    (destination / "inventory.txt").write_bytes(raw)
