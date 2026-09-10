"""Nominal molecular scenario accounting and vector tradeoff behavior."""
import math

import pytest

from engine import hedonic_model


def expand(candidate, structures=None, profiles=None, volume=1000., multipliers=None):
    function = getattr(hedonic_model, "expand_natural_scenario", None)
    assert callable(function), "Natural scenario expansion missing"
    return function(candidate, structures or {}, profiles or {}, volume, multipliers)


def pareto(records, **kwargs):
    function = getattr(hedonic_model, "pareto_minimize", None)
    assert callable(function), "Pareto vector filtering missing"
    return function(records, **kwargs)


def test_same_canonical_molecule_from_direct_and_two_naturals_is_aggregated():
    result = expand({"direct": 100., "oil_a": 100., "oil_b": 200.},
                    {"direct": "CCO"}, {
                        "oil_a": [{"name": "ethanol", "smiles": "OCC", "fraction": .5}],
                        "oil_b": [{"name": "ethanol", "smiles": "CCO", "fraction": .25}]})
    assert result["components"] == [{"smiles": "CCO", "nominal_fraction": .2}]
    assert result["modeled_raw_equivalent_ul"] == 200.
    assert result["unresolved_raw_equivalent_ul"] == 200.
    assert result["per_stock_coverage"]["oil_a"]["modeled_fraction"] == .5


def test_missing_structures_and_unreported_residual_are_not_renormalized():
    result = expand({"oil": 100., "unknown_stock": 80., "zero": 0.}, profiles={"oil": [
        {"name": "known", "smiles": "CCO", "fraction": .2},
        {"name": "unresolved", "smiles": None, "fraction": .3}]})
    assert result["components"] == [{"smiles": "CCO", "nominal_fraction": .02}]
    assert result["modeled_raw_equivalent_ul"] == 20.
    assert result["unresolved_raw_equivalent_ul"] == 160.
    assert "zero" not in result["per_stock_coverage"]
    assert result["basis"] == "NOMINAL_COMPOSITION_PROXY_NOT_EXACT_MASS"


def test_scenario_multiplier_changes_coverage_without_rebalancing_residual():
    profile = {"oil": [{"name": "ethanol", "smiles": "CCO", "fraction": .4}]}
    result = expand({"oil": 100.}, profiles=profile, multipliers={"ethanol": 1.5})
    assert result["modeled_raw_equivalent_ul"] == pytest.approx(60.)
    assert result["unresolved_raw_equivalent_ul"] == pytest.approx(40.)
    assert profile["oil"][0]["fraction"] == .4


@pytest.mark.parametrize("fraction", [-.1, math.nan, math.inf, True])
def test_invalid_fraction_rejected(fraction):
    with pytest.raises(ValueError):
        expand({"oil": 100.}, profiles={"oil": [
            {"name": "x", "smiles": "CCO", "fraction": fraction}]})


def test_perturbed_closure_includes_unmapped_constituents():
    with pytest.raises(ValueError):
        expand({"oil": 100.}, profiles={"oil": [
            {"name": "known", "smiles": "CCO", "fraction": .5},
            {"name": "unknown", "fraction": .4}]}, multipliers={"unknown": 2.})


@pytest.mark.parametrize("value", [0., -1., math.nan, math.inf])
def test_nonpositive_or_nonfinite_multiplier_rejected(value):
    with pytest.raises(ValueError):
        expand({"oil": 100.}, multipliers={"x": value})


def test_unknown_positive_multiplier_name_is_not_silently_ignored():
    with pytest.raises(ValueError, match="Unknown constituent multiplier"):
        expand({"oil": 100.}, profiles={"oil": [
            {"name": "ethanol", "smiles": "CCO", "fraction": .3}]},
            multipliers={"ethnaol": 1.2})


def test_overlapping_stock_mappings_and_invalid_molecules_rejected():
    with pytest.raises(ValueError):
        expand({"a": 100.}, {"a": "CCO"}, {"a": []})
    with pytest.raises(ValueError):
        expand({"a": 100.}, {"a": "invalid molecule"})


@pytest.mark.parametrize("candidate,volume", [
    ({"a": -1}, 1000), ({"a": math.nan}, 1000), ({"a": 10}, 0),
    ({"a": 10}, math.inf), ({"a": 101}, 100), ({"a": True}, 1000)])
def test_invalid_doses_or_volume_rejected(candidate, volume):
    with pytest.raises(ValueError):
        expand(candidate, volume=volume)


def test_distinct_stereoisomers_are_not_collapsed():
    result = expand({"left": 10., "right": 10.},
                    {"left": "C[C@H](O)C(=O)O", "right": "C[C@@H](O)C(=O)O"})
    assert len(result["components"]) == 2
    assert {r["nominal_fraction"] for r in result["components"]} == {.01}


def test_geraniol_and_nerol_ez_isomers_stay_distinct_while_repeated_geraniol_aggregates():
    # PubChem isomeric records: geraniol CID637566 (2E), nerol CID643820 (2Z).
    geraniol = "CC(=CCC/C(=C/CO)/C)C"
    nerol = "CC(=CCC/C(=C\\CO)/C)C"
    result = expand({"geraniol": 10., "nerol": 10., "oil": 100.},
                    {"geraniol": geraniol, "nerol": nerol},
                    {"oil": [{"name": "geraniol", "smiles": geraniol, "fraction": .2}]})
    assert len(result["components"]) == 2
    assert sorted(r["nominal_fraction"] for r in result["components"]) == [.01, .03]
    assert result["modeled_raw_equivalent_ul"] == 40.


def test_pareto_keeps_tradeoffs_and_ties_in_original_order_and_identity():
    records = [{"id": "a", "loss_vector": [1., 3.]},
               {"id": "b", "loss_vector": [3., 1.]},
               {"id": "dominated", "loss_vector": [4., 4.]},
               {"id": "a_tie", "loss_vector": [1., 3.]}]
    result = pareto(records)
    assert [r["id"] for r in result] == ["a", "b", "a_tie"]
    assert result[0] is records[0]
    assert len(records) == 4


def test_pareto_empty_and_custom_vector_key():
    assert pareto([]) == []
    records = [{"v": [2.]}, {"v": [1.]}]
    assert pareto(records, vector_key="v") == [records[1]]


@pytest.mark.parametrize("vectors", [[[1.], [1., 2.]], [[math.nan]], [[math.inf]], [[]]])
def test_pareto_rejects_invalid_vector_dimensions_or_values(vectors):
    with pytest.raises(ValueError):
        pareto([{"loss_vector": vector} for vector in vectors])
