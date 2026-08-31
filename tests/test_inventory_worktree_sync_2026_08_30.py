import hashlib
import json
from pathlib import Path

import pytest

from engine.inventory_parser import (
    CURRENT_INVENTORY_SNAPSHOT_PATH,
    inventory_counts,
    load_current_inventory_snapshot,
    load_current_user_inventory_overlay,
    parse_inventory,
)
from engine.name_utils import normalize_name

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY = PROJECT_ROOT / "inventory.txt"
AUTHORITY_RECEIPT = (
    PROJECT_ROOT
    / "docs"
    / "research"
    / "INVENTORY_STOCK_AUTHORITY_2026-08-30.md"
)
SYNC_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_worktree_sync_20260830.json"
)
SYNC_SUCCESSOR = (
    PROJECT_ROOT
    / "data"
    / "governance"
    / "inventory_worktree_sync_20260831.json"
)


def _records(*, include_unavailable: bool = True):
    return parse_inventory(
        INVENTORY,
        unique=False,
        include_solvents=True,
        include_unavailable=include_unavailable,
    )


def test_consolidated_inventory_has_declared_stock_row_count():
    assert inventory_counts(INVENTORY)["raw_entries"] == 279


@pytest.mark.parametrize(
    ("name", "dilution"),
    (
        ("Parmavert", 1.0),
        ("Cedrat FCF oil Sicilian", 1.0),
        ("Ambrettolide", 0.10),
        ("Habanolide", 1.0),
        ("Romandolide", 1.0),
        ("Ambrofix Crystals", 1.0),
        ("Diethyl Phthalate", 1.0),
        ("Cinnamon Bark EO - Telvada USDA Organic", 1.0),
    ),
)
def test_reconfirmed_stocks_are_present_and_owned(name, dilution):
    matches = [record for record in _records() if record.name == name]
    assert matches
    assert any(record.status == "owned" for record in matches)
    assert any(record.dilution == pytest.approx(dilution) for record in matches)


def test_evernyl_keeps_owned_and_unprepared_stocks_distinct():
    evernyl = [record for record in _records() if record.name == "Evernyl"]
    crystals = next(row for row in evernyl if row.raw_name.startswith("Evernyl (crystals)"))
    working = next(row for row in evernyl if row.raw_name.startswith("Evernyl (20% w/w in DPG)"))
    planned = next(row for row in evernyl if row.raw_name.startswith("Evernyl (10% w/w in DEP)"))

    assert (crystals.status, crystals.dilution) == ("owned", pytest.approx(1.0))
    assert (working.status, working.dilution, working.fraction_basis, working.carrier) == (
        "owned",
        pytest.approx(0.20),
        "mass_fraction",
        "dpg",
    )
    assert planned.status == "planned_preparation"
    assert planned.execution_ready is False
    assert planned.execution_hold_reason == "NOT_YET_PREPARED"
    assert planned.raw_name not in {
        row.raw_name for row in _records(include_unavailable=False)
    }


@pytest.mark.parametrize(
    ("name", "status"),
    (
        ("Benzyl Salicylate", "not_owned"),
        ("Polysantol", "depleted"),
        ("Nagarmortha Oil", "depleted"),
        ("Gamma Decalactone", "out_of_stock"),
    ),
)
def test_latest_unavailable_and_depleted_authority_is_preserved(name, status):
    row = next(record for record in _records() if record.name == name)
    assert row.status == status
    assert row.execution_ready is False


def test_v7_recovered_working_stocks_remain_w_w_and_carrier_held():
    expected = {
        "Liffarome": 0.10,
        "Cis-3-Hexenyl Salicylate": 0.20,
        "Caryophyllene Acetate": 0.20,
    }
    for name, fraction in expected.items():
        row = next(record for record in _records() if record.name == name)
        assert row.status == "owned"
        assert row.dilution == pytest.approx(fraction)
        assert row.fraction_basis == "mass_fraction"
        assert row.execution_ready is False
        assert row.execution_hold_reason == "CARRIER_UNSPECIFIED"


