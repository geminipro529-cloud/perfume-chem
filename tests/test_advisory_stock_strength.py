"""No missing-strength defaults or action authority in legacy advisory vectors."""

from decimal import Decimal

import pytest

from engine.advisory_stock_strength import (
    declared_stock_fraction,
    validated_advisory_dilutions,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("neat", 1), ("**Undiluted**", 1), ("pure", 1), ("neat solid", 1),
        ("10% w/w in DPG", .1), ("10% (w/v) in DEP", .1),
        ("pre-dilute 1% v/v in ethanol", .01), ("0,1%", .001),
    ],
)
def test_explicit_fraction_is_not_a_basis_or_density_conversion(text, expected):
    assert declared_stock_fraction(text) == expected


@pytest.mark.parametrize(
    "text", ["", "unknown", "neat?", "10", "10% or neat", "0%", "101%", "-1%", None],
)
def test_invalid_or_ambiguous_declarations_abstain(text):
    with pytest.raises(ValueError, match="cannot default to neat"):
        declared_stock_fraction(text)


@pytest.mark.parametrize("fraction", [True, None, 0, -1, 1.01, float("nan"), float("inf")])
def test_invalid_fraction_never_reaches_a_positive_dose_vector(fraction):
    with pytest.raises(ValueError, match="advisory abstained"):
        validated_advisory_dilutions({"A": 10}, {"A": fraction}, context="advisory")


@pytest.mark.parametrize("dose", [True, None, -1, float("nan"), float("inf")])
def test_invalid_dose_abstains(dose):
    with pytest.raises(ValueError, match="advisory abstained"):
        validated_advisory_dilutions({"A": dose}, {"A": 1}, context="advisory")


def test_zero_dose_does_not_invent_a_strength():
    assert validated_advisory_dilutions({"A": 0}, {}, context="advisory") == {}


def test_stock_metadata_is_preserved_and_not_promoted():
    specs = {"A": {"declared": True, "fraction": Decimal("0.1"), "basis": "w/w", "carrier": "DPG"}}
    before = {name: dict(spec) for name, spec in specs.items()}
    assert validated_advisory_dilutions(
        {"A": Decimal("10")}, {"A": Decimal("0.1")}, context="advisory", stock_specs=specs,
    ) == {"A": .1}
    assert specs == before
    assert "compounding_authority" not in specs["A"]
