"""Fail-closed stock-basis lineage validation for immutable formula versions.

A stock normalization is not a design revision.  The former may change the exact
LabStockSolution used for a material only when active-equivalent dose is preserved;
the latter may change design dose/materials only while retained materials keep their
exact stock solution.  Mixing those operations in one parent->child edge is rejected.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lab import LabFormulaComponent, LabFormulaVersion, LabStockSolution
from app.models.lab_planning import LabFormulaVersionEdge

STOCK_NORMALIZATION = "STOCK_NORMALIZATION"
DESIGN_REVISION = "DESIGN_REVISION"
FORMULA_TRANSITION_CLASSES = frozenset({STOCK_NORMALIZATION, DESIGN_REVISION})

_PLAN_RELATIVE_TOLERANCE = Decimal("1e-9")
_PLAN_ABSOLUTE_TOLERANCE_G = Decimal("1e-12")


def _canonical_sha256(payload: Any) -> str:
    """Hash the receipt's JSON-native contract without claiming RFC 8785."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


ACTIVE_EQUIVALENCE_RULE_SET = {
    "schema": "active-equivalence-plan-rule-v2",
    "quantity_model": (
        "planned_active_mass_g=requested_mass_g*declared_active_mass_fraction"
    ),
    "authoritative_input_fields": {
        "requested_mass_g": "lab_formula_components.requested_mass_g_decimal_text",
        "active_fraction": "lab_stock_solutions.active_fraction_decimal_text",
    },
    "legacy_float_projection_authority": False,
    "accepted_fraction_basis": "mass_fraction",
    "relative_tolerance": str(_PLAN_RELATIVE_TOLERANCE),
    "absolute_tolerance_g": str(_PLAN_ABSOLUTE_TOLERANCE_G),
    "decision_scope": "PLANNED_FORMULA_LINEAGE_ONLY",
    "physical_measurement_authority": False,
    "measurement_uncertainty_evaluated": False,
    "cross_basis_conversion_allowed": False,
}
ACTIVE_EQUIVALENCE_RULE_SET_SHA256 = _canonical_sha256(
    ACTIVE_EQUIVALENCE_RULE_SET
)


class StockLineageError(ValueError):
    """Stable non-demotable formula-lineage rejection."""

    def __init__(self, code: str, message: str, *, receipt: dict[str, Any] | None = None) -> None:
        self.code = code
        self.receipt = dict(receipt or {})
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class _MaterialDose:
    material_id: str
    active_mass_g: Decimal
    stock_solution_ids: tuple[str, ...]
    raw_mass_g: Decimal


def _decimal(value: object, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
            f"{field} must be a finite decimal quantity.",
        ) from error
    if not result.is_finite():
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
            f"{field} must be a finite decimal quantity.",
        )
    return result


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _authoritative_decimal(
    *,
    exact_text: object,
    legacy_projection: object,
    field: str,
) -> Decimal:
    if not isinstance(exact_text, str) or not exact_text.strip():
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_DECIMAL_REBIND_REQUIRED",
            f"{field} has no exact decimal text; create a new immutable record from verified source values.",
        )
    if exact_text != exact_text.strip():
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
            f"{field} exact decimal text is not canonical.",
        )
    exact = _decimal(exact_text, f"{field} exact decimal text")
    if _decimal_text(exact) != exact_text:
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
            f"{field} exact decimal text is not canonical.",
        )
    projection = _decimal(legacy_projection, f"{field} legacy float projection")
    try:
        projections_match = float(exact) == float(projection)
    except (OverflowError, ValueError) as error:
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
            f"{field} cannot be validated against its legacy float projection.",
        ) from error
    if not projections_match:
        raise StockLineageError(
            "ACTIVE_EQUIVALENT_DECIMAL_PROJECTION_MISMATCH",
            f"{field} exact decimal authority disagrees with its legacy float projection.",
        )
    return exact


def _comparison_limit(left: Decimal, right: Decimal) -> Decimal:
    relative = max(abs(left), abs(right)) * _PLAN_RELATIVE_TOLERANCE
    return max(_PLAN_ABSOLUTE_TOLERANCE_G, relative)


