from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path

import engine.project_verification as project_verification
from engine.project_verification import (
    CheckSpec,
    CommandOutcome,
    _default_runner,
    _local_tool,
    build_check_specs,
    default_verification_report_path,
    engine_test_shards,
    run_project_verification,
    write_verification_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_tool_prefers_supported_runtime_environment(tmp_path, monkeypatch):
    supported_scripts = tmp_path / "supported" / "Scripts"
    supported_scripts.mkdir(parents=True)
    supported_python = supported_scripts / "python.exe"
    supported_tool = supported_scripts / "mypy.exe"
    supported_python.touch()
    supported_tool.touch()

    repository_tool = tmp_path / ".venv" / "Scripts" / "mypy.exe"
    repository_tool.parent.mkdir(parents=True)
    repository_tool.touch()

    monkeypatch.setattr(project_verification.sys, "executable", str(supported_python))

    assert _local_tool(tmp_path, "mypy") == (str(supported_tool),)


def test_wheel_smoke_installs_declared_dependencies_from_local_wheelhouse(tmp_path):
    from engine.project_verification import _wheel_install_command

    command = _wheel_install_command(
        Path("python"),
        tmp_path / "perfume_chem_engine.whl",
        tmp_path,
    )

    assert "--no-index" in command
    assert "--find-links" in command
    assert str(tmp_path.resolve()) in command
    assert "--no-deps" not in command

    package_build = {
        spec.name: spec for spec in build_check_specs(PROJECT_ROOT)
    }["package-build"].command
    assert "--no-deps" not in package_build


def test_engine_shards_cover_every_test_file_once():
    shards = engine_test_shards(PROJECT_ROOT)
    assigned = [path for paths in shards.values() for path in paths]
    discovered = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in (PROJECT_ROOT / "tests").glob("test_*.py")
    )

    assert sorted(assigned) == discovered
    assert len(assigned) == len(set(assigned))


def test_verifier_records_pass_fail_skip_and_completion_gate(tmp_path):
    checks = (
        CheckSpec("good", ("good",), required=True),
        CheckSpec("bad", ("bad",), required=True),
        CheckSpec("optional", ("optional",), required=False, environment="docker"),
    )

    def fake_runner(spec: CheckSpec) -> CommandOutcome:
        return CommandOutcome(
            returncode=1 if spec.name == "bad" else 0,
            stdout=f"ran {spec.name}",
            stderr="expected failure" if spec.name == "bad" else "",
            duration_seconds=0.01,
        )

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=fake_runner,
        include_docker=False,
    )
    payload = report.as_dict()

    assert payload["passed"] == ["good"]
    assert payload["failed"] == ["bad"]
    assert payload["skipped"] == ["optional"]
    assert payload["completion_gate"] == "FAIL"
    assert payload["docker_status"] == "SKIPPED"
    assert payload["known_legacy_limitations"]
    assert "scientific_data_coverage" in payload
    assert "golden_output_changes" in payload
    assert "release_readiness" in payload
    assert payload["verification_scope"] == "custom"
    assert payload["selected_checks"] == ["good", "bad", "optional"]
    assert payload["omitted_checks"] == []


def test_partial_or_custom_success_is_not_a_phase_zero_completion_claim(tmp_path):
    checks = (
        CheckSpec("good", ("good",), required=True),
        CheckSpec("optional", ("optional",), required=False, environment="docker"),
    )

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=lambda spec: CommandOutcome(0, "ok", "", 0.01),
        include_docker=False,
    )

    assert report.completion_gate == "NOT_EVALUATED"


def test_optional_environment_check_fails_when_it_runs_and_breaks(tmp_path):
    checks = (
        CheckSpec("docker-build", ("docker", "build"), required=False),
    )

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=lambda spec: CommandOutcome(1, "", "build failed", 0.01),
        include_docker=True,
    )

    assert report.completion_gate == "FAIL"


def test_selected_subset_reports_omitted_checks_and_is_not_evaluated(tmp_path):
    checks = (
        CheckSpec("one", ("one",)),
        CheckSpec("two", ("two",)),
    )

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        selected=("one",),
        runner=lambda spec: CommandOutcome(0, "ok", "", 0.01),
    )

    assert report.verification_scope == "partial"
    assert report.selected_checks == ("one",)
    assert report.omitted_checks == ("two",)
    assert report.completion_gate == "NOT_EVALUATED"


def test_golden_fixture_lock_mismatch_is_a_failing_check(tmp_path):
    fixture_dir = tmp_path / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    fixture = fixture_dir / "golden_formula_cases.json"
    fixture.write_text('{"changed": true}\n', encoding="utf-8")
    fixture.with_suffix(".sha256").write_text("not-the-real-hash\n", encoding="ascii")
    checks = (CheckSpec("golden-formula-regression", ("golden",)),)

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=lambda spec: CommandOutcome(0, "ok", "", 0.01),
    )

    lock = next(check for check in report.checks if check.name == "golden-fixture-lock")
    assert lock.status == "FAIL"
    assert report.completion_gate == "FAIL"


