"""Bounded, machine-readable verification for the Laboratory Beta baseline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import venv
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.error import URLError
from urllib.request import urlopen

from engine.odor_thresholds import ODT_VERIFICATION
from engine.release_readiness import ReadinessInput, build_release_readiness
from engine.science_audit import build_science_audit_contract

PROJECT_ROOT = Path(__file__).resolve().parents[1]

KNOWN_LEGACY_LIMITATIONS = (
    "Full-engine Ruff cleanup remains legacy debt; the canonical truth-core slice is blocking.",
    "Compatibility requests may omit the finished solvent matrix; strict mode requires it, and headspace remains modeled rather than measured.",
    "Temporal evolution is heuristic and is not calibrated to skin or blotter measurements.",
    "Longevity, sillage, receptor activation, and emotion outputs remain unsupported; preference fits remain UNKNOWN until held-out validation passes.",
    "Composite natural OAV is olfactory headspace evidence, not regulatory constituent composition.",
)

_ENGINE_TEST_SHARDS = {
    "truth-core": (
        "tests/test_artifact_rebind.py",
        "tests/test_authority_gates.py",
        "tests/test_bottle_addition.py",
        "tests/test_c0_physical_model_inventory.py",
        "tests/test_c1_thermophysical_contracts.py",
        "tests/test_c2_matrix_environment.py",
        "tests/test_canonical_hashing.py",
        "tests/test_canonical_quantities.py",
        "tests/test_canonical_serialization.py",
        "tests/test_ci_contract.py",
        "tests/test_engine_compilation.py",
        "tests/test_llm_cache.py",
        "tests/test_golden_formula_regression.py",
        "tests/test_intervention_trial.py",
        "tests/test_interventions.py",
        "tests/test_mixture.py",
        "tests/test_oav_authority.py",
        "tests/test_project_verification.py",
        "tests/test_preference.py",
        "tests/test_provenance_model.py",
        "tests/test_quantities.py",
        "tests/test_reconstruction_allergen_authority.py",
        "tests/test_receptor_evidence_quarantine.py",
        "tests/test_release_scoring_contract.py",
        "tests/test_release_readiness.py",
        "tests/test_safety_assessment.py",
        "tests/test_scientific_contract.py",
        "tests/test_tracing.py",
        "tests/test_workbench.py",
    ),
    "data-knowledge": (
        "tests/test_aromachemical_expansion.py",
        "tests/test_b8_backfill_dashboard.py",
        "tests/test_data_spine_loader.py",
        "tests/test_ifra_safety.py",
        "tests/test_inventory_material_additions.py",
        "tests/test_kb_migration.py",
        "tests/test_kb_query.py",
        "tests/test_literature_rules_contract.py",
        "tests/test_optimizer_determinism.py",
        "tests/test_property_estimator.py",
        "tests/test_range_gap_analysis.py",
        "tests/test_science_audit.py",
        "tests/test_science_kb.py",
        "tests/test_scientific_data_authority_report.py",
        "tests/test_scientific_truth_inventory.py",
    ),
    "gates-families": (
        "tests/test_a1_authoritative_contracts.py",
        "tests/test_a1_audit_contract_gaps.py",
        "tests/test_classical_family_resolution.py",
        "tests/test_family_archetypes.py",
        "tests/test_family_gate_applicability.py",
        "tests/test_gate_aware_optimizer.py",
        "tests/test_oav_intelligence.py",
        "tests/test_optimizer_thermodynamic_unification.py",
        "tests/test_pipeline_formula_state.py",
        "tests/test_pipeline_gates.py",
        "tests/test_pipeline_interventions.py",
        "tests/test_pipeline_part4.py",
        "tests/test_pipeline_part5.py",
        "tests/test_pipeline_preflight.py",
        "tests/test_pipeline_robustness.py",
        "tests/test_pipeline_scenario_matrix.py",
        "tests/test_run_evidence_contract.py",
        "tests/test_accord_graph.py",
        "tests/test_bottle_events.py",
        "tests/test_inventory_operations.py",
        "tests/test_evidence_ledger.py",
        "tests/test_inventory_stock_model.py",
        "tests/test_reconstruction_anti_compression.py",
        "tests/test_reconstruction_bridge.py",
        "tests/test_reconstruction_chassis.py",
        "tests/test_reconstruction_ensembles.py",
        "tests/test_reconstruction_identity.py",
        "tests/test_reconstruction_quantity.py",
        "tests/test_reconstruction_rank_prior.py",
        "tests/test_reconstruction_unknowns.py",
        "tests/test_target_formula.py",
        "tests/test_units_concentration.py",
        "tests/test_sensory_ledger.py",
        "tests/test_analytical_ledger.py",
        "tests/test_safety_regulatory.py",
        "tests/test_reports_generator.py",
        "tests/test_experiments_planner.py",
        "tests/test_versioning_formula.py",
        "tests/test_brand_profiles.py",
        "tests/test_bottle_console.py",
        "tests/test_authority_derivation.py",
    ),
    "legacy": (
        "tests/test_calibration_feedback.py",
        "tests/test_diffusion_regression.py",
        "tests/test_formula_memory.py",
        "tests/test_interaction_graph.py",
        "tests/test_pipeline_audit_verify.py",
        "tests/test_verify_formula_workflow_parser.py",
    ),
}


@dataclass(frozen=True, slots=True)
class CheckSpec:
    """One bounded verification command."""

    name: str
    command: tuple[str, ...]
    cwd: str = "."
    required: bool = True
    environment: str | None = None
    timeout_seconds: int = 600


@dataclass(frozen=True, slots=True)
class CommandOutcome:
    """Captured subprocess result independent of subprocess implementation."""

    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Serializable outcome for one check."""

    name: str
    status: str
    required: bool
    command: tuple[str, ...]
    duration_seconds: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "required": self.required,
            "command": list(self.command),
            "duration_seconds": round(self.duration_seconds, 3),
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ProjectVerificationReport:
    """Aggregate Phase 0 completion evidence."""

    checks: tuple[CheckResult, ...]
    known_legacy_limitations: tuple[str, ...]
    scientific_data_coverage: dict
    golden_output_changes: dict
    docker_status: str
    verification_scope: str
    selected_checks: tuple[str, ...]
    omitted_checks: tuple[str, ...]
    completion_gate: str
    release_readiness: dict

    @property
    def passed(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if check.status == "PASS")

    @property
    def failed(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if check.status == "FAIL")

    @property
    def skipped(self) -> tuple[str, ...]:
        return tuple(check.name for check in self.checks if check.status == "SKIPPED")

    def as_dict(self) -> dict:
        return {
            "passed": list(self.passed),
            "failed": list(self.failed),
            "skipped": list(self.skipped),
            "known_legacy_limitations": list(self.known_legacy_limitations),
            "scientific_data_coverage": self.scientific_data_coverage,
            "golden_output_changes": self.golden_output_changes,
            "docker_status": self.docker_status,
            "verification_scope": self.verification_scope,
            "selected_checks": list(self.selected_checks),
            "omitted_checks": list(self.omitted_checks),
            "completion_gate": self.completion_gate,
            "release_readiness": self.release_readiness,
            "checks": [check.as_dict() for check in self.checks],
        }


