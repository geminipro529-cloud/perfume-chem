"""Formula calculation endpoints."""

from typing import Any, Dict

from engine.bottle_addition import (
    AdditionCalculationError,
    AdditionRequest,
    BottleSnapshot,
    PipetteProfile,
    StockSolution,
)
from engine.mixture import (
    MixtureComponent,
    MixtureRole,
    known_solvent_physical_data,
)
from engine.quantities import Density, MolarMass, Volume
from engine.workbench import CalculationMode, PerfumeWorkbench, WorkbenchFormulaRequest
from fastapi import APIRouter, HTTPException

from app.core.exceptions import DilutionCalculationError
from app.domain.ingredients.chemistry import (
    calculate_dilution,
    calculate_drops_to_ml,
    calculate_ml_to_drops,
)
from app.schemas.chemical import (
    BottleAdditionCalculation,
    DilutionCalculation,
    DilutionResult,
)
from app.schemas.perfume import FormulaCreate
from app.services.validation_pipeline import attach_validation, validate_formula

router = APIRouter()
workbench = PerfumeWorkbench()


@router.post("/calculate-dilution", response_model=DilutionResult)
async def calculate_dilution_endpoint(
    dilution: DilutionCalculation
) -> DilutionResult:
    """Calculate dilution for a concentrate"""
    try:
        result = calculate_dilution(
            concentrate_volume=dilution.concentrate_volume,
            concentrate_percent=dilution.concentrate_percent,
            target_percent=dilution.target_percent,
        )
        return DilutionResult(**result, solvent=dilution.solvent)
    except DilutionCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/drops-to-ml/{drops}")
async def drops_to_ml(drops: int, drop_size: float = 0.05) -> Dict[str, float]:
    """Convert drops to milliliters"""
    ml = calculate_drops_to_ml(drops, drop_size)
    return {"drops": drops, "milliliters": ml, "drop_size": drop_size}


@router.get("/ml-to-drops/{volume}")
async def ml_to_drops(
    volume: float, drop_size: float = 0.05
) -> Dict[str, float | int]:
    """Convert milliliters to drops"""
    drops = calculate_ml_to_drops(volume, drop_size)
    return {"milliliters": volume, "drops": drops, "drop_size": drop_size}


@router.post("/analyze-formula")
async def analyze_formula(formula: FormulaCreate) -> Dict[str, Any]:
    """Analyze a formula through the canonical evidence-labeled workbench."""
    percentage_by_name: dict[str, float] = {}
    for ingredient in formula.ingredients:
        percentage_by_name[ingredient.name] = (
            percentage_by_name.get(ingredient.name, 0.0) + ingredient.percentage
        )
    report = validate_formula(percentage_by_name)
    try:
        request = _to_workbench_request(formula)
        payload = workbench.analyze(request).as_dict()
        payload.update(
            {
                "total_volume_ml": formula.total_volume_ml,
                "concentration_percent": formula.concentration_percent,
            }
        )
        response: Dict[str, Any] = attach_validation(payload, report)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/calculate-addition")
