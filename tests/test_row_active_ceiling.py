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
# An exact-preference row above the ceiling (Tuberlia Base 54.6%, Cedarwood
# Virginia 43.5%) is never cut for it, and used to go unnamed.
_WHITE_FLORAL = dict(idea="jasmine tuberose white floral")
_PINE_RAIN = dict(idea="pine forest after rain")


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


def _named_above_ceiling(result: dict[str, Any], formula: dict[str, Any]) -> set[str]:
    """The stock ids the formula's own holds name above the ceiling (the
    report's holds are the optimized formula's; a variant's are not shown)."""

    if formula["rows"] != result["optimized_formula"]["rows"]:
        return set()
    return {
        hold.split(":", 1)[1]
        for hold in result["constraint_audit"]["holds"]
        if hold.startswith("ROW_ABOVE_ACTIVE_CEILING:")
    }


@pytest.mark.parametrize(
    "brief",
    [_WHITE_MUSK, _QUIET_SKIN, _WHITE_FLORAL, _PINE_RAIN],
    ids=["white_musk", "quiet_skin", "white_floral", "pine_rain"],
)
def test_no_composed_row_passes_the_active_ceiling(brief: dict[str, Any]) -> None:
    # Every row, liquid or weighed, is at or under the ceiling, or the formula
    # names it in a ROW_ABOVE_ACTIVE_CEILING hold (the rows that could take its
    # excess could not).
    result = design_inventory_formula(**brief)
    for formula in _formulas(result):
        rows = formula["rows"]
        total_active = sum(_row_active(row) for row in rows)
        named = _named_above_ceiling(result, formula)
        over = {
            row["identity_name"]: float(_row_active(row) / total_active)
            for row in rows
            if _row_active(row) > CEILING * total_active and row["stock_id"] not in named
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


def _ceiling_pass(choices: list[Any]) -> tuple[dict[int, int], list[str]]:
    free_rows = [
        (index, planner._allocation_weight(choice), planner._design_cap_ul(choice, TOTAL))
        for index, choice in enumerate(choices)
    ]
    allocated, _fallback_holds = _fallback(choices)
    holds: list[str] = []
    return planner._hold_active_ceiling(allocated, free_rows, {}, choices, TOTAL, holds), holds


def test_a_restraint_share_row_never_takes_another_row_s_excess(firm_caps: dict[str, int]) -> None:
    # A 3% restraint share on a 1% stock (design cap 180 uL) once took over
    # 5,000 uL of a volume row's excess.  The bulk fallback never releases a
    # role with an explicit restraint share, nor a row with a hard cap, so no
    # row can take the excess here: the volume row keeps it, named.
    firm_caps.update({"Cedramber": 300})
    choices = [
        _choice("Habanolide", function="volume", max_raw_share=0.2),
        _choice("Isobutyl Quinoline", 0.01, max_raw_share=0.03),
        _choice("Cedramber"),
    ]
    assert planner._design_cap_ul(choices[1], TOTAL) == 180

    result, holds = _ceiling_pass(choices)

    assert sum(result.values()) == TOTAL
    assert result[1] <= 180
    assert result[2] <= 300
    assert _shares(choices, result)[0] > CEILING
    assert holds == ["ROW_ABOVE_ACTIVE_CEILING:stock:Habanolide"]


def test_a_row_the_fallback_would_release_takes_the_excess_and_says_why(
    firm_caps: dict[str, int]
) -> None:
    # A row with no restraint share may pass its design cap for the ceiling,
    # as the fallback's last role-cap stage would release it; the total was
    # already full, so its hold says it was for the ceiling.
    firm_caps.update({"Cedramber": 300})
    choices = [
        _choice("Habanolide", function="volume", max_raw_share=0.2),
        _choice("Isobutyl Quinoline", 0.01, max_raw_share=0.03),
        _choice("Cedramber"),
        _choice("Hedione"),
    ]
    caps = [planner._design_cap_ul(choice, TOTAL) for choice in choices]

    result, holds = _ceiling_pass(choices)

    assert sum(result.values()) == TOTAL
    assert result[1] <= caps[1] and result[2] <= 300
    assert result[3] > caps[3]
    assert _shares(choices, result)[3] <= CEILING
    assert sorted(holds) == [
        "ROLE_CAP_EXCEEDED_FOR_ACTIVE_CEILING:stock:Hedione",
        "ROW_ABOVE_ACTIVE_CEILING:stock:Habanolide",
    ]


def test_a_requested_quantity_above_the_ceiling_is_named_and_never_cut() -> None:
    # 4000 uL of neat Habanolide in 6000 uL of neat rows: 66.7% of the active.
    choices = []
    for identity in ("Habanolide", "Ethylene Brassylate", "Hedione"):
        role = planner.RoleSpec(f"r_{identity}", identity, "base", "volume", 0.3, ())
        choices.append(planner.Choice(role, _capability(identity, 1.0).candidate, 1.0, ()))
    quantities = [
        {"scope": "MATERIAL_DOSE", "material": "Habanolide", "amount_decimal": "4000", "unit": "uL"}
    ]

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=quantities)

    assert rows[0]["amount_decimal"] == "4000"
    assert totals["liquid_total_ul"] == str(TOTAL)
    assert f"ROW_ABOVE_ACTIVE_CEILING:{rows[0]['stock_id']}" in holds