def engine_test_shards(project_root: Path = PROJECT_ROOT) -> dict[str, tuple[str, ...]]:
    """Return the explicit shard manifest, using repository-relative paths."""

    del project_root
    return {name: tuple(paths) for name, paths in _ENGINE_TEST_SHARDS.items()}


def _local_tool(project_root: Path, tool: str) -> tuple[str, ...]:
    runtime_dir = Path(sys.executable).resolve().parent
    candidates = (
        runtime_dir / f"{tool}.exe",
        runtime_dir / tool,
        project_root / ".venv" / "Scripts" / f"{tool}.exe",
        project_root / ".venv" / "bin" / tool,
    )
    for candidate in candidates:
        if candidate.exists():
            return (str(candidate),)
    return (tool,)


def build_check_specs(project_root: Path = PROJECT_ROOT) -> tuple[CheckSpec, ...]:
    """Build the canonical Phase 0 checks for repository-owned verification."""

    python = sys.executable
    pytest = (python, "-m", "pytest")
    ruff = _local_tool(project_root, "ruff")
    mypy = _local_tool(project_root, "mypy")
    poetry = _local_tool(project_root, "poetry")

    checks: list[CheckSpec] = [
        CheckSpec("engine-compile", (python, "-m", "compileall", "-q", "engine")),
        CheckSpec(
            "engine-lint",
            ruff
            + (
                "check",
                "--color",
                "never",
                "engine/workbench.py",
                "engine/authority_gates.py",
                "engine/bottle_addition.py",
                "engine/calibration/hashing.py",
                "engine/canonical_serialization.py",
                "engine/intervention_hypotheses.py",
                "engine/intervention_profiles.py",
                "engine/intervention_trial.py",
                "engine/interventions.py",
                "engine/mixture.py",
                "engine/preference.py",
                "engine/provenance.py",
                "engine/quantities.py",
                "engine/release_readiness.py",
                "engine/safety_assessment.py",
                "engine/scientific_contract.py",
                "engine/project_verification.py",
                "engine/pipeline/formula_state.py",
                "engine/pipeline/simulator.py",
                "engine/domain_errors.py",
                "engine/units/concentration.py",
                "engine/target/formula.py",
                "engine/reconstruction/anti_compression.py",
                "engine/bottle/events.py",
                "engine/inventory/operations.py",
                "engine/analytical/ledger.py",
                "engine/evidence/ledger.py",
                "engine/safety/regulatory.py",
                "engine/sensory/ledger.py",
                "engine/versioning/formula_version.py",
                "engine/reconstruction/rank_prior.py",
                "engine/reconstruction/ensembles.py",
                "engine/reconstruction/chassis.py",
                "engine/reconstruction/recognizer.py",
                "engine/inventory/stock_model.py",
                "engine/identity/resolver.py",
                "scripts/pipeline_audit.py",
                "scripts/formula_release_gate.py",
                "scripts/rebind_formula_artifact.py",
            ),
        ),
        CheckSpec(
            "engine-typecheck",
            mypy
            + (
                "--explicit-package-bases",
                "--follow-imports=skip",
                "--ignore-missing-imports",
                "engine/workbench.py",
                "engine/authority_gates.py",
                "engine/bottle_addition.py",
                "engine/calibration/hashing.py",
                "engine/canonical_serialization.py",
                "engine/intervention_hypotheses.py",
                "engine/intervention_trial.py",
                "engine/interventions.py",
                "engine/mixture.py",
                "engine/preference.py",
                "engine/provenance.py",
                "engine/quantities.py",
                "engine/release_readiness.py",
                "engine/safety_assessment.py",
                "engine/scientific_contract.py",
                "engine/project_verification.py",
                "engine/domain_errors.py",
                "engine/units/concentration.py",
                "engine/target/formula.py",
                "engine/reconstruction/anti_compression.py",
                "engine/bottle/events.py",
                "engine/inventory/operations.py",
                "engine/analytical/ledger.py",
                "engine/evidence/ledger.py",
                "engine/safety/regulatory.py",
                "engine/sensory/ledger.py",
                "engine/versioning/formula_version.py",
                "engine/reconstruction/rank_prior.py",
                "engine/reconstruction/ensembles.py",
                "engine/reconstruction/chassis.py",
                "engine/reconstruction/recognizer.py",
                "engine/inventory/stock_model.py",
                "engine/identity/resolver.py",
            ),
        ),
        CheckSpec(
            "formula-artifact-validation",
            (
                python,
                "scripts/pipeline_audit.py",
                "artifact-verify",
                "--json",
            ),
        ),
    ]

    for shard_name, paths in _ENGINE_TEST_SHARDS.items():
        checks.append(
            CheckSpec(
                f"engine-tests-{shard_name}",
                pytest
                + paths
                + (
                    "-q",
                    f"--junitxml=verification_runs/engine-{shard_name}.xml",
                ),
                timeout_seconds=900,
            )
        )

    checks.extend(
        (
            CheckSpec(
                "backend-lint",
                poetry
                + ("run", "ruff", "check", "--color", "never", "app"),
                cwd="backend",
            ),
            CheckSpec(
                "backend-typecheck",
                poetry
                + (
                    "run",
                    "mypy",
                    "app",
                    "--ignore-missing-imports",
                ),
                cwd="backend",
            ),
            CheckSpec(
                "backend-tests",
                poetry
                + (
                    "run",
                    "pytest",
                    "-q",
                    "--basetemp=../output/verification-temp/backend-pytest",
                    "--junitxml=../verification_runs/backend.xml",
                ),
                cwd="backend",
                timeout_seconds=1200,
            ),
            CheckSpec(
                "scientific-audit",
                pytest
                + (
                    "tests/test_scientific_contract.py",
                    "tests/test_science_audit.py",
                    "tests/test_oav_authority.py",
                    "tests/test_receptor_evidence_quarantine.py",
                    "-q",
                ),
            ),
            CheckSpec(
                "material-data-validation",
                pytest
                + (
                    "tests/test_data_spine_loader.py",
                    "tests/test_inventory_material_additions.py",
                    "tests/test_property_estimator.py",
                    "-q",
                ),
            ),
            CheckSpec(
                "knowledge-rule-validation",
                pytest
                + (
                    "tests/test_literature_rules_contract.py",
                    "tests/test_kb_migration.py",
                    "tests/test_kb_query.py",
                    "-q",
                ),
            ),
            CheckSpec(
                "golden-formula-regression",
                pytest + ("tests/test_golden_formula_regression.py", "-q"),
            ),
            CheckSpec(
                "golden-api-regression",
                poetry
                + (
                    "run",
                    "pytest",
                    "tests/integration/test_api_endpoints.py",
                    "-k",
                    "golden_explicit_solvent",
                    "-q",
                ),
                cwd="backend",
            ),
            CheckSpec(
                "package-build",
                (
                    python,
                    "-m",
                    "pip",
                    "wheel",
                    ".",
                    "-w",
                    "dist",
                    "--no-build-isolation",
                ),
            ),
            CheckSpec(
                "package-wheel-smoke",
                (
                    python,
                    "-m",
                    "engine.project_verification",
                    "wheel-smoke",
                    "--dist-dir",
                    "dist",
                ),
            ),
            CheckSpec(
                "docker-build",
                (
                    "docker",
                    "build",
                    "--tag",
                    "perfume-chem-phase0",
                    "--file",
                    "backend/Dockerfile",
                    ".",
                ),
                required=False,
                environment="docker",
                timeout_seconds=1200,
            ),
            CheckSpec(
                "docker-smoke-test",
                (
                    python,
                    "-m",
                    "engine.project_verification",
                    "docker-smoke",
                    "--image",
                    "perfume-chem-phase0",
                ),
                required=False,
                environment="docker",
                timeout_seconds=600,
            ),
        )
    )
    return tuple(checks)


