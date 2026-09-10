"""Certify the deterministic, shadow-only SolForge vertical slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.perception.complexity_registry import ModuleState, load_complexity_registry
from engine.solforge.governance import verify_gate_foundation_receipt


class VerticalSliceVerificationError(RuntimeError):
    """The shadow vertical slice cannot issue a valid acceptance receipt."""


VERTICAL_SLICE_AUTHORITY_FLAGS = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "scientific": False,
    "sensory": False,
}

_V1 = "configs/complexity/complexity_module_registry_v1.json"
_V2 = "configs/complexity/complexity_module_registry_v2.json"
_V3 = "configs/complexity/complexity_module_registry_v3.json"
_GATE_RECEIPT = "data/governance/solforge_gate_foundation_acceptance_v2.json"
_FIXTURE = "tests/fixtures/solforge/vertical_slice_cases_v1.json"
_FIXTURE_HASH = "tests/fixtures/solforge/vertical_slice_cases_v1.sha256"

_SOLFORGE_TESTS = (
    "tests/test_solforge_architectural_adapter.py",
    "tests/test_solforge_backend_export.py",
    "tests/test_solforge_contracts.py",
    "tests/test_solforge_evidence_adapters.py",
    "tests/test_solforge_gate_foundation_integration.py",
    "tests/test_solforge_gate_foundation_receipt.py",
    "tests/test_solforge_gate_preflight.py",
    "tests/test_solforge_hypotheses.py",
    "tests/test_solforge_orchestrator.py",
    "tests/test_solforge_runtime_isolation.py",
    "tests/test_solforge_vertical_slice.py",
    "tests/test_solforge_vertical_slice_receipt.py",
)

_DEPENDENCY_TESTS = (
    "tests/test_architectural_delta.py",
    "tests/test_complexity_inventory.py",
    "tests/test_complexity_registry.py",
    "tests/test_complexity_registry_v3.py",
    "tests/test_hedonic_evidence_gate_v2.py",
    "tests/test_intervention_recommend_solforge.py",
    "tests/test_interventions.py",
    "tests/test_pipeline_interventions.py",
    "tests/test_preference.py",
    "tests/test_scoped_preference.py",
    "tests/test_temporal_sensory_evidence.py",
)

VERTICAL_SLICE_FILES = (
    "backend/poetry.lock",
    "backend/pyproject.toml",
    "backend/app/schemas/lab.py",
    "backend/app/schemas/solforge.py",
    "backend/tests/test_solforge_schemas.py",
    _V1,
    _V2,
    _V3,
    _GATE_RECEIPT,
    "engine/evidence_contracts.py",
    "engine/hedonic_evidence.py",
    "engine/perception/architectural_delta.py",
    "engine/perception/complexity_inventory.py",
    "engine/perception/complexity_registry.py",
    "engine/preference.py",
    "engine/sensory/ledger.py",
    "engine/sensory/order_balance.py",
    "engine/solforge/__init__.py",
    "engine/solforge/adapters.py",
    "engine/solforge/contracts.py",
    "engine/solforge/governance.py",
    "engine/solforge/hypotheses.py",
    "engine/solforge/orchestrator.py",
    "engine/solforge/vertical_slice_verifier.py",
    "scripts/intervention_recommend.py",
    _FIXTURE,
    _FIXTURE_HASH,
    *_SOLFORGE_TESTS,
)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repository_commit(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    commit = result.stdout.strip().lower()
    if result.returncode or len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise VerticalSliceVerificationError("repository commit is unavailable")
    return commit


def _commit_is_ancestor(project_root: Path, commit: object) -> bool:
    if not isinstance(commit, str) or len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        return False
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=project_root,
        capture_output=True,
        check=False,
        timeout=10,
    )
    return result.returncode == 0


def _registry_census(project_root: Path) -> tuple[dict[str, object], tuple[str, ...]]:
    registry_path = project_root / _V3
    registry = load_complexity_registry(project_root, registry_path)
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    runtime = sorted(
        module.module_id for module in registry.modules if module.runtime_eligible
    )
    unauthorized_imports = sorted(
        module.module_id
        for module in registry.modules
        if module.state is not ModuleState.ADMITTED_RUNTIME
        and module.import_path is not None
    )
    issues: list[str] = []
    if runtime:
        issues.append("SolForge or replacement modules are runtime eligible")
    if unauthorized_imports:
        issues.append("non-admitted modules expose runtime imports")
    if payload.get("authority_flags") != {
        "compounding": False,
        "formula": False,
        "hedonic": False,
        "purchase": False,
        "release": False,
        "safety": False,
        "scientific": False,
        "sensory": False,
    }:
        issues.append("registry authority flags are not closed")
    census = {
        "schema_version": registry.schema_version,
        "base_registry_chain": payload.get("base_registry_chain"),
        "runtime_eligible": runtime,
        "unauthorized_imports": unauthorized_imports,
        "states": {
            module_id: registry.module_by_id(module_id).state.value
            for module_id in (
                "architectural-delta-engine",
                "temporal-sensory-ledger",
                "hedonic-preference-learner",
                "solforge-shadow-orchestrator",
            )
        },
        "authority_flags": payload.get("authority_flags"),
    }
    return census, tuple(issues)


def _vertical_slice_census(
    project_root: Path,
) -> tuple[dict[str, object], tuple[str, ...]]:
    fixture_path = project_root / _FIXTURE
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    sidecar = (project_root / _FIXTURE_HASH).read_text(encoding="utf-8").split()
    observed_hash = _file_sha256(fixture_path)
    cases = fixture.get("cases")
    issues: list[str] = []
    if len(sidecar) < 2 or sidecar[0] != observed_hash:
        issues.append("vertical slice fixture sidecar hash mismatch")
    if not isinstance(cases, list) or len(cases) != 4:
        issues.append("vertical slice must contain exactly four cases")
        cases = []
    by_id = {
        item.get("case_id"): item for item in cases if isinstance(item, dict)
    }
    expected_ids = (
        "ZERO_CITRUS_NO_CHANGE",
        "NEROLI_SUPPORT_BRIDGE",
        "ONE_PRECISE_MUSK",
        "HABANOLIDE_ROMANDOLIDE_FACTORIAL",
    )
    if tuple(item.get("case_id") for item in cases) != expected_ids:
        issues.append("vertical slice case identities or order changed")
    factorial = by_id.get("HABANOLIDE_ROMANDOLIDE_FACTORIAL", {})
    expected_arms = [
        "CONTROL",
        "HABANOLIDE",
        "ROMANDOLIDE",
        "HABANOLIDE_X_ROMANDOLIDE",
    ]
    if factorial.get("expected_arm_ids") != expected_arms:
        issues.append("factorial arm contract is incomplete")
    if fixture.get("authority_flags") != {
        "compounding": False,
        "hedonic": False,
        "physical_execution": False,
        "purchase": False,
        "release": False,
        "safety": False,
        "sensory": False,
    }:
        issues.append("vertical slice fixture authority flags are not closed")
    census = {
        "fixture_sha256": observed_hash,
        "case_count": len(cases),
        "case_ids": [item.get("case_id") for item in cases],
        "decisions": {
            str(item.get("case_id")): item.get("expected_decision") for item in cases
        },
        "factorial": {
            "arm_ids": factorial.get("expected_arm_ids"),
            "constant_total_verified": not issues
            and "tests/test_solforge_vertical_slice.py" in _SOLFORGE_TESTS,
        },
        "test_only_authority": fixture.get("authority_flags"),
    }
    return census, tuple(issues)


def _run_command(command: list[str], project_root: Path) -> dict[str, object]:
    environment = dict(os.environ)
    environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    result = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        check=False,
        timeout=300,
    )
    stdout = result.stdout.encode("utf-8")
    stderr = result.stderr.encode("utf-8")
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout_sha256": sha256_hex(stdout),
        "stderr_sha256": sha256_hex(stderr),
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _run_checks(project_root: Path) -> tuple[dict[str, object], ...]:
    temp_parent = project_root / ".tmp-solforge-slice-verifier"
    temp_parent.mkdir(exist_ok=True)
    root_temp = Path(tempfile.mkdtemp(prefix="root-", dir=temp_parent))
    backend_temp = Path(tempfile.mkdtemp(prefix="backend-", dir=temp_parent))
    root_tests = tuple(dict.fromkeys((*_SOLFORGE_TESTS, *_DEPENDENCY_TESTS)))
    ruff_files = tuple(path for path in VERTICAL_SLICE_FILES if path.endswith(".py"))
    commands = (
        [
            sys.executable,
            "-m",
            "pytest",
            *root_tests,
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(root_temp),
        ],
        [
            "poetry",
            "-C",
            "backend",
            "run",
            "pytest",
            "tests/test_solforge_schemas.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(backend_temp),
        ],
        [sys.executable, "-m", "ruff", "check", *ruff_files],
        ["git", "diff", "--check", "--", *VERTICAL_SLICE_FILES],
    )
    return tuple(_run_command(command, project_root) for command in commands)


def _required_hashes(project_root: Path) -> dict[str, str]:
    missing = [path for path in VERTICAL_SLICE_FILES if not (project_root / path).is_file()]
    if missing:
        raise VerticalSliceVerificationError(
            "missing required vertical-slice file: " + ", ".join(missing)
        )
    return {path: _file_sha256(project_root / path) for path in VERTICAL_SLICE_FILES}


def verify_vertical_slice(
    project_root: Path,
    *,
    output_path: Path,
) -> dict[str, object]:
    """Run fixed checks and write one canonical non-authoritative receipt."""

    project_root = Path(project_root).resolve()
    preflight = verify_gate_foundation_receipt(project_root)
    if not preflight.ready:
        raise VerticalSliceVerificationError("; ".join(preflight.blockers))
    registry_census, registry_issues = _registry_census(project_root)
    slice_census, slice_issues = _vertical_slice_census(project_root)
    if registry_issues or slice_issues:
        raise VerticalSliceVerificationError("; ".join((*registry_issues, *slice_issues)))
    checks = _run_checks(project_root)
    failures = [check for check in checks if check.get("exit_code") != 0]
    if failures:
        failed_command = failures[0].get("command", [])
        raise VerticalSliceVerificationError(
            "verification command failed: " + " ".join(map(str, failed_command))
        )
    core = {
        "schema_version": "solforge_vertical_slice_acceptance_v1",
        "repository_commit": _repository_commit(project_root),
        "gate_foundation_acceptance_sha256": preflight.acceptance_sha256,
        "file_sha256": _required_hashes(project_root),
        "checks": list(checks),
        "registry_census": registry_census,
        "vertical_slice_census": slice_census,
        "authority_flags": dict(VERTICAL_SLICE_AUTHORITY_FLAGS),
    }
    receipt = {
        "acceptance_core": core,
        "acceptance_sha256": sha256_hex(canonical_json_bytes(core)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    issues = validate_vertical_slice_receipt(project_root, receipt)
    if issues:
        raise VerticalSliceVerificationError("; ".join(issues))
    output = Path(output_path)
    if not output.is_absolute():
        output = project_root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def validate_vertical_slice_receipt(
    project_root: Path,
    receipt: object,
) -> tuple[str, ...]:
    """Return every integrity issue found in a vertical-slice receipt."""

    project_root = Path(project_root).resolve()
    if not isinstance(receipt, dict) or not isinstance(
        receipt.get("acceptance_core"), dict
    ):
        return ("receipt or acceptance_core is malformed",)
    core: dict[str, Any] = receipt["acceptance_core"]
    issues: list[str] = []
    if core.get("schema_version") != "solforge_vertical_slice_acceptance_v1":
        issues.append("schema version is invalid")
    if core.get("authority_flags") != VERTICAL_SLICE_AUTHORITY_FLAGS:
        issues.append("authority flags are not the required all-false mapping")
    file_hashes = core.get("file_sha256")
    if not isinstance(file_hashes, dict) or set(file_hashes) != set(
        VERTICAL_SLICE_FILES
    ):
        issues.append("required file hash set does not match")
    else:
        for relative, expected in file_hashes.items():
            path = project_root / relative
            if not path.is_file() or _file_sha256(path) != expected:
                issues.append(f"file hash mismatch: {relative}")
    checks = core.get("checks")
    if not isinstance(checks, list) or not checks:
        issues.append("verification checks are missing")
    elif any(
        not isinstance(check, dict) or check.get("exit_code") != 0
        for check in checks
    ):
        issues.append("one or more verification commands failed")
    preflight = verify_gate_foundation_receipt(project_root)
    if not preflight.ready:
        issues.append("Gate Foundation receipt is stale")
    elif core.get("gate_foundation_acceptance_sha256") != preflight.acceptance_sha256:
        issues.append("Gate Foundation acceptance SHA-256 mismatch")
    try:
        registry_census, registry_issues = _registry_census(project_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        registry_census, registry_issues = {}, ("registry census failed",)
    if registry_issues or core.get("registry_census") != registry_census:
        issues.append("registry census mismatch")
    try:
        slice_census, slice_issues = _vertical_slice_census(project_root)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        slice_census, slice_issues = {}, ("vertical slice census failed",)
    if slice_issues or core.get("vertical_slice_census") != slice_census:
        issues.append("vertical slice census mismatch")
    if not _commit_is_ancestor(project_root, core.get("repository_commit")):
        issues.append("receipt commit is not an ancestor of HEAD")
    expected_acceptance = sha256_hex(canonical_json_bytes(core))
    if receipt.get("acceptance_sha256") != expected_acceptance:
        issues.append("acceptance SHA-256 mismatch")
    return tuple(issues)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    verify_vertical_slice(args.project_root, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "VERTICAL_SLICE_AUTHORITY_FLAGS",
    "VERTICAL_SLICE_FILES",
    "VerticalSliceVerificationError",
    "validate_vertical_slice_receipt",
    "verify_vertical_slice",
]
