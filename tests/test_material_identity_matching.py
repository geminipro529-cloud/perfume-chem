"""Identity matching must not collapse different materials into one stock."""

from __future__ import annotations

import re

import pytest

from engine.formula_recommendations import (
    AXIS_CANDIDATES,
    _material_in_inventory,
    load_inventory,
)
from engine.optimizer.models import (
    material_identity_key,
    material_match_keys,
    materials_match,
)

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
    ("Heliotropal (Piperonal)", "Heliotropin"),
    ("Eugenol", "Methyl Eugenol"),
    ("Linalool", "Linalool Oxide"),
    # Stock spellings of the same pairs.
    ("Hedione 10% w/w in DPG", "Hedione HC"),
    ("Galaxolide (50% in DEP)", "Habanolide (neat / as supplied)"),
    ("Isoeugenol (neat)", "Eugenol (10%)"),
    # Other spellings, word orders, suffixes and aliases of the same pairs.
    ("Vetiver EO (India)", "Haitian Vetiver EO"),
    ("Vetiver (Indian)", "Haitian Vetiver EO"),
    ("Vetiver Bourbon", "Vetiver India"),
    ("Vetiver Haiti", "Vetiver India"),
    ("Vetiver EO (Haiti)", "Ruh Khus"),
    ("Hedione HC 10% in DPG", "Hedione"),
    ("methyl dihydrojasmonate high cis", "Hedione"),
    ("Hedione HC", "methyl dihydrojasmonate"),
    ("Iso E Super Plus", "iso e super"),
    ("Iso-E-Super Plus (10% in DPG)", "ISO E SUPER"),
    ("Habanolide 10% in DEP", "galaxolide 50"),
    ("Exaltolide", "Delta Muscenone"),
    ("AIMI", "Methyl Ionone Gamma Coeur"),
    ("Isomethyl Ionone Alpha", "Methyl Ionone Gamma Coeur (10% in DPG)"),
    ("AIMI", "Ultralia"),
    ("Sandalore (neat)", "bacdanol 10% in DPG"),
    ("Lavandin Grosso EO", "Lavender EO"),
    ("Iso Eugenol", "Eugenol"),
    ("b-ionone", "Dihydro-beta-ionone"),
    ("Beta Ionone", "Ionone Beta Dihydro"),
    ("Vertofix Coeur (10%)", "vertofix"),
    ("Coeur Vertofix", "Vertofix (neat / as supplied)"),
    ("Piperonal", "Heliotropal"),
    ("Heliotropin (10% in DPG)", "heliotropal"),
    # Two subtypes of one umbrella never match each other.
    ("Siam Benzoin", "Benzoin Sumatra Resinoid (10%)"),
    ("Benzoin Siam Resinoid", "Benzoin Sumatra"),
    ("Aldehyde C11 undecylic", "Aldehyde C11 undecylenic"),
    ("C11 Undecanal (10%)", "C11 undecylenic (1%)"),
]

# An umbrella name with no subtype matches each of its subtypes (decision:
# bare "Aldehyde C-11" is undecylenic in trade usage; bare benzoin resinoid
# finds the benzoin owned). Only umbrellas the concept table declares.
UMBRELLA_MATCHES = [
    ("benzoin resinoid", "Siam Benzoin"),
    ("Benzoin Resinoid", "Siam Benzoin (50% w/w in DPG)"),
    ("benzoin", "Benzoin Sumatra Resinoid (10%)"),
    ("aldehyde c11", "Aldehyde C11 undecylenic (1%)"),
    ("Aldehyde C11 (1%)", "Aldehyde C11 undecylic"),
]

# Different origins or extraction methods stated on both sides.
ORIGIN_OR_METHOD_DIFFERS = [
    ("Lavender Absolute", "Lavender EO"),
    ("Labdanum Absolute", "Labdanum Resinoid"),
    ("Vetiver EO (Java)", "Vetiver EO (Haiti)"),
    ("Geranium Bourbon", "Geranium EO Egypt"),
    ("Orris Concrete", "Orris Absolute"),
    ("Ginger CO2 extract", "Ginger EO"),
    ("Vanilla Tincture", "Vanilla Absolute"),
    ("Oakmoss Resinoid", "Oakmoss Absolute"),
]