def _tail(value: str, line_count: int = 30) -> str:
    return "\n".join(value.splitlines()[-line_count:])


def _default_runner(project_root: Path) -> Callable[[CheckSpec], CommandOutcome]:
    verification_temp = project_root / "output" / "verification-temp"
    verification_temp.mkdir(parents=True, exist_ok=True)
    pip_cache = project_root / "output" / "verification-pip-cache"
    pip_cache.mkdir(parents=True, exist_ok=True)

    def run(spec: CheckSpec) -> CommandOutcome:
        started = time.monotonic()
        env = dict(os.environ)
        env["TEMP"] = str(verification_temp)
        env["TMP"] = str(verification_temp)
        env["PIP_CACHE_DIR"] = str(pip_cache)
        if spec.cwd == "backend":
            env.setdefault("OPENAI_API_KEY", "test-key")
            env.setdefault("SECRET_KEY", "test-secret-key-for-ci")
        try:
            completed = subprocess.run(
                spec.command,
                cwd=project_root / spec.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=spec.timeout_seconds,
                env=env,
                check=False,
            )
            return CommandOutcome(
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=time.monotonic() - started,
            )
        except subprocess.TimeoutExpired as exc:
            return CommandOutcome(
                returncode=124,
                stdout=str(exc.stdout or ""),
                stderr=f"Timed out after {spec.timeout_seconds} seconds.",
                duration_seconds=time.monotonic() - started,
            )
        except OSError as exc:
            return CommandOutcome(
                returncode=127,
                stdout="",
                stderr=f"Executable not found or could not start: {exc}",
                duration_seconds=time.monotonic() - started,
            )

    return run