def _finalize_receipt(receipt: dict[str, Any], result: str) -> dict[str, Any]:
    receipt["result"] = result
    unsigned = {
        key: value for key, value in receipt.items() if key != "comparison_sha256"
    }
    receipt["comparison_sha256"] = _canonical_sha256(unsigned)
    return receipt


async def _material_vector(
    session: AsyncSession,
    version_id: str,
) -> dict[str, _MaterialDose]:
    result = await session.execute(
        select(LabFormulaComponent, LabStockSolution)
        .join(
            LabStockSolution,
            LabFormulaComponent.stock_solution_id == LabStockSolution.id,
        )
        .where(LabFormulaComponent.formula_version_id == version_id)
        .order_by(LabFormulaComponent.position, LabFormulaComponent.id)
    )
    active_by_material: dict[str, Decimal] = defaultdict(Decimal)
    raw_by_material: dict[str, Decimal] = defaultdict(Decimal)
    stock_ids_by_material: dict[str, list[str]] = defaultdict(list)
    for component, stock in result.all():
        if stock.fraction_basis != "mass_fraction":
            raise StockLineageError(
                "ACTIVE_EQUIVALENT_AUTHORITY_UNAVAILABLE",
                "Formula components are mass-governed; active-equivalent comparison requires mass_fraction stock authority.",
                receipt={
                    "formula_version_id": version_id,
                    "stock_solution_id": stock.id,
                    "fraction_basis": stock.fraction_basis,
                },
            )
        raw_mass = _authoritative_decimal(
            exact_text=component.requested_mass_g_decimal_text,
            legacy_projection=component.requested_mass_g,
            field=f"formula component {component.id} requested_mass_g",
        )
        if raw_mass <= 0:
            raise StockLineageError(
                "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
                f"Formula component {component.id} requested_mass_g must be positive.",
            )
        active_fraction = _authoritative_decimal(
            exact_text=stock.active_fraction_decimal_text,
            legacy_projection=stock.active_fraction,
            field=f"stock {stock.id} active_fraction",
        )
        if not Decimal("0") < active_fraction <= Decimal("1"):
            raise StockLineageError(
                "ACTIVE_EQUIVALENT_NUMERIC_AUTHORITY_INVALID",
                f"Stock {stock.id} active_fraction must be in (0, 1].",
            )
        active_mass = raw_mass * active_fraction
        active_by_material[stock.material_id] += active_mass
        raw_by_material[stock.material_id] += raw_mass
        stock_ids_by_material[stock.material_id].append(stock.id)
    return {
        material_id: _MaterialDose(
            material_id=material_id,
            active_mass_g=active_by_material[material_id],
            stock_solution_ids=tuple(sorted(stock_ids_by_material[material_id])),
            raw_mass_g=raw_by_material[material_id],
        )
        for material_id in sorted(active_by_material)
    }


