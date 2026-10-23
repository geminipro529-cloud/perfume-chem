"""No single row carries more than 40% of the formula's active oil."""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from types import SimpleNamespace
from typing import Any

import pytest

from engine.formulation_intelligence import detection_pass as dp
from engine.research import composition_planner as planner
from engine.research.formula_design import design_inventory_formula

CEILING = Decimal("0.40")
CARRIERS = {"benzyl benzoate", "diethyl phthalate", "dipropylene glycol", "triethyl citrate"}
TOTAL = 6000

_QUIET_SKIN = dict(
    idea=(
        "Create a six-material intimate human skin scent with soft warmth and "
        "close diffusion, not detergent, shampoo or loud clean musk."
    ),
    formula_name="Quiet Human Six",
    max_materials=6,
)
_WHITE_MUSK = dict(idea="a white musk laundry scent")


def _row_active(row: dict[str, Any]) -> Decimal:
    # A functional carrier counts 0; a weighed solid counts 1 mg as 1 uL.
    if str(row["identity_name"]).casefold() in CARRIERS:
        return Decimal(0)
    return Decimal(row["amount_decimal"]) * Decimal(row["stock_fraction_decimal"])


def _formulas(result: dict[str, Any]) -> list[dict[str, Any]]:
    variants = [
        variant["formula"]
        for variant in result.get("design_variants") or []
        if isinstance(variant, dict) and variant.get("formula", {}).get("rows")
    ]
    return [result["optimized_formula"], *variants]


@pytest.mark.parametrize("brief", [_WHITE_MUSK, _QUIET_SKIN], ids=["white_musk", "quiet_skin"])
def test_no_composed_row_passes_the_active_ceiling(brief: dict[str, Any]) -> None:
    result = design_inventory_formula(**brief)
    for formula in _formulas(result):
        rows = formula["rows"]
        total_active = sum(_row_active(row) for row in rows)
        over = {
            row["identity_name"]: float(_row_active(row) / total_active)
            for row in rows
            if row["amount_unit"] == "uL" and _row_active(row) > CEILING * total_active
        }
        assert not over, over
        liquid = sum(Decimal(row["amount_decimal"]) for row in rows if row["amount_unit"] == "uL")
        assert liquid == Decimal(formula["separate_totals"]["liquid_total_ul"]) == TOTAL


# Synthetic stocks: firm (identity hard) caps are given per name, and no
# normal-use ceiling or IFRA cap applies, so the stages alone are exercised.
def _stocked(name: str, dilution: float = 1.0) -> Any:
    stock = SimpleNamespace(
        name=name,
        identity_name=name,
        raw_name=name,
        physical_form="liquid",
        fraction_basis="neat" if dilution >= 1 else "mass_fraction",
        carrier="" if dilution >= 1 else "DPG",
        dilution=dilution,
        stock_id=f"stock:{name}",
    )
    return SimpleNamespace(stock=stock, solid=False)


def _choice(name: str, dilution: float = 1.0, *, function: str = "character", max_raw_share=None, named=False):
    role = planner.RoleSpec(
        f"r_{name}", name, "heart", function, 0.1, (),
        max_raw_share=max_raw_share, serves_requested_facet=named,
    )
    return planner.Choice(role, _stocked(name, dilution), 1.0, ())


