from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from hashlib import sha256
from pathlib import Path

import pytest

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

    package_build = {spec.name: spec for spec in build_check_specs(PROJECT_ROOT)}[
        "package-build"
    ].command
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


def test_engine_shards_discover_new_tests_and_wire_commands(tmp_path, monkeypatch):
    monkeypatch.setattr(
        project_verification,
        "_ENGINE_TEST_SHARDS",
        {"core": ("tests/test_existing.py",), "empty": ()},
    )
    for name in (
        "tests/test_existing.py",
        "tests/test_z.py",
        "tests/test_a.py",
        "tests/nested/test_nested.py",
        "backend/tests/test_backend.py",
        "tests/helper.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    shards = engine_test_shards(tmp_path)
    assert shards["core"] == ("tests/test_existing.py",)
    assert shards["additional"] == ("tests/test_a.py", "tests/test_z.py")
    specs = {spec.name: spec for spec in build_check_specs(tmp_path)}
    assert "engine-tests-empty" not in specs
    for name in ("core", "additional"):
        command = specs[f"engine-tests-{name}"].command
        assert tuple(arg for arg in command if arg.startswith("tests/")) == shards[name]
    (tmp_path / "tests/test_b.py").touch()
    assert engine_test_shards(tmp_path)["core"] == shards["core"]
    assert engine_test_shards(tmp_path)["additional"] == (
        "tests/test_a.py",
        "tests/test_b.py",
        "tests/test_z.py",
    )


def test_engine_shards_without_new_tests_do_not_add_empty_check(tmp_path, monkeypatch):
    monkeypatch.setattr(project_verification, "_ENGINE_TEST_SHARDS", {})
    assert engine_test_shards(tmp_path) == {}
    assert not any(spec.name.startswith("engine-tests-") for spec in build_check_specs(tmp_path))


def test_full_selector_drops_only_checks_already_covered_by_suites():
    specs = build_check_specs(PROJECT_ROOT)
    full = project_verification._select_checks(specs, None, False)
    full_names = {spec.name for spec in full}

    assert project_verification._FULL_SCOPE_DUPLICATE_CHECKS <= {
        spec.name for spec in specs
    }
    assert not project_verification._FULL_SCOPE_DUPLICATE_CHECKS & full_names
    assert {
        "engine-compile",
        "engine-lint",
        "engine-typecheck",
        "formula-artifact-validation",
        "backend-lint",
        "backend-typecheck",
        "backend-tests",
        "package-build",
        "package-wheel-smoke",
    } <= full_names


def test_quick_selector_retains_targeted_regressions():
    specs = build_check_specs(PROJECT_ROOT)

    assert tuple(
        spec.name for spec in project_verification._select_checks(specs, None, True)
    ) == (
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


@pytest.mark.parametrize(
    "failure_name",
    ("engine-compile", "engine-lint", "engine-typecheck"),
)
def test_quick_failure_skips_remaining_checks_without_running_them(
    tmp_path, monkeypatch, failure_name
):
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
    checks = tuple(CheckSpec(name, (name,)) for name in quick_names)
    called: list[str] = []

    def fake_runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(
            1 if spec.name == failure_name else 0,
            "",
            "required check failed" if spec.name == failure_name else "",
            0.01,
        )

    monkeypatch.setattr(
        project_verification,
        "_golden_output_changes",
        lambda project_root: {"status": "unchanged"},
    )
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=fake_runner,
        quick=True,
    )

    failure_index = quick_names.index(failure_name)
    assert called == list(quick_names[: failure_index + 1])
    assert report.failed == (failure_name,)
    assert report.skipped == quick_names[failure_index + 1 :]
    assert "golden-fixture-lock" not in tuple(result.name for result in report.checks)
    assert all(
        f"{failure_name} failure" in (result.reason or "")
        for result in report.checks
        if result.status == "SKIPPED"
    )


def test_selected_empty_uses_parallel_canonical_full_and_preserves_order(
    tmp_path, monkeypatch
):
    canonical = (
        CheckSpec("engine-compile", ("compile",)),
        CheckSpec("engine-lint", ("lint",)),
        CheckSpec("engine-tests-core", ("core",)),
        CheckSpec("engine-tests-additional", ("additional",)),
        CheckSpec("backend-lint", ("backend-lint",)),
        CheckSpec("scientific-audit", ("duplicate",)),
        CheckSpec("package-build", ("package-build",)),
        CheckSpec("package-wheel-smoke", ("package-wheel-smoke",)),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def runner(spec: CheckSpec) -> CommandOutcome:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.05 if spec.name.endswith(("compile", "core")) else 0.005)
        with lock:
            active -= 1
        return CommandOutcome(0, spec.name, "", 0.03)

    report = run_project_verification(
        project_root=tmp_path,
        runner=runner,
        selected=[],
    )

    assert report.verification_scope == "full"
    expected = tuple(spec.name for spec in canonical if spec.name != "scientific-audit")
    assert report.selected_checks == expected
    assert report.omitted_checks == ("scientific-audit",)
    assert "scientific-audit" not in tuple(result.name for result in report.checks)
    assert tuple(result.name for result in report.checks) == report.selected_checks
    assert maximum_active >= 2


def test_canonical_parallelism_is_bounded(tmp_path, monkeypatch):
    canonical = tuple(
        CheckSpec(f"engine-tests-{index}", (str(index),)) for index in range(8)
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def runner(spec: CheckSpec) -> CommandOutcome:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return CommandOutcome(0, "", "", 0.03)

    run_project_verification(project_root=tmp_path, runner=runner)

    assert 2 <= maximum_active <= project_verification._MAX_PARALLEL_CHECKS


def test_custom_and_explicit_selection_remain_sequential(tmp_path, monkeypatch):
    checks = (
        CheckSpec("engine-tests-a", ("a",)),
        CheckSpec("engine-tests-b", ("b",)),
    )
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    calls: list[str] = []
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def runner(spec: CheckSpec) -> CommandOutcome:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        calls.append(spec.name)
        time.sleep(0.005)
        with lock:
            active -= 1
        return CommandOutcome(0, "", "", 0.01)

    custom = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=runner,
    )
    explicit = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        selected=("engine-tests-b", "engine-tests-a", "engine-tests-b"),
        runner=runner,
    )

    assert custom.verification_scope == "custom"
    assert explicit.verification_scope == "partial"
    assert calls == [
        "engine-tests-a",
        "engine-tests-b",
        "engine-tests-b",
        "engine-tests-a",
    ]
    assert maximum_active == 1