def test_golden_fixture_lock_is_independent_of_json_line_endings(tmp_path):
    fixture_dir = tmp_path / "tests" / "fixtures"
    fixture_dir.mkdir(parents=True)
    fixture = fixture_dir / "golden_formula_cases.json"
    payload = {"schema_version": 1, "cases": [{"id": "line-endings"}]}
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    fixture.with_suffix(".sha256").write_text(
        sha256(canonical).hexdigest() + "\n", encoding="ascii"
    )
    checks = (CheckSpec("golden-formula-regression", ("golden",)),)

    for newline in (b"\n", b"\r\n"):
        rendered = json.dumps(payload, indent=2).replace("\n", newline.decode())
        fixture.write_bytes(rendered.encode("ascii") + newline)
        report = run_project_verification(
            project_root=tmp_path,
            checks=checks,
            runner=lambda spec: CommandOutcome(0, "ok", "", 0.01),
        )

        lock = next(
            check for check in report.checks if check.name == "golden-fixture-lock"
        )
        assert lock.status == "PASS"


def test_missing_executable_is_reported_as_a_structured_failure(tmp_path):
    checks = (CheckSpec("missing-tool", ("phase-zero-tool-that-does-not-exist",)),)

    report = run_project_verification(project_root=tmp_path, checks=checks)

    assert report.failed == ("missing-tool",)
    assert "not found" in report.checks[0].stderr_tail.lower()
    assert report.completion_gate == "FAIL"


def test_default_runner_routes_child_temp_inside_project(tmp_path):
    outcome = _default_runner(tmp_path)(
        CheckSpec(
            "temp-contract",
            (
                sys.executable,
                "-c",
                "import os; print(os.environ['TEMP']); print(os.environ['TMP'])",
            ),
        )
    )

    expected = str(tmp_path / "output" / "verification-temp")
    assert outcome.returncode == 0
    assert outcome.stdout.splitlines() == [expected, expected]


def test_package_and_docker_checks_validate_release_artifacts():
    specs = {spec.name: spec for spec in build_check_specs(PROJECT_ROOT)}

    assert specs["backend-typecheck"].command[-4:] == (
        "run",
        "mypy",
        "app",
        "--ignore-missing-imports",
    )
    engine_typecheck = set(specs["engine-typecheck"].command)
    assert {
        "engine/interventions.py",
        "engine/mixture.py",
        "engine/preference.py",
        "engine/quantities.py",
        "engine/release_readiness.py",
        "engine/safety_assessment.py",
    } <= engine_typecheck
    package_build = specs["package-build"].command
    assert package_build[:3] == (sys.executable, "-m", "pip")
    assert "wheel" in package_build
    assert specs["package-wheel-smoke"].command[1:4] == (
        "-m",
        "engine.project_verification",
        "wheel-smoke",
    )
    assert specs["docker-build"].command == (
        "docker",
        "build",
        "--tag",
        "perfume-chem-phase0",
        "--file",
        "backend/Dockerfile",
        ".",
    )
    assert "engine.project_verification" in specs["docker-smoke-test"].command
    assert "docker-smoke" in specs["docker-smoke-test"].command
    assert "health_check" not in " ".join(specs["docker-smoke-test"].command)


def test_backend_suite_timeout_has_full_run_margin():
    specs = {spec.name: spec for spec in build_check_specs(PROJECT_ROOT)}

    assert specs["backend-tests"].timeout_seconds == 1200


def test_ruff_checks_explicitly_disable_ansi_color():
    specs = {spec.name: spec for spec in build_check_specs(PROJECT_ROOT)}

    for check_name in ("engine-lint", "backend-lint"):
        command = specs[check_name].command
        color_index = command.index("--color")
        assert command[color_index + 1] == "never"


def test_a1_production_modules_are_linted_and_typechecked():
    specs = {spec.name: spec for spec in build_check_specs(PROJECT_ROOT)}
    a1_targets = {
        "engine/domain_errors.py",
        "engine/units/concentration.py",
        "engine/target/formula.py",
        "engine/reconstruction/anti_compression.py",
        "engine/bottle/events.py",
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
    }

    assert a1_targets <= set(specs["engine-lint"].command)
    assert a1_targets <= set(specs["engine-typecheck"].command)


def test_only_canonical_full_scope_can_pass_with_optional_skips(tmp_path, monkeypatch):
    canonical = (
        CheckSpec("required", ("required",)),
        CheckSpec(
            "docker-build",
            ("docker", "build"),
            required=False,
            environment="docker",
        ),
    )
    monkeypatch.setattr(
        project_verification,
        "build_check_specs",
        lambda project_root: canonical,
    )

    report = run_project_verification(
        project_root=tmp_path,
        runner=lambda spec: CommandOutcome(0, "ok", "", 0.01),
    )

    assert report.verification_scope == "full"
    assert report.completion_gate == "PASS_WITH_SKIPS"


def test_partial_report_path_cannot_overwrite_canonical_full_evidence(
    tmp_path, monkeypatch
):
    canonical = (CheckSpec("required", ("required",)),)
    monkeypatch.setattr(
        project_verification,
        "build_check_specs",
        lambda project_root: canonical,
    )
    runner = lambda spec: CommandOutcome(0, "ok", "", 0.01)  # noqa: E731
    full = run_project_verification(project_root=tmp_path, runner=runner)
    partial = run_project_verification(
        project_root=tmp_path,
        checks=canonical,
        selected=("required",),
        runner=runner,
    )
    full_path = default_verification_report_path(tmp_path, full)
    partial_path = default_verification_report_path(tmp_path, partial)

    write_verification_report(full, full_path)
    write_verification_report(partial, partial_path)

    assert full_path.name == "project_verification.json"
    assert partial_path.name == "project_verification_partial.json"
    assert full_path != partial_path
    assert json.loads(full_path.read_text(encoding="utf-8"))["verification_scope"] == "full"