async def calculate_addition(calculation: BottleAdditionCalculation) -> Dict[str, Any]:
    """Calculate an exact additive mass balance and optional pipette plan."""
    try:
        pipette = (
            PipetteProfile(**calculation.pipette.model_dump())
            if calculation.pipette is not None
            else None
        )
        result = workbench.calculate_addition(
            AdditionRequest(
                bottle=BottleSnapshot(**calculation.bottle.model_dump()),
                stock=StockSolution(**calculation.stock.model_dump()),
                target_active_mass_fraction=calculation.target_active_mass_fraction,
                pipette=pipette,
            )
        )
        payload: Dict[str, Any] = result.as_dict()
        return payload
    except AdditionCalculationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _to_workbench_request(formula: FormulaCreate) -> WorkbenchFormulaRequest:
    batch_volume_ml = formula.total_volume_ml or 100.0
    solvent_rows = [
        ingredient
        for ingredient in formula.ingredients
        if (ingredient.role or "").strip().lower() == "solvent"
    ]
    aromatic_rows = [
        ingredient
        for ingredient in formula.ingredients
        if (ingredient.role or "").strip().lower() != "solvent"
    ]
    if not aromatic_rows:
        raise ValueError("Formula must contain at least one non-solvent ingredient")

    assumptions: list[str] = []
    if formula.total_volume_ml is None:
        assumptions.append(
            "No total_volume_ml was supplied; a 100 mL calculation basis is used."
        )

    if solvent_rows:
        aromatic_basis_ml = batch_volume_ml
        assumptions.append(
            "Explicit solvent rows are present, so percentages are interpreted as "
            "finished-product volume fractions and solvent rows are included in the "
            "finished liquid matrix when their physical data are available."
        )
        if formula.concentration_percent is not None:
            assumptions.append(
                "The declared concentration_percent is retained as metadata but is not "
                "used because explicit solvent rows define the finished composition."
            )
    else:
        concentration_percent = formula.concentration_percent
        if concentration_percent is None:
            concentration_percent = 15.0
            assumptions.append(
                "No concentration_percent was supplied; a 15% finished-product "
                "concentration is used."
            )
        if concentration_percent <= 0:
            raise ValueError(
                "concentration_percent must be greater than zero when solvent rows are absent"
            )
        aromatic_basis_ml = batch_volume_ml * concentration_percent / 100.0
        assumptions.append(
            "Without explicit solvent rows, percentages are interpreted as concentrate "
            "composition and scaled by concentration_percent."
        )

    raw_ul_by_name: dict[str, float] = {}
    active_ul_by_name: dict[str, float] = {}
    for ingredient in aromatic_rows:
        raw_ul = aromatic_basis_ml * 1000.0 * ingredient.percentage / 100.0
        raw_ul_by_name[ingredient.name] = raw_ul_by_name.get(ingredient.name, 0.0) + raw_ul
        active_ul_by_name[ingredient.name] = (
            active_ul_by_name.get(ingredient.name, 0.0)
            + raw_ul * ingredient.stock_active_fraction
        )

    dilutions = {
        name: active_ul_by_name[name] / raw_ul
        for name, raw_ul in raw_ul_by_name.items()
    }
    if any(ingredient.stock_density_g_ml is not None for ingredient in aromatic_rows):
        assumptions.append(
            "Formula-row stock density metadata is retained by the API schema but is not "
            "consumed by the current headspace model."
        )

    matrix_components: list[MixtureComponent] = []
    for ingredient in solvent_rows:
        known = known_solvent_physical_data(ingredient.name)
        density = (
            Density.from_g_ml(ingredient.stock_density_g_ml)
            if ingredient.stock_density_g_ml is not None
            else (known.density if known is not None else None)
        )
        molar_mass = (
            MolarMass.from_g_mol(ingredient.molar_mass_g_mol)
            if ingredient.molar_mass_g_mol is not None
            else (known.molar_mass if known is not None else None)
        )
        density_source = (
            "user_supplied"
            if ingredient.stock_density_g_ml is not None
            else (known.source if known is not None else "missing")
        )
        molar_mass_source = (
            "user_supplied"
            if ingredient.molar_mass_g_mol is not None
            else (known.source if known is not None else "missing")
        )
        matrix_components.append(
            MixtureComponent(
                name=ingredient.name,
                role=MixtureRole.SOLVENT,
                volume=Volume.from_ml(
                    batch_volume_ml * ingredient.percentage / 100.0
                ),
                density=density,
                molar_mass=molar_mass,
                source="explicit_formula_solvent",
                density_source=density_source,
                molar_mass_source=molar_mass_source,
            )
        )

    return WorkbenchFormulaRequest(
        formula_name=formula.name,
        ingredients_ul=raw_ul_by_name,
        dilutions=dilutions,
        batch_volume_ml=batch_volume_ml,
        assumptions=tuple(assumptions),
        matrix_components=tuple(matrix_components),
        stock_fraction_bases={
            ingredient.name: ingredient.stock_fraction_basis
            for ingredient in aromatic_rows
            if ingredient.stock_fraction_basis is not None
        },
        mode=CalculationMode(formula.calculation_mode),
    )
