"""Every composed formula carries as much active and long-lasting material as
Kenny's weakest reference formula: 57 uL of long-lasting material per mL of a
30 mL bottle (his weakest is 57.2, median 66) and 52% of the concentrate active
(his weakest 52.7%, median 73%).  The volume is moved between the formula's own
rows; what the caps, the named-note floor and the 40% active ceiling leave
short is reported as a hold, never forced.
"""

from __future__ import annotations

from decimal import Decimal
from functools import lru_cache
from typing import Any, Sequence

import pytest

from engine.formulation_intelligence import composition_checks as checks
from engine.formulation_intelligence import detection_pass as dp
from engine.formulation_intelligence import yardstick
from engine.material_resolver import gate_vp_25c_pa
from engine.pipeline import gates
from engine.research import composition_planner as planner
from engine.research.formula_design import design_inventory_formula

TOTAL = 6000


def _floor_ul() -> Decimal:
    """The long-lasting active volume a formula holds: 57 uL/mL x 30 mL."""

    return planner.LONG_LASTING_FLOOR_ACTIVE_UL


@lru_cache(maxsize=None)
def _candidate(identity: str, dilution: float, solid: bool = False) -> Any:
    from engine.formulation_intelligence.material_capability_index import (
        build_material_capability_index,
    )

    return next(
        capability.candidate
        for capability in build_material_capability_index().capabilities
        if capability.identity_name == identity
        and float(capability.candidate.stock.dilution) == dilution
        and capability.candidate.solid is solid
    )


def _choice(
    identity: str,
    dilution: float = 1.0,
    *,
    function: str = "character",
    share: float = 0.1,
    cap: float | None = None,
    named: bool = False,
    generic: bool = False,
    solid: bool = False,
    role_id: str | None = None,
) -> Any:
    role = planner.RoleSpec(
        role_id or f"r_{identity}", identity, "base", function, share, (),
        max_raw_share=cap, serves_requested_facet=named, generic_slot=generic,
    )
    return planner.Choice(role, _candidate(identity, dilution, solid), 1.0, ())