@pytest.fixture
def firm_caps(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    caps: dict[str, int] = {}
    monkeypatch.setattr(planner, "_ifra_cap_ul", lambda *_args: None)
    monkeypatch.setattr(planner, "_normal_use_ceiling_cap_ul", lambda *_args: None)
    monkeypatch.setattr(
        planner, "_hard_cap_ul", lambda candidate, _total: caps.get(candidate.stock.name)
    )
    return caps


def _fallback(choices: list[Any]) -> tuple[dict[int, int], list[str]]:
    free_rows = [
        (index, planner._allocation_weight(choice), planner._design_cap_ul(choice, TOTAL))
        for index, choice in enumerate(choices)
    ]
    holds: list[str] = []
    return planner._allocate_with_bulk_fallback(TOTAL, free_rows, choices, TOTAL, holds), holds


def _shares(choices: list[Any], allocated: dict[int, int]) -> dict[int, Decimal]:
    active = {index: planner._active_ul(choices[index], amount) for index, amount in allocated.items()}
    total = sum(active.values())
    return {index: value / total for index, value in active.items()}


def test_a_neat_and_a_ten_percent_named_row_spill_by_one_ratio(firm_caps: dict[str, int]) -> None:
    # The 10% row weighs three times its share; it no longer takes the spill x3.
    firm_caps.update({"Habanolide": 1100, "Ethylene Brassylate": 1100, "Cedramber": 1100})
    choices = [
        _choice("Ambrettolide", max_raw_share=0.16, named=True),
        _choice("Ambrox Super", 0.1, max_raw_share=0.0445, named=True),
        _choice("Habanolide"),
        _choice("Ethylene Brassylate"),
        _choice("Cedramber"),
    ]
    caps = [planner._design_cap_ul(choice, TOTAL) for choice in choices]
    assert caps[:2] == [960, 267]
    allocated, holds = _fallback(choices)

    assert sum(allocated.values()) == TOTAL
    ratio = Decimal(allocated[0]) / caps[0]
    assert ratio > 1
    assert abs(Decimal(allocated[1]) - ratio * caps[1]) <= 1
    assert all(allocated[index] <= caps[index] for index in (2, 3, 4))
    assert max(_shares(choices, allocated).values()) <= CEILING
    assert sorted(holds) == [
        "ROLE_CAP_EXCEEDED_TO_FILL_TOTAL:stock:Ambrettolide",
        "ROLE_CAP_EXCEEDED_TO_FILL_TOTAL:stock:Ambrox Super",
    ]


def test_a_named_accord_under_spill_rises_with_one_ratio(firm_caps: dict[str, int]) -> None:
    firm_caps.update({"Iso E Super": 1500, "Hedione": 1500, "Cashmeran": 1500})
    choices = [
        _choice("Lavender EO", max_raw_share=0.10, named=True),
        _choice("Linalyl Acetate", max_raw_share=0.05, named=True),
        _choice("Ambrox Super", 0.25, function="fixative", max_raw_share=0.04, named=True),
        _choice("Iso E Super"),
        _choice("Hedione"),
        _choice("Cashmeran"),
    ]
    caps = [planner._design_cap_ul(choice, TOTAL) for choice in choices]
    allocated, _holds = _fallback(choices)

    assert sum(allocated.values()) == TOTAL
    ratios = [Decimal(allocated[index]) / caps[index] for index in range(3)]
    assert min(ratios) > 1
    for index in range(3):
        assert abs(Decimal(allocated[index]) - ratios[0] * caps[index]) <= 1, (allocated, caps)
    assert max(_shares(choices, allocated).values()) <= CEILING


@lru_cache(maxsize=None)
def _capability(identity: str, dilution: float) -> Any:
    from engine.formulation_intelligence.material_capability_index import (
        build_material_capability_index,
    )

    return next(
        capability
        for capability in build_material_capability_index().capabilities
        if capability.identity_name == identity
        and float(capability.candidate.stock.dilution) == dilution
        and not capability.candidate.solid
    )


def test_too_few_rows_keep_the_design_and_name_the_rows_above_the_ceiling() -> None:
    # Two neat rows: one of them always carries at least half the active oil.
    choices = []
    for identity in ("Habanolide", "Ethylene Brassylate"):
        role = planner.RoleSpec(f"r_{identity}", identity, "base", "volume", 0.5, ())
        choices.append(planner.Choice(role, _capability(identity, 1.0).candidate, 1.0, ()))
    for choice in choices:
        assert planner._firm_cap_ul(choice, TOTAL) is None

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=())

    assert totals["liquid_total_ul"] == str(TOTAL)
    assert sum(int(row["amount_decimal"]) for row in rows) == TOTAL
    assert len(rows) == 2
    over = [hold for hold in holds if hold.startswith("ROW_ABOVE_ACTIVE_CEILING:")]
    assert over
    assert {hold.split(":", 1)[1] for hold in over} <= {row["stock_id"] for row in rows}


