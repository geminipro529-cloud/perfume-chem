"""V5 inventory execution-authority firewall.

This module separates three scopes that must never be collapsed:

1. target / ideal computational architecture;
2. current-inventory computational build design;
3. physical execution against an exact bottle or prepared stock.

The reconciliation input schema matches the V5 review table exported from the
current inventory workbook.  Workbook-side fields are retained as evidence, but
V5 status/policy fields control current-inventory design interpretation.  A
physical action additionally requires a resolved ExactStockRef and a non-HOLD
physical gate.

No result from this module grants sensory, liking, safety, stability, release,
or measured-headspace authority.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class V5ExecutionAuthorityError(ValueError):
    """Raised when a reconciliation or formula row is structurally invalid."""


RECONCILIATION_COLUMNS = (
    "Material",
    "Uses",
    "Workbook Inventory Status",
    "Workbook Stock Description",
    "Workbook Active Fraction",
    "Workbook Carrier",
    "Workbook ExactStockRef",
    "Workbook Physical Gate",
    "V5 Match Method",
    "V5 Canonical Material",
    "V5 Status",
    "V5 Actual Stock(s)",
    "V5 Can Prepare",
    "V5 Formula-Use Policy",
    "V5 User Note",
    "Final Execution State",
)

PHYSICAL_MODES = frozenset({"LIVE_BATCH", "BATCH_RESCUE"})
CURRENT_BUILD_MODES = frozenset(
    {
        "INVENTORY_MAPPING",
        "COMPLIANCE_BUILD",
        "RELEASE_REVIEW",
    }
)
DESIGN_MODES = frozenset(
    {
        "RECONSTRUCTION",
        "CREATIVE_FORMULATION",
        "STRUCTURAL_CHASSIS",
        "FLANKER_MODULE",
        "SENSORY_EXPERIMENT",
        "ANALYTICAL_INTERPRETATION",
    }
)

_UNRESOLVED_TOKENS = frozenset({"", "UNRESOLVED", "UNKNOWN", "NONE", "N/A", "NA"})


def _text(value: object) -> str:
    return str(value or "").strip()


def _upper(value: object) -> str:
    return _text(value).upper()


def _resolved_ref(value: object) -> str | None:
    text = _text(value)
    if text.upper() in _UNRESOLVED_TOKENS:
        return None
    return text


def _fraction(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    text = _text(value)
    if not text or text.upper() in _UNRESOLVED_TOKENS:
        return None
    try:
        result = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result) or not 0.0 < result <= 1.0:
        return None
    return result


def _has_any(text: str, tokens: Sequence[str]) -> bool:
    upper = text.upper()
    return any(token in upper for token in tokens)


def _v5_status_class(status: str) -> str:
    upper = status.upper()
    if "PLANNED ACQUISITION" in upper or "DESIGN-AVAILABLE" in upper:
        return "PLANNED_DESIGN_AVAILABLE"
    if _has_any(upper, ("OUT OF STOCK", "GAP", "MISSING", "NOT OWNED")):
        return "UNAVAILABLE"
    if "CONSTRUCTIBLE ACCORD" in upper:
        return "CONSTRUCTIBLE_NOT_PREPARED"
    if "HAVE" in upper:
        return "HAVE"
    if not upper:
        return "UNMAPPED"
    return "OTHER"


def _final_hold(value: object) -> bool:
    return _upper(value).startswith("HOLD")


def _physical_gate_hold(value: object) -> bool:
    return _upper(value) in {"", "HOLD", "FAIL", "BLOCK", "BLOCKED", "UNKNOWN"}


def _product_basis(policy: str, stock: str, workbook_stock: str) -> bool:
    joined = " ".join((policy, stock, workbook_stock)).upper()
    return "PRODUCT BASIS" in joined or "PRODUCT-BASIS" in joined


def _policy_forbids_neat_model(policy: str) -> bool:
    upper = policy.upper()
    return (
        "DO NOT DOSE OR MODEL AS NEAT" in upper
        or "DO NOT DOSE AS NEAT" in upper
        or "DO NOT MODEL AS NEAT" in upper
    )


@dataclass(frozen=True, slots=True)
class MaterialExecutionAuthority:
    material: str
    canonical_material: str | None
    v5_status: str
    v5_status_class: str
    exact_stock_ref: str | None
    physical_gate: str
    final_execution_state: str
    design_allowed: bool
    current_inventory_build_allowed: bool
    physical_execution_allowed: bool
    quantitative_design_allowed: bool
    product_basis: bool
    active_fraction: float | None
    carrier: str | None
    can_prepare: str | None
    formula_use_policy: str | None
    reasons: tuple[str, ...]
    evidence: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "material": self.material,
            "canonical_material": self.canonical_material,
            "v5_status": self.v5_status,
            "v5_status_class": self.v5_status_class,
            "exact_stock_ref": self.exact_stock_ref,
            "physical_gate": self.physical_gate,
            "final_execution_state": self.final_execution_state,
            "design_allowed": self.design_allowed,
            "current_inventory_build_allowed": self.current_inventory_build_allowed,
            "physical_execution_allowed": self.physical_execution_allowed,
            "quantitative_design_allowed": self.quantitative_design_allowed,
            "product_basis": self.product_basis,
            "active_fraction": self.active_fraction,
            "carrier": self.carrier,
            "can_prepare": self.can_prepare,
            "formula_use_policy": self.formula_use_policy,
            "reasons": list(self.reasons),
            "evidence": dict(self.evidence),
            "claim_ceiling": "COMPUTATIONAL_INVENTORY_AND_EXECUTION_AUTHORITY_ONLY",
            "sensory_authority": False,
            "liking_authority": False,
            "safety_authority": False,
            "stability_authority": False,
            "release_authority": False,
        }


@dataclass(frozen=True, slots=True)
class FormulaExecutionAuthority:
    mode: str
    status: str
    allowed: bool
    physical_execution_allowed: bool
    rows: tuple[MaterialExecutionAuthority, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "allowed": self.allowed,
            "physical_execution_allowed": self.physical_execution_allowed,
            "rows": [row.as_dict() for row in self.rows],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "claim_ceiling": "COMPUTATIONAL_INVENTORY_AND_EXECUTION_AUTHORITY_ONLY",
            "physical_liking_state": "NOT TESTED",
        }


def validate_reconciliation_row(row: Mapping[str, Any]) -> None:
    missing = [name for name in RECONCILIATION_COLUMNS if name not in row]
    if missing:
        raise V5ExecutionAuthorityError(
            "reconciliation row missing required column(s): " + ", ".join(missing)
        )
    if not _text(row.get("Material")):
        raise V5ExecutionAuthorityError("reconciliation row Material must not be blank")


def evaluate_reconciliation_row(row: Mapping[str, Any]) -> MaterialExecutionAuthority:
    """Evaluate one V5 reconciliation row without silently repairing conflicts."""

    validate_reconciliation_row(row)
    material = _text(row["Material"])
    canonical = _text(row.get("V5 Canonical Material")) or None
    v5_status = _text(row.get("V5 Status"))
    status_class = _v5_status_class(v5_status)
    exact_ref = _resolved_ref(row.get("Workbook ExactStockRef"))
    physical_gate = _text(row.get("Workbook Physical Gate"))
    final_state = _text(row.get("Final Execution State"))
    policy = _text(row.get("V5 Formula-Use Policy"))
    v5_stock = _text(row.get("V5 Actual Stock(s)"))
    workbook_stock = _text(row.get("Workbook Stock Description"))
    workbook_carrier = _text(row.get("Workbook Carrier"))
    active_fraction = _fraction(row.get("Workbook Active Fraction"))
    is_product_basis = _product_basis(policy, v5_stock, workbook_stock)

    reasons: list[str] = []
    mapped = bool(canonical and status_class != "UNMAPPED")

    design_allowed = status_class in {
        "HAVE",
        "PLANNED_DESIGN_AVAILABLE",
        "CONSTRUCTIBLE_NOT_PREPARED",
    }
    if not mapped and status_class != "PLANNED_DESIGN_AVAILABLE":
        design_allowed = False
        reasons.append("V5_MAPPING_NOT_RESOLVED")

    current_build_allowed = status_class == "HAVE" and mapped
    if status_class == "PLANNED_DESIGN_AVAILABLE":
        current_build_allowed = False
        reasons.append("PLANNED_MATERIAL_NOT_PHYSICALLY_OWNED")
    elif status_class == "CONSTRUCTIBLE_NOT_PREPARED":
        current_build_allowed = False
        reasons.append("CONSTRUCTIBLE_ACCORD_NOT_YET_PREPARED")
    elif status_class == "UNAVAILABLE":
        design_allowed = False
        current_build_allowed = False
        reasons.append("V5_STATUS_UNAVAILABLE")
    elif status_class in {"UNMAPPED", "OTHER"}:
        current_build_allowed = False
        reasons.append("V5_STATUS_NOT_EXECUTION_READY")

    if _final_hold(final_state):
        reasons.append("FINAL_EXECUTION_STATE_HOLD")
    if _physical_gate_hold(physical_gate):
        reasons.append("PHYSICAL_GATE_HOLD")
    if exact_ref is None:
        reasons.append("EXACTSTOCKREF_UNRESOLVED")

    carrier = workbook_carrier or None
    carrier_conflict = "CONFLICT" in workbook_carrier.upper()
    if carrier_conflict:
        reasons.append("CARRIER_CONFLICT_PRESERVED")

    if active_fraction is None and not is_product_basis:
        reasons.append("ACTIVE_FRACTION_NOT_STRUCTURED")

    if _policy_forbids_neat_model(policy) and active_fraction == 1.0:
        reasons.append("ACTIVE_FRACTION_CONFLICT_WITH_V5_POLICY")

    quantitative_design_allowed = bool(
        design_allowed
        and not carrier_conflict
        and (
            is_product_basis
            or (
                active_fraction is not None
                and "ACTIVE_FRACTION_CONFLICT_WITH_V5_POLICY" not in reasons
            )
        )
    )

    physical_allowed = bool(
        current_build_allowed
        and exact_ref is not None
        and not _physical_gate_hold(physical_gate)
        and not _final_hold(final_state)
        and quantitative_design_allowed
    )

    if physical_allowed:
        reasons = [
            reason
            for reason in reasons
            if reason
            not in {
                "FINAL_EXECUTION_STATE_HOLD",
                "PHYSICAL_GATE_HOLD",
                "EXACTSTOCKREF_UNRESOLVED",
            }
        ]

    return MaterialExecutionAuthority(
        material=material,
        canonical_material=canonical,
        v5_status=v5_status,
        v5_status_class=status_class,
        exact_stock_ref=exact_ref,
        physical_gate=physical_gate,
        final_execution_state=final_state,
        design_allowed=design_allowed,
        current_inventory_build_allowed=current_build_allowed,
        physical_execution_allowed=physical_allowed,
        quantitative_design_allowed=quantitative_design_allowed,
        product_basis=is_product_basis,
        active_fraction=active_fraction,
        carrier=carrier,
        can_prepare=_text(row.get("V5 Can Prepare")) or None,
        formula_use_policy=policy or None,
        reasons=tuple(dict.fromkeys(reasons)),
        evidence={
            "uses": _text(row.get("Uses")),
            "workbook_inventory_status": _text(row.get("Workbook Inventory Status")),
            "workbook_stock_description": workbook_stock,
            "workbook_carrier": workbook_carrier,
            "v5_match_method": _text(row.get("V5 Match Method")),
            "v5_actual_stocks": v5_stock,
            "v5_user_note": _text(row.get("V5 User Note")),
        },
    )


def evaluate_formula_execution_authority(
    rows: Sequence[Mapping[str, Any]],
    *,
    mode: str,
) -> FormulaExecutionAuthority:
    """Evaluate a formula-scoped set of reconciliation rows for one operating mode."""

    mode_name = _upper(mode)
    if not mode_name:
        raise V5ExecutionAuthorityError("mode must not be blank")
    evaluated = tuple(evaluate_reconciliation_row(row) for row in rows)
    if not evaluated:
        raise V5ExecutionAuthorityError("at least one reconciliation row is required")

    blockers: list[str] = []
    warnings: list[str] = []

    if mode_name in PHYSICAL_MODES:
        for row in evaluated:
            if not row.physical_execution_allowed:
                blockers.append(f"{row.material}:PHYSICAL_HOLD")
        allowed = not blockers
        status = "PHYSICAL_READY" if allowed else "HOLD"
    elif mode_name in CURRENT_BUILD_MODES:
        for row in evaluated:
            if not row.current_inventory_build_allowed:
                blockers.append(f"{row.material}:CURRENT_BUILD_UNAVAILABLE")
            elif not row.quantitative_design_allowed:
                blockers.append(f"{row.material}:QUANTITATIVE_BASIS_HOLD")
            if not row.physical_execution_allowed:
                warnings.append(f"{row.material}:PHYSICAL_EXECUTION_HOLD")
        allowed = not blockers
        status = "CURRENT_BUILD_ALLOWED" if allowed else "HOLD"
    else:
        for row in evaluated:
            if not row.design_allowed:
                blockers.append(f"{row.material}:DESIGN_UNAVAILABLE")
            elif not row.quantitative_design_allowed:
                warnings.append(f"{row.material}:QUANTITATIVE_DESIGN_HOLD")
            if not row.physical_execution_allowed:
                warnings.append(f"{row.material}:PHYSICAL_EXECUTION_HOLD")
        allowed = not blockers
        status = "DESIGN_ALLOWED" if allowed else "HOLD"

    return FormulaExecutionAuthority(
        mode=mode_name,
        status=status,
        allowed=allowed,
        physical_execution_allowed=all(
            row.physical_execution_allowed for row in evaluated
        ),
        rows=evaluated,
        blockers=tuple(blockers),
        warnings=tuple(dict.fromkeys(warnings)),
    )


def reconciliation_row_from_formula_stock_spec(
    material: str,
    stock_spec: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt a formula stock-spec mapping into the V5 reconciliation schema.

    This adapter is intentionally strict.  It never assumes neat stock when a
    fraction is missing, and it never invents an ExactStockRef.
    """

    fraction = stock_spec.get("fraction")
    if fraction is None:
        fraction_text: object = ""
    else:
        parsed = _fraction(fraction)
        if parsed is None:
            raise V5ExecutionAuthorityError(
                f"{material}: stock_spec fraction must be numeric in (0, 1]"
            )
        fraction_text = parsed

    return {
        "Material": material,
        "Uses": stock_spec.get("uses", ""),
        "Workbook Inventory Status": stock_spec.get("workbook_inventory_status", ""),
        "Workbook Stock Description": stock_spec.get("stock_description", ""),
        "Workbook Active Fraction": fraction_text,
        "Workbook Carrier": stock_spec.get("carrier", ""),
        "Workbook ExactStockRef": stock_spec.get("exact_stock_ref", "UNRESOLVED"),
        "Workbook Physical Gate": stock_spec.get("physical_gate", "HOLD"),
        "V5 Match Method": stock_spec.get("v5_match_method", "FORMULA_STOCK_SPEC"),
        "V5 Canonical Material": stock_spec.get("v5_canonical_material", material),
        "V5 Status": stock_spec.get("v5_status", ""),
        "V5 Actual Stock(s)": stock_spec.get("v5_actual_stocks", stock_spec.get("stock_description", "")),
        "V5 Can Prepare": stock_spec.get("v5_can_prepare", ""),
        "V5 Formula-Use Policy": stock_spec.get("v5_formula_use_policy", ""),
        "V5 User Note": stock_spec.get("v5_user_note", ""),
        "Final Execution State": stock_spec.get("final_execution_state", "HOLD — EXACTSTOCKREF UNRESOLVED"),
    }


def evaluate_formula_stock_specs(
    formula: Mapping[str, Any],
    *,
    mode: str,
) -> FormulaExecutionAuthority:
    """Evaluate formula stock_specs with no implicit neat or physical authority."""

    ingredients = dict(formula.get("ingredients_ul", {}) or {})
    stock_specs = dict(formula.get("stock_specs", {}) or {})
    dilutions = dict(formula.get("dilutions", {}) or {})
    rows: list[dict[str, Any]] = []
    for raw_name, raw_amount in ingredients.items():
        name = _text(raw_name)
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError) as exc:
            raise V5ExecutionAuthorityError(f"{name}: ingredient dose must be numeric") from exc
        if not math.isfinite(amount) or amount < 0.0:
            raise V5ExecutionAuthorityError(f"{name}: ingredient dose must be finite and nonnegative")
        if amount == 0.0:
            continue
        spec = dict(stock_specs.get(raw_name, stock_specs.get(name, {})) or {})
        if "fraction" not in spec and name in dilutions:
            spec["fraction"] = dilutions[name]
        rows.append(reconciliation_row_from_formula_stock_spec(name, spec))
    return evaluate_formula_execution_authority(rows, mode=mode)
