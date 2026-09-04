"""Replay the clean-room V19 native design-contract integration receipt."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from engine.calibration.hashing import stable_file_hash, stable_json_hash

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT / "data" / "governance" / "complex_perfumery_v19_native_design_integration_20260817.json"
)


def _load() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_v19_native_integration_receipt_is_semantically_bound() -> None:
    receipt = _load()
    body = deepcopy(receipt)
    expected = body.pop("semantic_receipt_sha256")

    assert expected == stable_json_hash(body)
    assert receipt["state"] == (
        "CLEAN_ROOM_NATIVE_DESIGN_CONTRACTS_INSTALLED_PACKAGE_CONTENT_QUARANTINED"
    )


def test_v19_native_integration_file_hashes_replay() -> None:
    receipt = _load()
    integration = receipt["native_integration"]
    for key in ("clean_room_module", "native_export", "focused_test"):
        artifact = integration[key]
        assert stable_file_hash(ROOT / artifact["path"]) == artifact["sha256"]

    archive = receipt["archive"]
    assert archive["restoration_verified"] is True
    assert stable_file_hash(ROOT / archive["path"]) == archive["archived_sha256"]
    assert archive["source_prechange_sha256"] == archive["archived_sha256"]


def test_v19_installs_only_the_three_nonduplicative_native_contracts() -> None:
    receipt = _load()
    decisions = receipt["integration_decisions"]

    assert [item["decision"] for item in decisions[:3]] == [
        "INTEGRATED_CLEAN_ROOM_NATIVE",
        "INTEGRATED_CLEAN_ROOM_NATIVE",
        "INTEGRATED_CLEAN_ROOM_NATIVE",
    ]
    assert decisions[3]["decision"] == ("REUSE_EXISTING_NATIVE_OWNERS_NO_DUPLICATE_SUBSYSTEM")
    integration = receipt["native_integration"]
    assert integration["canonical_adapter"] == ("engine.pipeline.preflight.FormulaDoseReceipt")
    for field in (
        "new_pipeline_scripts",
        "new_pipeline_owners",
        "new_database_owners",
        "new_writable_persistence_paths",
        "package_modules_imported",
        "package_schemas_imported",
        "package_registries_imported",
        "package_formulas_imported",
        "package_source_ledger_imported",
    ):
        assert integration[field] == 0


def test_v19_chat_failure_and_package_quarantine_are_explicit() -> None:
    receipt = _load()
    chat = receipt["deepluna_chat"]

    assert chat["project_id"] == "perfume-chem-cheapluna-isolated"
    assert chat["preflight_readiness"] == "READY"
    assert chat["open_reserved_nano_usd"] == 0
    assert chat["unknown_reservations"] == 0
    assert len(chat["jobs"]) == 2
    assert {item["execution_status"] for item in chat["jobs"]} == {"CONTRACT_ERROR"}
    assert chat["provider_runs"] == 0
    assert chat["provider_api_calls"] == 0
    assert chat["provider_tokens"] == 0
    assert all(item["promotion_allowed"] is False for item in receipt["source_artifacts"])


def test_v19_native_contracts_do_not_promote_scientific_or_release_authority() -> None:
    receipt = _load()

    assert set(receipt["authority"].values()) == {False}
    boundary = receipt["truth_boundary"]
    assert boundary["design_contracts_installed"] is True
    assert boundary["package_content_installed"] is False
    assert boundary["source_rights_resolved"] is False
    assert boundary["physical_results_created"] == 0
    assert boundary["sensory_results_created"] == 0
    assert boundary["formula_or_inventory_mutations"] == 0
    assert boundary["strict_empirical_oav_created"] is False
    assert boundary["release_state_changed"] is False