def _synthetic(stock_id: str, *, named: bool = False) -> Any:
    role = SimpleNamespace(
        role_id=stock_id, serves_requested_facet=named, generic_slot=False,
        exact_preference_required=False,
    )
    stock = SimpleNamespace(stock_id=stock_id, identity_name=stock_id, name=stock_id, dilution=1.0)
    return SimpleNamespace(role=role, candidate=SimpleNamespace(stock=stock))


def test_a_named_row_the_floor_wants_at_forty_percent_stops_at_its_ceiling(monkeypatch) -> None:
    # The floor wants 2400.4 uL of 6001; the two equal donors give in steps of
    # 2 uL, so an even take lands on 2401 (above the ceiling) or 2399.
    monkeypatch.setattr(planner, "_allocation_weight", lambda _choice: 1.0)
    monkeypatch.setattr(planner, "_firm_cap_ul", lambda _choice, _total: None)
    choices = [_synthetic("lavender", named=True), _synthetic("cedar"), _synthetic("vetiver")]
    allocated = {0: 601, 1: 2700, 2: 2700}
    holds: list[str] = []
    result = planner._lead_with_named_notes(
        allocated, [(index, 1.0, None) for index in allocated], {}, choices, TOTAL, holds
    )

    assert sum(result.values()) == sum(allocated.values())
    share = Decimal(result[0]) / sum(result.values())
    assert share <= CEILING
    assert result[0] == 2400
    assert not [hold for hold in holds if hold.startswith("NAMED_NOTE_FLOOR_SHORT")]


def _drow(i: int, name: str, amount: int, role: str, note: str, slot: str, fraction: str = "1") -> dict:
    return {
        "row_id": f"r{i}", "identity_name": name, "material": name, "amount_decimal": str(amount),
        "amount_unit": "uL", "stock_fraction_decimal": fraction, "role": role, "note": note,
        "slot": slot, "stock_id": f"s{i}",
    }


def test_a_detection_raise_that_puts_a_third_row_past_the_ceiling_is_rejected(monkeypatch) -> None:
    # Raising the silent 10% row takes neat volume out of the formula, so the
    # lead, 38.8% of the active oil as composed, would carry 40.6%.
    rows = [
        _drow(0, "Lead", 780, "character", "heart", "facet_lead"),
        _drow(1, "Filler", 700, "volume", "heart", "diffusion_texture"),
        _drow(2, "Other", 520, "texture", "top", "top_green_layer"),
        _drow(3, "Quiet", 100, "structure", "base", "base_wood_layer", fraction="0.1"),
    ]
    per_ul = {"Lead": 1.0, "Filler": 1.0, "Other": 1.0, "Quiet": 0.006}
    monkeypatch.setattr(
        dp, "_simulate",
        lambda rows, amounts: {
            rows[i]["identity_name"]: {w: float(a) * per_ul[rows[i]["identity_name"]] for w in dp.WINDOWS}
            for i, a in amounts.items()
        },
    )
    monkeypatch.setattr(dp, "_row_cap", lambda row, role, index, total: (Decimal(5000), "role cap"))
    monkeypatch.setattr(dp, "_blocking_checks", lambda formula, name: set())

    result = dp.apply_detection_pass(
        {"rows": rows}, role_plan=None, interpretation={}, formula_name="t", index=[object()],
    )

    quiet = next(e for e in result["detection_check"]["roles"] if e["material"] == "Quiet")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "40% active ceiling"
    assert [r["amount_decimal"] for r in result["rows"]] == ["780", "700", "520", "100"]