def test_aliases_do_not_collapse_telvada_into_other_cinnamon_stocks():
    assert normalize_name("Evernyl (20% w/w in DPG)") == "evernyl"
    assert normalize_name("Evernyl (10% w/w in DEP)") == "evernyl"
    assert normalize_name("Cinnamon Bark EO (Telvada)") == (
        "cinnamon bark eo - telvada usda organic"
    )
    assert normalize_name("Cinnamon Bark EO - Telvada USDA Organic (neat)") == (
        "cinnamon bark eo - telvada usda organic"
    )
    assert normalize_name("Cinnamon Bark EO (10%; NYSUPPLY)") != (
        "cinnamon bark eo - telvada usda organic"
    )


def test_existing_hash_pinned_overlay_remains_bound_to_live_inventory():
    overlay = load_current_user_inventory_overlay()
    assert overlay["authority"] == "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY"


def test_pinned_v5_snapshot_accepts_git_checkout_line_endings(tmp_path):
    """The committed LF payload remains identical after a Windows CRLF checkout."""

    committed_bytes = CURRENT_INVENTORY_SNAPSHOT_PATH.read_bytes().replace(
        b"\r\n", b"\n"
    )
    windows_checkout = tmp_path / CURRENT_INVENTORY_SNAPSHOT_PATH.name
    windows_checkout.write_bytes(committed_bytes.replace(b"\n", b"\r\n"))

    payload = load_current_inventory_snapshot(windows_checkout)

    assert payload["authority"] == "CURRENT_INVENTORY_MASTER_V5_EXTERNAL_SNAPSHOT"


def test_sync_manifest_hashes_every_distributed_inventory_file():
    payload = json.loads(SYNC_MANIFEST.read_text(encoding="utf-8"))
    successor = json.loads(SYNC_SUCCESSOR.read_text(encoding="utf-8"))
    assert payload["sync_id"] == "INVENTORY-WORKTREE-SYNC-20260830-001"
    assert successor["sync_id"] == "INVENTORY-WORKTREE-SYNC-20260831-002"
    parent_bytes = SYNC_MANIFEST.read_bytes().replace(b"\r\n", b"\n")
    assert successor["parent"]["sha256"] == hashlib.sha256(parent_bytes).hexdigest()
    superseded = {
        record["path"]: record
        for record in successor["superseded_compatibility_files"]
    }
    for group in (
        "current_authority_files",
        "frozen_evidence_files",
        "compatibility_files",
    ):
        for record in payload[group]:
            replacement = superseded.get(record["path"])
            if replacement is not None:
                assert replacement["prior_sha256"] == record["sha256"]
                continue
            path = PROJECT_ROOT / record["path"]
            content = path.read_bytes()
            if path.suffix.lower() == ".xlsx":
                assert path.stat().st_size == record["size_bytes"]
            else:
                # Git may materialize text as CRLF or LF according to the
                # target worktree's attributes. The committed blob content is
                # authoritative; normalize checkout line endings only for the
                # transport-integrity comparison.
                content = content.replace(b"\r\n", b"\n")
            assert hashlib.sha256(content).hexdigest() == record["sha256"]

    for record in successor["successor_compatibility_files"]:
        path = PROJECT_ROOT / record["path"]
        content = path.read_bytes().replace(b"\r\n", b"\n")
        assert len(content) == record["size_bytes"]
        assert hashlib.sha256(content).hexdigest() == record["sha256"]


def test_authority_receipt_preserves_formula_and_claim_boundaries():
    text = AUTHORITY_RECEIPT.read_text(encoding="utf-8").casefold()
    for phrase in (
        "279 stock rows",
        "do not silently rebase",
        "target / ideal",
        "current-inventory build",
        "not tested / hold",
        "does not inherit",
        "not yet prepared",
    ):
        assert phrase in text
