from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.formula_release_gate import (
    current_repository_evidence_hashes,
    validate_pipeline_analysis_artifact,
)
from scripts.verify_d0_claim_matrix import (
    EXPECTED_CONTROL_SHA256,
    build_gate_payload,
)
from tests.historical_snapshots import assert_historical_artifact

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT / "data" / "governance" / "complex_perfumery_v6_verifier_reconciliation_20260812.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_sha256(payload: dict[str, object]) -> str:
    canonical = dict(payload)
    canonical.pop("semantic_self_sha256", None)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _receipt() -> dict[str, object]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def test_v6_verifier_reconciliation_is_self_hashing_and_parent_pinned() -> None:
    receipt = _receipt()
    assert receipt["semantic_self_sha256"] == _semantic_sha256(receipt)
    for parent in receipt["parents"]:
        path = ROOT / parent["path"]
        assert path.is_file()
        assert_historical_artifact(path, parent["sha256"], parent["byte_size"])


def test_v6_reconciliation_preserves_the_byte_pinned_d0_quarantine() -> None:
    receipt = _receipt()
    formula = ROOT / "formulas" / "Prada_LHomme_Architecture_Control_30mL_EdT.md"
    assert _sha256(formula) == EXPECTED_CONTROL_SHA256
    assert receipt["rebind_review"]["write_performed"] is False
    assert receipt["rebind_review"]["formula_file_mutated"] is False
    assert receipt["rebind_review"]["d0_binding_mutated"] is False

    gate = build_gate_payload(ROOT)
    assert gate["status"] == "PASS"
    assert gate["formula_bindings"][0]["sha256"] == EXPECTED_CONTROL_SHA256
    assert gate["study_authorized"] is False
    assert gate["release_authority"] is False
    assert gate["scientific_outcome"] == "unmeasured"


def test_v6_reconciliation_replays_the_single_explicit_artifact_hold() -> None:
    receipt = _receipt()
    formula = ROOT / "formulas" / "Prada_LHomme_Architecture_Control_30mL_EdT.md"
    result = validate_pipeline_analysis_artifact(
        formula,
        repository_hashes=current_repository_evidence_hashes(),
    )
    expected = receipt["diagnosis"]["artifact_verify"]["sole_blocker"]
    # The immutable report retains the old invalid artifact diagnosis. The
    # current formula intentionally has no executable analysis attachment.
    assert expected["status"] == "TAMPERED"
    assert result["status"] == "QUARANTINED"
    assert result["artifact_binding_status"] == "STALE"
    assert result["quarantine_explicit"] is True
    assert result["release_authority"] is False


def test_v6_reconciliation_resolves_timeout_without_inflating_authority() -> None:
    receipt = _receipt()
    diagnosis = receipt["diagnosis"]
    assert diagnosis["isolated_golden_explicit_solvent"]["status"] == "PASS"
    assert diagnosis["focused_contract_replay"]["passed"] == 95
    assert diagnosis["quick_project_verify"] == {
        "status": "FAIL",
        "completed": True,
        "timed_out": False,
        "elapsed_seconds": 43.22,
        "stderr_bytes": 0,
        "failed_checks": ["formula-artifact-validation"],
    }

    decision = receipt["decision"]
    assert decision["timeout_diagnosis_resolved"] is True
    assert decision["v6_remains_current_collection_state"] is True
    assert decision["optional_identities_remaining"] == 4
    assert decision["p6_exact_parent_bytes_remaining"] == 2
    assert decision["implementation_complete"] is False
    assert decision["package_installation_complete"] is False
    assert decision["release_complete"] is False
    assert all(value is False for value in receipt["authority"].values())


def test_v6_reconciliation_records_no_package_or_repository_expansion() -> None:
    receipt = _receipt()
    decision = receipt["decision"]
    assert decision["migration_required"] is False
    assert decision["new_truth_store_created"] is False
    assert decision["new_pipeline_script_created"] is False
    assert decision["package_code_installed"] is False
    assert decision["formula_or_build_mutated"] is False
    assert decision["inventory_or_stock_mutated"] is False
    assert decision["physical_execution_authorized"] is False
