"""Live checks for the formula editor: IFRA Category 4 and EU allergens on the finished bottle.

The same engine functions the release gate's safety check uses, without the rest of the
gate, so the editor can ask on every edit: each row's active material as % w/w of the
bottle (stocks topped up with ethanol), then the IFRA 51 Category 4 table with natural
constituents and group totals, then the EU allergen label line (leave-on). It reads
material data only and changes nothing. It is a screen, not release authority: the gate
on the saved card still decides.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any

from engine.ifra_safety import eu_allergen_rows
from engine.ifra_standards import (
    FinishedProductRow,
    IFRACheck,
    IFRAGroupCheck,
    estimate_finished_product_pct_w_w,
    evaluate_ifra,
    load_ifra_table,
    load_natural_constituents,
    load_undisclosed_bases,
    undisclosed_base,
)
from engine.material_resolver import resolve_material
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

SCHEMA_VERSION = "workbench-formula-checks-v1"
ETHANOL_NAMES = frozenset({"ethanol", "perfumer's alcohol", "perfumers alcohol", "alcohol"})
# A registry density outside this range is a data error, as on the bench sheet.
_DENSITY_RANGE_G_ML = (0.5, 3.0)
_Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)]


class FormulaCheckRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    # A liquid in µL of its stock, or a solid in mg: exactly one.
    amount_ul: Decimal | None = Field(default=None, gt=0, le=10_000_000, allow_inf_nan=False)
    amount_mg: Decimal | None = Field(default=None, gt=0, le=10_000_000, allow_inf_nan=False)
    stock_fraction: Decimal = Field(default=Decimal(1), gt=0, le=1, allow_inf_nan=False)
    fraction_basis: _Text | None = None
    carrier: _Text | None = None

    @model_validator(mode="after")
    def _one_amount(self) -> FormulaCheckRow:
        if (self.amount_ul is None) == (self.amount_mg is None):
            raise ValueError("Give each row amount_ul or amount_mg, not both.")
        return self


class FormulaChecksRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[FormulaCheckRow] = Field(min_length=1, max_length=200)
    # The finished bottle; ignored when the rows list their ethanol themselves.
    bottle_ml: Decimal = Field(default=Decimal(30), gt=0, le=100_000, allow_inf_nan=False)


@lru_cache(maxsize=4096)
def _identity(name: str) -> tuple[tuple[str, ...], float | None]:
    """The row's other names for the IFRA table (as the gate tries them) and its density."""
    resolved = resolve_material(name)
    names = [resolved.canonical_name, resolved.profile_name, resolved.registry_name]
    alt = tuple(n for n in dict.fromkeys(names) if n and n != name)
    material = resolved.registry_material
    density = getattr(material, "density_25c_g_ml", None) if material is not None else None
    try:
        value = float(density) if density is not None else None
    except (TypeError, ValueError):
        value = None
    low, high = _DENSITY_RANGE_G_ML
    if value is None or not low <= value <= high:
        value = None
    return alt, value


def _is_ethanol(name: str) -> bool:
    return name.strip().casefold() in ETHANOL_NAMES


def _row_dict(check: IFRACheck) -> dict[str, Any]:
    return {
        "material": check.material,
        "ifra_name": check.ifra_name,
        "ifra_status": check.status,
        "standard": check.standard,
        "actual_pct": check.pct,
        "limit_pct": check.limit_pct,
        "usage_pct": round(check.ratio * 100.0, 1) if check.ratio is not None else None,
        "verdict": check.verdict,
        "message": check.message,
    }


def _group_dict(group: IFRAGroupCheck) -> dict[str, Any]:
    ratio_rule = group.rule == "sum_of_ratios_le_1"
    limit = 1.0 if ratio_rule else group.limit_pct
    return {
        "group": group.id,
        "standard": group.standard,
        "rule": group.rule,
        "members": dict(group.member_pcts),
        "actual_pct": group.total,
        "limit_pct": limit,
        "usage_pct": round(group.total / limit * 100.0, 1) if limit else None,
        "verdict": group.verdict,
        "message": group.message,
    }


def compute_formula_checks(request: FormulaChecksRequest) -> dict[str, Any]:
    ethanol_ul = 0.0
    rows: list[FinishedProductRow] = []
    alt_names: dict[str, tuple[str, ...]] = {}
    for row in request.rows:
        if _is_ethanol(row.material):
            ethanol_ul += float(row.amount_ul or 0)
            continue
        alt, density = _identity(row.material)
        alt_names[row.material] = alt
        fraction = float(row.stock_fraction)
        if row.amount_mg is not None:
            # A weighed solid: its active grams are known, and it adds no volume.
            rows.append(FinishedProductRow(
                name=row.material, stock_ul=0.0, active_fraction=fraction,
                active_g=float(row.amount_mg) / 1000.0 * fraction,
            ))
            continue
        rows.append(FinishedProductRow(
            name=row.material,
            stock_ul=float(row.amount_ul or 0),
            active_fraction=fraction,
            active_density_g_ml=density,
            carrier=row.carrier,
            fraction_basis=row.fraction_basis or "unspecified",
        ))
    concentrate_ul = sum(row.stock_ul for row in rows)
    from_rows = ethanol_ul > 0
    bottle_ml = (concentrate_ul + ethanol_ul) / 1000.0 if from_rows else float(request.bottle_ml)
    estimate = estimate_finished_product_pct_w_w(rows, batch_volume_ml=bottle_ml)
    pct = dict(estimate.pct_w_w)

    table = load_ifra_table()
    evaluation = evaluate_ifra(
        pct, table=table, constituents=load_natural_constituents(), alt_names=alt_names
    )
    bases = load_undisclosed_bases()
    undisclosed = sorted(
        c.material for c in evaluation.unchecked
        if undisclosed_base(bases, [c.material, *alt_names.get(c.material, ())]) is not None
    )
    unrecognised = sorted(c.material for c in evaluation.unchecked if c.material not in undisclosed)
    holds = [c.material for c in evaluation.holds]
    if evaluation.failures:
        verdict = "FAIL"
    elif unrecognised or holds or estimate.overfilled:
        verdict = "HOLD"
    elif evaluation.warnings or undisclosed:
        verdict = "WARN"
    else:
        verdict = "PASS"

    return {
        "schema_version": SCHEMA_VERSION,
        "bottle_ml": bottle_ml,
        "bottle_source": "rows" if from_rows else "bottle_ml",
        "concentrate_ml": estimate.concentrate_ml,
        "ethanol_ml": estimate.ethanol_ml,
        "oil_pct": 100.0 * estimate.concentrate_ml / bottle_ml,
        "overfilled": estimate.overfilled,
        "finished_mass_g": estimate.finished_mass_g,
        "pct_w_w": pct,
        "ifra": {
            "amendment": table.amendment_in_force,
            "category": table.category,
            "basis": table.basis,
            "verdict": verdict,
            "rows": [_row_dict(c) for c in evaluation.checks],
            "groups": [_group_dict(g) for g in evaluation.group_checks],
            "unrecognised": unrecognised,
            "undisclosed_bases": undisclosed,
        },
        "allergens": {
            "use": "leave_on",
            "declare": eu_allergen_rows(pct, leave_on=True),
            "counted": "named allergen materials only; allergens inside naturals and bases are not counted",
        },
        "assumptions": list(estimate.assumptions),
        "release_authority": False,
        "inventory_modified": False,
        "compounding_authority": False,
    }