@pytest.fixture
def plain_caps(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Only the roles' own caps bind: identity hard caps are given per name,
    and no IFRA cap, normal-use ceiling or screening default applies."""

    caps: dict[str, int] = {}
    monkeypatch.setattr(planner, "_ifra_cap_ul", lambda *_args: None)
    monkeypatch.setattr(planner, "_normal_use_ceiling_cap_ul", lambda *_args: None)
    monkeypatch.setattr(planner, "_screening_default_cap_ul", lambda *_args: None)
    monkeypatch.setattr(
        planner,
        "_hard_cap_ul",
        lambda candidate, _total: caps.get(candidate.stock.identity_name or candidate.stock.name),
    )
    return caps


def _free_rows(choices: Sequence[Any]) -> list[tuple[int, float, int | None]]:
    return [
        (index, planner._allocation_weight(choice), planner._design_cap_ul(choice, TOTAL))
        for index, choice in enumerate(choices)
        if not choice.candidate.solid
    ]


def _composed(choices: Sequence[Any], holds: list[str]) -> dict[int, int]:
    """The allocation as the composer leaves it before the floors step."""

    free_rows = _free_rows(choices)
    allocated = planner._allocate_with_bulk_fallback(TOTAL, free_rows, choices, TOTAL, holds)
    return planner._lead_with_named_notes(allocated, free_rows, {}, choices, TOTAL, holds)


def _floors(choices: Sequence[Any], state: dict[int, int], holds: list[str]) -> dict[int, int]:
    return planner._meet_longevity_floors(
        dict(state), _free_rows(choices), {}, choices, TOTAL, holds,
    )


def _active(choices: Sequence[Any], state: dict[int, int]) -> Decimal:
    return sum(
        (planner._active_ul(choices[index], amount) for index, amount in state.items()), Decimal(0)
    )


def _long_active(choices: Sequence[Any], state: dict[int, int]) -> Decimal:
    return sum(
        (
            planner._active_ul(choices[index], amount)
            for index, amount in state.items()
            if planner._is_long_lasting(choices[index])
        ),
        Decimal(0),
    )


def _named_share(choices: Sequence[Any], state: dict[int, int]) -> Decimal:
    named = sum(
        (
            planner._active_ul(choices[index], amount)
            for index, amount in state.items()
            if choices[index].role.serves_requested_facet
        ),
        Decimal(0),
    )
    return named / _active(choices, state)


def _max_row_share(choices: Sequence[Any], state: dict[int, int]) -> Decimal:
    total = _active(choices, state)
    return max(planner._active_ul(choices[index], amount) for index, amount in state.items()) / total


def test_the_floor_constants_are_the_gate_s_and_the_yardstick_s() -> None:
    assert planner.LONG_LASTING_VP_25C_PA == gates.TENACITY_LONG_LASTING_VP_25C_PA
    assert planner.LONGEVITY_FLOOR_BOTTLE_ML == checks.DEFAULT_BOTTLE_ML
    assert planner.LONGEVITY_FLOOR_BOTTLE_ML == Decimal(str(yardstick.BOTTLE_ML))
    # 57 uL per mL of a 30 mL bottle.
    assert planner.LONG_LASTING_FLOOR_ACTIVE_UL == Decimal(1710)
    assert planner.ACTIVE_SHARE_FLOOR == Decimal("0.52")


@pytest.mark.parametrize(
    "identity,dilution,long_lasting",
    [
        ("Hedione", 1.0, True),
        ("Iso E Super", 1.0, False),
        ("Galaxolide", 0.5, True),
        ("Benzyl Salicylate", 1.0, True),
        ("Vanillin", 0.1, False),
        ("Linalool", 1.0, False),
    ],
)
def test_long_lasting_agrees_with_the_release_gate(
    identity: str, dilution: float, long_lasting: bool
) -> None:
    vp = gate_vp_25c_pa(identity)
    assert vp is not None
    # The gate's own screen, and the planner's reading of it.
    assert (vp < gates.TENACITY_LONG_LASTING_VP_25C_PA) is long_lasting
    assert planner._is_long_lasting(_choice(identity, dilution)) is long_lasting


def test_a_formula_under_the_longevity_floor_is_brought_to_it(plain_caps: dict[str, int]) -> None:
    # A named neat citrus, two unnamed neat rows that are not long-lasting and
    # two unnamed neat long-lasting rows whose shares leave them small.
    choices = [
        _choice("Bergamot FCF Oil Sicilian", named=True, share=.30, cap=.25,
                role_id="facet_citrus_peel"),
        _choice("Linalool", share=.35, cap=.35, function="volume"),
        _choice("Dihydromyrcenol", share=.25, cap=.35, function="volume"),
        _choice("Hedione", share=.06, cap=.20, function="structure"),
        _choice("Cedarwood Virginia", share=.04, cap=.20, function="structure"),
    ]
    before = _composed(choices, [])
    assert _long_active(choices, before) < _floor_ul()

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=())
    state = {index: int(row["amount_decimal"]) for index, row in enumerate(rows)}

    assert _long_active(choices, state) >= _floor_ul()
    assert not [hold for hold in holds if hold.startswith("LONG_LASTING_FLOOR_SHORT")]
    assert _named_share(choices, state) >= planner.NAMED_NOTE_FLOOR_SHARE
    assert _max_row_share(choices, state) <= planner.ROW_ACTIVE_CEILING_SHARE
    assert sum(state.values()) == int(totals["liquid_total_ul"]) == TOTAL
    # The long-lasting rows grew; nothing was added, dropped or swapped.
    assert state[3] > before[3] and state[4] > before[4]
    assert len(rows) == len(choices)


def test_the_active_floor_moves_volume_from_the_diluted_rows_to_the_neat_ones(
    plain_caps: dict[str, int]
) -> None:
    choices = [
        _choice("Aurantiol", 0.1, share=.40, cap=.30),
        _choice("Neroli EO", 0.1, share=.30, cap=.30),
        _choice("Hedione", share=.10, cap=.30, function="structure"),
        _choice("Cedarwood Virginia", share=.10, cap=.30, function="structure"),
        _choice("Habanolide", share=.10, cap=.30, function="fixative"),
    ]
    holds: list[str] = []
    before = _composed(choices, [])
    assert _active(choices, before) / TOTAL < planner.ACTIVE_SHARE_FLOOR

    after = _floors(choices, before, holds)

    assert _active(choices, after) / TOTAL >= planner.ACTIVE_SHARE_FLOOR
    assert not [hold for hold in holds if hold.startswith("ACTIVE_SHARE_FLOOR_SHORT")]
    assert sum(after.values()) == TOTAL
    # The diluted rows gave, the neat rows took.
    assert after[0] < before[0] and after[1] < before[1]
    assert all(after[index] > before[index] for index in (2, 3, 4))


def test_weak_grade_named_leads_leave_the_floors_short_and_say_which_rows(
    plain_caps: dict[str, int]
) -> None:
    # The brief names two notes Kenny owns only as weak stocks; the named-note
    # floor pins them where they are, so no volume is left to move.
    plain_caps.update({"Tobacco Absolute": 4000, "Isobutyl Quinoline": 2000})
    choices = [
        _choice("Tobacco Absolute", 0.1, named=True, share=.30, cap=.30),
        _choice("Isobutyl Quinoline", 0.01, named=True, share=.20, cap=.30),
        _choice("Linalool", share=.25, cap=.30, function="volume"),
        _choice("Hedione", share=.25, cap=.30, function="structure"),
    ]
    holds: list[str] = []
    before = _composed(choices, [])
    after = _floors(choices, before, holds)

    assert _long_active(choices, after) < _floor_ul()
    short = [
        hold for hold in holds
        if hold.startswith(("LONG_LASTING_FLOOR_SHORT:", "ACTIVE_SHARE_FLOOR_SHORT:"))
    ]
    assert len(short) == 2, holds
    reached = Decimal(short[0].split(":", 1)[1] if "LONG_LASTING" in short[0] else short[1].split(":", 1)[1])
    assert reached == (_long_active(choices, after) / planner.LONGEVITY_FLOOR_BOTTLE_ML).quantize(
        Decimal("0.1")
    )
    assert sorted(hold for hold in holds if hold.startswith("WEAK_GRADE_NAMED_ROW:")) == sorted(
        f"WEAK_GRADE_NAMED_ROW:{choices[index].candidate.stock.stock_id}" for index in (0, 1)
    )
    # No firm cap was passed to chase the floor, and the total is unchanged.
    for index in after:
        firm = planner._firm_cap_ul(choices[index], TOTAL)
        assert firm is None or after[index] <= firm
    assert sum(after.values()) == TOTAL


def test_a_functional_carrier_never_counts_and_never_grows(plain_caps: dict[str, int]) -> None:
    carrier = _choice("Benzyl Benzoate", share=.20, cap=.30, function="volume")
    # Below the threshold by vapour pressure, yet no active material at all.
    assert gate_vp_25c_pa("Benzyl Benzoate") < planner.LONG_LASTING_VP_25C_PA
    assert planner._is_long_lasting(carrier) is False
    choices = [
        carrier,
        _choice("Linalool", share=.30, cap=.30, function="volume"),
        _choice("Dihydromyrcenol", share=.30, cap=.30, function="volume"),
        _choice("Cedarwood Virginia", share=.10, cap=.20, function="structure"),
    ]
    holds: list[str] = []
    before = _composed(choices, [])
    assert _long_active(choices, before) < _floor_ul()

    after = _floors(choices, before, holds)

    assert _long_active(choices, after) >= _floor_ul()
    assert after[0] == before[0]
    assert sum(after.values()) == TOTAL


_TWICE_GIVING_DONORS = {
    # Linalool gives within the long-lasting rows' caps, then again when the
    # second pass lets them pass their role caps.
    "within_then_past_cap": (
        [
            ("Benzyl Benzoate", 1.0, .60, .70, "fixative", False),
            ("Linalool", 1.0, .10, .10, "modifier", False),
            ("Hedione", 1.0, .05, .05, "structure", False),
            ("Cedarwood Virginia", 1.0, .05, .05, "structure", False),
            ("Habanolide", 1.0, .05, .05, "structure", False),
        ],
        {0: 5000, 1: 400, 2: 200, 3: 200, 4: 200},
        1,
    ),
    # The 10% Neroli gives to the neat rows for the active floor, then to the
    # long-lasting rows for the long-lasting floor.
    "active_then_long_lasting": (
        [
            ("Benzyl Benzoate", 1.0, .50, .50, "fixative", False),
            ("Neroli EO", 0.1, .20, .20, "modifier", False),
            ("Linalool", 1.0, .10, .50, "character", True),
            ("Dihydromyrcenol", 1.0, .10, .50, "character", True),
            ("Hedione", 1.0, .05, .0834, "structure", False),
            ("Cedarwood Virginia", 1.0, .05, .0834, "structure", False),
        ],
        {0: 3000, 1: 1000, 2: 600, 3: 600, 4: 400, 5: 400},
        1,
    ),
}


@pytest.mark.parametrize("case", sorted(_TWICE_GIVING_DONORS))
def test_a_donor_giving_in_several_passes_keeps_half_its_entry_dose(
    plain_caps: dict[str, int], case: str
) -> None:
    # "Keep half" was measured at the start of each pass, so a donor giving in
    # two of them kept a quarter ("vanilla tonka gourmand": Linalool 83 -> 21).
    spec, before, donor = _TWICE_GIVING_DONORS[case]
    choices = [
        _choice(name, dilution, share=share, cap=cap, function=function, named=named,
                role_id=f"facet_{name.split()[0].lower()}" if named else None)
        for name, dilution, share, cap, function, named in spec
    ]
    holds: list[str] = []

    after = _floors(choices, before, holds)

    assert sum(after.values()) == TOTAL
    assert after[donor] < before[donor]
    for index, entry in before.items():
        assert after[index] >= max(min(entry, 10), -(-entry // 2)), (index, before, after)


def test_the_amber_base_rows_are_left_alone_by_the_floor_step(plain_caps: dict[str, int]) -> None:
    # The amber lead is long-lasting and the amber layer is not, so without the
    # rule one would take volume and the other would give it.
    amber_lead = _choice("Ambrox Super", 0.25, share=.20, cap=.22, function="structure",
                         role_id="facet_amber_mineral")
    amber_layer = _choice("Amber Xtreme", 0.1, share=.10, cap=.10, function="structure",
                          role_id="base_amber_layer")
    assert planner._is_long_lasting(amber_lead) is True
    assert planner._is_long_lasting(amber_layer) is False
    choices = [
        amber_lead,
        amber_layer,
        _choice("Linalool", share=.30, cap=.30, function="volume"),
        _choice("Dihydromyrcenol", share=.25, cap=.30, function="volume"),
        _choice("Cedarwood Virginia", share=.10, cap=.20, function="structure"),
    ]
    holds: list[str] = []
    before = _composed(choices, [])
    assert _long_active(choices, before) < _floor_ul()

    after = _floors(choices, before, holds)

    assert (after[0], after[1]) == (before[0], before[1])
    assert _long_active(choices, after) >= _floor_ul()
    assert sum(after.values()) == TOTAL


def _drow(index: int, name: str, amount: int, role: str, slot: str, fraction: str = "1") -> dict:
    return {
        "row_id": f"r{index}", "identity_name": name, "material": name,
        "amount_decimal": str(amount), "amount_unit": "uL",
        "stock_fraction_decimal": fraction, "role": role, "note": "base", "slot": slot,
        "stock_id": f"s{index}",
    }


def test_a_detection_raise_that_would_break_the_long_lasting_floor_is_rejected(monkeypatch) -> None:
    # The only row that could donate is the long-lasting one, and the formula
    # sits exactly on the floor.
    rows = [
        _drow(0, "Linalool", 100, "texture", "top_green_layer"),
        _drow(1, "Galaxolide", int(_floor_ul()), "volume", "base_musk_layer"),
    ]
    per_ul = {"Linalool": 0.001, "Galaxolide": 0.01}
    monkeypatch.setattr(
        dp, "_simulate",
        lambda rows, amounts: {
            rows[i]["identity_name"]: {
                window: float(amount) * per_ul[rows[i]["identity_name"]] for window in dp.WINDOWS
            }
            for i, amount in amounts.items()
        },
    )
    monkeypatch.setattr(dp, "_row_cap", lambda row, role, index, total: (Decimal(5000), "role cap"))
    monkeypatch.setattr(dp, "_blocking_checks", lambda formula, name: set())

    result = dp.apply_detection_pass(
        {"rows": rows}, role_plan=None, interpretation={}, formula_name="t", index=[object()],
    )

    quiet = next(e for e in result["detection_check"]["roles"] if e["material"] == "Linalool")
    assert quiet["status"] == "silent_at_cap"
    assert quiet["binding_limit"] == "long-lasting floor"
    assert [row["amount_decimal"] for row in result["rows"]] == ["100", str(int(_floor_ul()))]


def test_a_diluted_long_lasting_raise_keeps_the_long_lasting_measure(monkeypatch) -> None:
    # "Slow" is a 10% long-lasting stock: each uL raised adds 0.1 uL of
    # long-lasting active, and each uL the neat long-lasting "Fixer" gives
    # takes 1 uL.  The formula is under the floor (430 uL), so the measure
    # may not fall: "Fresh" (not long-lasting) gives first, and the raise keeps
    # the largest part the measure allows (166 uL: 150 from Fresh, 16 from Fixer).
    rows = [
        _drow(0, "Lead", 400, "character", "facet_lead"),
        _drow(1, "Heart", 400, "character", "facet_heart"),
        _drow(2, "Slow", 300, "structure", "base_resin_layer", fraction="0.1"),
        _drow(3, "Fixer", 400, "volume", "base_musk_layer"),
        _drow(4, "Fresh", 300, "texture", "top_green_layer"),
    ]
    per_ul = {"Lead": 0.01, "Heart": 0.01, "Slow": 0.0022, "Fixer": 0.01, "Fresh": 0.01}
    monkeypatch.setattr(
        dp, "_simulate",
        lambda rows, amounts: {
            rows[i]["identity_name"]: {
                window: float(amount) * per_ul[rows[i]["identity_name"]] for window in dp.WINDOWS
            }
            for i, amount in amounts.items()
        },
    )
    monkeypatch.setattr(dp, "_row_cap", lambda row, role, index, total: (Decimal(5000), "role cap"))
    monkeypatch.setattr(dp, "_blocking_checks", lambda formula, name: set())
    monkeypatch.setattr(planner, "_long_lasting_material", lambda name: name in {"Slow", "Fixer"})

    result = dp.apply_detection_pass(
        {"rows": rows}, role_plan=None, interpretation={}, formula_name="t", index=[object()],
    )

    amounts = {row["identity_name"]: row["amount_decimal"] for row in result["rows"]}
    assert amounts == {"Lead": "400", "Heart": "400", "Slow": "466", "Fixer": "384", "Fresh": "150"}
    slow = next(e for e in result["detection_check"]["roles"] if e["material"] == "Slow")
    assert slow["status"] == "raised"
    long_active = Decimal(amounts["Slow"]) * Decimal("0.1") + Decimal(amounts["Fixer"])
    assert long_active >= Decimal(430)


def _row_measures(rows: Sequence[dict]) -> tuple[Decimal, Decimal]:
    """(uL/mL of long-lasting active on the 30 mL basis, % of the concentrate active)."""

    active = long_active = raw = Decimal(0)
    for row in rows:
        amount = Decimal(row["amount_decimal"])
        raw += amount
        if planner._key(row["identity_name"]) in planner._DESIGN_FUNCTIONAL_CARRIERS:
            continue
        part = amount * Decimal(row["stock_fraction_decimal"])
        active += part
        if planner._long_lasting_material(row["identity_name"]):
            long_active += part
    return long_active / planner.LONGEVITY_FLOOR_BOTTLE_ML, active / raw * 100


def _composed_rows(formula: dict) -> list[dict]:
    """The formula's rows as composed, before the detection pass moved them."""

    rows = [dict(row) for row in formula["rows"]]
    for adjustment in formula["detection_check"]["adjustments"]:
        rows[adjustment["row_index"]]["amount_decimal"] = adjustment["amount_before_decimal"]
    return rows


def test_the_detection_pass_keeps_a_briefs_long_lasting_measure() -> None:
    # The pass used to raise the 10% Labdanum from 336 to 1344 uL with volume
    # from neat long-lasting rows (Hedione HC, Romandolide, ...), taking the
    # formula from 49.8 to 41.6 uL/mL of long-lasting material.
    result = design_inventory_formula(idea="pipe tobacco and vanilla")
    formula = result["optimized_formula"]
    before, _ = _row_measures(_composed_rows(formula))
    after, _ = _row_measures(formula["rows"])
    assert after >= min(before, planner.LONG_LASTING_FLOOR_UL_PER_ML), (before, after)


def test_the_floor_holds_describe_the_rows_the_detection_pass_delivers() -> None:
    # The pass raises rows of this brief: the floor holds are measured on the
    # delivered rows, not on the composer's rows before the pass.
    result = design_inventory_formula(idea="vanilla tonka gourmand")
    formula = result["optimized_formula"]
    assert formula["detection_check"]["adjustments"]
    long_per_ml, active_pct = _row_measures(formula["rows"])
    for holds in (result["constraint_audit"]["holds"], result["critic"]["issues"]):
        figures = {
            hold.split(":", 1)[0]: Decimal(hold.split(":", 1)[1])
            for hold in holds
            if hold.startswith(("LONG_LASTING_FLOOR_SHORT:", "ACTIVE_SHARE_FLOOR_SHORT:"))
        }
        assert (long_per_ml < planner.LONG_LASTING_FLOOR_UL_PER_ML) == (
            "LONG_LASTING_FLOOR_SHORT" in figures
        )
        assert (active_pct < planner.ACTIVE_SHARE_FLOOR * 100) == (
            "ACTIVE_SHARE_FLOOR_SHORT" in figures
        )
        if "LONG_LASTING_FLOOR_SHORT" in figures:
            assert abs(figures["LONG_LASTING_FLOOR_SHORT"] - long_per_ml) <= Decimal("0.1")
        if "ACTIVE_SHARE_FLOOR_SHORT" in figures:
            assert abs(figures["ACTIVE_SHARE_FLOOR_SHORT"] - active_pct) <= Decimal("0.1")
    # The primary variant's critic is the report's critic.
    assert result["design_variants"][0]["critic"]["issues"] == result["critic"]["issues"]


def test_a_named_weighed_crystal_counts_in_the_named_share(plain_caps: dict[str, int]) -> None:
    # A named amber crystal lead of 525 mg beside a named note Kenny owns only
    # at 1%: counted, the crystal already carries the floor share, so the lead
    # pass stops draining the unnamed base row beside it (which it used to
    # empty to its last 10 uL to make a 1% stock hold 40% of the active oil).
    choices = [
        _choice("Ambrox Super", 1.0, solid=True, named=True, share=.35, cap=.35,
                function="structure", role_id="facet_amber_mineral"),
        _choice("Lavender EO", 0.01, named=True, share=.10, cap=.05,
                role_id="facet_aromatic_lavender"),
        _choice("Tobacco Absolute", 0.1, share=.30, cap=.95),
    ]
    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=())
    crystal, lavender, base = rows
    assert (crystal["amount_unit"], base["amount_unit"]) == ("mg", "uL")

    crystal_mg = Decimal(crystal["amount_decimal"])
    active = crystal_mg + sum(
        Decimal(row["amount_decimal"]) * Decimal(row["stock_fraction_decimal"])
        for row in (lavender, base)
    )
    named = crystal_mg + Decimal(lavender["amount_decimal"]) * Decimal(
        lavender["stock_fraction_decimal"]
    )
    assert named / active >= planner.NAMED_NOTE_FLOOR_SHARE
    assert not [hold for hold in holds if hold.startswith("NAMED_NOTE_FLOOR_SHORT")]
    # The base row keeps its role, instead of being drained to a trace.
    assert int(base["amount_decimal"]) >= 3000
    assert int(lavender["amount_decimal"]) + int(base["amount_decimal"]) == TOTAL
    assert totals["mass_total_mg"] == crystal["amount_decimal"]


