"""Constraint-first composition checks and deterministic mixture generation."""

from __future__ import annotations

from itertools import islice, product
from math import isclose
from typing import Iterable

from .contracts import (
    C10ContractError,
    CandidateAccounting,
    CandidateDose,
    CandidateRole,
    ConstraintViolation,
    DesignStage,
    FeasibilityAssessment,
    GateStatus,
    MixtureCandidate,
    MixtureDesignAxis,
    MixtureDesignResult,
    MixtureDomain,
    canonical_sha256,
)

_TOLERANCE = 1.0e-9


def candidate_formula_state_sha256(
    domain: MixtureDomain,
    candidate: MixtureCandidate,
) -> str:
    """Bind a composition to exact stock definitions and its design domain."""

    return canonical_sha256(
        {
            "schema": "c10-candidate-formula-state-v1",
            "domain_sha256": domain.content_sha256,
            "doses": tuple(
                {
                    "stock_id": dose.stock_id,
                    "raw_mass_mg": dose.raw_mass_mg,
                    "module_id": dose.module_id,
                }
                for dose in candidate.doses
            ),
        }
    )


def _add(target: dict[str, float], key: str, value: float) -> None:
    target[key] = target.get(key, 0.0) + value


def _violation(code: str, detail: str) -> ConstraintViolation:
    return ConstraintViolation(code=code, detail=detail)


def _multiple_of_increment(value: float, increment: float) -> bool:
    units = value / increment
    return isclose(units, round(units), rel_tol=0.0, abs_tol=_TOLERANCE)


