"""Identity matching must not collapse different materials into one stock."""

from __future__ import annotations

import re

import pytest

from engine.formula_recommendations import (
    AXIS_CANDIDATES,
    _material_in_inventory,
    load_inventory,
)
from engine.optimizer.models import material_match_keys, materials_match

DENY_PAIRS = [
    ("Habanolide", "Galaxolide"),
    ("Muscenone Delta", "Exaltolide"),
    ("Alpha Isomethyl Ionone", "Methyl Ionone Gamma Coeur"),
    ("Bacdanol", "Sandalore"),
    ("Haitian Vetiver EO", "Indian Vetiver"),
    ("Lavender", "Lavandin"),
    ("Isoeugenol", "Eugenol"),
    ("Hedione", "Hedione HC"),
    ("Iso E Super", "Iso E Super Plus"),
    ("beta ionone", "Dihydro Beta Ionone"),
    ("Vertofix", "Vertofix Coeur"),
    ("Heliotropal", "Heliotropin"),
    ("Ultralia", "Alpha Isomethyl Ionone"),
    ("benzoin resinoid", "Siam Benzoin"),
    # Stock spellings of the same pairs.
    ("Hedione 10% w/w in DPG", "Hedione HC"),
    ("Galaxolide (50% in DEP)", "Habanolide (neat / as supplied)"),
    ("Isoeugenol (neat)", "Eugenol (10%)"),
]

SAME_MATERIAL = [
    ("Hedione", "hedione"),
    ("Iso E Super", "  iso  e   super "),
    ("Hedione 10% w/w in DPG", "Hedione"),
    ("Exaltolide (10%)", "exaltolide"),
    ("Helional 10% v/v in ethanol", "Helional"),
    ("Hedione HC", "hedione hc"),
    ("Alpha Isomethyl Ionone", "AIMI"),
    ("methyl dihydrojasmonate", "Hedione"),
]


def test_strength_and_carrier_alt_names_are_not_identity_keys():
    assert "10%" not in material_match_keys("exaltolide")
    assert "10%" not in material_match_keys("Hexyl Acetate 1% v/v in DPG")
    for name in ("Exaltolide", "Vanillin", "Tonalide", "Rose Oxide", "Labdanum Absolute"):
        for key in material_match_keys(name):
            assert not re.fullmatch(r"\s*\d+(\.\d+)?\s*%\s*", key), (name, key)
    assert materials_match("Exaltolide", "Hexyl Acetate 1% v/v in DPG") is False
    assert materials_match("Exaltolide", "Vanillin") is False


@pytest.mark.parametrize(("a", "b"), DENY_PAIRS)
def test_non_interchangeable_pairs_never_match(a, b):
    assert materials_match(a, b) is False
    assert materials_match(b, a) is False


@pytest.mark.parametrize(("a", "b"), SAME_MATERIAL)
def test_same_material_spellings_still_match(a, b):
    assert materials_match(a, b) is True
    assert materials_match(b, a) is True


def _base(name: str) -> str:
    low = re.sub(r"\s+", " ", name.strip().lower())
    low = re.sub(r"\s*\([^)]*\)\s*$", "", low)
    return re.sub(r"[\s,]+\d+(?:\.\d+)?\s*%.*$", "", low).strip()


# Candidate -> stock pairs whose names differ but which are the same material
# through an explicit alias.
EXPLICIT_ALIAS_MATCHES = {
    "dbca": "Dimethyl Benzyl Carbinyl Acetate",
    "labdanum": "Labdanum Resinoid",
}
# Pre-existing grade-level collapses from qualifier-token normalization in
# _material_alias_keys (not substring matching). Pinned so a change is visible.
KNOWN_GRADE_COLLAPSES = {
    "bergamot eo": "Bergamot FCF oil Sicilian",
    "labdanum absolute": "Labdanum Resinoid",
}


def test_axis_candidates_resolve_only_to_the_same_inventory_material():
    inventory = load_inventory()
    names = sorted({name for options in AXIS_CANDIDATES.values() for name, _, _ in options})
    wrong = []
    for name in names:
        item = _material_in_inventory(name, inventory)
        if item is None:
            continue
        stock = item["name"]
        if _base(stock) == _base(name):
            continue
        if EXPLICIT_ALIAS_MATCHES.get(name) == stock or KNOWN_GRADE_COLLAPSES.get(name) == stock:
            continue
        wrong.append(f"{name!r} -> {stock!r}")
    assert wrong == []
