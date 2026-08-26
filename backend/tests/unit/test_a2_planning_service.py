from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.models.lab_planning import (
    LabBuildPlanLine,
    LabBuildPlanVersion,
    LabInventoryMappingEvidenceLink,
    LabTargetEvidenceLink,
)
from app.services.lab_planning import (
    BuildPlanLineInput,
    InventoryMappingInput,
    PlanningConflictError,
    PlanningDomainError,
    TargetLineInput,
)
from app.services.lab_service import LabService
from tests.a2_planning_fixtures import (
    _build_plan_command,
    _formula_versions,
    _plan_at_status,
    _planning_graph,
    _target_command,
)


@pytest.mark.asyncio
async def test_target_revision_is_append_only_hash_chained_and_evidence_backed(
    db_session,
):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="target:jasmine",
        classification="EXACT",
        source_locator="test://target-jasmine",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    first = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Initial documentary hypothesis",
        )
    )
    second = await service.revise_target_hypothesis(
        first.id,
        _target_command(
            evidence_id=evidence.id,
            rationale="New documentary evidence",
        ),
    )
    assert second.target_id == first.target_id
    assert second.version_number == 2
    assert second.parent_version_id == first.id
    assert second.parent_sha256 == first.content_sha256
    assert await service.repository.get_target_version(first.id) == first
    links = await db_session.scalar(
        select(func.count()).select_from(LabTargetEvidenceLink)
    )
    assert links == 2


@pytest.mark.asyncio
async def test_acceptance_references_one_immutable_target_version(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="target:acceptance",
        classification="EXACT",
        source_locator="test://target-acceptance",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    target = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Acceptance fixture",
        )
    )
    accepted = await service.accept_target(
        target.id,
        reviewer="Sol",
        rationale="Evidence gate passed",
    )
    assert accepted.target_hypothesis_version_id == target.id
    with pytest.raises(PlanningConflictError) as duplicate:
        await service.accept_target(
            target.id,
            reviewer="Sol",
            rationale="Duplicate",
        )
    assert duplicate.value.code == "TARGET_ALREADY_ACCEPTED"


@pytest.mark.asyncio
async def test_formula_lineage_rejects_self_edge_and_cycle(db_session):
    service = LabService(db_session)
    parent, child = await _formula_versions(service)
    edge = await service.link_formula_version(
        child.id,
        parent.id,
        relationship_kind="DERIVED_FROM",
        change={"kind": "REBALANCE"},
        rationale="Immutable revision",
    )
    assert edge.child_version_id == child.id
    with pytest.raises(PlanningConflictError) as self_edge:
        await service.link_formula_version(
            parent.id,
            parent.id,
            relationship_kind="DERIVED_FROM",
            change={},
            rationale="Self",
        )
    assert self_edge.value.code == "FORMULA_VERSION_SELF_EDGE"
    with pytest.raises(PlanningConflictError) as cycle:
        await service.link_formula_version(
            parent.id,
            child.id,
            relationship_kind="DERIVED_FROM",
            change={"kind": "REBALANCE"},
            rationale="Cycle",
        )
    assert cycle.value.code == "FORMULA_VERSION_CYCLE"


@pytest.mark.asyncio
async def test_mapping_never_rewrites_target_identity_and_is_evidence_backed(
    db_session,
):
    service, target, acceptance, mapping, target_line, stock, _evidence = (
        await _planning_graph(db_session)
    )
    assert mapping.target_line_id == target_line.id
    assert mapping.stock_solution_id == stock.id
    assert target_line.target_identity == "Jasmine Absolute"
    assert target.id == acceptance.target_hypothesis_version_id
    assert (
        await db_session.scalar(
            select(func.count()).select_from(
                LabInventoryMappingEvidenceLink
            )
        )
        == 1
    )
    assert service is not None


@pytest.mark.asyncio
async def test_mapping_revision_is_hash_chained(db_session):
    service, _target, _acceptance, mapping, _target_line, _stock, evidence = (
        await _planning_graph(db_session)
    )
    revised = await service.revise_inventory_mapping(
        mapping.id,
        InventoryMappingInput(
            target_line_id=mapping.target_line_id,
            stock_solution_id=mapping.stock_solution_id,
            target_identity=mapping.target_identity,
            build_identity=mapping.build_identity,
            identity_status=mapping.identity_status,
            inventory_status=mapping.inventory_status,
            substitution_class=mapping.substitution_class,
            preserved_functions=("heart",),
            lost_functions=("diffusion",),
            confidence=0.8,
            rationale="New lot assessment",
            evidence_links=(evidence.id,),
        ),
    )
    assert revised.mapping_id == mapping.mapping_id
    assert revised.version_number == 2
    assert revised.parent_version_id == mapping.id
    assert revised.parent_sha256 == mapping.content_sha256