def test_dynamic_additional_shard_runs_in_canonical_full(tmp_path, monkeypatch):
    monkeypatch.setattr(
        project_verification,
        "_ENGINE_TEST_SHARDS",
        {"core": ("tests/test_existing.py",)},
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_existing.py").touch()
    (tests_dir / "test_new.py").touch()
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(0, "", "", 0.01)

    report = run_project_verification(project_root=tmp_path, runner=runner, selected=[])

    assert "engine-tests-additional" in report.selected_checks
    assert "engine-tests-additional" in called


def test_parallel_runner_exception_becomes_structured_failure(tmp_path, monkeypatch):
    canonical = (
        CheckSpec("engine-tests-core", ("core",)),
        CheckSpec("engine-tests-sibling", ("sibling",)),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})

    def broken_runner(spec: CheckSpec) -> CommandOutcome:
        if spec.name == "engine-tests-core":
            raise RuntimeError("worker exploded")
        return CommandOutcome(0, "sibling survived", "", 0.01)

    report = run_project_verification(project_root=tmp_path, runner=broken_runner)

    assert report.failed == ("engine-tests-core",)
    assert "RuntimeError: worker exploded" in report.checks[0].stderr_tail
    assert report.passed == ("engine-tests-sibling",)


def test_malformed_parallel_runner_outcome_becomes_structured_failure(
    tmp_path, monkeypatch
):
    canonical = (CheckSpec("engine-tests-core", ("core",)),)
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})

    report = run_project_verification(
        project_root=tmp_path,
        runner=lambda spec: object(),
    )

    assert report.failed == ("engine-tests-core",)
    assert "AttributeError" in report.checks[0].stderr_tail


def test_failed_producer_skips_dependent_smoke_check(tmp_path, monkeypatch):
    canonical = (
        CheckSpec("package-build", ("build",)),
        CheckSpec("package-wheel-smoke", ("smoke",)),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(1, "", "build failed", 0.01)

    report = run_project_verification(project_root=tmp_path, runner=runner)

    assert called == ["package-build"]
    assert report.checks[0].status == "FAIL"
    assert report.checks[1].status == "SKIPPED"
    assert "package-build did not pass" in (report.checks[1].reason or "")


def test_custom_failed_producer_also_skips_dependent_smoke_check(
    tmp_path, monkeypatch
):
    checks = (
        CheckSpec("package-build", ("build",)),
        CheckSpec("package-wheel-smoke", ("smoke",)),
    )
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(1, "", "build failed", 0.01)

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=runner,
    )

    assert called == ["package-build"]
    assert tuple(result.status for result in report.checks) == ("FAIL", "SKIPPED")