def assess_candidate(
    domain: MixtureDomain,
    candidate: MixtureCandidate,
    *,
    require_gate_receipts: bool = True,
) -> FeasibilityAssessment:
    """Apply every known hard gate before any objective or utility is read."""

    stocks = {stock.stock_id: stock for stock in domain.stocks}
    stock_totals: dict[str, float] = {}
    material_active: dict[str, float] = {}
    family_active: dict[str, float] = {}
    module_active: dict[str, float] = {}
    carrier_masses: dict[str, float] = {}
    violations: list[ConstraintViolation] = []
    raw_mass = 0.0
    active_mass = 0.0
    carrier_mass = 0.0
    unallocated_mass = 0.0
    cost = 0.0

    seen_stock_ids: set[str] = set()
    declared_modules = {item.module_id for item in domain.module_active_mass_ranges}
    for dose in candidate.doses:
        raw_mass += dose.raw_mass_mg
        if dose.stock_id in seen_stock_ids:
            violations.append(
                _violation(
                    "DUPLICATE_STOCK_DOSE",
                    f"stock {dose.stock_id} appears in more than one dose row",
                )
            )
        seen_stock_ids.add(dose.stock_id)
        if declared_modules and dose.module_id not in declared_modules:
            violations.append(
                _violation(
                    "UNKNOWN_MODULE",
                    f"module {dose.module_id} is outside the declared module domain",
                )
            )
        stock = stocks.get(dose.stock_id)
        if stock is None:
            unallocated_mass += dose.raw_mass_mg
            violations.append(
                _violation("UNKNOWN_STOCK", f"stock {dose.stock_id} is not in the domain")
            )
            continue

        _add(stock_totals, stock.stock_id, dose.raw_mass_mg)
        if dose.raw_mass_mg + _TOLERANCE < stock.minimum_measurable_raw_mass_mg:
            violations.append(
                _violation(
                    "BELOW_MEASURABLE_MINIMUM",
                    f"stock {stock.stock_id} dose is below its measurable minimum",
                )
            )
        if not _multiple_of_increment(dose.raw_mass_mg, stock.dispensing_increment_mg):
            violations.append(
                _violation(
                    "OFF_DISPENSING_INCREMENT",
                    f"stock {stock.stock_id} dose is not an integer dispensing increment",
                )
            )

        dose_active = dose.raw_mass_mg * stock.active_mass_fraction
        dose_carrier = 0.0
        for carrier, fraction in stock.carrier_mass_fractions:
            amount = dose.raw_mass_mg * fraction
            dose_carrier += amount
            _add(carrier_masses, carrier, amount)
        allocated = dose_active + dose_carrier
        unallocated_mass += max(0.0, dose.raw_mass_mg - allocated)
        active_mass += dose_active
        carrier_mass += dose_carrier
        cost += dose.raw_mass_mg * stock.cost_per_raw_mass_mg
        _add(material_active, stock.material_id, dose_active)
        _add(family_active, stock.family, dose_active)
        _add(module_active, dose.module_id, dose_active)

    for stock_id, total in sorted(stock_totals.items()):
        if total > stocks[stock_id].available_raw_mass_mg + _TOLERANCE:
            violations.append(
                _violation(
                    "INVENTORY_EXCEEDED",
                    f"stock {stock_id} requires {total:g} mg but only "
                    f"{stocks[stock_id].available_raw_mass_mg:g} mg is available",
                )
            )

    if not domain.total_active_mass_mg.contains(active_mass, tolerance=_TOLERANCE):
        violations.append(
            _violation(
                "TOTAL_ACTIVE_MASS_BREACH",
                f"active mass {active_mass:g} mg is outside "
                f"[{domain.total_active_mass_mg.minimum:g}, "
                f"{domain.total_active_mass_mg.maximum:g}] mg",
            )
        )

    for module_constraint in domain.module_active_mass_ranges:
        value = module_active.get(module_constraint.module_id, 0.0)
        if not (
            module_constraint.minimum_active_mass_mg - _TOLERANCE
            <= value
            <= module_constraint.maximum_active_mass_mg + _TOLERANCE
        ):
            violations.append(
                _violation(
                    "MODULE_RANGE_BREACH",
                    f"module {module_constraint.module_id} active mass {value:g} mg is outside "
                    f"[{module_constraint.minimum_active_mass_mg:g}, "
                    f"{module_constraint.maximum_active_mass_mg:g}] mg",
                )
            )

    for floor in domain.recognizer_floors:
        value = material_active.get(floor.material_id, 0.0)
        if value + _TOLERANCE < floor.minimum_active_mass_mg:
            violations.append(
                _violation(
                    "RECOGNIZER_FLOOR_BREACH",
                    f"material {floor.material_id} active mass {value:g} mg is below "
                    f"recognizer floor {floor.minimum_active_mass_mg:g} mg",
                )
            )

    for family_constraint in domain.family_fraction_ranges:
        value = family_active.get(family_constraint.family, 0.0)
        fraction = value / active_mass if active_mass > _TOLERANCE else 0.0
        if not (
            family_constraint.minimum_fraction - _TOLERANCE
            <= fraction
            <= family_constraint.maximum_fraction + _TOLERANCE
        ):
            violations.append(
                _violation(
                    "FAMILY_RANGE_BREACH",
                    f"family {family_constraint.family} active fraction {fraction:g} is outside "
                    f"[{family_constraint.minimum_fraction:g}, "
                    f"{family_constraint.maximum_fraction:g}]",
                )
            )

    for cap in domain.negative_space_caps:
        value = material_active.get(cap.material_id, 0.0)
        if value > cap.maximum_active_mass_mg + _TOLERANCE:
            violations.append(
                _violation(
                    "NEGATIVE_SPACE_BREACH",
                    f"material {cap.material_id} active mass {value:g} mg exceeds "
                    f"protected-negative-space cap {cap.maximum_active_mass_mg:g} mg",
                )
            )

    formula_hash = candidate_formula_state_sha256(domain, candidate)
    if require_gate_receipts:
        receipts = {receipt.gate_id: receipt for receipt in candidate.gate_receipts}
        for gate_id in domain.required_gate_ids:
            receipt = receipts.get(gate_id)
            if receipt is None:
                violations.append(
                    _violation("MISSING_HARD_GATE", f"required gate {gate_id} has no receipt")
                )
                continue
            if receipt.subject_sha256 != formula_hash:
                violations.append(
                    _violation(
                        "HARD_GATE_SUBJECT_MISMATCH",
                        f"gate {gate_id} is not bound to the candidate formula state",
                    )
                )
            if receipt.status is not GateStatus.PASS:
                violations.append(
                    _violation(
                        "HARD_GATE_NOT_PASS",
                        f"gate {gate_id} has status {receipt.status.value}",
                    )
                )

    accounting = CandidateAccounting(
        raw_mass_mg=raw_mass,
        active_mass_mg=active_mass,
        carrier_mass_mg=carrier_mass,
        unallocated_mass_mg=unallocated_mass,
        carrier_masses_mg=tuple(sorted(carrier_masses.items())),
        module_active_masses_mg=tuple(sorted(module_active.items())),
        material_active_masses_mg=tuple(sorted(material_active.items())),
        family_active_masses_mg=tuple(sorted(family_active.items())),
        cost=cost,
    )
    return FeasibilityAssessment(
        candidate_id=candidate.candidate_id,
        formula_state_sha256=formula_hash,
        feasible=not violations,
        violations=tuple(violations),
        accounting=accounting,
    )


