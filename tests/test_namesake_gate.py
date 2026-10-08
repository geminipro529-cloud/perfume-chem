"""namesake gate: a formula's name promises odours its materials must carry (AGENTS.md RULE 3)."""

import pytest

import engine.pipeline.gates as gates_module
from engine.ingredient_intelligence import get_profile
from engine.pipeline.formula_state import build_formula_state


def _state(ingredients: dict[str, float]):
    return build_formula_state(
        ingredients,
        {name: 1.0 for name in ingredients},
        stock_specs={
            name: {"fraction": 1.0, "fraction_basis": "mass_per_volume", "carrier": "", "declared": True}
            for name in ingredients
        },
    )


_COCOA_TUBEROSE_BASE = {
    "Hedione": 900.0,
    "Cocoa Absolute": 600.0,
    "Tuberose Absolute": 100.0,
    "Iso E Super": 400.0,
}


def _namesake(name: str, ingredients: dict[str, float]):
    return gates_module._gate_namesake({"name": name}, _state(ingredients))


def test_name_word_without_a_carrier_warns_naming_it():
    result = _namesake("Cocoa Vetiver Tuberose — 30 mL EdP", _COCOA_TUBEROSE_BASE)

    assert result.gate == "namesake"
    assert result.status == "WARN"
    assert "Name says vetiver, but no material above trace smells of vetiver" in result.detail
    assert result.data["words"] == ["cocoa", "vetiver", "tuberose"]
    assert result.data["missing"] == ["vetiver"]
    assert result.data["carried_by"]["cocoa"] == ["Cocoa Absolute"]
    assert result.data["carried_by"]["tuberose"] == ["Tuberose Absolute"]


def test_vetiver_at_normal_dose_carries_vetiver():
    result = _namesake(
        "Cocoa Vetiver Tuberose — 30 mL EdP",
        {**_COCOA_TUBEROSE_BASE, "Vetiver EO": 150.0},
    )

    assert result.status == "PASS"
    assert result.data["missing"] == []
    assert result.data["carried_by"]["vetiver"] == ["Vetiver EO"]


def test_vetiver_only_at_trace_does_not_carry_it():
    # 1 uL in ~2,000 uL fragrance-active is 0.05%, below the 0.1% trace share.
    result = _namesake(
        "Cocoa Vetiver Tuberose — 30 mL EdP",
        {**_COCOA_TUBEROSE_BASE, "Vetiver EO": 1.0},
    )

    assert result.status == "WARN"
    assert result.data["missing"] == ["vetiver"]
    assert "Name says vetiver" in result.detail
    assert any(label.startswith("Vetiver EO") and "(trace)" in label
               for label in result.data["closest"]["vetiver"])


def test_name_without_odour_words_skips():
    result = _namesake("CHIMIE L'Homme Intense R6 v1 30mL EDP", _COCOA_TUBEROSE_BASE)

    assert result.status == "SKIP"
    assert "no odour words in the name" in result.detail


def test_missing_name_skips():
    result = gates_module._gate_namesake({}, _state(_COCOA_TUBEROSE_BASE))

    assert result.status == "SKIP"
    assert result.detail == "no formula name"


def test_non_odour_words_are_ignored():
    result = _namesake(
        "CHIMIE L'Homme Femme Tuberose Intense Research Build Corrected v1 R6 30mL EdP",
        _COCOA_TUBEROSE_BASE,
    )

    assert result.status == "PASS"
    assert result.data["words"] == ["tuberose"]


def test_synergy_partner_of_vetiver_does_not_carry_vetiver():
    profile = get_profile("Cedarwood EO")
    assert profile is not None and "Vetiver EO" in profile.synergies

    result = _namesake("Vetiver Wood", {"Cedarwood EO": 300.0, "Hedione": 300.0})

    assert result.status == "WARN"
    assert result.data["missing"] == ["vetiver"]
    assert "Cedarwood EO" not in result.data["carried_by"]["vetiver"]


def test_resinoid_carries_resin():
    result = _namesake("Resin Reserve", {"Olibanum Resinoid": 300.0, "Hedione": 300.0})

    assert result.status == "PASS"
    assert result.data["carried_by"]["resin"] == ["Olibanum Resinoid"]


def test_namesake_is_advisory_and_never_blocking():
    assert "namesake" not in gates_module.HARD_BLOCKING_GATES
    assert "namesake" in gates_module.ADVISORY_FAILURE_GATES


# Reviewer cases: real formulas that WARNed falsely, or PASSed/SKIPped wrongly.
_PLAIN_BASE = {"Hedione": 300.0, "Iso E Super": 300.0}


@pytest.mark.parametrize(
    ("name", "material", "word"),
    [
        ("Amber Vanilla", "Vanillin", "vanilla"),
        ("Vetiver Moderne", "Vetival", "vetiver"),
        ("Osmanthus Sandalwood Creme", "Sandalore", "sandalwood"),
        ("White Suede", "Suederal", "suede"),
        ("Tonka Wood", "Tonkarome", "tonka"),
        ("Jasmin d'Orris", "Jasmine Sambac 10%", "jasmin"),
        ("Jasmin d'Orris", "Orivone", "orris"),
    ],
)
def test_material_carries_its_own_odour_word(name, material, word):
    result = _namesake(name, {**_PLAIN_BASE, material: 150.0})

    assert material in result.data["carried_by"][word]
    assert word not in result.data["missing"]


