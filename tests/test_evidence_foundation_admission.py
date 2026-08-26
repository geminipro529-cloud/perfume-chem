from __future__ import annotations

import hashlib
import json
from pathlib import Path

from engine.perception.complexity_registry import (
    ModuleState,
    load_current_complexity_registry,
)

ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE = ROOT / "data/governance/evidence_foundation_admission_v1.json"
SCREEN_ROOT = ROOT / "data/benchmarks/solforge/evidence_foundation_screen_v2"
CORPUS = ROOT / "tests/fixtures/complexity_replacement_benchmark_cases_v8.json"
RETEST = ROOT / "data/governance/protected_evidence_retest_admission_v1.json"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sidecar_sha256(path: Path) -> str:
    return path.with_suffix(".sha256").read_text(encoding="ascii").split()[0]


def test_evidence_foundation_all_stop_is_hash_bound_and_runtime_unreachable() -> None:
    payload = json.loads(GOVERNANCE.read_text(encoding="utf-8"))
    decisions = json.loads(
        (SCREEN_ROOT / "screen_decisions.json").read_text(encoding="utf-8")
    )

    assert _file_sha256(GOVERNANCE) == _sidecar_sha256(GOVERNANCE)
    assert payload["schema_version"] == "evidence_foundation_admission_v1"
    assert payload["decision"] == "ALL_STOP_RUNTIME_UNREACHABLE"
    assert payload["confirmation_started"] is False
    assert payload["registry_disposition"] == {
        "current_registry": "configs/complexity/complexity_module_registry_v6.json",
        "registry_v6_created": True,
        "runtime_admission_changed": False,
    }
    assert (
        ROOT / "configs/complexity/complexity_module_registry_v6.json"
    ).is_file()

    evidence = payload["evidence"]
    expected_paths = {
        "corpus": CORPUS,
        "effective_manifest": SCREEN_ROOT / "effective_manifest.json",
        "execution_receipt": SCREEN_ROOT / "execution_receipt.json",
        "receipt": SCREEN_ROOT / "receipt.json",
        "screen_decisions": SCREEN_ROOT / "screen_decisions.json",
    }
    assert set(evidence) == set(expected_paths)
    for key, path in expected_paths.items():
        assert evidence[key]["path"] == path.relative_to(ROOT).as_posix()
        assert evidence[key]["file_sha256"] == _file_sha256(path)
        assert evidence[key]["file_sha256"] == _sidecar_sha256(path)

    decision_by_module = {
        row["module_id"]: row for row in decisions["decisions"]
    }
    module_by_id = {row["module_id"]: row for row in payload["modules"]}
    assert set(module_by_id) == {
        "temporal_oav_error_sentinel",
        "temporal_sensory_ledger",
        "hedonic_preference_learner",
    }
    assert set(module_by_id) == set(decision_by_module)
    for module_id, module in module_by_id.items():
        decision = decision_by_module[module_id]
        assert module["state"] == "RETAINED_AS_PROVENANCE_TOMBSTONE"
        assert module["runtime_reachable"] is False
        assert module["confirmation_started"] is False
        assert module["plain_control_wins"] == decision["plain_control_wins"]
        assert module["placebo_wins"] == decision["placebo_wins"]
        assert module["reason_codes"] == decision["reasons"]

    assert all(value is False for value in payload["authority"].values())


def test_current_registry_exposes_only_the_previously_admitted_delta_engine() -> None:
    registry = load_current_complexity_registry(ROOT)
    admitted = {
        module.module_id for module in registry.modules if module.runtime_eligible
    }
    assert admitted == {"architectural-delta-engine"}

    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = registry.module_by_id(module_id)
        assert module.state is ModuleState.RETIRED_BENCHMARK_UNDERPERFORMER
        assert module.import_path is None
        assert module.runtime_eligible is False

    assert "temporal-oav-error-sentinel" not in {
        module.module_id for module in registry.modules
    }


def test_protected_evidence_retest_is_hash_bound_and_rejects_both_learners() -> None:
    payload = json.loads(RETEST.read_text(encoding="utf-8"))

    assert _file_sha256(RETEST) == _sidecar_sha256(RETEST)
    assert payload["decision"] == "ARCHITECTURAL_ONLY_TEMPORAL_AND_HEDONIC_RETIRED"
    assert payload["model_identity"]["model"] == "gpt-5.6-sol"
    assert payload["model_identity"]["reasoning_effort"] == "xhigh"
    assert payload["model_identity"]["fast_mode"] == "NOT_EXPOSED"
    assert payload["module_dispositions"]["architectural-delta-engine"][
        "runtime_reachable"
    ] is True
    for module_id in ("temporal-sensory-ledger", "hedonic-preference-learner"):
        module = payload["module_dispositions"][module_id]
        assert module["state"] == "RETIRED_BENCHMARK_UNDERPERFORMER"
        assert module["runtime_reachable"] is False
    confirmation = payload["benchmark_evidence"][-1]["combined_six_case_result"]
    assert confirmation["wins_vs_plain"] == 3
    assert confirmation["wins_vs_noop"] == 3
    assert confirmation["median_gain_vs_plain"] == 1.0
    assert confirmation["median_gain_vs_noop"] == 1.0
    assert confirmation["admitted"] is False
    assert all(value is False for value in payload["authority"].values())
