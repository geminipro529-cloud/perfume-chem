"""Hash-bound verification for the SolForge Gate Foundation."""

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


class GateFoundationVerificationError(RuntimeError):
    """The Gate Foundation cannot issue a valid acceptance receipt."""


ACCEPTANCE_AUTHORITY_FLAGS = {
    "compounding": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
    "universal_preference": False,
}

GATE_FOUNDATION_FILES = (
    "engine/evidence_contracts.py",
    "engine/hedonic_evidence.py",
    "engine/evidence/unsupported_science.py",
    "engine/optimizer/models.py",
    "engine/optimizer/scoring.py",
    "engine/pipeline/oav_evidence.py",
    "engine/pipeline/release_evidence.py",
    "engine/pipeline/release_scoring.py",
    "engine/solforge/gate_foundation.py",
    "scripts/formula_release_gate.py",
    "scripts/scientific_truth_inventory.py",
    "tests/test_evidence_contracts.py",
    "tests/test_oav_evidence_gate_v2.py",
    "tests/test_hedonic_evidence_gate_v2.py",
    "tests/test_release_evidence_gate_v2.py",
    "tests/test_legacy_hedonic_runtime_isolation.py",
    "tests/test_active_scoring_consumers.py",
    "tests/test_formula_release_evidence_cli.py",
    "tests/test_solforge_gate_foundation_integration.py",
    "tests/test_solforge_gate_foundation_receipt.py",
)

_PYTEST_FILES = tuple(
    path for path in GATE_FOUNDATION_FILES if path.startswith("tests/")
) + (
    "tests/test_oav_authority.py",
    "tests/test_release_scoring_contract.py",
    "tests/test_preference.py",
    "tests/test_scoped_preference.py",
    "tests/test_scientific_truth_inventory.py",
    "tests/test_c9_unsupported_science.py",
)

_RUFF_FILES = tuple(
    path
    for path in GATE_FOUNDATION_FILES
    if path.endswith(".py")
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
    if result.returncode or len(commit) != 40:
        raise GateFoundationVerificationError("repository commit is unavailable")
    return commit


def _source_census(project_root: Path) -> tuple[str, ...]:
    issues: list[str] = []
    from engine.family_scorer import FAMILY_WEIGHT_PRESETS
    from engine.optimizer.models import ObjectiveWeights

    if ObjectiveWeights().hedonic != 0:
        issues.append("nonzero active hedonic weight")
    if any(
        profile.hedonic != 0
        for profile in FAMILY_WEIGHT_PRESETS.values()
        if not isinstance(profile, str)
    ):
        issues.append("nonzero family hedonic weight")
    callers: list[str] = []
    legacy_call_token = "score_" + "hedonic("
    for base_name in ("engine", "scripts"):
        for path in (project_root / base_name).rglob("*.py"):
            if legacy_call_token in path.read_text(encoding="utf-8"):
                callers.append(path.relative_to(project_root).as_posix())
    allowed = {
        "engine/hedonic_model.py",
        "engine/optimizer/scoring.py",
        "scripts/verify_c0_physical_model_inventory.py",
    }
    unexpected = sorted(set(callers).difference(allowed))
    if unexpected:
        issues.append("unauthorized score_hedonic callers: " + ", ".join(unexpected))
    return tuple(issues)


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
    temp_parent = project_root / ".tmp-solforge-gate-verifier"
    temp_parent.mkdir(exist_ok=True)
    base_temp = Path(tempfile.mkdtemp(prefix="pytest-", dir=temp_parent))
    commands = (
        [
            sys.executable,
            "-m",
            "pytest",
            *_PYTEST_FILES,
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(base_temp),
        ],
        [sys.executable, "-m", "ruff", "check", *_RUFF_FILES],
        ["git", "diff", "--check", "--", *GATE_FOUNDATION_FILES],
    )
    return tuple(_run_command(command, project_root) for command in commands)


def _acceptance_core(
    project_root: Path,
    checks: tuple[dict[str, object], ...],
) -> dict[str, object]:
    missing = [path for path in GATE_FOUNDATION_FILES if not (project_root / path).is_file()]
    if missing:
        raise GateFoundationVerificationError(
            "missing required Gate Foundation file: " + ", ".join(missing)
        )
    return {
        "schema_version": "solforge_gate_foundation_acceptance_v1",
        "repository_commit": _repository_commit(project_root),
        "file_sha256": {
            path: _file_sha256(project_root / path) for path in GATE_FOUNDATION_FILES
        },
        "checks": list(checks),
        "source_census": {
            "status": "PASS",
            "issues": [],
            "authorized_legacy_replay_only": True,
        },
        "authority_flags": dict(ACCEPTANCE_AUTHORITY_FLAGS),
    }


def verify_gate_foundation(
    project_root: Path,
    *,
    output_path: Path,
) -> dict[str, object]:
    """Run the frozen checks and write a canonical acceptance receipt."""

    project_root = Path(project_root).resolve()
    census_issues = _source_census(project_root)
    if census_issues:
        raise GateFoundationVerificationError("; ".join(census_issues))
    checks = _run_checks(project_root)
    failures = [check for check in checks if check.get("exit_code") != 0]
    if failures:
        failed_command = failures[0].get("command", [])
        raise GateFoundationVerificationError(
            "verification command failed: " + " ".join(map(str, failed_command))
        )
    core = _acceptance_core(project_root, checks)
    receipt = {
        "acceptance_core": core,
        "acceptance_sha256": sha256_hex(canonical_json_bytes(core)),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    issues = validate_gate_foundation_receipt(project_root, receipt)
    if issues:
        raise GateFoundationVerificationError("; ".join(issues))
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


def validate_gate_foundation_receipt(
    project_root: Path,
    receipt: object,
) -> tuple[str, ...]:
    """Return every integrity issue found in a Gate Foundation receipt."""

    project_root = Path(project_root).resolve()
    if not isinstance(receipt, dict) or not isinstance(
        receipt.get("acceptance_core"), dict
    ):
        return ("receipt or acceptance_core is malformed",)
    core: dict[str, Any] = receipt["acceptance_core"]
    issues: list[str] = []
    if core.get("schema_version") != "solforge_gate_foundation_acceptance_v1":
        issues.append("schema version is invalid")
    if core.get("authority_flags") != ACCEPTANCE_AUTHORITY_FLAGS:
        issues.append("authority flags are not the required all-false mapping")
    file_hashes = core.get("file_sha256")
    if not isinstance(file_hashes, dict) or set(file_hashes) != set(
        GATE_FOUNDATION_FILES
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
    verify_gate_foundation(args.project_root, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ACCEPTANCE_AUTHORITY_FLAGS",
    "GATE_FOUNDATION_FILES",
    "GateFoundationVerificationError",
    "validate_gate_foundation_receipt",
    "verify_gate_foundation",
]