def test_negated_word_is_not_required():
    result = _namesake("Cedar Azure — No Bergamot", {**_PLAIN_BASE, "Cedarwood EO": 200.0})

    assert result.status == "PASS"
    assert "bergamot" not in result.data["words"]
    assert result.data["not_required"] == ["bergamot"]


def test_without_and_free_negate():
    result = _namesake("Iris without Violet, Musk-free", {**_PLAIN_BASE, "Orivone": 150.0})

    assert result.data["words"] == ["iris"]
    assert set(result.data["not_required"]) == {"violet", "musk"}


def test_violet_leaf_does_not_carry_violet():
    result = _namesake("Violet Noir", {**_PLAIN_BASE, "Violet Leaf Absolute": 150.0})

    assert result.data["words"] == ["violet"]
    assert result.status == "WARN"
    assert result.data["missing"] == ["violet"]


def test_orange_peel_does_not_carry_orange_blossom():
    result = _namesake("Orange Blossom", {**_PLAIN_BASE, "Orange Peel EO": 150.0})

    assert result.data["words"] == ["orange blossom"]
    assert result.status == "WARN"
    assert "Name says orange blossom" in result.detail


def test_plural_words_are_checked():
    result = _namesake("Roses and Violets", _PLAIN_BASE)

    assert result.data["words"] == ["rose", "violet"]
    assert result.status == "WARN"


def test_generic_modifier_is_not_an_odour_word():
    result = _namesake("Citrus Fresh", {**_PLAIN_BASE, "Orange Peel EO": 150.0})

    assert result.data["words"] == ["citrus"]
    assert result.status == "PASS"


def test_opaque_base_makes_a_missing_word_unverified_not_missing():
    result = _namesake("Blue Lavender", {**_PLAIN_BASE, "Oops Fougere Base": 600.0})

    assert result.status == "SKIP"
    assert result.data["missing"] == []
    assert result.data["unverified"] == {"lavender": ["Oops Fougere Base"]}
    assert "Oops Fougere Base has no odour data, so lavender couldn't be checked" in result.detail


def test_cassis_without_a_carrier_is_not_claimed_carried():
    result = _namesake(
        "Cassis Iris Smoke", {**_PLAIN_BASE, "Orivone": 150.0, "Olibanum Resinoid": 150.0}
    )

    assert result.data["words"] == ["cassis", "iris", "smoke"]
    assert result.status == "WARN"
    assert result.data["missing"] == ["cassis"]
    assert "Every odour word" not in result.detail


def test_vetival_own_odour_text_carries_vetiver():
    # Vetival's ODT descriptor is "suede-vetiver dryness": its own odour is vetiver.
    result = _namesake(
        "Cocoa Vetiver Tuberose — 30 mL EdP", {**_COCOA_TUBEROSE_BASE, "Vetival": 60.0}
    )

    assert result.status == "PASS"
    assert result.data["carried_by"]["vetiver"] == ["Vetival"]


def test_rosewood_does_not_carry_rose():
    result = _namesake("Rose Noir", {**_PLAIN_BASE, "Rosewood EO": 150.0})

    assert "Rosewood EO" not in result.data["carried_by"]["rose"]


# Round 3 review fixes.
def test_french_name_words_are_checked_not_dropped():
    result = _namesake("Osmanthus Tabac Fumé", {**_PLAIN_BASE, "Osmanthus Absolute": 150.0})

    assert result.status == "WARN"
    assert result.data["missing"] == ["tabac", "fume"]
    assert "Every odour word" not in result.detail


def test_single_material_without_odour_data_is_named_not_masking():
    result = _namesake("Pineapple Chypre", {**_PLAIN_BASE, "D-Limonene": 300.0})

    assert result.status == "WARN"
    assert result.data["missing"] == ["pineapple"]
    assert result.data["no_odour_data"] == ["D-Limonene"]
    assert "no odour data for D-Limonene" in result.detail


def test_bridge_prose_does_not_carry_oud():
    result = _namesake(
        "Rose Oud", {**_PLAIN_BASE, "Phenethyl Alcohol": 150.0, "Nagarmotha Oil": 150.0}
    )

    assert result.status == "WARN"
    assert result.data["missing"] == ["oud"]


def test_trade_name_prefix_does_not_carry_word():
    result = _namesake("Citron Noir", {**_PLAIN_BASE, "Citronellol": 150.0})

    assert result.status == "WARN"
    assert result.data["missing"] == ["citron"]


def test_harvest_and_origin_words_are_not_required():
    result = _namesake(
        "Rose de Mai", {**_PLAIN_BASE, "Phenethyl Alcohol": 150.0, "Citronellol": 150.0}
    )

    assert result.data["words"] == ["rose"]
    assert result.status == "PASS"
    assert result.data["not_checked"] == {"de mai": "origin"}


def test_not_negates_a_name_word():
    result = _namesake("Iris, not powdery", {**_PLAIN_BASE, "Orivone": 150.0})

    assert result.data["words"] == ["iris"]
    assert result.data["not_required"] == ["powdery"]


def test_no_followed_by_a_number_does_not_negate():
    result = _namesake("No. 5 Rose Aldehyde", _PLAIN_BASE)

    assert result.data["words"] == ["rose", "aldehyde"]
    assert result.data["not_required"] == []
