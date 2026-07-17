from __future__ import annotations

from pathlib import Path

import tomllib

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


def test_hosted_github_actions_workflow_is_removed():
    assert not WORKFLOW_PATH.exists()


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