def test_the_short_holds_describe_the_rows_the_ceiling_pass_delivers(
    plain_caps: dict[str, int]
) -> None:
    # Half the concentrate is a capped carrier, so the long-lasting Hedione
    # (2100 uL after the bulk fallback, over the floor) carries 70% of the
    # active oil; the ceiling pass then gives 600 uL of it to the Linalool
    # modifier, which takes the formula under the long-lasting floor.
    plain_caps.update({"Benzyl Benzoate": 3000})
    choices = [
        _choice("Benzyl Benzoate", share=.50, cap=.50, function="fixative"),
        _choice("Hedione", share=.30, cap=.05, function="volume"),
        _choice("Linalool", share=.10, function="modifier"),
        _choice("Dihydromyrcenol", share=.10, cap=.05),
    ]
    before = _floors(choices, _composed(choices, []), [])
    assert _long_active(choices, before) >= _floor_ul()

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=())
    state = {index: int(row["amount_decimal"]) for index, row in enumerate(rows)}

    assert sum(state.values()) == int(totals["liquid_total_ul"]) == TOTAL
    assert state[1] < before[1]
    long_per_ml = (_long_active(choices, state) / planner.LONGEVITY_FLOOR_BOTTLE_ML).quantize(
        Decimal("0.1")
    )
    active_pct = (_active(choices, state) / TOTAL * 100).quantize(Decimal("0.1"))
    assert long_per_ml < planner.LONG_LASTING_FLOOR_UL_PER_ML
    short = sorted(
        hold for hold in holds
        if hold.startswith(("LONG_LASTING_FLOOR_SHORT:", "ACTIVE_SHARE_FLOOR_SHORT:"))
    )
    assert short == [
        f"ACTIVE_SHARE_FLOOR_SHORT:{active_pct}",
        f"LONG_LASTING_FLOOR_SHORT:{long_per_ml}",
    ]


