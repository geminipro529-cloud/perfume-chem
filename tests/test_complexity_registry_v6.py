from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from engine.perception.harmonic_request_router import (
    HarmonicRequestDomain,
    HarmonicRouteRequestV1,
)
from engine.perception.harmonic_runtime_registry import (
    V6_ADMITTED_ARCHITECTURE_MODULE_IDS,
    load_harmonic_runtime_registry,
)
from engine.solforge.harmonic_runtime import (
    HarmonicRuntimeAdmissionError,
    run_admitted_cypress_harmonic,
)
from tests.test_complexity_registry_v5 import _copy_v5_project

ROOT = Path(__file__).resolve().parents[1]
V5 = ROOT / "configs/complexity/complexity_module_registry_v5.json"
V6 = ROOT / "configs/complexity/complexity_module_registry_v6.json"
ALL_FALSE_AUTHORITY = {
    "compounding": False,
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "scientific": False,
    "sensory": False,
    "similarity": False,
    "stability": False,
}


def test_v6_is_additive_and_admits_only_the_benchmarked_architecture_scope() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    registry = load_harmonic_runtime_registry(ROOT)

    assert registry.schema_version == "complexity_module_registry_v6"
    assert hashlib.sha256(V5.read_bytes()).hexdigest() == payload["base_registry"][
        "sha256"
    ]
    assert registry.admitted_architecture_module_ids == (
        V6_ADMITTED_ARCHITECTURE_MODULE_IDS
    )
    assert registry.evidence_only_module_ids == (
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    )
    assert registry.admitted_scope == {
        "cypress_target_architecture": True,
        "target_variant_rebuild": True,
        "inventory_and_authority_guarding": True,
        "experiment_design": True,
        "evidence_only_request_routing": False,
    }
    assert registry.authority_flags == ALL_FALSE_AUTHORITY


def test_v6_preserves_v5_tombstones_and_never_reactivates_retired_cards() -> None:
    registry = load_harmonic_runtime_registry(ROOT)

    assert {
        "construction-profile",
        "complexity-expansion-frontier",
        "musk-design-restraint",
        "citrus-architecture-selector",
        "within-sniff-observation-contract",
        "temporal-observation-contract",
        "order-balance-contract",
        "sensory-panel-contract",
    }.issubset(registry.nonruntime_base_module_ids)
    assert not set(registry.nonruntime_base_module_ids).intersection(
        registry.admitted_architecture_module_ids
    )
    assert "advanced-musk-intelligence" in registry.nonruntime_base_module_ids


def test_v6_verifies_every_frozen_evidence_and_source_binding() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    registry = load_harmonic_runtime_registry(ROOT)

    for record in (
        *payload["admission_evidence"],
        *payload["source_bindings"],
    ):
        source = ROOT / record["path"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == record["sha256"]
    assert registry.full_gate == {
        "case_count": 6,
        "wins_vs_plain": 6,
        "wins_vs_placebo": 5,
        "median_gain_vs_plain": 10,
        "median_gain_vs_placebo": 13.5,
        "integrated_critical_errors": [],
    }


def _copy_v6_project(tmp_path: Path) -> tuple[Path, Path]:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    project, _ = _copy_v5_project(tmp_path)
    paths = {
        payload["base_registry"]["path"],
        *(record["path"] for record in payload["admission_evidence"]),
        *(record["path"] for record in payload["source_bindings"]),
    }
    target_registry = project / V6.relative_to(ROOT)
    target_registry.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(V6, target_registry)
    for relative in sorted(paths):
        source = ROOT / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
    return project, target_registry


def test_v6_tampering_fails_closed(tmp_path: Path) -> None:
    project, registry_path = _copy_v6_project(tmp_path / "source")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    source = project / payload["source_bindings"][0]["path"]
    source.write_bytes(source.read_bytes() + b"\n# drift\n")
    with pytest.raises(ValueError, match="source binding hash mismatch"):
        load_harmonic_runtime_registry(project, registry_path=registry_path)

    project, registry_path = _copy_v6_project(tmp_path / "receipt")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    receipt = project / payload["admission_evidence"][1]["path"]
    receipt.write_bytes(receipt.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="admission evidence hash mismatch"):
        load_harmonic_runtime_registry(project, registry_path=registry_path)

    project, registry_path = _copy_v6_project(tmp_path / "authority")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["authority_flags"]["hedonic"] = True
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="authority flags"):
        load_harmonic_runtime_registry(project, registry_path=registry_path)


@pytest.mark.parametrize(
    "domains",
    [
        (HarmonicRequestDomain.TEMPORAL_EVIDENCE,),
        (HarmonicRequestDomain.PREFERENCE_EVIDENCE,),
        (
            HarmonicRequestDomain.ARCHITECTURE,
            HarmonicRequestDomain.TEMPORAL_EVIDENCE,
        ),
    ],
)
def test_runtime_rejects_every_unadmitted_evidence_only_or_mixed_scope(
    domains: tuple[HarmonicRequestDomain, ...],
) -> None:
    with pytest.raises(
        HarmonicRuntimeAdmissionError,
        match="EVIDENCE_ONLY_REQUEST_ROUTING_NOT_ADMITTED",
    ):
        run_admitted_cypress_harmonic(
            HarmonicRouteRequestV1(
                request_id="UNADMITTED-SCOPE",
                domains=domains,
                target_identity=(
                    "CYP-02 Cypress subject architecture"
                    if HarmonicRequestDomain.ARCHITECTURE in domains
                    else None
                ),
            ),
            project_root=ROOT,
        )


def test_runtime_runs_exact_cyp02_architecture_with_no_downstream_authority() -> None:
    result = run_admitted_cypress_harmonic(
        HarmonicRouteRequestV1(
            request_id="CYP-02-RUNTIME-SMOKE",
            domains=(HarmonicRequestDomain.ARCHITECTURE,),
            target_identity="CYP-02 Cypress subject architecture",
        ),
        project_root=ROOT,
    )

    assert result.admitted_module_ids == V6_ADMITTED_ARCHITECTURE_MODULE_IDS
    assert result.route.domains == (HarmonicRequestDomain.ARCHITECTURE,)
    assert result.route.vote_counting_used is False
    assert result.program.frontier_result.target.target_identity == (
        "A luxurious Cypress-subject perfume in which high-quality French "
        "Cypress EO is made more beautiful by a relational floral heart, rooted "
        "depth, controlled contrast, and temporal reveal rather than by "
        "botanical literalism"
    )
    assert result.authority_flags == ALL_FALSE_AUTHORITY
    assert result.program.formula_mutation_authorized is False
    assert result.program.physical_execution_authorized is False
    assert result.program.hedonic_authority is False
    assert result.program.release_authority is False


def test_runtime_rejects_an_unbenchmarked_architecture_identity() -> None:
    with pytest.raises(
        HarmonicRuntimeAdmissionError,
        match="TARGET_IDENTITY_OUTSIDE_ADMITTED_RUNTIME_SCOPE",
    ):
        run_admitted_cypress_harmonic(
            HarmonicRouteRequestV1(
                request_id="UNSEEN-RUNTIME-TARGET",
                domains=(HarmonicRequestDomain.ARCHITECTURE,),
                target_identity="Cypress and Orange Blossom Nocturne",
            ),
            project_root=ROOT,
        )