def test_reversed_custom_dependency_executes_build_before_smoke(tmp_path, monkeypatch):
    checks = (
        CheckSpec("package-wheel-smoke", ("smoke",)),
        CheckSpec("package-build", ("build",)),
    )
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(0, "", "", 0.01)

    report = run_project_verification(
        project_root=tmp_path,
        checks=checks,
        runner=runner,
    )

    assert called == ["package-build", "package-wheel-smoke"]
    assert tuple(result.name for result in report.checks) == (
        "package-wheel-smoke",
        "package-build",
    )
    assert tuple(result.status for result in report.checks) == ("PASS", "PASS")


def test_successful_producer_runs_dependent_smoke_check(tmp_path, monkeypatch):
    canonical = (
        CheckSpec("package-build", ("build",)),
        CheckSpec("package-wheel-smoke", ("smoke",)),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(0, "", "", 0.01)

    report = run_project_verification(project_root=tmp_path, runner=runner)

    assert called == ["package-build", "package-wheel-smoke"]
    assert tuple(result.status for result in report.checks) == ("PASS", "PASS")


def test_failed_docker_build_skips_docker_smoke(tmp_path, monkeypatch):
    canonical = (
        CheckSpec(
            "docker-build",
            ("docker", "build"),
            required=False,
            environment="docker",
        ),
        CheckSpec(
            "docker-smoke-test",
            ("docker", "smoke"),
            required=False,
            environment="docker",
        ),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    monkeypatch.setattr(project_verification.shutil, "which", lambda executable: executable)
    called: list[str] = []

    def runner(spec: CheckSpec) -> CommandOutcome:
        called.append(spec.name)
        return CommandOutcome(1, "", "docker build failed", 0.01)

    report = run_project_verification(
        project_root=tmp_path,
        runner=runner,
        include_docker=True,
    )

    assert called == ["docker-build"]
    assert tuple(result.status for result in report.checks) == ("FAIL", "SKIPPED")


@pytest.mark.parametrize(
    ("include_docker", "docker_path", "reason"),
    (
        (False, "docker", "Docker checks require --include-docker."),
        (True, None, "Docker executable is unavailable."),
    ),
)
def test_docker_environment_skip_reason_is_preserved_for_both_checks(
    tmp_path,
    monkeypatch,
    include_docker,
    docker_path,
    reason,
):
    canonical = (
        CheckSpec(
            "docker-build",
            ("docker", "build"),
            required=False,
            environment="docker",
        ),
        CheckSpec(
            "docker-smoke-test",
            ("docker", "smoke"),
            required=False,
            environment="docker",
        ),
    )
    monkeypatch.setattr(project_verification, "build_check_specs", lambda root: canonical)
    monkeypatch.setattr(project_verification, "_scientific_data_coverage", lambda: {})
    monkeypatch.setattr(project_verification.shutil, "which", lambda executable: docker_path)

    report = run_project_verification(
        project_root=tmp_path,
        runner=lambda spec: (_ for _ in ()).throw(
            AssertionError("Docker runner should not be invoked")
        ),
        include_docker=include_docker,
    )

    assert tuple(result.status for result in report.checks) == ("SKIPPED", "SKIPPED")
    assert tuple(result.reason for result in report.checks) == (reason, reason)


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
    checks = (CheckSpec("docker-build", ("docker", "build"), required=False),)

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

        lock = next(check for check in report.checks if check.name == "golden-fixture-lock")
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
                "import os; from pathlib import Path; p=Path(os.environ['TEMP']); "
                "(p/'scratch.txt').write_text('temporary'); "
                "print(p); print(os.environ['TMP'])",
            ),
        )
    )

    assert outcome.returncode == 0
    temp, tmp = outcome.stdout.splitlines()
    assert temp == tmp
    scratch = Path(temp)
    assert scratch.parent == tmp_path / "output" / "verification-temp"
    assert not scratch.exists()