def test_a_formula_of_requested_rows_only_still_carries_the_floor_holds() -> None:
    # Every liquid row is a requested quantity, so nothing is allocated; the
    # delivered rows still carry no long-lasting material and say so.
    choices = [
        _choice("Linalool", share=.5, function="volume"),
        _choice("Dihydromyrcenol", share=.5, function="volume"),
    ]
    quantities = [
        {"scope": "MATERIAL_DOSE", "material": name, "amount_decimal": "3000", "unit": "uL"}
        for name in ("Linalool", "Dihydromyrcenol")
    ]

    rows, totals, holds = planner._formula_rows(choices, liquid_total_ul=TOTAL, quantities=quantities)

    assert [row["amount_decimal"] for row in rows] == ["3000", "3000"]
    assert totals["liquid_total_ul"] == str(TOTAL)
    assert "LONG_LASTING_FLOOR_SHORT:0.0" in holds
    assert not [hold for hold in holds if hold.startswith("ACTIVE_SHARE_FLOOR_SHORT:")]


def test_a_light_brief_reaches_the_floor_or_carries_the_hold() -> None:
    result = design_inventory_formula(idea="A fresh citrus cologne")
    formula = result["optimized_formula"] or result["initial_formula"]
    rows = [row for row in formula["rows"] if row["amount_unit"] == "uL"]
    long_active = sum(
        (
            Decimal(row["amount_decimal"]) * Decimal(row["stock_fraction_decimal"])
            for row in rows
            if planner._key(row["identity_name"]) not in planner._DESIGN_FUNCTIONAL_CARRIERS
            and planner._long_lasting_material(row["identity_name"])
        ),
        Decimal(0),
    )
    per_ml = long_active / planner.LONGEVITY_FLOOR_BOTTLE_ML
    holds = result["constraint_audit"]["holds"]
    assert per_ml >= planner.LONG_LASTING_FLOOR_UL_PER_ML or any(
        hold.startswith("LONG_LASTING_FLOOR_SHORT:") for hold in holds
    ), per_ml
    # The light brief's base layers keep their 3% cap (October's decision): the
    # floor is not reached by growing them.
    from engine.formulation_intelligence.semantic_brief_adapter import (
        LIGHT_BASE_LAYER_MAX_RAW_SHARE,
    )

    layers = [row for row in rows if str(row["slot"]).startswith("base_") and str(row["slot"]).endswith("_layer")]
    assert layers
    for row in layers:
        assert Decimal(row["amount_decimal"]) <= Decimal(str(LIGHT_BASE_LAYER_MAX_RAW_SHARE)) * 6000
