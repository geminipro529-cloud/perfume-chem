"""Fail-closed checks for the V13 full-objective completion handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.calibration.hashing import stable_json_hash
from tests.historical_snapshots import assert_historical_artifact, historical_replay_status

ROOT = Path(__file__).resolve().parents[1]
AUDIT = (
    ROOT / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_AUDIT_V13_20260816.json"
)
PLAN = ROOT / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_PLAN_V13_20260816.md"
LEDGER = (
    ROOT
    / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_SHA256SUMS_V13_20260816.txt"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load() -> dict[str, object]:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def test_v13_completion_audit_is_self_hashing_and_fail_closed() -> None:
    audit = _load()
    declared = audit.pop("semantic_receipt_sha256")
    assert stable_json_hash(audit) == declared

    original = _load()
    assert original["objective_complete"] is False
    assert original["collection_complete"] is False
    assert original["implementation_complete"] is False
    assert (
        original[
            "implementation_complete_for_authorized_recovered_non_p6_native_scopes_in_current_worktree"
        ]
        is True
    )
    assert original["package_installation_complete"] is False
    assert original["installation_authorized"] is False
    assert original["release_complete"] is False
    assert not any(original["authority"].values())


def test_v13_collection_pins_are_exact_and_unrecovered_g2_sources_stay_held() -> None:
    audit = _load()
    for entry in audit["parent_evidence"]:
        path = ROOT / entry["path"]
        assert_historical_artifact(path, entry["sha256"], entry["byte_size"])

    boundary = audit["g2_native_metadata_boundary"]
    held = set()
    for entry in boundary["files"]:
        path = ROOT / entry["path"]
        status = historical_replay_status(path, entry["sha256"], entry["byte_size"])
        if status == "HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE":
            held.add(entry["path"])
    assert held == {"backend/app/schemas/lab.py", "backend/app/services/lab_service.py"}

    assert audit["current_collection_state"]["v13_sealed_exact_outer_candidate_lower_bound"] == 47
    assert audit["current_collection_state"]["current_exact_outer_candidate_lower_bound"] == 48
    assert audit["current_collection_state"]["defensible_chat_denominator_lower_bound"] == 48
    assert audit["current_collection_state"]["denominator_complete"] is False


def test_v13_preserves_mass_authority_and_external_holds() -> None:
    audit = _load()
    boundary = audit["g2_native_metadata_boundary"]
    assert boundary["metadata_contract_complete"] is True
    assert boundary["physical_preparations_executed"] is False
    assert boundary["canonical_quantity_and_stock_authority"] == (
        "MASS_FRACTION_AND_MASS_INVENTORY_MOVEMENTS_ONLY"
    )
    assert boundary["volume_fraction_stock_creation_allowed"] is False
    assert boundary["mass_volume_conversion_allowed"] is False
    assert boundary["active_dose_or_stock_gate_satisfaction_allowed"] is False

    expected = {
        "f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d",
        "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
        "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
        "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
        "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
    }
    assert {entry["sha256"] for entry in audit["blocking_parent_bytes"]} == expected
    assert audit["current_collection_state"]["source_rights_state"] == "UNKNOWN"
    post_v13 = audit["current_collection_state"]["post_v13_source_delta"]
    assert post_v13["exact_outer_available_outside_repository"]["package_receipt_created"] is False
    assert post_v13["exact_outer_available_outside_repository"]["promotion_allowed"] is False
    assert post_v13["source_only_unrecovered_candidate"]["exact_bytes_available_locally"] is False
    assert audit["verification"]["full_release_verifier"].startswith("KNOWN_TIMEOUT_NOT_PASS")


def test_v13_completion_ledger_preserves_exact_pins_and_explicit_replay_holds() -> None:
    lines = [line for line in LEDGER.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 9
    held = set()
    for line in lines:
        sha256, byte_size, relative_path = line.split("\t")
        path = ROOT / relative_path
        status = historical_replay_status(path, sha256, int(byte_size))
        if status == "HOLD_ORIGINAL_SOURCE_BYTES_UNAVAILABLE":
            held.add(relative_path)
    assert held == {"backend/app/schemas/lab.py", "backend/app/services/lab_service.py"}

    plan = PLAN.read_text(encoding="utf-8")
    assert "RECOVERED_NON_P6_NATIVE_SOFTWARE_SCOPE_COMPLETE" in plan
    assert "package installation is not authorized" in plan
    assert "All source-admission" in plan
