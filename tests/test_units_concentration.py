"""Tests for engine.units.concentration."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.units.concentration import (
    parse_concentration,
    ConcentrationBasis,
    classify_material_category,
    compute_active_accounting,
    Concentration,
)
import pytest


def test_parse_w_w():
    c = parse_concentration("50% w/w")
    assert c.value == 0.5
    assert c.basis == ConcentrationBasis.WEIGHT_WEIGHT


def test_parse_in_dpg():
    c = parse_concentration("50% in DPG")
    assert c.value == 0.5
    assert c.carrier == "dipropylene glycol"


def test_parse_neat():
    c = parse_concentration("neat")
    assert c.value == 1.0
    assert c.is_neat


def test_parse_bare_pct_fails_strict():
    with pytest.raises(ValueError):
        parse_concentration("10%", strict=True)


@pytest.mark.parametrize("basis", ["w/w", "v/v", "w/v"])
@pytest.mark.parametrize("parenthesized", [False, True])
def test_explicit_basis_and_carrier_preserve_both(basis, parenthesized):
    label = f"({basis})" if parenthesized else basis
    raw = f"10% {label} in DPG"
    result = parse_concentration(raw)
    assert result.value == 0.1
    assert result.basis == basis
    assert result.carrier == "dipropylene glycol"
    assert result.raw_input == raw


@pytest.mark.parametrize("raw", ["10% (w/w in DPG", "10% w/w) in DPG"])
def test_explicit_basis_carrier_rejects_malformed_parentheses(raw):
    with pytest.raises(ValueError):
        parse_concentration(raw)


def test_parse_bare_pct_warns_nonstrict():
    c = parse_concentration("10%", strict=False)
    assert c.basis == ConcentrationBasis.UNSPECIFIED


def test_classify_solvent():
    assert classify_material_category("Ethanol") == "solvent"
    assert classify_material_category("Ethanol 96%") == "solvent"
    assert classify_material_category("DPG") == "carrier"  # still works
    assert classify_material_category("Bergamot FCF") == "odorant"
    assert classify_material_category("BHT") == "technical"


def test_classify_carrier():
    assert classify_material_category("DPG") == "carrier"


def test_classify_odorant():
    assert classify_material_category("Bergamot FCF") == "odorant"


def test_active_accounting():
    materials: list[tuple[str, float, float]] = [
        ("Iso E Super", 450.0, 1.0),
        ("Galaxolide 50% in DPG", 280.0, 0.5),
        ("DPG", 100.0, 1.0),
        ("BHT 10%", 10.0, 0.1),  # concentration suffix stripped → "technical"
    ]
    acct = compute_active_accounting(materials)
    assert acct.total_raw_ul == 840.0
    # "BHT 10%" → technical, but its diluent is unspecified → inactive → unallocated
    # Mass conservation uses classified_total (includes unallocated)
    assert acct.classified_total == acct.total_raw_ul
