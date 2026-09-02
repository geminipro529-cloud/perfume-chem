from decimal import Decimal

import pytest
from sqlalchemy import update

from app.models.lab import LabStockSolution
from app.services.lab_planning import PlanningConflictError
from app.services.lab_service import FormulaComponentInput, LabService
from app.services.stock_lineage import (
    ACTIVE_EQUIVALENCE_RULE_SET_SHA256,
    StockLineageError,
    validate_formula_version_physical_lineage,
    validate_formula_version_transition,
)


@pytest.mark.asyncio
async def test_prada_citronellol_stock_normalization_regression_hard_fails(db_session):
    service = LabService(db_session)
    material = await service.create_material("Citronellol")
    ten_percent = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.10,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
        solvent_name="test carrier",
    )
    neat = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
    )
    formula = await service.create_formula("Prada L'Homme Citronellol regression")
    parent = await service.add_formula_version(
        formula.id,
        brief={"state": "parent-10-percent"},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=ten_percent.id,
                requested_mass_g=14.363,
            ),
        ),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={"state": "unsafe-child-neat"},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=neat.id,
                requested_mass_g=14.0,
            ),
        ),
    )

    with pytest.raises(PlanningConflictError) as error:
        await service.link_formula_version(
            child.id,
            parent.id,
            relationship_kind="STOCK_NORMALIZATION",
            change={"incident": "PRADA_LHOMME_V2_2_CITRONELLOL"},
            rationale="Must preserve active-equivalent dose",
        )

    assert error.value.code == "STOCK_NORMALIZATION_ACTIVE_EQUIVALENCE_MISMATCH"
    assert "1.4363" in str(error.value)
    assert "14" in str(error.value)
    assert "9.747267" in str(error.value)


@pytest.mark.asyncio
async def test_stock_normalization_accepts_active_equivalent_rebase(db_session):
    service = LabService(db_session)
    material = await service.create_material("Citronellol")
    ten_percent = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.10,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
    )
    neat = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
    )
    formula = await service.create_formula("Citronellol compatible stock rebase")
    parent = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=ten_percent.id,
                requested_mass_g=14.363,
            ),
        ),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(
            FormulaComponentInput(
                stock_solution_id=neat.id,
                requested_mass_g=1.4363,
            ),
        ),
    )

    edge = await service.link_formula_version(
        child.id,
        parent.id,
        relationship_kind="STOCK_NORMALIZATION",
        change={"reason": "10 percent to neat"},
        rationale="Same active target",
    )

    assert edge.relationship_kind == "STOCK_NORMALIZATION"
    receipt = edge.change_json["stock_lineage_receipt"]
    assert receipt["schema"] == "formula-stock-lineage-v3"
    assert receipt["result"] == "PASS_PLAN_ACTIVE_EQUIVALENT"
    assert receipt["rule_set_sha256"] == ACTIVE_EQUIVALENCE_RULE_SET_SHA256
    assert receipt["authority"] == {
        "claim_class": "EXACT",
        "scope": "PLANNED_FORMULA_LINEAGE_ONLY",
        "plan_transition_authority": True,
        "physical_measurement_authority": False,
        "formula_release_authority": False,
        "measurement_uncertainty_evaluated": False,
        "numeric_persistence": "EXACT_DECIMAL_TEXT_WITH_LEGACY_FLOAT_PROJECTION",
        "legacy_float_projection_authority": False,
    }
    assert receipt["materials"][0]["parent_active_mass_g"] == "1.4363"
    assert receipt["materials"][0]["child_active_mass_g"] == "1.4363"
    assert len(receipt["comparison_sha256"]) == 64

    assert (
        await validate_formula_version_physical_lineage(db_session, child.id)
    ) == receipt

    receipt["result"] = "PASS_ACTIVE_EQUIVALENT"
    with pytest.raises(StockLineageError) as mismatch:
        await validate_formula_version_physical_lineage(db_session, child.id)
    assert mismatch.value.code == "STOCK_LINEAGE_RECEIPT_MISMATCH"