async def validate_formula_version_transition(
    session: AsyncSession,
    *,
    parent_version_id: str,
    child_version_id: str,
    transition_class: str,
) -> dict[str, Any]:
    """Validate one immutable parent->child formula transition and return its receipt."""

    normalized_class = str(transition_class).strip().upper()
    if normalized_class not in FORMULA_TRANSITION_CLASSES:
        raise StockLineageError(
            "FORMULA_TRANSITION_CLASS_REQUIRED",
            "Formula-version edges must be classified as STOCK_NORMALIZATION or DESIGN_REVISION.",
        )
    parent = await session.get(LabFormulaVersion, parent_version_id)
    child = await session.get(LabFormulaVersion, child_version_id)
    if parent is None or child is None:
        raise StockLineageError(
            "FORMULA_VERSION_NOT_FOUND",
            "Both parent and child formula versions are required for stock-lineage validation.",
        )
    if parent.formula_id != child.formula_id:
        raise StockLineageError(
            "FORMULA_LINEAGE_FORMULA_MISMATCH",
            "Parent and child formula versions must belong to the same formula.",
        )

    parent_vector = await _material_vector(session, parent.id)
    child_vector = await _material_vector(session, child.id)
    parent_materials = set(parent_vector)
    child_materials = set(child_vector)
    receipt: dict[str, Any] = {
        "schema": "formula-stock-lineage-v3",
        "transition_class": normalized_class,
        "parent_version_id": parent.id,
        "child_version_id": child.id,
        "formula_id": parent.formula_id,
        "rule_set": dict(ACTIVE_EQUIVALENCE_RULE_SET),
        "rule_set_sha256": ACTIVE_EQUIVALENCE_RULE_SET_SHA256,
        "authority": {
            "claim_class": "EXACT",
            "scope": "PLANNED_FORMULA_LINEAGE_ONLY",
            "plan_transition_authority": True,
            "physical_measurement_authority": False,
            "formula_release_authority": False,
            "measurement_uncertainty_evaluated": False,
            "numeric_persistence": "EXACT_DECIMAL_TEXT_WITH_LEGACY_FLOAT_PROJECTION",
            "legacy_float_projection_authority": False,
        },
        "materials": [],
    }

    if normalized_class == STOCK_NORMALIZATION:
        if parent_materials != child_materials:
            receipt["parent_only_material_ids"] = sorted(
                parent_materials - child_materials
            )
            receipt["child_only_material_ids"] = sorted(
                child_materials - parent_materials
            )
            _finalize_receipt(receipt, "FAIL_PLAN_MATERIAL_SET_CHANGED")
            raise StockLineageError(
                "STOCK_NORMALIZATION_MATERIAL_SET_CHANGED",
                "Stock normalization cannot add or remove design materials.",
                receipt=receipt,
            )
        for material_id in sorted(parent_materials):
            before = parent_vector[material_id]
            after = child_vector[material_id]
            ratio = (
                after.active_mass_g / before.active_mass_g
                if before.active_mass_g > 0
                else None
            )
            difference = abs(after.active_mass_g - before.active_mass_g)
            acceptance_limit = _comparison_limit(
                before.active_mass_g,
                after.active_mass_g,
            )
            row = {
                "material_id": material_id,
                "parent_stock_solution_ids": list(before.stock_solution_ids),
                "child_stock_solution_ids": list(after.stock_solution_ids),
                "parent_raw_mass_g": _decimal_text(before.raw_mass_g),
                "child_raw_mass_g": _decimal_text(after.raw_mass_g),
                "parent_active_mass_g": _decimal_text(before.active_mass_g),
                "child_active_mass_g": _decimal_text(after.active_mass_g),
                "active_multiplier": (
                    _decimal_text(ratio) if ratio is not None else None
                ),
                "absolute_difference_g": _decimal_text(difference),
                "acceptance_tolerance_g": _decimal_text(acceptance_limit),
            }
            receipt["materials"].append(row)
            if difference > acceptance_limit:
                _finalize_receipt(receipt, "FAIL_PLAN_ACTIVE_EQUIVALENCE")
                raise StockLineageError(
                    "STOCK_NORMALIZATION_ACTIVE_EQUIVALENCE_MISMATCH",
                    "Stock normalization changed active-equivalent dose "
                    f"for material {material_id}: {_decimal_text(before.active_mass_g)} g -> "
                    f"{_decimal_text(after.active_mass_g)} g"
                    + (
                        f" ({_decimal_text(ratio)}x)."
                        if ratio is not None
                        else "."
                    ),
                    receipt=receipt,
                )
        return _finalize_receipt(receipt, "PASS_PLAN_ACTIVE_EQUIVALENT")

    # DESIGN_REVISION: retained design materials must keep the exact stock authority.
    for material_id in sorted(parent_materials & child_materials):
        before = parent_vector[material_id]
        after = child_vector[material_id]
        if before.stock_solution_ids != after.stock_solution_ids:
            mixed_receipt = {
                **receipt,
                "material_id": material_id,
                "parent_stock_solution_ids": list(before.stock_solution_ids),
                "child_stock_solution_ids": list(after.stock_solution_ids),
            }
            _finalize_receipt(
                mixed_receipt,
                "FAIL_MIXED_STOCK_NORMALIZATION_AND_DESIGN_REVISION",
            )
            raise StockLineageError(
                "MIXED_STOCK_NORMALIZATION_AND_DESIGN_REVISION",
                "A DESIGN_REVISION cannot also change the exact stock solution for a retained material; split into two immutable versions.",
                receipt=mixed_receipt,
            )
    return _finalize_receipt(receipt, "PASS_DESIGN_REVISION_STOCKS_STABLE")