# A side stating no origin/method, or the same one spelled differently.
ORIGIN_OR_METHOD_COMPATIBLE = [
    ("Lavender", "Lavender EO"),
    ("Haitian Vetiver EO", "Vetiver EO (Haiti)"),
    ("Vetiver EO", "Haitian Vetiver EO"),
    ("Labdanum", "Labdanum Resinoid"),
    ("Vetiver EO (Bourbon)", "Vetiver EO (Reunion)"),
    # Stated rule: FCF only removes furocoumarins from the same expressed oil.
    ("Bergamot EO", "Bergamot FCF oil Sicilian"),
    ("Bergamot FCF", "Bergamot EO"),
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
    # Same material, no shared alias key: equal cores once stock, origin,
    # method, Greek-letter and spelling variants are set aside.
    ("Heliotropal (Piperonal)", "heliotropal"),
    ("Ambrofix", "Ambrofix Crystals"),
    ("Ambrofix (30% active)", "Ambrofix Crystals"),
    ("Petitgrain EO", "Petitgrain EO Paraguay"),
    ("Petitgrain", "Petitgrain EO Paraguay"),
    ("Vertofix Couer", "Vertofix Coeur"),
    ("Vetiver Haiti EO", "Haitian Vetiver EO"),
    ("C11 undecylenic", "Aldehyde C11 undecylenic"),
    ("C11 undecylenic (1%)", "Aldehyde C11 undecylenic"),
    ("Benzoin Siam Resinoid", "Siam Benzoin"),
    ("Cinnamon Bark Essential Oil", "Cinnamon Bark EO - Telvada USDA Organic"),
    ("Aldehyde C-14 Gamma Undecalactone", "Gamma Undecalactone"),
    ("α-Damascone", "Alpha Damascone"),
    ("Jasmine Sambac Abs 10%", "Jasmine Sambac"),
    # Found by the formulas/ corpus probe.
    ("Benzyl Sal", "Benzyl Salicylate"),
    ("Cedarwood VA", "Cedarwood oil Virginia"),
    ("Ambrox Super ~33%", "Ambrox Super"),
    ("γ-Nonalactone (Aldehyde C-18)", "Aldehyde C-18"),
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


@pytest.mark.parametrize(("a", "b"), UMBRELLA_MATCHES)
def test_umbrella_name_matches_each_subtype(a, b):
    assert materials_match(a, b) is True
    assert materials_match(b, a) is True


@pytest.mark.parametrize(("a", "b"), ORIGIN_OR_METHOD_DIFFERS)
def test_different_stated_origins_or_methods_never_match(a, b):
    assert materials_match(a, b) is False
    assert materials_match(b, a) is False


@pytest.mark.parametrize(("a", "b"), ORIGIN_OR_METHOD_COMPATIBLE)
def test_unstated_or_equal_origin_and_method_still_match(a, b):
    assert materials_match(a, b) is True
    assert materials_match(b, a) is True


@pytest.mark.parametrize(("a", "b"), DENY_PAIRS + ORIGIN_OR_METHOD_DIFFERS)
def test_identity_keys_keep_different_materials_apart(a, b):
    # Duplicate removal keys on material_identity_key; it must not merge them.
    assert material_identity_key(a) != material_identity_key(b)


IDENTITY_KEY_VARIANTS = [
    ("Hedione", "  HEDIONE "),
    ("Hedione", "Hedione 10% w/w in DPG"),
    ("Hedione HC", "hedione  hc"),
    ("Hedione HC", "Hedione HC 10% in DPG"),
    ("Iso E Super Plus", "iso e super plus 10% in DPG"),
    ("Iso E Super", "iso e  super"),
    ("Lavender Absolute", "lavender absolute (10% in ethanol)"),
    ("Vetiver EO (India)", "vetiver eo (india)"),
    ("Exaltolide (10%)", "exaltolide"),
    ("Siam Benzoin", "Siam Benzoin (50% w/w in DPG)"),
    ("Alpha Isomethyl Ionone", "AIMI"),
    ("methyl dihydrojasmonate", "Hedione"),
]


@pytest.mark.parametrize(("a", "b"), IDENTITY_KEY_VARIANTS)
def test_identity_keys_equal_for_same_material_variants(a, b):
    assert material_identity_key(a) == material_identity_key(b)


def _base(name: str) -> str:
    low = re.sub(r"\s+", " ", name.strip().lower())
    low = re.sub(r"\s*\([^)]*\)\s*$", "", low)
    return re.sub(r"[\s,]+\d+(?:\.\d+)?\s*%.*$", "", low).strip()


# Candidate -> stock pairs whose names differ but which are the same material
# through an explicit alias.
EXPLICIT_ALIAS_MATCHES = {
    "dbca": "Dimethyl Benzyl Carbinyl Acetate",
    "labdanum": "Labdanum Resinoid",
    # Stated FCF rule: same expressed oil, furocoumarins removed.
    "bergamot eo": "Bergamot FCF oil Sicilian",
    # Umbrella names find the subtype owned (first in inventory order).
    "aldehyde c11": "Aldehyde C11 undecylenic",
    "benzoin resinoid": "Siam Benzoin",
}
# Candidates with no same-material stock: each must resolve to nothing rather
# than to a different material.
EXPECTED_NO_MATCH = {
    "vertofix coeur",  # stock is Vertofix
    "labdanum absolute",  # stock is Labdanum Resinoid, a different extract
}


def test_axis_candidates_resolve_only_to_the_same_inventory_material():
    inventory = load_inventory()
    names = sorted({name for options in AXIS_CANDIDATES.values() for name, _, _ in options})
    assert EXPECTED_NO_MATCH <= set(names)
    wrong = []
    for name in names:
        item = _material_in_inventory(name, inventory)
        if name in EXPECTED_NO_MATCH:
            if item is not None:
                wrong.append(f"{name!r} -> {item['name']!r} (expected no match)")
            continue
        if item is None:
            continue
        stock = item["name"]
        if _base(stock) == _base(name) or EXPLICIT_ALIAS_MATCHES.get(name) == stock:
            continue
        wrong.append(f"{name!r} -> {stock!r}")
    assert wrong == []


# Real inventory.txt and formula spellings -> the inventory line they must find.
# A line for the very product named wins over a same-molecule product reached
# through a data alias (Ambrofix is not Ambrox Super; Heliotropal and
# Heliotropin are separate piperonal stock lines).
INVENTORY_LOOKUPS = {
    "Heliotropal (Piperonal)": "Heliotropal",
    "heliotropal": "Heliotropal",
    "Heliotropin": "Heliotropin",
    "Ambrofix": "Ambrofix Crystals",
    "Ambrofix 30%": "Ambrofix Crystals",
    "Ambrofix (30% active)": "Ambrofix Crystals",
    "Ambrox Super": "Ambrox Super",
    "Ambrox Super Crystals": "Ambrox Super Crystals",
    "Petitgrain EO": "Petitgrain EO Paraguay",
    "Petitgrain": "Petitgrain EO Paraguay",
    "Vetiver Haiti EO": "Haitian Vetiver EO",
    "C11 undecylenic": "Aldehyde C11 undecylenic",
    "C11 undecylenic (1%)": "Aldehyde C11 undecylenic",
    "Aldehyde C11": "Aldehyde C11 undecylenic",
    "Aldehyde C11 (1%)": "Aldehyde C11 undecylenic",
    "Benzoin Resinoid": "Siam Benzoin",
    "Benzoin Resinoid (50% in DPG)": "Siam Benzoin",
    "Benzoin Siam Resinoid": "Siam Benzoin",
    "Siam Benzoin (50% in DPG)": "Siam Benzoin",
    "Benzyl Sal": "Benzyl Salicylate",
    "Ambrox Super ~33%": "Ambrox Super",
    "Benzoin Sumatra Resinoid": "Benzoin Sumatra Resinoid",
    "Cinnamon Bark Essential Oil": "Cinnamon Bark EO - Telvada USDA Organic",
    "Aldehyde C-14 Gamma Undecalactone": "Gamma Undecalactone",
    "α-Damascone": "Alpha Damascone",
    "Jasmine Sambac Abs 10%": "Jasmine Sambac",
    "Linalool Oxide": "Linalool Oxide",
    "Linalool": "Linalool",
}


def test_real_inventory_lookups_find_the_named_product():
    inventory = load_inventory()
    found = {}
    for query in INVENTORY_LOOKUPS:
        item = _material_in_inventory(query, inventory)
        found[query] = item and item["name"]
    assert found == INVENTORY_LOOKUPS


def test_grades_and_subtypes_do_not_find_another_line():
    inventory = load_inventory()
    for query in ("Vertofix Couer", "Vertofix Coeur", "Aldehyde C11 undecylic", "Methyl Eugenol"):
        assert _material_in_inventory(query, inventory) is None, query


@pytest.mark.parametrize(
    ("a", "b"),
    [("Linalool", "Linalool Oxide"), ("Eugenol", "Methyl Eugenol")],
)
def test_resolved_identity_keys_keep_derivatives_apart(a, b):
    assert material_identity_key(a) != material_identity_key(b)
    assert material_identity_key(b) not in {"linalool", "eugenol"}