@pytest.mark.asyncio
async def test_exact_mapping_rejects_contradictory_stock_identity(db_session):
    service, _target, _acceptance, mapping, target_line, _stock, evidence = (
        await _planning_graph(db_session)
    )
    other_material = await service.create_material("Orris Butter")
    other_stock = await service.create_stock_solution(
        material_id=other_material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=1.0,
    )
    with pytest.raises(PlanningConflictError) as error:
        await service.revise_inventory_mapping(
            mapping.id,
            InventoryMappingInput(
                target_line_id=target_line.id,
                stock_solution_id=other_stock.id,
                target_identity="Jasmine Absolute",
                build_identity="Jasmine Absolute",
                identity_status="EXACT",
                inventory_status="EXACT_LOT_AVAILABLE",
                substitution_class="EXACT",
                preserved_functions=(),
                lost_functions=(),
                confidence=1.0,
                rationale="Contradictory exact identity",
                evidence_links=(evidence.id,),
            ),
        )
    assert error.value.code == "EXACT_MAPPING_IDENTITY_MISMATCH"


@pytest.mark.asyncio
async def test_build_plan_is_independent_and_revision_copies_complete_lines(
    db_session,
):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    draft = await service.create_build_plan(
        _build_plan_command(
            target,
            acceptance,
            mapping,
            target_line,
            stock,
            evidence,
        )
    )
    review = await service.transition_build_plan(
        draft.id,
        next_status="UNDER_REVIEW",
        actor="reviewer",
        rationale="Ready for review",
    )
    assert review.plan_id == draft.plan_id
    assert review.version_number == 2
    assert review.parent_version_id == draft.id
    assert review.parent_sha256 == draft.content_sha256
    draft_lines = await service.repository.build_plan_lines(draft.id)
    review_lines = await service.repository.build_plan_lines(review.id)
    assert len(draft_lines) == len(review_lines) == 1
    ignored = {"id", "build_plan_version_id", "created_at"}
    assert {
        key: value
        for key, value in vars(draft_lines[0]).items()
        if not key.startswith("_") and key not in ignored
    } == {
        key: value
        for key, value in vars(review_lines[0]).items()
        if not key.startswith("_") and key not in ignored
    }
    assert await db_session.scalar(
        select(func.count()).select_from(LabBuildPlanVersion)
    ) == 2
    assert await db_session.scalar(
        select(func.count()).select_from(LabBuildPlanLine)
    ) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("current", "next_status"),
    [
        ("DRAFT", "APPROVED"),
        ("UNDER_REVIEW", "RESERVED"),
        ("APPROVED", "CLOSED"),
    ],
)
async def test_build_plan_rejects_invalid_transition(
    db_session,
    current,
    next_status,
):
    plan = await _plan_at_status(db_session, current)
    with pytest.raises(PlanningConflictError) as error:
        await LabService(db_session).transition_build_plan(
            plan.id,
            next_status=next_status,
            actor="Sol",
            rationale="Invalid transition",
        )
    assert error.value.code == "INVALID_BUILD_PLAN_TRANSITION"
    assert str(error.value) == (
        f"Build plan cannot transition from {current} to {next_status}."
    )


@pytest.mark.parametrize(
    "factory",
    [
        lambda: TargetLineInput(
            line_id="line",
            target_identity="Jasmine",
            source_name="Source",
            grade="absolute",
            presence_probability=1.1,
            target_raw_quantity=1.0,
            target_active_quantity=0.1,
            unit="g",
            concentration_fraction=0.1,
            concentration_basis="mass_fraction",
            functional_roles=(),
            evidence_links=("evidence",),
            uncertainty={},
        ),
        lambda: BuildPlanLineInput(
            line_id="line",
            target_line_id="target-line",
            target_identity="Jasmine",
            inventory_mapping_version_id="mapping",
            stock_solution_id="stock",
            planned_raw_quantity=1.0,
            planned_active_quantity=0.1,
            unit="g",
            concentration_fraction=0.1,
            concentration_basis="mass_fraction",
            density_g_ml=None,
            density_source=None,
            standard_uncertainty=None,
            measurement_method="gravimetric",
            resolution=0,
            expected_transfer_loss=0,
            substitution_class="EXACT",
            preserved_functions=(),
            lost_functions=(),
            rationale="Invalid resolution",
            evidence_links=("evidence",),
        ),
        lambda: InventoryMappingInput(
            target_line_id="target-line",
            stock_solution_id=None,
            target_identity="Jasmine",
            build_identity="Jasmine",
            identity_status="EXACT",
            inventory_status="EXACT_LOT_AVAILABLE",
            substitution_class="EXACT",
            preserved_functions=(),
            lost_functions=(),
            confidence=float("nan"),
            rationale="Invalid confidence",
            evidence_links=("evidence",),
        ),
    ],
)
def test_planning_dtos_reject_invalid_quantities(factory):
    with pytest.raises(PlanningDomainError):
        factory()


def test_planning_dtos_are_frozen():
    line = TargetLineInput(
        line_id="line",
        target_identity="Jasmine",
        source_name="Source",
        grade="absolute",
        presence_probability=1.0,
        target_raw_quantity=1.0,
        target_active_quantity=0.1,
        unit="g",
        concentration_fraction=0.1,
        concentration_basis="mass_fraction",
        functional_roles=(),
        evidence_links=("evidence",),
        uncertainty={},
    )
    assert replace(line, grade="concrete").grade == "concrete"
    with pytest.raises((AttributeError, TypeError)):
        line.grade = "concrete"