def _scientific_data_coverage() -> dict:
    science = build_science_audit_contract()
    counts: dict[str, int] = {}
    for metadata in ODT_VERIFICATION.values():
        verification = str((metadata or {}).get("vfy", "UNKNOWN"))
        counts[verification] = counts.get(verification, 0) + 1
    return {
        "odt_verification_counts": counts,
        "science_coverage_pct": science.get("data_coverage_pct", {}),
    }


def _golden_output_changes(project_root: Path) -> dict:
    fixture = project_root / "tests" / "fixtures" / "golden_formula_cases.json"
    lock = fixture.with_suffix(".sha256")
    if not fixture.exists():
        return {"status": "missing", "changed": None}
    try:
        payload = json.loads(fixture.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "status": "invalid_json",
            "changed": True,
            "expected_sha256": None,
            "actual_sha256": None,
            "error": str(exc),
        }
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    actual = sha256(canonical).hexdigest()
    expected = lock.read_text(encoding="ascii").strip() if lock.exists() else None
    return {
        "status": "unchanged" if expected == actual else "changed_or_unlocked",
        "changed": expected != actual,
        "expected_sha256": expected,
        "actual_sha256": actual,
    }


def _select_checks(
    checks: Sequence[CheckSpec], selected: Iterable[str] | None, quick: bool
) -> tuple[CheckSpec, ...]:
    by_name = {check.name: check for check in checks}
    if selected:
        requested = tuple(dict.fromkeys(selected))
        unknown = sorted(set(requested).difference(by_name))
        if unknown:
            raise ValueError("Unknown verification checks: " + ", ".join(unknown))
        return tuple(by_name[name] for name in requested)
    if quick:
        quick_names = (
            "engine-compile",
            "engine-lint",
            "engine-typecheck",
            "formula-artifact-validation",
            "scientific-audit",
            "material-data-validation",
            "knowledge-rule-validation",
            "golden-formula-regression",
            "golden-api-regression",
        )
        return tuple(by_name[name] for name in quick_names)
    return tuple(checks)


