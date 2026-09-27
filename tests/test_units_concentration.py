"""Tests for engine.units.concentration."""

from __future__ import annotations

import pytest

from engine.units.concentration import (
    ConcentrationBasis,
    classify_material_category,
    compute_active_accounting,
    parse_concentration,
)


def test_parse_w_w():
    c = parse_concentration("50% w/w")
    assert c.value == 0.5
    assert c.basis == ConcentrationBasis.WEIGHT_WEIGHT


def test_parse_in_dpg():
    c = parse_concentration("50% in DPG")
    assert c.value == 0.5
    assert c.carrier == "dipropylene glycol"


@pytest.mark.parametrize(
    ("raw", "basis", "carrier"),
    [
        ("10% w/w in DPG", ConcentrationBasis.WEIGHT_WEIGHT, "dipropylene glycol"),
        ("20% (w/w) in TEC", ConcentrationBasis.WEIGHT_WEIGHT, "triethyl citrate"),
        ("30% v/v in DEP", ConcentrationBasis.VOLUME_VOLUME, "diethyl phthalate"),
        ("5% w/v in IPM", ConcentrationBasis.WEIGHT_VOLUME, "isopropyl myristate"),
    ],
)
def test_parse_explicit_basis_with_carrier(raw, basis, carrier):
    c = parse_concentration(raw)
    assert c.value > 0.0
    assert c.basis == basis
    assert c.carrier == carrier


def test_parse_neat():
    c = parse_concentration("neat")
    assert c.value == 1.0
    assert c.is_neat


def test_parse_bare_pct_fails_strict():
    with pytest.raises(ValueError):
        parse_concentration("10%", strict=True)


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
    assert classify_material_category("Dipropylene Glycol (DPG)") == "carrier"
    assert classify_material_category("Isopropyl Myristate (IPM)") == "carrier"


def test_classify_odorant():
    assert classify_material_category("Bergamot FCF") == "odorant"
    assert classify_material_category("Bergamot FCF (10% in DPG)") == "odorant"


def test_classify_annotated_technical_material_as_technical():
    assert classify_material_category("EDTA (10% in DPG)") == "technical"


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


@pytest.mark.parametrize(
    "basis",
    [ConcentrationBasis.WEIGHT_WEIGHT, ConcentrationBasis.WEIGHT_VOLUME],
)
def test_volume_only_active_accounting_rejects_mass_based_stocks(basis):
    from engine.units.concentration import DeclaredStock, StockComponent

    stock = DeclaredStock(
        name="Mass-based stock",
        raw_amount=100.0,
        unit="uL",
        basis=basis,
        components=(
            StockComponent("odorant_active", 0.25, "odorant"),
            StockComponent("carrier", 0.75, "carrier"),
        ),
    )

    with pytest.raises(
        ValueError,
        match="volume-only ActiveAccounting cannot represent w/w or w/v stocks",
    ):
        compute_active_accounting([stock])
