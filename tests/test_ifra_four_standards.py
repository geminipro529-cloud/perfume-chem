"""Estragole, methyl eugenol, methyl N-methylanthranilate and safrole standards, their
Annex I natural sources, and the Orange Peel EO species note."""

from __future__ import annotations

import json

import pytest

from engine.ifra_standards import (
    DEFAULT_CONSTITUENTS_PATH,
    evaluate_ifra,
    load_natural_constituents,
)


def _group(evaluation, gid):
    return next(g for g in evaluation.group_checks if g.id == gid)


@pytest.mark.parametrize(
    ("name", "standard", "limit"),
    [
        ("Estragole", "IFRA_STD_099", 0.014),
        ("Methyl Eugenol", "IFRA_STD_100", 0.011),
        ("Methyl N-Methylanthranilate", "IFRA_STD_094", 0.1),
    ],
)
def test_restricted_substance_fails_above_and_passes_below_its_limit(name, standard, limit):
    above = evaluate_ifra({name: limit * 1.5}).checks[0]
    below = evaluate_ifra({name: limit * 0.5}).checks[0]
    assert above.verdict == "fail" and standard in above.message
    assert below.verdict == "pass" and below.standard == standard


@pytest.mark.parametrize("name", ["Safrole", "Isosafrole", "Dihydrosafrole"])
def test_safrole_family_is_prohibited_as_an_ingredient(name):
    check = evaluate_ifra({name: 0.001}).checks[0]
    assert check.verdict == "fail" and "IFRA_STD_179" in check.message


def test_safrole_isosafrole_dihydrosafrole_are_summed_against_one_limit():
    group = _group(
        evaluate_ifra({"Safrole": 0.004, "Isosafrole": 0.004, "Dihydrosafrole": 0.004}),
        "safrole_isosafrole_dihydrosafrole_total",
    )
    assert group.limit_pct == 0.01
    assert group.total == pytest.approx(0.012)
    assert group.verdict == "fail"


def test_rose_essential_oil_counts_methyl_eugenol_and_fails_naming_the_stock():
    stock = "Rose Essential Oil (Rosa Damascena, India)"
    group = _group(evaluate_ifra({stock: 1.0}), "IFRA_STD_100_constituents")
    assert group.total == pytest.approx(0.02)
    assert group.verdict == "fail"
    assert stock in group.message and "Rose oil" in group.message


@pytest.mark.parametrize(
    ("stock", "standard", "level"),
    [
        ("Elemi EO", "IFRA_STD_100", 0.4),
        ("Nutmeg EO", "IFRA_STD_100", 1.2),
        ("Magnolia EO", "IFRA_STD_100", 2.8),
        ("Rose de Mai Absolute", "IFRA_STD_100", 0.5),
        ("Tuberose Absolute", "IFRA_STD_100", 1.8),
        ("Anise EO", "IFRA_STD_099", 3.3),  # star anise, the higher candidate
    ],
)
def test_natural_counts_toward_its_substance(stock, standard, level):
    total = next(
        t for t in evaluate_ifra({stock: 0.1}).constituent_totals if t.standard == standard
    )
    assert total.total == pytest.approx(0.1 * level / 100)


def test_estragole_and_methyl_eugenol_no_longer_wait():
    raw = json.loads(DEFAULT_CONSTITUENTS_PATH.read_text(encoding="utf-8"))
    assert "Anise EO" not in raw["unmapped_owned_naturals"]
    assert "Elemi EO" not in raw["unmapped_owned_naturals"]
    assert {"IFRA_STD_099", "IFRA_STD_100"} <= load_natural_constituents().standards


def test_orange_peel_eo_lists_both_species_and_says_it_is_not_recorded():
    raw = json.loads(DEFAULT_CONSTITUENTS_PATH.read_text(encoding="utf-8"))
    note = raw["stocks"]["Orange Peel EO"]["note"]
    assert "sweet" in note and "bitter" in note and "not recorded" in note
    check = evaluate_ifra({"Orange Peel EO": 0.1}).checks[0]
    assert check.standard == "IFRA_STD_088"
    assert "species is not recorded" in check.message


def test_basil_counts_the_estragole_chemotype_and_says_it_is_not_recorded():
    stock = "Basil EO (India, Ocimum Basilicum)"
    evaluation = evaluate_ifra({stock: 0.1})
    totals = {t.standard: t.total for t in evaluation.constituent_totals}
    # Chemotype unknown: the estragole type's 80 % estragole and 0.5 % methyl eugenol.
    assert totals["IFRA_STD_099"] == pytest.approx(0.08)
    assert totals["IFRA_STD_100"] == pytest.approx(0.0005)
    assert _group(evaluation, "IFRA_STD_099_constituents").verdict == "fail"
    assert "chemotype is not recorded" in evaluation.checks[0].message


def test_red_mandarin_counts_the_mandarin_oil_methyl_n_methylanthranilate():
    evaluation = evaluate_ifra({"Red Mandarin EO": 1.0})
    total = next(t for t in evaluation.constituent_totals if t.standard == "IFRA_STD_094")
    assert total.total == pytest.approx(0.004)
    assert _group(evaluation, "IFRA_STD_094_constituents").verdict == "pass"