def run_project_verification(
    *,
    project_root: Path = PROJECT_ROOT,
    checks: Sequence[CheckSpec] | None = None,
    runner: Callable[[CheckSpec], CommandOutcome] | None = None,
    selected: Iterable[str] | None = None,
    quick: bool = False,
    include_docker: bool = False,
) -> ProjectVerificationReport:
    """Run selected checks without hiding failures or unavailable environments."""

    project_root = Path(project_root)
    (project_root / "verification_runs").mkdir(parents=True, exist_ok=True)
    custom_checks = checks is not None
    available_checks = tuple(checks) if checks is not None else build_check_specs(project_root)
    selected_checks = _select_checks(available_checks, selected, quick)
    selected_names = tuple(spec.name for spec in selected_checks)
    omitted_names = tuple(spec.name for spec in available_checks if spec.name not in selected_names)
    if selected or quick:
        verification_scope = "partial"
    elif custom_checks:
        verification_scope = "custom"
    else:
        verification_scope = "full"
    execute = runner or _default_runner(project_root)
    results: list[CheckResult] = []

    for spec in selected_checks:
        if spec.environment == "docker" and not include_docker:
            results.append(
                CheckResult(
                    name=spec.name,
                    status="SKIPPED",
                    required=spec.required,
                    command=spec.command,
                    reason="Docker checks require --include-docker.",
                )
            )
            continue
        if spec.environment == "docker" and shutil.which("docker") is None:
            results.append(
                CheckResult(
                    name=spec.name,
                    status="SKIPPED",
                    required=spec.required,
                    command=spec.command,
                    reason="Docker executable is unavailable.",
                )
            )
            continue

        outcome = execute(spec)
        results.append(
            CheckResult(
                name=spec.name,
                status="PASS" if outcome.returncode == 0 else "FAIL",
                required=spec.required,
                command=spec.command,
                duration_seconds=outcome.duration_seconds,
                stdout_tail=_tail(outcome.stdout),
                stderr_tail=_tail(outcome.stderr),
            )
        )

    golden_changes = _golden_output_changes(project_root)
    if "golden-formula-regression" in selected_names:
        lock_matches = golden_changes["status"] == "unchanged"
        results.append(
            CheckResult(
                name="golden-fixture-lock",
                status="PASS" if lock_matches else "FAIL",
                required=True,
                command=(),
                reason=(
                    "Golden fixture SHA-256 matches its reviewed lock."
                    if lock_matches
                    else "Golden fixture is missing, changed, or unlocked."
                ),
            )
        )

    executed_failures = [result for result in results if result.status == "FAIL"]
    if executed_failures:
        completion_gate = "FAIL"
    elif verification_scope != "full":
        completion_gate = "NOT_EVALUATED"
    elif any(result.status == "SKIPPED" for result in results):
        completion_gate = "PASS_WITH_SKIPS"
    else:
        completion_gate = "PASS"

    docker_results = [result for result in results if result.name.startswith("docker-")]
    if not docker_results or all(result.status == "SKIPPED" for result in docker_results):
        docker_status = "SKIPPED"
    elif any(result.status == "FAIL" for result in docker_results):
        docker_status = "FAIL"
    else:
        docker_status = "PASS"

    local_release_gate = completion_gate in {"PASS", "PASS_WITH_SKIPS"}
    release_readiness = build_release_readiness(
        ReadinessInput(
            code_checks_passed=local_release_gate,
            data_contracts_passed=local_release_gate,
            local_validation_passed=local_release_gate,
            migration_verified=local_release_gate,
            backup_restore_verified=local_release_gate,
            heldout_sensory_validation_passed=False,
        )
    ).as_dict()

    return ProjectVerificationReport(
        checks=tuple(results),
        known_legacy_limitations=KNOWN_LEGACY_LIMITATIONS,
        scientific_data_coverage=_scientific_data_coverage(),
        golden_output_changes=golden_changes,
        docker_status=docker_status,
        verification_scope=verification_scope,
        selected_checks=selected_names,
        omitted_checks=omitted_names,
        completion_gate=completion_gate,
        release_readiness=release_readiness,
    )


