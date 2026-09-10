from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.gate_foundation import GATE_FOUNDATION_FILES
from engine.solforge.governance import (
    GATE_FOUNDATION_RECEIPT_PATH,
    verify_gate_foundation_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = GATE_FOUNDATION_RECEIPT_PATH


def _copy_gate_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    for relative in (*GATE_FOUNDATION_FILES, RECEIPT.as_posix()):
        source = ROOT / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return project


def _rewrite_receipt(project: Path, mutate) -> None:
    path = project / RECEIPT
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    payload["acceptance_sha256"] = sha256_hex(
        canonical_json_bytes(payload["acceptance_core"])
    )
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_current_gate_foundation_receipt_is_ready() -> None:
    result = verify_gate_foundation_receipt(ROOT)
    assert result.ready is True
    assert result.blockers == ()
    assert result.acceptance_sha256 == "83b64ef4d72cd7b6117e61e689519061dbb1fe3abcd62f6de4044ff6ee3e4182"


def test_solforge_refuses_missing_receipt(tmp_path: Path) -> None:
    result = verify_gate_foundation_receipt(tmp_path)
    assert result.ready is False
    assert result.blockers == ("Gate Foundation receipt is missing",)


def test_solforge_refuses_malformed_receipt(tmp_path: Path) -> None:
    path = tmp_path / RECEIPT
    path.parent.mkdir(parents=True)
    path.write_text("{", encoding="utf-8")
    result = verify_gate_foundation_receipt(tmp_path)
    assert result.ready is False
    assert result.blockers == ("Gate Foundation receipt is malformed JSON",)


def test_solforge_refuses_stale_gate_foundation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _copy_gate_fixture(tmp_path)
    (project / "engine/hedonic_evidence.py").write_text("changed", encoding="utf-8")
    monkeypatch.setattr("engine.solforge.governance._commit_is_ancestor", lambda *_: True)
    result = verify_gate_foundation_receipt(project)
    assert result.ready is False
    assert "file hash mismatch: engine/hedonic_evidence.py" in result.blockers


def test_solforge_refuses_changed_test_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _copy_gate_fixture(tmp_path)
    (project / "tests/test_evidence_contracts.py").write_text("changed", encoding="utf-8")
    monkeypatch.setattr("engine.solforge.governance._commit_is_ancestor", lambda *_: True)
    result = verify_gate_foundation_receipt(project)
    assert "file hash mismatch: tests/test_evidence_contracts.py" in result.blockers


def test_solforge_refuses_failed_recorded_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _copy_gate_fixture(tmp_path)
    _rewrite_receipt(
        project,
        lambda payload: payload["acceptance_core"]["checks"][0].update(exit_code=1),
    )
    monkeypatch.setattr("engine.solforge.governance._commit_is_ancestor", lambda *_: True)
    result = verify_gate_foundation_receipt(project)
    assert "one or more verification commands failed" in result.blockers


def test_solforge_refuses_wrong_repository_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _copy_gate_fixture(tmp_path)
    monkeypatch.setattr("engine.solforge.governance._commit_is_ancestor", lambda *_: False)
    result = verify_gate_foundation_receipt(project)
    assert "receipt commit is not an ancestor of HEAD" in result.blockers


def test_solforge_refuses_any_true_authority_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _copy_gate_fixture(tmp_path)
    _rewrite_receipt(
        project,
        lambda payload: payload["acceptance_core"]["authority_flags"].update(
            release=True
        ),
    )
    monkeypatch.setattr("engine.solforge.governance._commit_is_ancestor", lambda *_: True)
    result = verify_gate_foundation_receipt(project)
    assert "authority flags are not the required all-false mapping" in result.blockers