@pytest.mark.asyncio
async def test_stock_lineage_uses_exact_decimal_text_not_float_projection(db_session):
    service = LabService(db_session)
    material = await service.create_material("High precision stock")
    fraction = Decimal("0.1234567890123456789")
    mass = Decimal("0.9876543210987654321")
    parent_stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=fraction,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
    )
    child_stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=fraction,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
    )
    formula = await service.create_formula("Exact decimal lineage")
    parent = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(parent_stock.id, mass),),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(child_stock.id, mass),),
    )

    edge = await service.link_formula_version(
        child.id,
        parent.id,
        relationship_kind="STOCK_NORMALIZATION",
        change={"reason": "same exact decimal target"},
        rationale="Exact decimal persistence regression",
    )

    assert parent_stock.active_fraction_decimal_text == str(fraction)
    parent_component = (
        await service.repository.formula_components(parent.id)
    )[0]
    assert parent_component.requested_mass_g_decimal_text == str(mass)
    expected_active = format(fraction * mass, "f").rstrip("0").rstrip(".")
    receipt = edge.change_json["stock_lineage_receipt"]
    assert receipt["materials"][0]["parent_active_mass_g"] == expected_active
    assert receipt["materials"][0]["child_active_mass_g"] == expected_active


@pytest.mark.asyncio
async def test_legacy_float_only_lineage_requires_explicit_decimal_rebind(db_session):
    service = LabService(db_session)
    material = await service.create_material("Legacy float stock")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.1,
        fraction_basis="mass_fraction",
        initial_mass_g=10.0,
    )
    formula = await service.create_formula("Legacy decimal rebind")
    parent = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(stock.id, Decimal("1.0")),),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(stock.id, Decimal("1.0")),),
    )
    await db_session.execute(
        update(LabStockSolution)
        .where(LabStockSolution.id == stock.id)
        .values(active_fraction_decimal_text=None)
    )
    await db_session.commit()

    with pytest.raises(StockLineageError) as error:
        await validate_formula_version_transition(
            db_session,
            parent_version_id=parent.id,
            child_version_id=child.id,
            transition_class="DESIGN_REVISION",
        )

    assert error.value.code == "ACTIVE_EQUIVALENT_DECIMAL_REBIND_REQUIRED"


@pytest.mark.asyncio
async def test_design_revision_cannot_hide_stock_normalization(db_session):
    service = LabService(db_session)
    material = await service.create_material("Citronellol")
    ten_percent = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.10,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
    )
    neat = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=1.0,
        fraction_basis="mass_fraction",
        initial_mass_g=100.0,
    )
    formula = await service.create_formula("No mixed transition")
    parent = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(ten_percent.id, 14.363),),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(neat.id, 1.4363),),
    )

    with pytest.raises(PlanningConflictError) as error:
        await service.link_formula_version(
            child.id,
            parent.id,
            relationship_kind="DESIGN_REVISION",
            change={"reason": "must not mix"},
            rationale="Stock change cannot hide in design revision",
        )
    assert error.value.code == "MIXED_STOCK_NORMALIZATION_AND_DESIGN_REVISION"


@pytest.mark.asyncio
async def test_non_mass_fraction_lineage_holds_without_conversion_authority(db_session):
    service = LabService(db_session)
    material = await service.create_material("Volume-basis stock")
    stock = await service.create_stock_solution(
        material_id=material.id,
        active_fraction=0.10,
        fraction_basis="volume_fraction",
        initial_mass_g=100.0,
        density_g_ml=1.0,
    )
    formula = await service.create_formula("Unsupported active-equivalent basis")
    parent = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(stock.id, 1.0),),
    )
    child = await service.add_formula_version(
        formula.id,
        brief={},
        constraints={},
        components=(FormulaComponentInput(stock.id, 1.0),),
    )

    with pytest.raises(PlanningConflictError) as error:
        await service.link_formula_version(
            child.id,
            parent.id,
            relationship_kind="DESIGN_REVISION",
            change={},
            rationale="No mass-basis authority",
        )
    assert error.value.code == "ACTIVE_EQUIVALENT_AUTHORITY_UNAVAILABLE"
