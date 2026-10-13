from __future__ import annotations

import tomllib
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "checks.yml"
HOOK_CONFIG_PATH = PROJECT_ROOT / ".pre-commit-config.yaml"


def _hook_config() -> dict:
    return yaml.safe_load(HOOK_CONFIG_PATH.read_text(encoding="utf-8"))


def _local_hooks() -> dict[str, dict]:
    config = _hook_config()
    local_repository = next(repo for repo in config["repos"] if repo["repo"] == "local")
    return {hook["id"]: hook for hook in local_repository["hooks"]}


def test_hosted_checks_mirror_the_pre_push_gate_and_backend_order():
    # Direction 4 (12 Oct 2026): hosted checks are back, mirroring the local gate.
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert "pull_request" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    quick_runs = [step.get("run", "") for step in workflow["jobs"]["quick-verify"]["steps"]]
    assert "python scripts/pipeline_audit.py project-verify --quick --json" in quick_runs
    backend_runs = [step.get("run", "") for step in workflow["jobs"]["backend"]["steps"]]
    order = [
        next(i for i, run in enumerate(backend_runs) if run.startswith(command))
        for command in ("poetry run ruff check app", "poetry run mypy app", "poetry run pytest")
    ]
    assert order == sorted(order)
    assert any("compare_failures.py" in run for run in backend_runs)
    assert (PROJECT_ROOT / "backend" / "tests" / "known_failures.txt").is_file()
    assert "secrets." not in WORKFLOW_PATH.read_text(encoding="utf-8")


def test_quick_project_verification_runs_before_push():
    config = _hook_config()
    hook = _local_hooks()["project-verify-quick"]

    assert config["minimum_pre_commit_version"] == "4.4.0"
    assert config["default_install_hook_types"] == ["pre-push"]
    assert hook["entry"] == "python scripts/pipeline_audit.py project-verify --quick --json"
    assert hook["language"] == "unsupported"
    assert hook["stages"] == ["pre-push", "manual"]
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False


def test_full_project_verification_remains_an_explicit_manual_gate():
    hook = _local_hooks()["project-verify-full"]

    assert hook["entry"] == "python scripts/pipeline_audit.py project-verify --json"
    assert hook["stages"] == ["manual"]
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False


def test_docker_verification_remains_available_as_an_explicit_manual_gate():
    hook = _local_hooks()["project-verify-docker"]

    assert hook["entry"].endswith("project-verify --include-docker --json")
    assert hook["stages"] == ["manual"]
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False


def test_root_development_extra_installs_pre_commit():
    project = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["optional-dependencies"]["dev"]

    assert any(requirement.startswith("pre-commit") for requirement in dependencies)
    assert any(requirement.startswith("build") for requirement in dependencies)


def test_readme_documents_installation_and_local_trust_boundary():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "pre-commit install --hook-type pre-push" in readme
    assert "developer-controlled" in readme
