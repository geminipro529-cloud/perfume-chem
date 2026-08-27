from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import scripts.scientific_truth_inventory as inventory
from engine.evidence_contracts import canonical_json_bytes, sha256_hex

ROOT = Path(__file__).resolve().parents[1]
BASELINE_COMMIT = "e3101a3c44b32b5993255c47dffd5a0baa5252b7"
BASELINE_BRANCH = "codex/complex-perfumery-publish"
BASELINE_RECORD = (
    ROOT / "data" / "governance" / "temporal_oav_hedonic_recovery_baseline_v1.json"
)
BASELINE_SIDECAR = BASELINE_RECORD.with_suffix(".sha256")


def _expectation(payload: bytes) -> dict[str, object]:
    return {
        "name": "candidate.md",
        "byte_length": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _build(tmp_path: Path) -> tuple[dict[str, object], Path, dict[str, object]]:
    build = getattr(inventory, "build_recovery_baseline", None)
    assert callable(build), "Task 1 recovery-baseline builder is missing"
    payload = b"exact task-1 source candidate\n"
    candidate = tmp_path / "candidate.md"
    candidate.write_bytes(payload)
    expectation = _expectation(payload)
    record = build(
        ROOT,
        candidate,
        candidate_expectation=expectation,
        repository_commit=BASELINE_COMMIT,
        repository_branch=BASELINE_BRANCH,
    )
    return record, candidate, expectation


def _rehash(record: dict[str, object]) -> dict[str, object]:
    changed = deepcopy(record)
    changed["acceptance_sha256"] = sha256_hex(
        canonical_json_bytes(changed["acceptance_core"])
    )
    return changed


def test_baseline_binds_exact_repository_registry_files_and_boundaries(
    tmp_path: Path,
) -> None:
    record, candidate, expectation = _build(tmp_path)
    core = record["acceptance_core"]

    assert record["schema_version"] == "temporal_oav_hedonic_recovery_baseline_v1"
    assert core["repository"] == {
        "branch": BASELINE_BRANCH,
        "commit": BASELINE_COMMIT,
    }
    assert core["registry"]["schema_version"] == "complexity_module_registry_v5"
    assert core["registry"]["sha256"] == (
        "905fd3e67697e1bac7b2ffd8dc53a14b558fc9bd0595103ea29fba49af8ce2b0"
    )
    assert core["module_dispositions"]["architectural-delta-engine"] == {
        "state": "ADMITTED_RUNTIME",
        "import_path": "engine.perception.architectural_delta",
        "runtime_eligible": True,
    }
    assert core["module_dispositions"]["temporal-sensory-ledger"]["state"] == (
        "RETIRED_BENCHMARK_UNDERPERFORMER"
    )
    assert core["module_dispositions"]["hedonic-preference-learner"]["state"] == (
        "RETIRED_BENCHMARK_UNDERPERFORMER"
    )
    assert core["module_dispositions"]["universal-perceptual-topology-core"][
        "runtime_eligible"
    ] is False
    assert core["module_dispositions"]["wood-depth-model-v2"][
        "runtime_eligible"
    ] is False
    assert len(core["source_files"]) == 8
    assert core["source_candidate"]["exact_bytes_status"] == "VERIFIED"
    assert core["source_candidate"]["disposition"] == "SOURCE_CANDIDATE_ONLY"
    assert set(core["authority_flags"].values()) == {False}
    assert core["boundaries"] == {
        "modeled_oav_is_hedonic_evidence": False,
        "modeled_oav_is_sensory_evidence": False,
        "retained_downstream_artifacts_runtime_installed": False,
        "target_ideal_separate_from_current_inventory": True,
    }
    assert core["preserved_untracked_paths"] == [
        ".tmp-publish-complexity-solforge/",
        ".tmp-publish-registry/",
        ".tmp-solforge-gate-verifier/",
        ".tmp-solforge-slice-verifier/",
    ]

    validate = getattr(inventory, "validate_recovery_baseline", None)
    assert callable(validate), "Task 1 recovery-baseline validator is missing"
    assert validate(
        ROOT,
        record,
        candidate_path=candidate,
        candidate_expectation=expectation,
    ) == ()


def test_baseline_validation_rejects_source_hash_drift(tmp_path: Path) -> None:
    record, candidate, expectation = _build(tmp_path)
    changed = deepcopy(record)
    changed["acceptance_core"]["source_files"][0]["sha256"] = "0" * 64
    issues = inventory.validate_recovery_baseline(
        ROOT,
        _rehash(changed),
        candidate_path=candidate,
        candidate_expectation=expectation,
    )
    assert any("source file census mismatch" in issue for issue in issues)


def test_baseline_validation_rejects_registry_disposition_drift(
    tmp_path: Path,
) -> None:
    record, candidate, expectation = _build(tmp_path)
    changed = deepcopy(record)
    changed["acceptance_core"]["module_dispositions"][
        "temporal-sensory-ledger"
    ]["state"] = "ADMITTED_RUNTIME"
    issues = inventory.validate_recovery_baseline(
        ROOT,
        _rehash(changed),
        candidate_path=candidate,
        candidate_expectation=expectation,
    )
    assert "module disposition census mismatch" in issues


def test_baseline_validation_rejects_authority_or_boundary_promotion(
    tmp_path: Path,
) -> None:
    record, candidate, expectation = _build(tmp_path)
    promoted = deepcopy(record)
    promoted["acceptance_core"]["authority_flags"]["hedonic"] = True
    assert "authority flags are not the required all-false mapping" in (
        inventory.validate_recovery_baseline(
            ROOT,
            _rehash(promoted),
            candidate_path=candidate,
            candidate_expectation=expectation,
        )
    )

    collapsed = deepcopy(record)
    collapsed["acceptance_core"]["boundaries"][
        "target_ideal_separate_from_current_inventory"
    ] = False
    assert "evidence boundaries do not match the frozen policy" in (
        inventory.validate_recovery_baseline(
            ROOT,
            _rehash(collapsed),
            candidate_path=candidate,
            candidate_expectation=expectation,
        )
    )


def test_baseline_validation_fails_closed_on_malformed_candidate(
    tmp_path: Path,
) -> None:
    record, _, _ = _build(tmp_path)
    malformed = deepcopy(record)
    malformed["acceptance_core"]["source_candidate"]["expected_sha256"] = "bad"
    issues = inventory.validate_recovery_baseline(ROOT, _rehash(malformed))
    assert "source candidate record is malformed" in issues


def test_missing_or_mismatched_candidate_remains_unavailable_and_unpromoted(
    tmp_path: Path,
) -> None:
    build = getattr(inventory, "build_recovery_baseline", None)
    assert callable(build), "Task 1 recovery-baseline builder is missing"
    missing = tmp_path / "missing.md"
    expectation = _expectation(b"expected")
    record = build(
        ROOT,
        missing,
        candidate_expectation=expectation,
        repository_commit=BASELINE_COMMIT,
        repository_branch=BASELINE_BRANCH,
    )
    candidate = record["acceptance_core"]["source_candidate"]
    assert candidate["exact_bytes_status"] == "EXACT_BYTES_UNAVAILABLE"
    assert candidate["disposition"] == "SOURCE_CANDIDATE_ONLY"
    assert candidate["observed_sha256"] is None
    assert candidate["blockers"] == ["SOURCE_CANDIDATE_EXACT_BYTES_UNAVAILABLE"]
    assert set(record["acceptance_core"]["authority_flags"].values()) == {False}

    mismatch = tmp_path / "candidate.md"
    mismatch.write_bytes(b"wrong")
    mismatched = build(
        ROOT,
        mismatch,
        candidate_expectation=expectation,
        repository_commit=BASELINE_COMMIT,
        repository_branch=BASELINE_BRANCH,
    )["acceptance_core"]["source_candidate"]
    assert mismatched["exact_bytes_status"] == "EXACT_BYTES_UNAVAILABLE"
    assert mismatched["observed_sha256"] == hashlib.sha256(b"wrong").hexdigest()
    assert mismatched["blockers"] == ["SOURCE_CANDIDATE_EXACT_BYTES_MISMATCH"]


def test_writer_freezes_exact_json_and_sidecar(tmp_path: Path) -> None:
    record, _, _ = _build(tmp_path)
    output = tmp_path / "baseline.json"
    sidecar = tmp_path / "baseline.sha256"
    writer = getattr(inventory, "write_recovery_baseline", None)
    assert callable(writer), "Task 1 recovery-baseline writer is missing"
    writer(record, output, sidecar)

    assert json.loads(output.read_text(encoding="utf-8")) == record
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert sidecar.read_text(encoding="ascii") == f"{digest}  {output.name}\n"
    first_json = output.read_bytes()
    first_sidecar = sidecar.read_bytes()
    writer(record, output, sidecar)
    assert output.read_bytes() == first_json
    assert sidecar.read_bytes() == first_sidecar


def test_direct_script_cli_can_import_engine_registry(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    sidecar = tmp_path / "baseline.sha256"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "scientific_truth_inventory.py"),
            "--repo-root",
            str(ROOT),
            "--recovery-baseline-output",
            str(output),
            "--recovery-baseline-sha-output",
            str(sidecar),
            "--repository-commit",
            BASELINE_COMMIT,
            "--repository-branch",
            BASELINE_BRANCH,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert sidecar.is_file()


def test_committed_recovery_baseline_and_sidecar_validate() -> None:
    record = json.loads(BASELINE_RECORD.read_text(encoding="utf-8"))
    assert inventory.validate_recovery_baseline(ROOT, record) == ()
    digest = hashlib.sha256(BASELINE_RECORD.read_bytes()).hexdigest()
    assert BASELINE_SIDECAR.read_text(encoding="ascii") == (
        f"{digest}  {BASELINE_RECORD.name}\n"
    )
