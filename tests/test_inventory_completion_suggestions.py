"""Stock page suggestions: what a not-ready stock is missing, and from where.

The strength always comes from the stock record. inventory.txt fills the basis
and carrier only from a line at that same strength; Kenny's standing rule
(dilutions in DPG, w/w unless recorded) fills what the line leaves unstated.
"""

from types import SimpleNamespace

import pytest

from engine.inventory_completions import suggest_inventory_completion


def _stock(dilution, basis="unspecified", carrier=""):
    return SimpleNamespace(dilution=dilution, fraction_basis=basis, carrier=carrier)


@pytest.mark.parametrize(
    ("line", "dilution", "basis", "carrier", "basis_source", "quote"),
    [
        ("Frangipani Absolute (10% in DPG)  # basis unspecified", 0.1, "mass_fraction", "DPG", "user_rule", "10% in DPG"),
        ("Labdanum Resinoid (10% w/w in DPG)  # confirmed", 0.1, "mass_fraction", "DPG", "inventory_txt", "10% w/w in DPG"),
        ("Ethyl Maltol (1% v/v nominal in ethanol)", 0.01, "volume_fraction", "ethanol", "inventory_txt", "1% v/v nominal in ethanol"),
        ("Opoponax Resinoid (50% w/w in DEP)", 0.5, "mass_fraction", "DEP", "inventory_txt", "50% w/w in DEP"),
        ("Ambrocenide (0.1% in TEC)  # SKU 5WU22696", 0.001, "mass_fraction", "TEC", "user_rule", "0.1% in TEC"),
        ("Exaltolide (10%)  # 10% in DPG", 0.1, "mass_fraction", "DPG", "user_rule", "10% in DPG"),
    ],
)
def test_a_line_at_the_stock_strength_supplies_what_it_states(
    line, dilution, basis, carrier, basis_source, quote
):
    suggestion = suggest_inventory_completion(_stock(dilution), [(325, line)])

    assert suggestion["fraction_basis"] == basis
    assert suggestion["carrier"] == carrier
    assert suggestion["sources"]["carrier"] == "inventory_txt"
    assert suggestion["sources"]["fraction_basis"] == basis_source
    assert suggestion["sources"]["fraction_percent_decimal"] == "stock_record"
    assert suggestion["inventory_line"] == 325
    assert suggestion["inventory_text"] == quote
    assert suggestion["source_text"].startswith(f"inventory.txt L325 says '{quote}'")
    assert suggestion["saved"] is False


def test_carrier_from_the_line_and_w_w_from_the_rule_say_both_sources():
    suggestion = suggest_inventory_completion(_stock(0.1), [(325, "Buccoxime (10% in DPG)")])

    assert suggestion["source_text"] == "inventory.txt L325 says '10% in DPG'; w/w by your rule"
    assert suggestion["fraction_percent_decimal"] == "10"


def test_a_line_at_another_strength_is_not_used():
    suggestion = suggest_inventory_completion(
        _stock(0.1),
        [(30, "Hexyl Acetate 1% v/v in ethanol  # Hexyl Acetate 10% already present")],
    )

    # Only the rule fills the gaps, and the strength is still the stock's own.
    assert suggestion["fraction_percent_decimal"] == "10"
    assert suggestion["carrier"] == "DPG"
    assert suggestion["fraction_basis"] == "mass_fraction"
    assert suggestion["sources"] == {
        "fraction_percent_decimal": "stock_record",
        "fraction_basis": "user_rule",
        "carrier": "user_rule",
    }
    assert suggestion["inventory_line"] is None
    assert suggestion["source_text"] == "Your rule: dilutions in DPG, w/w unless recorded"


def test_the_matching_line_is_chosen_among_several():
    suggestion = suggest_inventory_completion(
        _stock(0.01),
        [(124, "Rose Oxide (10% in DEP)"), (125, "Rose Oxide (1% w/w in TEC)")],
    )

    assert (suggestion["carrier"], suggestion["inventory_line"]) == ("TEC", 125)


def test_a_neat_line_suggests_neat_for_a_full_strength_stock():
    suggestion = suggest_inventory_completion(_stock(1.0), [(226, "Suederal (neat)")])

    assert suggestion["fraction_basis"] == "neat"
    assert suggestion["sources"]["fraction_basis"] == "inventory_txt"
    assert "carrier" not in suggestion
    assert suggestion["source_text"] == "inventory.txt L226 says 'neat'"


def test_the_rule_never_makes_a_full_strength_stock_a_dilution():
    assert suggest_inventory_completion(_stock(1.0), [(225, "Suederal (10% in DPG)")]) is None


def test_recorded_facts_are_not_re_suggested():
    assert suggest_inventory_completion(_stock(0.1, "mass_fraction", "dpg"), []) is None
    suggestion = suggest_inventory_completion(_stock(0.2, "mass_fraction", ""), [])
    assert "fraction_basis" not in suggestion
    assert suggestion["carrier"] == "DPG"


def test_an_unstated_carrier_word_is_not_a_carrier():
    suggestion = suggest_inventory_completion(_stock(0.2), [(1, "Myrrh (20% in carrier unstated)")])

    assert suggestion["carrier"] == "DPG"
    assert suggestion["sources"]["carrier"] == "user_rule"


def test_no_recorded_strength_means_no_suggestion():
    assert suggest_inventory_completion(_stock(0.0), [(1, "Thing (10% in DPG)")]) is None
