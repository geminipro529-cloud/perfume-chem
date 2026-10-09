"""The project screening default caps rows that have no researched ceiling (COMP-04)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from engine.research import composition_planner as planner
from engine.research import normal_use_ceilings as ceilings

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "normal_use_ceilings_fixture_v1.json"
TOTAL = 6000


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


def _choice(
    candidate: Any,
    *,
    function: str = "character",
    max_raw_share: float | None = None,
    named: bool = False,
) -> Any:
    role = planner.RoleSpec(
        "r",
        "Role",
        "heart",
        function,
        0.1,
        (),
        max_raw_share=max_raw_share,
        serves_requested_facet=named,
    )
    return planner.Choice(role, candidate, 1.0, ())


def _default_pct(name: str, dilution: float = 1.0, **kwargs: Any) -> Any:
    default = planner._screening_default(_choice(_stocked(name, dilution), **kwargs), TOTAL)
    return None if default is None else default.max_active_pct_of_concentrate


def test_shipped_block_is_a_labelled_screening_default() -> None:
    default = ceilings.active_screening_default()
    assert default is not None
    assert default.kind == "project_screening_default"
    assert default.label == "project screening default, not a safety or IFRA limit"


@pytest.mark.parametrize(
    ("name", "dilution", "pct", "cap_ul"),
    [
        ("Cedramber", 1.0, 2, 120),  # aroma chemical with no row: 2% active
        ("Cedramber", 0.1, 2, 1200),  # same active share from a 10% stock
        ("Bergamot EO", 1.0, 5, 300),  # natural with no row: 5% active
        ("Cedarwood Virginia", 1.0, 5, 300),  # a botanical name marks a natural too
        ("Iso E Super", 1.0, 15, 900),  # typical-use floor raises the default
    ],
)
def test_rows_without_a_ceiling_get_the_class_default(
    name: str, dilution: float, pct: int, cap_ul: int
) -> None:
    assert ceilings.match_normal_use_ceiling(name) is None
    choice = _choice(_stocked(name, dilution))
    assert _default_pct(name, dilution) == pct
    assert planner._design_cap_ul(choice, TOTAL) == min(cap_ul, planner._role_cap_ul(choice, TOTAL))


def test_a_researched_row_and_an_identity_hard_cap_win_over_the_default() -> None:
    assert ceilings.match_normal_use_ceiling("Alpha Damascone") is not None
    assert _default_pct("Alpha Damascone") is None
    assert planner._design_cap_ul(_choice(_stocked("Alpha Damascone")), TOTAL) == 12
    lemonile = _choice(_stocked("Lemonile"))
    assert planner._hard_cap_ul(lemonile.candidate, TOTAL) is not None
    assert _default_pct("Lemonile") is None
    assert planner._design_cap_ul(lemonile, TOTAL) == planner._hard_cap_ul(
        lemonile.candidate, TOTAL
    )


def test_a_named_note_row_keeps_its_role_cap() -> None:
    choice = _choice(_stocked("Cedramber"), named=True)
    assert planner._screening_default(choice, TOTAL) is None
    assert planner._design_cap_ul(choice, TOTAL) == planner._role_cap_ul(choice, TOTAL)


def test_a_functional_carrier_gets_no_default() -> None:
    # Benzyl Benzoate as the quiet carrier is a carrier, not an odorant dose.
    choice = _choice(_stocked("Benzyl Benzoate"), function="fixative")
    assert planner._screening_default(choice, TOTAL) is None
    assert planner._design_cap_ul(choice, TOTAL) == planner._role_cap_ul(choice, TOTAL)


def test_a_file_without_the_block_gives_no_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ceilings, "NORMAL_USE_CEILINGS_PATH", FIXTURE)
    assert ceilings.active_screening_default() is None
    choice = _choice(_stocked("Cedramber"))
    assert planner._screening_default(choice, TOTAL) is None
    assert planner._design_cap_ul(choice, TOTAL) == planner._role_cap_ul(choice, TOTAL)


def _fallback(choices: list[Any]) -> tuple[dict[int, int], list[str]]:
    free_rows = [
        (index, planner._allocation_weight(choice), planner._design_cap_ul(choice, TOTAL))
        for index, choice in enumerate(choices)
    ]
    holds: list[str] = []
    return planner._allocate_with_bulk_fallback(TOTAL, free_rows, choices, TOTAL, holds), holds


def test_defaults_that_cannot_fill_the_total_are_released_and_named() -> None:
    # Restrained rows are never released by the role-cap stages; the last
    # stage drops their screening defaults so the design is still built.
    choices = [
        _choice(_stocked("Alpha Damascone")),  # firm researched ceiling
        _choice(_stocked("Cedramber"), max_raw_share=0.6),
        _choice(_stocked("Bergamot EO"), max_raw_share=0.6),
    ]
    allocated, holds = _fallback(choices)

    assert sum(allocated.values()) == TOTAL
    assert allocated[0] <= 12
    assert allocated[1] <= 3600 and allocated[2] <= 3600
    assert sorted(holds) == [
        "SCREENING_DEFAULT_EXCEEDED_TO_FILL_TOTAL:stock:Bergamot EO",
        "SCREENING_DEFAULT_EXCEEDED_TO_FILL_TOTAL:stock:Cedramber",
    ]


def test_a_released_volume_row_is_named_by_its_default_not_its_role_cap() -> None:
    choices = [
        _choice(_stocked("Alpha Damascone")),
        _choice(_stocked("Cedramber"), function="volume"),
        _choice(_stocked("Iso E Super"), max_raw_share=0.3),
    ]
    allocated, holds = _fallback(choices)

    assert sum(allocated.values()) == TOTAL
    assert holds == ["SCREENING_DEFAULT_EXCEEDED_TO_FILL_TOTAL:stock:Cedramber"]


def test_spare_volume_goes_to_the_named_note_before_the_structure_rows() -> None:
    # The defaults leave the total unfillable.  The named note takes the
    # spare (past its role cap, and said so); the structure row and the
    # defaulted row stay within their caps.
    choices = [
        _choice(_stocked("Alpha Damascone")),
        _choice(_stocked("Cedramber"), function="volume"),
        _choice(_stocked("Amber Xtreme", 0.1), function="structure", max_raw_share=0.08),
        _choice(_stocked("Phenethyl Alcohol"), max_raw_share=0.07, named=True),
    ]
    allocated, holds = _fallback(choices)

    assert sum(allocated.values()) == TOTAL
    assert allocated[1] <= planner._design_cap_ul(choices[1], TOTAL)
    assert allocated[2] <= planner._design_cap_ul(choices[2], TOTAL)
    assert allocated[3] > planner._design_cap_ul(choices[3], TOTAL)
    assert holds == ["ROLE_CAP_EXCEEDED_TO_FILL_TOTAL:stock:Phenethyl Alcohol"]
