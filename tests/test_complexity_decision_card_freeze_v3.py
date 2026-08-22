from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_PATH = (
    ROOT
    / "data/governance/complexity_decision_card_candidate_freeze_20260823_v3.json"
)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def test_v3_freeze_binds_complete_inventory_catalog_and_module_bytes() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["schema_version"] == "complexity_decision_card_candidate_freeze_v3"
    assert receipt["inventory_coverage"] == {
        "workbook_sheets_parsed": 18,
        "current_master_records": 280,
        "august_added_materials": 30,
        "advisory_candidates": 35,
        "planned_and_prepare_rows": 4,
        "alias_and_non_equivalence_rows": 45,
    }
    for artifact in receipt["candidate_artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_v3_freeze_preserves_inventory_target_and_authority_firewalls() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))

    assert receipt["inventory_contract"]["target_identity_defined_by_inventory"] is False
    assert receipt["inventory_contract"]["roles_defined_by_inventory"] is False
    assert receipt["inventory_contract"]["hedonic_value_defined_by_inventory"] is False
    assert receipt["inventory_contract"]["advisory_candidate_creates_stock"] is False
    assert receipt["inventory_contract"]["unlisted_material_is_owned"] is False
    assert all(value is False for value in receipt["authority"].values())


def test_v3_freeze_allows_only_exact_prompt_evidence_reuse() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    policy = receipt["benchmark_evidence_reuse_policy"]

    assert policy["allowed"] is True
    assert policy["requires_identical_prompt_sha256"] is True
    assert policy["requires_visible_dom_response_verification"] is True
    assert policy["allows_changed_prompt_reuse"] is False
    assert receipt["predecessor_screen_run"]["verified_responses"] == 16
    assert receipt["predecessor_screen_run"]["clipboard_corrections"] == 3


def test_v3_freeze_semantic_hash_is_exact() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    semantic_hash = receipt.pop("semantic_receipt_sha256")

    assert semantic_hash == hashlib.sha256(canonical_bytes(receipt)).hexdigest()
