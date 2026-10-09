"""Advisory crowding and IFRA checks for composed formulas.

The composer's drafts are run through the release gate's own Hedione-share,
musk-count and IFRA functions (``engine.pipeline.gates.run_composition_gates``)
so a draft that over-doses Hedione, stacks musks or exceeds an IFRA limit is
flagged before anyone pipettes it. Nothing here re-implements a cap, a musk
rule or an IFRA limit, and nothing here changes the design decision: the
checks are attached beside the existing report keys.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

DEFAULT_BOTTLE_ML = Decimal(30)

_GATE_TO_CHECK = {
    "hedione_share": "hedione_share",
    "musk_count": "musk_count",
    "safety_ifra_allergen": "ifra",
    "safety": "ifra",
}


def _decimal(value: object) -> Decimal | None:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _gate_formula_record(
    name: str, rows: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Convert composer rows into the gate's formula record; list rows left out."""

    ingredients_ul: dict[str, Decimal] = {}
    dilutions: dict[str, Decimal] = {}
    stock_specs: dict[str, dict[str, Any]] = {}
    unchecked: list[dict[str, str]] = []
    for row in rows:
        material = str(row.get("material") or "")
        amount = _decimal(row.get("amount_decimal"))
        fraction = _decimal(row.get("stock_fraction_decimal"))
        unit = str(row.get("amount_unit") or "")
        if unit == "mg":
            # The gate reads liquid doses only; a weighed solid is not checked.
            unchecked.append({"material": material, "reason": "weighed solid (mg)"})
            continue
        if not material or amount is None or fraction is None or unit not in {"uL", "mL"}:
            unchecked.append({"material": material, "reason": "no stock strength or dose"})
            continue
        amount_ul = amount * (Decimal(1000) if unit == "mL" else Decimal(1))
        if material in dilutions and dilutions[material] != fraction:
            # Same material at a second strength: add it as the equivalent
            # volume of the first stock so the active total stays right.
            if dilutions[material] == 0:
                unchecked.append({"material": material, "reason": "no stock strength or dose"})
                continue
            amount_ul = amount_ul * fraction / dilutions[material]
            fraction = dilutions[material]
        ingredients_ul[material] = ingredients_ul.get(material, Decimal(0)) + amount_ul
        dilutions[material] = fraction
        stock_specs[material] = {
            "declared": True,
            "fraction": float(fraction),
            "fraction_basis": str(row.get("fraction_basis") or "unspecified"),
            "carrier": str(row.get("carrier") or ""),
            "stock_id": str(row.get("stock_id") or ""),
            "approximate": False,
        }
    record = {
        "number": 1,
        "name": name,
        "ingredients_ul": {key: float(value) for key, value in ingredients_ul.items()},
        "dilutions": {key: float(value) for key, value in dilutions.items()},
        "stock_specs": stock_specs,
    }
    return record, unchecked


def _ifra_checks(gate: Mapping[str, Any]) -> list[dict[str, str]]:
    data = dict(gate.get("data") or {})
    entries = [*data.get("rows", []), *data.get("groups", [])]
    checks: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(status: str, message: str) -> None:
        if message and message not in seen:
            seen.add(message)
            checks.append({"check": "ifra", "status": status, "message": message})

    for item in data.get("headroom_violations", []):
        add("FAIL", str(item.get("message", "")))
    for material in data.get("banned", []):
        message = next(
            (str(e.get("message", "")) for e in entries if e.get("material") == material),
            f"{material} is prohibited under IFRA Category 4.",
        )
        add("FAIL", message)
    for hold in data.get("holds", []):
        add("WARN", f"IFRA hold: {hold.get('message', '')}")
    if checks:
        return checks
    status = str(gate.get("status", ""))
    detail = str(gate.get("detail", ""))
    if status in {"FAIL", "HOLD"}:
        return [{"check": "ifra", "status": "WARN", "message": detail}]
    return [{
        "check": "ifra",
        "status": "WARN" if status == "WARN" and data.get("edge_dosing") else "PASS",
        "message": detail,
    }]