async def validate_formula_version_physical_lineage(
    session: AsyncSession,
    formula_version_id: str,
) -> dict[str, Any] | None:
    """Require one revalidated planned-lineage edge before physical work.

    This is an execution precondition, not a physical measurement or metrology
    result.  The persisted receipt must exactly equal the native recomputation.
    """

    version = await session.get(LabFormulaVersion, formula_version_id)
    if version is None:
        raise StockLineageError(
            "FORMULA_VERSION_NOT_FOUND",
            f"Formula version {formula_version_id} does not exist.",
        )
    if version.version_number <= 1:
        return None
    result = await session.execute(
        select(LabFormulaVersionEdge).where(
            LabFormulaVersionEdge.child_version_id == formula_version_id
        )
    )
    incoming = list(result.scalars())
    if len(incoming) != 1:
        raise StockLineageError(
            "FORMULA_TRANSITION_CLASS_REQUIRED",
            "Formula revision 2+ requires exactly one classified parent edge before it can drive physical execution.",
            receipt={
                "formula_version_id": formula_version_id,
                "incoming_edge_count": len(incoming),
            },
        )
    edge = incoming[0]
    recomputed = await validate_formula_version_transition(
        session,
        parent_version_id=edge.parent_version_id,
        child_version_id=edge.child_version_id,
        transition_class=edge.relationship_kind,
    )
    stored = dict(edge.change_json or {}).get("stock_lineage_receipt")
    if not isinstance(stored, dict) or stored.get("schema") != "formula-stock-lineage-v3":
        raise StockLineageError(
            "STOCK_LINEAGE_RECEIPT_REBIND_REQUIRED",
            "Formula revision requires a native v3 exact-decimal planned-lineage receipt before physical execution.",
            receipt={
                "formula_version_id": formula_version_id,
                "stored_schema": stored.get("schema") if isinstance(stored, dict) else None,
                "expected_schema": "formula-stock-lineage-v3",
                "recomputed_comparison_sha256": recomputed["comparison_sha256"],
            },
        )
    if stored != recomputed:
        raise StockLineageError(
            "STOCK_LINEAGE_RECEIPT_MISMATCH",
            "Persisted stock-lineage receipt does not equal the native recomputation.",
            receipt={
                "formula_version_id": formula_version_id,
                "stored_comparison_sha256": stored.get("comparison_sha256"),
                "recomputed_comparison_sha256": recomputed["comparison_sha256"],
            },
        )
    return recomputed


async def validate_workspace_stock_lineage(session: AsyncSession) -> list[dict[str, Any]]:
    """Re-run every persisted formula-edge invariant before workspace import commits."""

    versions = list(
        (
            await session.execute(
                select(LabFormulaVersion)
                .where(LabFormulaVersion.version_number > 1)
                .order_by(LabFormulaVersion.formula_id, LabFormulaVersion.version_number)
            )
        ).scalars()
    )
    receipts: list[dict[str, Any]] = []
    for version in versions:
        receipt = await validate_formula_version_physical_lineage(session, version.id)
        if receipt is not None:
            receipts.append(receipt)
    return receipts


__all__ = [
    "DESIGN_REVISION",
    "ACTIVE_EQUIVALENCE_RULE_SET",
    "ACTIVE_EQUIVALENCE_RULE_SET_SHA256",
    "FORMULA_TRANSITION_CLASSES",
    "STOCK_NORMALIZATION",
    "StockLineageError",
    "validate_formula_version_physical_lineage",
    "validate_formula_version_transition",
    "validate_workspace_stock_lineage",
]