def write_verification_report(report: ProjectVerificationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.as_dict(), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def default_verification_report_path(project_root: Path, report: ProjectVerificationReport) -> Path:
    """Keep targeted evidence from replacing the canonical full-scope report."""

    suffix = "" if report.verification_scope == "full" else f"_{report.verification_scope}"
    return project_root / "verification_runs" / f"project_verification{suffix}.json"


def _wheel_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _wheel_install_command(
    python: Path,
    wheel: Path,
    dist_dir: Path,
) -> tuple[str, ...]:
    """Install the package and declared dependencies from a local wheelhouse."""

    return (
        str(python),
        "-m",
        "pip",
        "install",
        "--no-index",
        "--find-links",
        str(dist_dir.resolve()),
        str(wheel.resolve()),
    )


def smoke_installed_wheel(dist_dir: Path) -> int:
    """Install the newest built wheel and import it outside the checkout."""

    wheels = sorted(
        dist_dir.glob("perfume_chem_engine-*.whl"),
        key=lambda path: path.stat().st_mtime,
    )
    if not wheels:
        print(f"No wheel found in {dist_dir}.", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="perfume-chem-wheel-") as temp_name:
        temp_dir = Path(temp_name)
        venv_dir = temp_dir / "venv"
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(venv_dir)
        python = _wheel_python(venv_dir)
        install = subprocess.run(
            _wheel_install_command(python, wheels[-1], dist_dir),
            cwd=temp_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if install.returncode != 0:
            print(install.stdout, file=sys.stderr)
            print(install.stderr, file=sys.stderr)
            return install.returncode
        smoke = subprocess.run(
            (
                str(python),
                "-c",
                (
                    "from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest; "
                    "result=PerfumeWorkbench().analyze(WorkbenchFormulaRequest("
                    "formula_name='wheel-smoke', ingredients_ul={'Hedione': 100.0}, "
                    "dilutions={'Hedione': 1.0}, batch_volume_ml=10.0)).as_dict(); "
                    "assert result['material_oav_table'][0]['name'] == 'Hedione'; "
                    "assert result['material_oav_table'][0]['oav'] is not None"
                ),
            ),
            cwd=temp_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if smoke.returncode != 0:
            print(smoke.stdout, file=sys.stderr)
            print(smoke.stderr, file=sys.stderr)
        return smoke.returncode


def smoke_docker_image(image: str, timeout_seconds: float = 60.0) -> int:
    """Run an image through its normal CMD and poll its real HTTP health route."""

    started = subprocess.run(
        (
            "docker",
            "run",
            "--detach",
            "--env",
            "OPENAI_API_KEY=test-key",
            "--env",
            "SECRET_KEY=test-secret-key-for-ci",
            "--publish",
            "127.0.0.1::8000",
            image,
        ),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if started.returncode != 0:
        print(started.stderr, file=sys.stderr)
        return started.returncode

    container_id = started.stdout.strip()
    try:
        port_result = subprocess.run(
            ("docker", "port", container_id, "8000/tcp"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if port_result.returncode != 0:
            print(port_result.stderr, file=sys.stderr)
            return port_result.returncode
        port = port_result.stdout.strip().rsplit(":", 1)[-1]
        health_url = f"http://127.0.0.1:{port}/health"
        deadline = time.monotonic() + timeout_seconds
        last_error = "container did not become healthy"
        while time.monotonic() < deadline:
            try:
                with urlopen(health_url, timeout=2.0) as response:  # noqa: S310
                    payload = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and payload.get("status") == "healthy":
                    print(f"Healthy container response from {health_url}")
                    return 0
                last_error = f"unexpected response: {response.status} {payload}"
            except (OSError, URLError, ValueError) as exc:
                last_error = str(exc)
            time.sleep(1.0)
        print(f"Docker health smoke failed: {last_error}", file=sys.stderr)
        return 1
    finally:
        logs = subprocess.run(
            ("docker", "logs", container_id),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if logs.stdout:
            print(logs.stdout)
        if logs.stderr:
            print(logs.stderr, file=sys.stderr)
        subprocess.run(
            ("docker", "rm", "--force", container_id),
            capture_output=True,
            check=False,
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 0 artifact smoke helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    wheel = subparsers.add_parser("wheel-smoke")
    wheel.add_argument("--dist-dir", type=Path, default=Path("dist"))
    docker = subparsers.add_parser("docker-smoke")
    docker.add_argument("--image", default="perfume-chem-phase0")
    docker.add_argument("--timeout-seconds", type=float, default=60.0)
    args = parser.parse_args(argv)
    if args.command == "wheel-smoke":
        return smoke_installed_wheel(args.dist_dir)
    return smoke_docker_image(args.image, args.timeout_seconds)


__all__ = [
    "CheckResult",
    "CheckSpec",
    "CommandOutcome",
    "ProjectVerificationReport",
    "build_check_specs",
    "default_verification_report_path",
    "engine_test_shards",
    "run_project_verification",
    "write_verification_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
