"""Fail-closed checks for the V15 full-objective completion handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.calibration.hashing import stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
AUDIT = (
    ROOT / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_AUDIT_V15_20260816.json"
)
PLAN = ROOT / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_PLAN_V15_20260816.md"
LEDGER = (
    ROOT
    / "output/quarantine/COMPLEX_PERFUMERY_FULL_OBJECTIVE_COMPLETION_SHA256SUMS_V15_20260816.txt"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load() -> dict[str, object]:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def test_v15_completion_audit_self_hash_and_global_holds() -> None:
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


def test_v15_parent_bytes_and_receipt_pins_are_exact() -> None:
    audit = _load()
    for entry in audit["parent_evidence"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["byte_size"]
        assert _sha256(path) == entry["sha256"]
        payload = None
        if "semantic_receipt_sha256" in entry:
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["semantic_receipt_sha256"] == entry["semantic_receipt_sha256"]
        if "receipt_sha256" in entry:
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["receipt_sha256"] == entry["receipt_sha256"]


def test_v15_collection_advances_without_native_or_formula_authority() -> None:
    audit = _load()
    assert audit["current_collection_state"]["exact_outer_candidate_lower_bound"] == 49
    assert audit["current_collection_state"]["denominator_complete"] is False
    assert audit["new_v15_package"]["strict_receipt_status"] == "VERIFIED_QUARANTINED"
    assert audit["new_v15_package"]["canonical_formula_selected"] is False
    assert audit["new_v15_package"]["active_dose_authority"] is False
    assert audit["new_v15_package"]["promotion_allowed"] is False

    native = audit["native_implementation_state"]
    assert native["migration_0017_required"] is False
    assert native["new_schema_required"] is False
    assert native["new_truth_store_required"] is False
    assert native["new_pipeline_script_required"] is False
    assert native["package_code_install_allowed"] is False
    assert native["package_formula_import_allowed"] is False


def test_v15_pending_card_blockers_and_ledger_replay() -> None:
    audit = _load()
    pending = audit["pending_source_card"]
    assert pending["sha256"] == "f4be1041bb8e2e8b5665962e580aa740996bd2f77b61299cca1d3cdf55014a5d"
    assert pending["counted_as_exact_outer_candidate"] is False
    assert pending["authority"] is False

    expected = {
        "8dd04ea6c69e5e3bd72b03e0ae15cb66ad66e9ac5581cf97666249e869c5a998",
        "e9e325bea9117dbe2a97ff67e77d57705a54244591278fac7a34915a7f0ae523",
        "8224f8a1609deb22b43651da825b9bf653a92143f00ee1d5d592130d162f97db",
        "582ae9902e47807f085a61b7add113c9239a2860445e8171fcf569b3ad6d28c5",
    }
    assert {item["sha256"] for item in audit["blocking_parent_bytes"]} == expected

    lines = [line for line in LEDGER.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) == 9
    for line in lines:
        sha256, byte_size, relative_path = line.split("\t")
        path = ROOT / relative_path
        assert path.stat().st_size == int(byte_size)
        assert _sha256(path) == sha256

    plan = PLAN.read_text(encoding="utf-8")
    assert "EXACT_COLLECTION_49" in plan
    assert "Global installation and release | Not achieved" in plan
