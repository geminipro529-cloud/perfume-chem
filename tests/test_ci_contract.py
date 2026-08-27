from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
HOOK_CONFIG_PATH = PROJECT_ROOT / ".pre-commit-config.yaml"


def _hook_config() -> dict:
    return yaml.safe_load(HOOK_CONFIG_PATH.read_text(encoding="utf-8"))


def _local_hooks() -> dict[str, dict]:
    config = _hook_config()
    local_repository = next(repo for repo in config["repos"] if repo["repo"] == "local")
    return {hook["id"]: hook for hook in local_repository["hooks"]}


def test_hosted_github_actions_workflow_is_pinned_and_fail_closed():
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    triggers = workflow.get("on", workflow.get(True))

    assert triggers["pull_request"]["branches"] == ["master"]
    assert triggers["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in triggers
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is True

    action_revisions = re.findall(r"uses:\s+[^@\s]+@([0-9a-f]{40})", workflow_text)
    assert len(action_revisions) == 4

    verify_steps = workflow["jobs"]["verify"]["steps"]
    verify_commands = "\n".join(
        str(step.get("run", "")) for step in verify_steps
    )
    assert "poetry run pytest --cov=app" in verify_commands
    assert "poetry run pip-audit --local --skip-editable" in verify_commands
    assert "project-verify --json" in verify_commands
    container_job = workflow["jobs"]["container-build"]
    container_commands = "\n".join(
        str(step.get("run", "")) for step in container_job["steps"]
    )
    assert container_job["needs"] == "verify"
    assert "docker build --file backend/Dockerfile" in container_commands
    assert "engine.project_verification docker-smoke" in container_commands
    assert "--timeout-seconds 90" in container_commands


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