def composition_checks(
    formula: Mapping[str, Any] | None,
    *,
    formula_name: str,
) -> dict[str, Any]:
    """Run the gate's crowding and IFRA functions on one composed formula."""

    rows = list((formula or {}).get("rows", []) or [])
    record, unchecked = _gate_formula_record(formula_name, rows)
    concentrate_ul = sum(record["ingredients_ul"].values())
    # Neither compose request carries a final volume, so the bottle is assumed.
    basis = (
        f"Checked as a {DEFAULT_BOTTLE_ML} mL bottle holding {concentrate_ul:g} uL of "
        f"composed stock concentrate (the request gave no final volume, so "
        f"{DEFAULT_BOTTLE_ML} mL is assumed)."
    )
    result: dict[str, Any] = {"basis": basis, "checks": [], "unchecked_rows": unchecked}
    if not record["ingredients_ul"]:
        result["checks"] = [{
            "check": "gate",
            "status": "SKIP",
            "message": "checks could not run: no row has a known stock strength",
        }]
        return result
    try:
        from engine.pipeline.gates import ReleaseGateConfig, run_composition_gates

        config = ReleaseGateConfig(
            expected_concentrate_ul=concentrate_ul,
            batch_volume_ml=float(DEFAULT_BOTTLE_ML),
            brief="auto",
            quantitative_claim=True,
            audit_enabled=False,
            mode="RELEASE_REVIEW",
            action="REPORT",
        )
        gates = [gate.as_dict() for gate in run_composition_gates(record, config)]
    except Exception as error:  # advisory: a gate failure must not fail the design
        result["checks"] = [{
            "check": "gate",
            "status": "ERROR",
            "message": f"checks could not run: {type(error).__name__}: {error}",
        }]
        return result
    checks: list[dict[str, str]] = []
    for gate in gates:
        name = _GATE_TO_CHECK.get(str(gate.get("gate", "")), str(gate.get("gate", "")))
        error = (gate.get("data") or {}).get("error")
        if error:
            checks.append({
                "check": name,
                "status": "ERROR",
                "message": f"checks could not run: {error}",
            })
        elif name == "ifra":
            checks.extend(_ifra_checks(gate))
        else:
            status = str(gate.get("status", ""))
            checks.append({
                "check": name,
                "status": status if status in {"PASS", "WARN", "FAIL", "SKIP"} else "WARN",
                "message": str(gate.get("detail", "")),
            })
    result["checks"] = checks
    return result


def attach_composition_checks(report: dict[str, Any]) -> dict[str, Any]:
    """Add ``composition_checks`` to a design report and each of its variants."""

    from engine.research.contracts import stable_payload_hash

    name = str(report.get("formula_name") or "Composed formula")
    computed: dict[int, dict[str, Any]] = {}

    def checks_for(formula: Mapping[str, Any]) -> dict[str, Any]:
        key = id(formula)
        if key not in computed:
            computed[key] = composition_checks(formula, formula_name=name)
        return computed[key]

    enhanced = dict(report)
    main = enhanced.get("optimized_formula") or enhanced.get("initial_formula")
    if isinstance(main, Mapping) and main.get("rows"):
        enhanced["composition_checks"] = checks_for(main)
    variants = []
    for variant in enhanced.get("design_variants") or []:
        formula = variant.get("formula") if isinstance(variant, Mapping) else None
        if isinstance(formula, Mapping) and formula.get("rows"):
            variant = {**variant, "composition_checks": checks_for(formula)}
        variants.append(variant)
    if "design_variants" in enhanced:
        enhanced["design_variants"] = variants
    if "design_sha256" in enhanced:
        enhanced["design_sha256"] = stable_payload_hash(
            {key: value for key, value in enhanced.items() if key != "design_sha256"}
        )
    return enhanced