def test_default_runner_preserves_failed_scratch_without_touching_other_runs(tmp_path):
    retained = tmp_path / "output" / "verification-temp" / "other-run"
    retained.mkdir(parents=True)
    (retained / "keep.txt").write_text("other evidence", encoding="utf-8")
    outcome = _default_runner(tmp_path)(
        CheckSpec(
            "failing-check",
            (
                sys.executable,
                "-c",
                "import os; from pathlib import Path; p=Path(os.environ['TEMP']); "
                "(p/'evidence.txt').write_text('failed evidence'); print(p); raise SystemExit(1)",
            ),
        )
    )
    scratch = Path(outcome.stdout.strip())
    assert outcome.returncode == 1
    assert (scratch / "evidence.txt").read_text() == "failed evidence"
    assert str(scratch) in outcome.stderr
    assert (retained / "keep.txt").read_text() == "other evidence"


def test_default_runner_isolates_pytest_scratch_junit_and_audit_paths(
    tmp_path, monkeypatch
):
    invocations: list[tuple[tuple[str, ...], dict[str, str]]] = []

    def fake_run(command, **kwargs):
        invocations.append((tuple(command), dict(kwargs["env"])))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(project_verification.subprocess, "run", fake_run)
    runner = _default_runner(tmp_path)
    original = (
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--basetemp=shared-temp",
        "--junitxml",
        "shared.xml",
    )
    assert runner(CheckSpec("engine-tests-a", original)).returncode == 0
    assert runner(CheckSpec("engine-tests-b", original)).returncode == 0

    basetemps: list[Path] = []
    junit_paths: list[Path] = []
    audit_paths: list[Path] = []
    for command, env in invocations:
        basetemp_args = [arg for arg in command if arg.startswith("--basetemp=")]
        junit_args = [arg for arg in command if arg.startswith("--junitxml=")]
        assert len(basetemp_args) == 1
        assert len(junit_args) == 1
        assert "shared-temp" not in command
        assert "shared.xml" not in command
        basetemps.append(Path(basetemp_args[0].split("=", 1)[1]))
        junit_paths.append(Path(junit_args[0].split("=", 1)[1]))
        audit_paths.append(Path(env["PERFUME_PIPELINE_AUDIT_PATH"]))

    assert len(set(basetemps)) == 2
    assert len(set(junit_paths)) == 2
    assert len(set(audit_paths)) == 2
    assert all(path.is_absolute() for path in basetemps + junit_paths + audit_paths)
    assert all(path.name == "pytest" for path in basetemps)
    assert all(path.parent.name.startswith("check-") for path in basetemps)
    assert all(
        path.parent.parent == tmp_path / "output" / "verification-temp"
        for path in basetemps
    )
    assert all(path.parent == basetemp.parent for path, basetemp in zip(audit_paths, basetemps))
    assert junit_paths[0].parent == junit_paths[1].parent
    assert junit_paths[0].parent.parent == tmp_path / "verification_runs"


def test_pytest_isolation_does_not_add_unrequested_junit_output(tmp_path):
    command = project_verification._isolated_pytest_command(
        (sys.executable, "-m", "pytest", "-q"),
        spec_name="focused",
        command_temp=tmp_path / "scratch",
        run_output=tmp_path / "reports",
    )

    assert sum(arg.startswith("--basetemp=") for arg in command) == 1
    assert not any(arg.startswith("--junitxml=") for arg in command)


@pytest.mark.parametrize("fail_teardown", [False, True])
def test_test_session_scratch_follows_whole_session_outcome(tmp_path, fail_teardown):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "conftest.py").write_text(
        (PROJECT_ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tests_dir / "test_scratch.py").write_text(
        "import os, tempfile\nfrom pathlib import Path\nimport pytest\n"
        "@pytest.fixture\ndef evidence(tmp_path):\n"
        "    (tmp_path / 'fixture_evidence.txt').write_text('keep on failure')\n"
        "    yield tmp_path\n"
        f"    if {fail_teardown!r}: raise RuntimeError('expected teardown failure')\n"
        "def test_scratch(evidence):\n"
        "    raw = Path(tempfile.mkdtemp())\n"
        "    (raw / 'raw_evidence.txt').write_text('raw tempfile output')\n"
        "    Path(os.environ['PERFUME_PIPELINE_AUDIT_PATH']).write_text('test audit')\n",
        encoding="utf-8",
    )
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PERFUME_PIPELINE_AUDIT_PATH", None)
    outcome = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert outcome.returncode == int(fail_teardown), outcome.stdout + outcome.stderr
    scratch = tmp_path / "output" / "pytest-temp"
    for filename in ("fixture_evidence.txt", "raw_evidence.txt", "pipeline_audit.jsonl"):
        assert bool(list(scratch.rglob(filename))) is fail_teardown


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


def test_partial_report_path_cannot_overwrite_canonical_full_evidence(tmp_path, monkeypatch):
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