def test_a_weighed_solid_above_the_ceiling_is_named_and_never_cut() -> None:
    from engine.formulation_intelligence.material_capability_index import (
        build_material_capability_index,
    )

    crystal = next(
        capability.candidate
        for capability in build_material_capability_index().capabilities
        if capability.identity_name == "Ambrox Super" and capability.candidate.solid
    )
    choices = [
        planner.Choice(
            planner.RoleSpec("r_amber", "Ambrox Super", "base", "structure", 0.2, ()),
            crystal, 1.0, (),
        )
    ]
    for identity in ("Habanolide", "Ethylene Brassylate"):
        role = planner.RoleSpec(f"r_{identity}", identity, "base", "volume", 0.4, ())
        choices.append(planner.Choice(role, _capability(identity, 1.0).candidate, 1.0, ()))
    # 5000 mg of neat crystal beside 6000 uL of neat liquid: 45% of the active.
    quantities = [
        {"scope": "MATERIAL_DOSE", "material": "Ambrox Super", "amount_decimal": "5000", "unit": "mg"}
    ]

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=quantities)

    solid = rows[0]
    assert (solid["amount_unit"], solid["amount_decimal"]) == ("mg", "5000")
    assert totals["liquid_total_ul"] == str(TOTAL)
    assert f"ROW_ABOVE_ACTIVE_CEILING:{solid['stock_id']}" in holds


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


def _detection(monkeypatch, rows: list[dict], per_ul: dict[str, float]) -> dict:
    monkeypatch.setattr(
        dp, "_simulate",
        lambda rows, amounts: {
            rows[i]["identity_name"]: {w: float(a) * per_ul[rows[i]["identity_name"]] for w in dp.WINDOWS}
            for i, a in amounts.items()
        },
    )
    monkeypatch.setattr(dp, "_row_cap", lambda row, role, index, total: (Decimal(5000), "role cap"))
    monkeypatch.setattr(dp, "_blocking_checks", lambda formula, name: set())
    monkeypatch.setattr(planner, "_long_lasting_material", lambda name: False)
    return dp.apply_detection_pass(
        {"rows": rows}, role_plan=None, interpretation={}, formula_name="t", index=[object()],
    )


def test_a_detection_raise_that_puts_a_weighed_row_past_the_ceiling_is_rejected(monkeypatch) -> None:
    # Raising the silent 1% row from 50 to 100 uL takes 50 uL of neat Filler
    # out of the active oil, so the 390 mg crystal, 39.4% of it as composed,
    # would carry 41.5%.
    rows = [
        {**_drow(0, "Crystal", 390, "structure", "base", "facet_amber_mineral"), "amount_unit": "mg"},
        _drow(1, "Lead", 330, "character", "heart", "facet_lead"),
        _drow(2, "Quiet", 50, "structure", "base", "base_wood_layer", fraction="0.01"),
        _drow(3, "Filler", 270, "volume", "base", "base_musk_layer"),
    ]

    result = _detection(monkeypatch, rows, {"Lead": 0.01, "Quiet": 0.015, "Filler": 0.01})

    quiet = next(e for e in result["detection_check"]["roles"] if e["material"] == "Quiet")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "40% active ceiling"
    assert [r["amount_decimal"] for r in result["rows"]] == ["390", "330", "50", "270"]


def test_a_row_composed_above_the_ceiling_is_not_raised_past_its_share(monkeypatch) -> None:
    # "Quiet" carries half the active oil as composed (the composer named it);
    # raising it to 750 uL would take it to 62.5%.
    rows = [
        _drow(0, "Lead", 300, "character", "heart", "facet_lead"),
        _drow(1, "Quiet", 600, "structure", "base", "base_wood_layer"),
        _drow(2, "Filler", 300, "volume", "base", "base_musk_layer"),
    ]

    result = _detection(monkeypatch, rows, {"Lead": 0.01, "Quiet": 0.0015, "Filler": 0.01})

    quiet = next(e for e in result["detection_check"]["roles"] if e["material"] == "Quiet")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "40% active ceiling"
    assert [r["amount_decimal"] for r in result["rows"]] == ["300", "600", "300"]
