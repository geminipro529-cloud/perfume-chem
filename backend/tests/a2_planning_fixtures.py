from app.services.lab_planning import (
    BuildPlanInput,
    BuildPlanLineInput,
    InventoryMappingInput,
    TargetHypothesisInput,
    TargetLineInput,
)
from app.services.lab_service import LabService


def _target_command(
    *,
    evidence_id: str,
    rationale: str,
) -> TargetHypothesisInput:
    return TargetHypothesisInput(
        product_key="reference:iris-control",
        schema_version="a2-target-v1",
        author="Sol",
        provenance_activity={"activity": "test-fixture"},
        uncertainty_summary={"basis": "bounded-test"},
        rationale=rationale,
        lines=(
            TargetLineInput(
                line_id="target-line-jasmine",
                target_identity="Jasmine Absolute",
                source_name="Jasmine absolute reference",
                grade="absolute",
                presence_probability=0.95,
                target_raw_quantity=1.0,
                target_active_quantity=0.1,
                unit="g",
                concentration_fraction=0.1,
                concentration_basis="mass_fraction",
                functional_roles=("heart", "diffusion"),
                evidence_links=(evidence_id,),
                uncertainty={"standard_uncertainty_g": 0.01},
            ),
        ),
    )


async def _formula_versions(service: LabService):
    formula = await service.create_formula("A2 lineage fixture")
    parent = await service.add_formula_version(
        formula.id,
        brief={"name": "parent"},
        constraints={},
        components=(),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={"name": "child"},
        constraints={},
        components=(),
    )
    return parent, child


async def _planning_graph(db_session):
    service = LabService(db_session)
    evidence = await service.record_evidence(
        claim_key="planning:jasmine",
        classification="EXACT",
        source_locator="test://planning-jasmine",
        source_version="1",
        method="bounded fixture",
        assumptions=(),
        limitations=(),
        payload_sha256=None,
    )
    material = await service.create_material("Jasmine Absolute")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.1,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
        density_g_ml=1.0,
        supplier="Test supplier",
        lot_number="LOT-A2-1",
    )
    target = await service.create_target_hypothesis(
        _target_command(
            evidence_id=evidence.id,
            rationale="Planning graph fixture",
        )
    )
    target_line = (await service.repository.target_lines(target.id))[0]
    acceptance = await service.accept_target(
        target.id,
        reviewer="Sol",
        rationale="Fixture evidence accepted",
    )
    mapping = await service.create_inventory_mapping(
        InventoryMappingInput(
            target_line_id=target_line.id,
            stock_solution_id=stock.id,
            target_identity="Jasmine Absolute",
            build_identity="Jasmine Absolute",
            identity_status="EXACT",
            inventory_status="EXACT_LOT_AVAILABLE",
            substitution_class="EXACT",
            preserved_functions=("heart", "diffusion"),
            lost_functions=(),
            confidence=1.0,
            rationale="Exact physical lot",
            evidence_links=(evidence.id,),
        )
    )
    return service, target, acceptance, mapping, target_line, stock, evidence


def _build_plan_command(
    target,
    acceptance,
    mapping,
    target_line,
    stock,
    evidence,
) -> BuildPlanInput:
    return BuildPlanInput(
        target_hypothesis_version_id=target.id,
        accepted_target_version_id=acceptance.id,
        schema_version="a2-build-plan-v1",
        author="Sol",
        inventory_snapshot_ref="inventory-sha256:test-fixture",
        uncertainty_summary={"basis": "bounded-test"},
        rationale="Executable planning fixture",
        lines=(
            BuildPlanLineInput(
                line_id="build-line-jasmine",
                target_line_id=target_line.id,
                target_identity="Jasmine Absolute",
                inventory_mapping_version_id=mapping.id,
                stock_solution_id=stock.id,
                planned_raw_quantity=1.0,
                planned_active_quantity=0.1,
                unit="g",
                concentration_fraction=0.1,
                concentration_basis="mass_fraction",
                density_g_ml=1.0,
                density_source="lot record",
                standard_uncertainty=0.01,
                measurement_method="gravimetric",
                resolution=0.001,
                expected_transfer_loss=0.01,
                substitution_class="EXACT",
                preserved_functions=("heart", "diffusion"),
                lost_functions=(),
                rationale="Exact physical lot",
                evidence_links=(evidence.id,),
            ),
        ),
    )


async def _plan_at_status(db_session, requested_status: str):
    service, target, acceptance, mapping, target_line, stock, evidence = (
        await _planning_graph(db_session)
    )
    plan = await service.create_build_plan(
        _build_plan_command(
            target,
            acceptance,
            mapping,
            target_line,
            stock,
            evidence,
        )
    )
    paths = {
        "DRAFT": (),
        "UNDER_REVIEW": ("UNDER_REVIEW",),
        "APPROVED": ("UNDER_REVIEW", "APPROVED"),
        "RESERVED": ("UNDER_REVIEW", "APPROVED", "RESERVED"),
        "EXECUTING": (
            "UNDER_REVIEW",
            "APPROVED",
            "RESERVED",
            "EXECUTING",
        ),
        "CLOSED": (
            "UNDER_REVIEW",
            "APPROVED",
            "RESERVED",
            "EXECUTING",
            "CLOSED",
        ),
    }
    for next_status in paths[requested_status]:
        plan = await service.transition_build_plan(
            plan.id,
            next_status=next_status,
            actor="Sol",
            rationale=f"Fixture transition to {next_status}",
        )
    return plan


async def _approved_plan(db_session):
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
        rationale="Review requested",
    )
    approved = await service.transition_build_plan(
        review.id,
        next_status="APPROVED",
        actor="reviewer",
        rationale="Plan approved",
    )
    line = (await service.repository.build_plan_lines(approved.id))[0]
    return service, approved, line, stock


__all__ = [
    "_approved_plan",
    "_build_plan_command",
    "_formula_versions",
    "_plan_at_status",
    "_planning_graph",
    "_target_command",
]
