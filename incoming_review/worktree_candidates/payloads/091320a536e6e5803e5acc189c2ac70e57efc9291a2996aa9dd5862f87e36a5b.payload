from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.solforge.gate_foundation import (
    ACCEPTANCE_AUTHORITY_FLAGS,
    GATE_FOUNDATION_FILES,
    GateFoundationVerificationError,
    validate_gate_foundation_receipt,
    verify_gate_foundation,
)

ROOT = Path(__file__).resolve().parents[1]


def test_verifier_writes_a_canonical_hash_bound_receipt(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._run_checks",
        lambda project_root: (
            {"command": ["test"], "exit_code": 0, "stdout_sha256": "a" * 64},
        ),
    )
    output = tmp_path / "receipt.json"
    receipt = verify_gate_foundation(ROOT, output_path=output)
    persisted = json.loads(output.read_text(encoding="utf-8"))
    assert persisted == receipt
    assert receipt["acceptance_core"]["authority_flags"] == (
        ACCEPTANCE_AUTHORITY_FLAGS
    )
    assert len(receipt["acceptance_sha256"]) == 64
    assert "generated_at_utc" in receipt
    assert "generated_at_utc" not in receipt["acceptance_core"]
    assert validate_gate_foundation_receipt(ROOT, receipt) == ()


def test_validation_rejects_missing_or_changed_source_hash(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._run_checks",
        lambda project_root: (
            {"command": ["test"], "exit_code": 0, "stdout_sha256": "a" * 64},
        ),
    )
    receipt = verify_gate_foundation(ROOT, output_path=tmp_path / "receipt.json")
    source_hashes = receipt["acceptance_core"]["file_sha256"]
    source_hashes.pop(next(iter(source_hashes)))
    assert "required file hash set does not match" in validate_gate_foundation_receipt(
        ROOT, receipt
    )


def test_validation_rejects_failed_command(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._run_checks",
        lambda project_root: (
            {"command": ["test"], "exit_code": 1, "stdout_sha256": "a" * 64},
        ),
    )
    with pytest.raises(GateFoundationVerificationError, match="command failed"):
        verify_gate_foundation(ROOT, output_path=tmp_path / "receipt.json")


def test_validation_rejects_true_authority_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._run_checks",
        lambda project_root: (
            {"command": ["test"], "exit_code": 0, "stdout_sha256": "a" * 64},
        ),
    )
    receipt = verify_gate_foundation(ROOT, output_path=tmp_path / "receipt.json")
    receipt["acceptance_core"]["authority_flags"]["release"] = True
    assert any(
        "authority flags" in issue
        for issue in validate_gate_foundation_receipt(ROOT, receipt)
    )


def test_source_census_rejects_nonzero_active_hedonic_weight(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._run_checks",
        lambda project_root: (
            {"command": ["test"], "exit_code": 0, "stdout_sha256": "a" * 64},
        ),
    )
    monkeypatch.setattr(
        "engine.solforge.gate_foundation._source_census",
        lambda project_root: ("nonzero active hedonic weight",),
    )
    with pytest.raises(
        GateFoundationVerificationError, match="nonzero active hedonic weight"
    ):
        verify_gate_foundation(ROOT, output_path=tmp_path / "receipt.json")


def test_required_hash_set_covers_gate_foundation_source_and_tests() -> None:
    assert "engine/evidence_contracts.py" in GATE_FOUNDATION_FILES
    assert "engine/pipeline/oav_evidence.py" in GATE_FOUNDATION_FILES
    assert "engine/hedonic_evidence.py" in GATE_FOUNDATION_FILES
    assert "engine/pipeline/release_evidence.py" in GATE_FOUNDATION_FILES
    assert "tests/test_solforge_gate_foundation_integration.py" in (
        GATE_FOUNDATION_FILES
    )
