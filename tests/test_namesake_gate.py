"""namesake gate: a formula's name promises odours its materials must carry (AGENTS.md RULE 3)."""

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
