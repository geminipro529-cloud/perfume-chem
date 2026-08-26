from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.vertical_slice_verifier import (
    VERTICAL_SLICE_AUTHORITY_FLAGS,
    VerticalSliceVerificationError,
    validate_vertical_slice_receipt,
    verify_vertical_slice,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _historical_gate_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "engine.solforge.vertical_slice_verifier.verify_gate_foundation_receipt",
        lambda _root: SimpleNamespace(
            ready=True,
            acceptance_sha256="a" * 64,
            blockers=(),
        ),
    )


def _passing_check() -> tuple[dict[str, object], ...]:
    return (
        {
            "command": ["test"],
            "exit_code": 0,
            "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
        },
    )


def _receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(
        "engine.solforge.vertical_slice_verifier._run_checks",
        lambda _project_root: _passing_check(),
    )
    return verify_vertical_slice(ROOT, output_path=tmp_path / "receipt.json")


def _rehash(receipt: dict) -> dict:
    changed = deepcopy(receipt)
    changed["acceptance_sha256"] = sha256_hex(
        canonical_json_bytes(changed["acceptance_core"])
    )
    return changed


def test_verifier_writes_canonical_hash_bound_vertical_slice_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "receipt.json"
    receipt = _receipt(tmp_path, monkeypatch)
    assert json.loads(output.read_text(encoding="utf-8")) == receipt
    assert receipt["acceptance_core"]["authority_flags"] == (
        VERTICAL_SLICE_AUTHORITY_FLAGS
    )
    assert receipt["acceptance_core"]["vertical_slice_census"]["case_count"] == 4
    assert receipt["acceptance_core"]["registry_census"]["runtime_eligible"] == []
    assert validate_vertical_slice_receipt(ROOT, receipt) == ()


def test_verifier_rejects_stale_gate_foundation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "engine.solforge.vertical_slice_verifier.verify_gate_foundation_receipt",
        lambda _root: SimpleNamespace(
            ready=False, acceptance_sha256=None, blockers=("stale gate",)
        ),
    )
    monkeypatch.setattr(
        "engine.solforge.vertical_slice_verifier._run_checks",
        lambda _project_root: _passing_check(),
    )
    with pytest.raises(VerticalSliceVerificationError, match="stale gate"):
        verify_vertical_slice(ROOT, output_path=tmp_path / "receipt.json")


def test_validation_rejects_changed_v3_base_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    receipt["acceptance_core"]["registry_census"]["base_registry_chain"][0][
        "sha256"
    ] = "0" * 64
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert "registry census mismatch" in issues


def test_validation_rejects_changed_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    fixture = "tests/fixtures/solforge/vertical_slice_cases_v1.json"
    receipt["acceptance_core"]["file_sha256"][fixture] = "0" * 64
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert f"file hash mismatch: {fixture}" in issues


def test_verifier_rejects_failed_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "engine.solforge.vertical_slice_verifier._run_checks",
        lambda _project_root: (
            {"command": ["pytest"], "exit_code": 1, "stdout_sha256": "a" * 64},
        ),
    )
    with pytest.raises(VerticalSliceVerificationError, match="verification command failed"):
        verify_vertical_slice(ROOT, output_path=tmp_path / "receipt.json")


def test_validation_rejects_unauthorized_runtime_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    receipt["acceptance_core"]["registry_census"]["runtime_eligible"] = [
        "solforge-shadow-orchestrator"
    ]
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert "registry census mismatch" in issues


def test_validation_rejects_nonconstant_interaction_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    receipt["acceptance_core"]["vertical_slice_census"]["factorial"][
        "constant_total_verified"
    ] = False
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert "vertical slice census mismatch" in issues


def test_validation_rejects_nonzero_authority_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    receipt["acceptance_core"]["authority_flags"]["release"] = True
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert "authority flags are not the required all-false mapping" in issues


def test_validation_rejects_repository_commit_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _receipt(tmp_path, monkeypatch)
    receipt["acceptance_core"]["repository_commit"] = "0" * 40
    issues = validate_vertical_slice_receipt(ROOT, _rehash(receipt))
    assert "receipt commit is not an ancestor of HEAD" in issues
