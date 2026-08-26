from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.perception.complexity_registry import ModuleState, load_complexity_registry

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_V3 = ROOT / "configs/complexity/complexity_module_registry_v3.json"
REGISTRY_V4 = ROOT / "configs/complexity/complexity_module_registry_v4.json"


def test_registry_v3_exposes_no_solforge_or_replacement_runtime_imports() -> None:
    registry = load_complexity_registry(ROOT, REGISTRY_V3)
    assert not any(module.runtime_eligible for module in registry.modules)
    for module in registry.modules:
        if module.state is not ModuleState.ADMITTED_RUNTIME:
            assert module.import_path is None
    states = {module.module_id: module.state for module in registry.modules}
    assert states["solforge-shadow-orchestrator"] is ModuleState.EXPERIMENT_COMPILER
    assert states["architectural-delta-engine"] is ModuleState.EXPERIMENT_COMPILER
    assert states["temporal-sensory-ledger"] is ModuleState.DIAGNOSTIC_ONLY
    assert states["hedonic-preference-learner"] is ModuleState.DIAGNOSTIC_ONLY


def test_frozen_registry_v4_fails_closed_after_rebuild_source_drift() -> None:
    with pytest.raises(ValueError, match="source binding hash mismatch"):
        load_complexity_registry(ROOT, REGISTRY_V4)


def test_retired_complexity_cards_are_provenance_tombstones() -> None:
    registry = load_complexity_registry(ROOT, REGISTRY_V3)
    states = {module.module_id: module.state for module in registry.modules}
    retired = {
        "construction-profile",
        "complexity-expansion-frontier",
        "musk-design-restraint",
        "complexity-model-admission",
        "complexity-model-lifecycle",
        "within-sniff-observation-contract",
        "temporal-observation-contract",
        "order-balance-contract",
        "sensory-panel-contract",
        "citrus-architecture-selector",
    }
    assert {module_id: states[module_id] for module_id in retired} == {
        module_id: ModuleState.PROVENANCE_TOMBSTONE for module_id in retired
    }


def test_existing_complexity_runtime_has_no_solforge_import() -> None:
    runtime_files = (
        "engine/perception/complexity_ensemble.py",
        "engine/perception/complexity_xhigh.py",
        "engine/perception/complexity_benchmark.py",
        "engine/perception/complexity_adapters.py",
    )
    for relative in runtime_files:
        text = (ROOT / relative).read_text(encoding="utf-8").casefold()
        assert "engine.solforge" not in text


def test_solforge_modules_do_not_import_legacy_composition_proxies() -> None:
    forbidden = (
        "engine.hedonic_model",
        "engine.optimizer.scoring",
        "engine.pipeline.oav_authority",
        "engine.pipeline.release_scoring",
    )
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "engine/solforge").glob("*.py"))
    )
    assert not any(name in source for name in forbidden)


def test_registry_v3_authority_flags_are_all_false() -> None:
    payload = json.loads(
        (ROOT / "configs/complexity/complexity_module_registry_v3.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["authority_flags"] == {
        "compounding": False,
        "formula": False,
        "hedonic": False,
        "purchase": False,
        "release": False,
        "safety": False,
        "scientific": False,
        "sensory": False,
    }


def test_admitted_runtime_import_graph_excludes_failed_evidence_modules() -> None:
    runtime = (ROOT / "engine/solforge/runtime.py").read_text(encoding="utf-8")
    architectural = (
        ROOT / "engine/solforge/architectural_adapter.py"
    ).read_text(encoding="utf-8")
    admitted_source = f"{runtime}\n{architectural}".casefold()

    assert "engine.solforge.architectural_adapter" in runtime
    for forbidden in (
        "engine.solforge.orchestrator",
        "engine.solforge.adapters",
        "engine.solforge.governance",
        "engine.hedonic_evidence",
        "engine.preference",
        "engine.preference_davidson",
        "engine.preference_validation",
        "engine.sensory.ledger",
        "engine.pipeline.oav_evidence",
    ):
        assert forbidden not in admitted_source
