"""No non-named row passes 35% of the fragrance-active volume (P1 crowding cap)."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from engine.research import composition_planner as planner


def _choice(name: str, *, named: bool = False, dilution: float = 1.0, exact: bool = False) -> Any:
    stock = SimpleNamespace(
        name=name, identity_name=name, raw_name=name, physical_form="liquid",
        fraction_basis="neat", carrier="", dilution=dilution, stock_id=f"stock:{name}",
        authority="TEST", source_ref="test", execution_ready=True, execution_hold_reason="",
    )
    role = planner.RoleSpec(
        name, name, "heart", "character", 0.1, (),
        serves_requested_facet=named, exact_preference_required=exact,
    )
    return planner.Choice(role, SimpleNamespace(stock=stock, solid=False, legacy_text_only=False, profile_source="test"), 1.0, ())


def _share(choices, amounts: dict[int, int], index: int) -> Decimal:
    active = {i: Decimal(a) * Decimal(str(choices[i].candidate.stock.dilution)) for i, a in amounts.items()}
    return active[index] / sum(active.values())


def _free(choices):
    return [(i, 1.0, None) for i in range(len(choices))]


def test_a_non_named_row_over_35_percent_is_capped() -> None:
    choices = [_choice("Lav", named=True), _choice("A"), _choice("B"), _choice("C")]
    holds: list[str] = []
    out = planner._cap_crowded_rows({0: 2000, 1: 2400, 2: 800, 3: 800}, _free(choices), {}, choices, holds)

    assert holds == []
    assert sum(out.values()) == 6000
    assert _share(choices, out, 1) <= Decimal("0.35")
    assert out[0] >= 2000  # freed volume never leaves the named row short


def test_a_named_row_is_not_capped() -> None:
    choices = [_choice("Lav", named=True), _choice("A"), _choice("B")]
    holds: list[str] = []
    start = {0: 4000, 1: 1000, 2: 1000}
    out = planner._cap_crowded_rows(dict(start), _free(choices), {}, choices, holds)

    assert out == start and holds == []


def test_an_impossible_cap_keeps_the_rows_and_holds() -> None:
    # Two rows only: the freed volume has nowhere to go but the other crowded row.
    choices = [_choice("A"), _choice("B")]
    holds: list[str] = []
    start = {0: 3000, 1: 3000}
    out = planner._cap_crowded_rows(dict(start), _free(choices), {}, choices, holds)

    assert out == start
    assert [h.split(":")[0] for h in holds] == ["CROWDING_CAP_UNMET"]


def test_exact_quantities_and_exact_counts_skip_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    choices = [_choice("A"), _choice("B"), _choice("C")]
    monkeypatch.setattr(planner, "_allocate_with_bulk_fallback", lambda *a, **k: {0: 4000, 1: 1000, 2: 1000})
    monkeypatch.setattr(planner, "_lead_with_named_notes", lambda allocated, *a, **k: allocated)
    monkeypatch.setattr(planner, "_design_cap_ul", lambda *a, **k: None)
    monkeypatch.setattr(planner, "effective_design_ready", lambda stock: True)
    monkeypatch.setattr(planner, "_normal_use_ceiling", lambda candidate: None)
    monkeypatch.setattr(planner, "_screening_default", lambda *a, **k: None)
    calls: list[int] = []
    monkeypatch.setattr(planner, "_cap_crowded_rows", lambda allocated, *a, **k: calls.append(1) or allocated)

    planner._formula_rows(choices, liquid_total_ul=6000, quantities=[], exact_material_count=True)
    planner._formula_rows(
        choices, liquid_total_ul=6000,
        quantities=[{"scope": "MATERIAL_DOSE", "material": "zzz", "amount_decimal": "1", "unit": "uL"}],
    )
    assert calls == []
    planner._formula_rows(choices, liquid_total_ul=6000, quantities=[])
    assert calls == [1]