def _axis_values(axis: MixtureDesignAxis, domain: MixtureDomain) -> tuple[float, ...]:
    stock = next((item for item in domain.stocks if item.stock_id == axis.stock_id), None)
    if stock is None:
        raise C10ContractError(f"axis stock {axis.stock_id} is not in the domain")
    increment = stock.dispensing_increment_mg
    if not _multiple_of_increment(axis.minimum_raw_mass_mg, increment):
        raise C10ContractError(f"axis minimum for {axis.stock_id} is off dispensing increment")
    if not _multiple_of_increment(axis.maximum_raw_mass_mg, increment):
        raise C10ContractError(f"axis maximum for {axis.stock_id} is off dispensing increment")
    start = round(axis.minimum_raw_mass_mg / increment)
    stop = round(axis.maximum_raw_mass_mg / increment)
    return tuple(index * increment for index in range(start, stop + 1))


def _candidate_from_point(
    domain: MixtureDomain,
    axes: tuple[MixtureDesignAxis, ...],
    values: Iterable[float],
    stage: DesignStage,
) -> MixtureCandidate:
    doses = tuple(
        CandidateDose(axis.stock_id, value, axis.module_id)
        for axis, value in zip(axes, values, strict=True)
        if value > _TOLERANCE
    )
    identity = canonical_sha256(
        {
            "schema": "c10-mixture-lattice-point-v1",
            "domain_sha256": domain.content_sha256,
            "stage": stage.value,
            "doses": doses,
        }
    )
    return MixtureCandidate(
        candidate_id=f"c10-{identity[:20]}",
        stage=stage,
        role=CandidateRole.SCREENING,
        doses=doses,
    )


def generate_mixture_design(
    domain: MixtureDomain,
    *,
    axes: tuple[MixtureDesignAxis, ...],
    stage: DesignStage,
    maximum_combinations: int,
) -> MixtureDesignResult:
    """Enumerate a bounded integer lattice and emit only feasible mixtures."""

    stage = DesignStage(stage)
    axes = tuple(sorted(axes, key=lambda item: (item.stock_id, item.module_id)))
    if not axes:
        raise C10ContractError("mixture design requires at least one axis")
    if len({item.stock_id for item in axes}) != len(axes):
        raise C10ContractError("mixture design axes must use unique stock IDs")
    maximum = int(maximum_combinations)
    if maximum <= 0:
        raise C10ContractError("maximum_combinations must be greater than zero")

    value_sets = tuple(_axis_values(axis, domain) for axis in axes)
    total_combinations = 1
    for values in value_sets:
        total_combinations *= len(values)

    candidates: list[MixtureCandidate] = []
    considered = 0
    rejected = 0
    truncated = total_combinations > maximum
    for point in islice(product(*value_sets), maximum):
        considered += 1
        candidate = _candidate_from_point(domain, axes, point, stage)
        assessment = assess_candidate(domain, candidate, require_gate_receipts=False)
        if assessment.feasible:
            if len(candidates) >= domain.maximum_candidates:
                truncated = True
                break
            candidates.append(candidate)
        else:
            rejected += 1

    return MixtureDesignResult(
        domain_sha256=domain.content_sha256,
        candidates=tuple(sorted(candidates, key=lambda item: item.candidate_id)),
        considered_count=considered,
        rejected_count=rejected,
        truncated=truncated,
    )


__all__ = [
    "assess_candidate",
    "candidate_formula_state_sha256",
    "generate_mixture_design",
]
