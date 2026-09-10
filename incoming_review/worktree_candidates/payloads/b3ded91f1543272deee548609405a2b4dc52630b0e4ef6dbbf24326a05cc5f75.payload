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
    V7_ADMITTED_ARCHITECTURE_MODULE_IDS,
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


def test_v6_frozen_registry_bytes_and_admission_contract_remain_exact() -> None:
    payload = json.loads(V6.read_text(encoding="utf-8"))
    assert hashlib.sha256(V6.read_bytes()).hexdigest() == (
        "fe2b4a975cec2d89869bdd1f1b9a3d00569902769d199f38503b8448376b506c"
    )
    assert payload["schema_version"] == "complexity_module_registry_v6"
    assert hashlib.sha256(V5.read_bytes()).hexdigest() == payload["base_registry"][
        "sha256"
    ]
    assert payload["admitted_scope"] == {
        "cypress_target_architecture": True,
        "target_variant_rebuild": True,
        "inventory_and_authority_guarding": True,
        "experiment_design": True,
        "evidence_only_request_routing": False,
    }
    assert payload["authority_flags"] == ALL_FALSE_AUTHORITY
    assert {row["module_id"] for row in payload["module_overrides"]} == {
        "architectural-delta-engine",
        "temporal-sensory-ledger",
        "hedonic-preference-learner",
    }
    assert tuple(row["module_id"] for row in payload["module_additions"]) == (
        "material-capability-atlas",
        "cypress-heart-frontier",
        "family-depth",
        "architecture-compiler",
        "harmonic-synthesis",
        "cypress-harmonic-program",
        "harmonic-request-router",
        "floral-depth-library",
        "depth-comparison-library",
    )
    assert payload["admission_evidence"] == [
        {
            "path": "data/governance/cypress_xhigh_screening_receipt_20260831.json",
            "sha256": "926cb104633ae05850a8e8b7d04d6c05515c3212da1cafea14c03b3a706e167a",
        },
        {
            "path": "data/governance/cypress_xhigh_admission_receipt_20260831.json",
            "sha256": "a7d7a4a15f0e8173cdd3d8bb6a5460f7660474aeffc0e73f865e6f20027dfc22",
        },
    ]


def test_v6_strict_loader_fails_closed_after_declared_successors() -> None:
    with pytest.raises(
        ValueError,
        match="source binding hash mismatch: engine/sensory/ledger.py",
    ):
        load_harmonic_runtime_registry(ROOT, registry_path=V6)


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
    current = load_harmonic_runtime_registry(ROOT)
    result = run_admitted_cypress_harmonic(
        HarmonicRouteRequestV1(
            request_id="CYP-02-RUNTIME-SMOKE",
            domains=(HarmonicRequestDomain.ARCHITECTURE,),
            target_identity="CYP-02 Cypress subject architecture",
        ),
        project_root=ROOT,
    )

    assert result.registry_sha256 == current.registry_sha256
    assert result.admitted_module_ids == V7_ADMITTED_ARCHITECTURE_MODULE_IDS
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
