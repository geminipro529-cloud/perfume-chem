"""Engine-audit stock records (31 Oct 2026: Kenny's "All five, in order" and "Mine is neat")."""

from __future__ import annotations

import pytest

from engine.inventory_parser import parse_current_inventory
from engine.research import composition_planner as cp


def _by_name() -> dict[str, object]:
    return {stock.name: stock for stock in parse_current_inventory()}


def test_bht_solution_is_a_weight_per_volume_ethanol_stock_the_composer_skips() -> None:
    bht = _by_name()["BHT 5% w/v in ethanol"]
    assert (bht.dilution, bht.fraction_basis, bht.carrier) == (0.05, "mass_per_volume", "ethanol")
    assert bht.status == "owned" and bht.execution_ready
    assert bht.source_ref.endswith("#INV-USER-20261014-STK-238")
    candidates, _, _ = cp._load_candidates([])
    assert not any(c.stock.name.startswith("BHT") for c in candidates)


@pytest.mark.parametrize(
    "name",
    [
        "Aldehyde C11 undecylenic",
        "Allyl Ionone (Ketone V)",
        "Azarbre",
        "Methyl Benzoate",
        "Champaca Flower EO",
        "Parmavert",
        "Eucalyptus Essential Oil",
        "Basil EO (India, Ocimum Basilicum)",
    ],
)
def test_audit_bottles_are_neat_owned_stocks_with_their_own_profile(name: str) -> None:
    stock = _by_name()[name]
    assert (stock.dilution, stock.fraction_basis) == (1.0, "neat")
    assert stock.status == "owned" and stock.execution_ready
    assert stock.authority == "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261014"
    candidates, _, _ = cp._load_candidates([])
    matches = [c for c in candidates if c.stock.stock_id == stock.stock_id]
    assert len(matches) == 1
    assert not matches[0].legacy_text_only
    assert matches[0].profile_source == "DECLARED_MATERIAL_PROFILE"


def test_basil_has_no_ten_percent() -> None:
    basil = {s.name: s.status for s in parse_current_inventory() if "basil" in s.name.casefold()}
    assert basil == {
        "Basil EO (India, Ocimum Basilicum)": "owned",
        "Basil EO ct. Methyl Chavicol 10%": "gap",
    }
