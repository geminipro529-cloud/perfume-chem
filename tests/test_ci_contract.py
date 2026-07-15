from __future__ import annotations

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"

REQUIRED_JOBS = {
    "backend-lint",
    "backend-typecheck",
    "backend-tests",
    "engine-lint",
    "engine-typecheck",
    "engine-tests",
    "scientific-audit",
    "material-data-validation",
    "knowledge-rule-validation",
    "golden-formula-regression",
    "package-build",
    "docker-build",
    "docker-smoke-test",
}


def _workflow() -> dict:
    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_ci_targets_the_real_release_branch_and_all_pull_requests():
    workflow = _workflow()
    triggers = workflow["on"]

    assert triggers["push"]["branches"] == ["master"]
    assert "pull_request" in triggers
    assert "workflow_dispatch" in triggers


def test_ci_exposes_every_phase_zero_required_job():
    jobs = set(_workflow()["jobs"])

    assert REQUIRED_JOBS <= jobs


def test_ci_uses_the_single_project_verifier_contract():
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "pipeline_audit.py project-verify" in workflow_text
    assert "--only" in workflow_text


def test_ci_pins_python_shards_timeouts_and_junit_evidence():
    workflow = _workflow()
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert workflow["env"]["PYTHON_VERSION"] == "3.11"
    assert workflow["jobs"]["engine-tests"]["strategy"]["matrix"]["shard"] == [
        "truth-core",
        "data-knowledge",
        "gates-families",
        "legacy",
    ]
    assert all("timeout-minutes" in job for job in workflow["jobs"].values())
    assert "verification_runs/backend.xml" in workflow_text
    assert "verification_runs/engine-${{ matrix.shard }}.xml" in workflow_text
    assert "actions/upload-artifact@v4" in workflow_text


def test_ci_smokes_installed_wheel_and_real_container_health():
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "--only package-wheel-smoke" in workflow_text
    assert "docker compose" not in workflow_text
    assert "--only docker-build --only docker-smoke-test" in workflow_text
    assert "health_check" not in workflow_text
