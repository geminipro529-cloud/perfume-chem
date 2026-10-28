"""A row the IFRA Category 4 table cannot recognise holds the safety gate.

An unrecognised row is never compared with a limit and drops out of the group sums, so a
restricted material under an unfamiliar stock name could otherwise pass with a warning.
"""

import pytest

from engine.ifra_standards import evaluate_ifra, load_ifra_table, single_material_limit_pct
from engine.inventory_parser import materialize_current_inventory
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_safety

TABLE = load_ifra_table()


def _gate(ingredients):
    state = build_formula_state(
        ingredients, {name: 1.0 for name in ingredients}, batch_volume_ml=30.0
    )
    return _gate_safety(state, ReleaseGateConfig(batch_volume_source="title"))


# --------------------------------------------------------------------------- matching


def test_word_order_variant_finds_alpha_damascone():
    material = TABLE.lookup("Damascone Alpha")
    assert material is not None
    assert material.name == "Alpha Damascone"
    assert material.standard == "IFRA_STD_077"
    assert TABLE.lookup("Damascone Alpha 10% in DPG") is material


def test_methyl_ionone_gamma_coeur_is_under_the_methyl_ionone_standard():
    material = TABLE.lookup("Methyl Ionone Gamma Coeur")
    assert material is not None
    assert material.status == "restricted"
    assert material.standard == TABLE.lookup("Alpha Isomethyl Ionone").standard
    assert material.standard == "IFRA_STD_063"
    # Its own stock identity, but summed with the other methyl ionones.
    assert material is not TABLE.lookup("Alpha Isomethyl Ionone")
    group = next(g for g in TABLE.group_rules if g.id == "methyl_ionones_total")
    assert "Methyl Ionone Gamma Coeur" in group.members


def test_near_misses_keep_their_own_entries():
    assert TABLE.lookup("Beta Damascone").name == "Beta Damascone"
    assert TABLE.lookup("Damascone Beta").name == "Beta Damascone"
    assert TABLE.lookup("Damascenone").name == "Damascenone"
    assert TABLE.lookup("Damascone Delta").name == "Delta Damascone"
    assert TABLE.lookup("Methyl Ionone").name == "Methyl Ionone Pure"
    assert TABLE.lookup("Alpha Ionone").name == "Alpha Ionone"
    assert TABLE.lookup("Ionone") is None  # no word is dropped to reach "Methyl Ionone"
    assert TABLE.lookup("Ionone Methyl").name == "Methyl Ionone Pure"


def test_word_order_variant_is_checked_against_its_limit_and_group():
    evaluation = evaluate_ifra({"Damascone Alpha": 0.03, "Beta Damascone": 0.03})
    row = next(c for c in evaluation.checks if c.material == "Damascone Alpha")
    assert row.ifra_name == "Alpha Damascone"
    assert row.verdict != "unchecked"
    group = next(g for g in evaluation.group_checks if g.id == "rose_ketones_total")
    assert group.verdict == "fail"  # 0.06 % > 0.043 %


# --------------------------------------------------------------------------- the gate


UNLISTED = "Unlisted Supplier Base"  # no owned stock is unrecognised any more


def test_unrecognised_row_holds_the_gate():
    # Orange Flower Absolute was the example until Kenny lifted its hold on 2026-10-28 ("Use
    # orange flower absolute freely"). (Supplier bases with no published composition are
    # flagged instead; see test_ifra_undisclosed_bases.py.)
    assert TABLE.lookup(UNLISTED) is None
    gate = _gate({"Evernyl": 240.0, UNLISTED: 20.0})

    assert gate.status == "HOLD"
    assert UNLISTED in gate.detail
    assert "To clear" in gate.detail
    assert gate.data["unchecked"] == [UNLISTED]
    hold = next(h for h in gate.data["holds"] if h["material"] == UNLISTED)
    assert "not recognised by the IFRA Category 4 table" in hold["message"]
    assert "supplier's IFRA certificate" in hold["message"]


def test_phenyl_acetaldehyde_is_restricted_by_its_own_standard():
    material = TABLE.lookup("Phenyl Acetaldehyde")
    assert material is not None
    assert material.status == "restricted"
    assert material.standard == "IFRA_STD_073"
    assert material.cat4_limit_pct == 0.25
    assert TABLE.standards["IFRA_STD_073"].cas == ("122-78-1",)

    evaluation = evaluate_ifra({"Phenyl Acetaldehyde": 0.3})
    row = next(c for c in evaluation.checks if c.material == "Phenyl Acetaldehyde")
    assert row.verdict == "fail"  # 0.3 % > 0.25 %


def test_reviewed_no_standard_stock_passes_the_gate():
    material = TABLE.lookup("Maltol")
    assert material is not None
    assert material.status == "no_standard"
    assert material.source_url == "https://ifrafragrance.org/standards-library"

    gate = _gate({"Evernyl": 240.0, "Maltol": 20.0})
    assert gate.data["unchecked"] == []
    assert gate.data["holds"] == []
    assert gate.status == "PASS"


def test_formula_with_every_row_recognised_keeps_its_verdict():
    gate = _gate({"Evernyl": 240.0})

    assert gate.data["unchecked"] == []
    assert gate.data["holds"] == []
    assert gate.status == "PASS"


# Owned stocks reviewed against the IFRA Standards Library on 2026-10-09 and left
# unrecognised on purpose. Each must keep holding, except the supplier bases and extracts
# with no published composition, which are flagged by name with a warning (Kenny,
# 2026-10-09), and Aurantiol, whose hydroxycitronellal share is counted as a Schiff base.
# On 2026-10-25 the stock thread's IFRA batch gave every other owned stock a table row
# (most from the supplier's IFRA certificate, the rest "no standard" after a full read of
# the Standards Library); Orange Flower Absolute keeps holding by Kenny's decision.
FLAGGED_BASES = {
    "Cabbage Rose Extract",  # MySkinRecipes PG extracts: no composition or IFRA document
    "Castoreum Synthetic",
    "Costus Olifac",  # stock name since the 2026-10-15 10% in DPG record
    "Iris Florentina Root Extract",
    "Lilyreal ND",
    "Magnolia Flower Extract",
}
# Both Aurantiol stocks carry Kenny's word since 2026-10-15, so their display
# names say which bottle each is.
SCHIFF_BASES = {
    "Aurantiol (neat)",
    "Aurantiol 10%",
}
# Orange Flower Absolute left on 2026-10-28: Kenny, "Use orange flower absolute freely".
STILL_HELD = FLAGGED_BASES | SCHIFF_BASES


def test_every_owned_stock_is_matched_or_holds_by_name():
    stocks = {s.name: s for s in materialize_current_inventory().stocks}
    unmatched = sorted(
        name
        for name, s in stocks.items()
        if TABLE.lookup(name, s.identity_name, s.raw_name) is None
    )
    assert set(unmatched) == STILL_HELD

    gate = _gate({name: 10.0 for name in unmatched})
    # Only flagged bases (warned) and Schiff bases (counted) are left, so nothing holds.
    assert gate.status == "WARN"
    assert sorted(gate.data["unchecked"]) == sorted(set(unmatched) - SCHIFF_BASES)
    held = {h["material"] for h in gate.data["holds"]}
    assert set(unmatched) - FLAGGED_BASES - SCHIFF_BASES <= held
    assert not held & (FLAGGED_BASES | SCHIFF_BASES)
    assert {u["material"] for u in gate.data["undisclosed_bases"]} == FLAGGED_BASES
    for name in set(unmatched) - SCHIFF_BASES:
        assert name in gate.detail


def test_freesia_hdi_fails_for_the_lilial_it_contains():
    # PerfumersWorld's IFRA certificate for Freesia HDL (Kenny's Freesia HDI) lists
    # Lilial at 0.7921 %, and the table treats Lilial as prohibited.
    material = TABLE.lookup("Freesia HDI")
    assert material is not None and material.status == "prohibited"
    assert TABLE.lookup("Freesia HDL") is material
    gate = _gate({"Evernyl": 240.0, "Freesia HDI": 10.0})
    assert gate.status == "FAIL"
    assert "Freesia HDI" in gate.detail and "Lilial" in gate.detail


def test_tonkarome_fails_for_the_6_methylcoumarin_it_contains():
    # PerfumersWorld's IFRA certificate for Tonkarome (2QV23715) lists 6-methylcoumarin
    # at 0.005 % and marks it prohibited; Kenny chose to block it on 25 Oct 2026.
    material = TABLE.lookup("Tonkarome")
    assert material is not None and material.status == "prohibited"
    assert material.standard == "IFRA_STD_160"
    gate = _gate({"Evernyl": 240.0, "Tonkarome": 10.0})
    assert gate.status == "FAIL"
    assert "Tonkarome" in gate.detail and "6-methylcoumarin" in gate.detail
    assert gate.data["undisclosed_bases"] == []


def test_canthoxal_and_rhodinol_carry_their_ifra_limits():
    # Kenny chose "Load all" on 21 Oct 2026 for the ingredients research thread's findings.
    canthoxal = TABLE.lookup("Canthoxal")
    assert (canthoxal.standard, canthoxal.cat4_limit_pct) == ("IFRA_STD_057", 2.5)
    assert TABLE.lookup("Para-anisyl Propanal").name == "Canthoxal"
    # A citronellol/geraniol blend with up to 40 % geraniol: the stricter geraniol limit applies to the whole stock.
    rhodinol = TABLE.lookup("Rhodinol")
    assert (rhodinol.standard, rhodinol.cat4_limit_pct) == ("IFRA_STD_037", 4.7)
    # PerfumersWorld's Rhodinol ex Citronella (3RB07724) is its own entry since 2026-10-25:
    # checked whole as citronellol, with its certificate's geraniol counted (9.96 %).
    ex_citronella = TABLE.lookup("Rhodinol ex Citronella")
    assert ex_citronella is not rhodinol
    assert (ex_citronella.standard, ex_citronella.cat4_limit_pct) == ("IFRA_STD_022", 12.0)
    status, limit = single_material_limit_pct("Rhodinol ex Citronella")
    assert status == "restricted"
    assert limit == pytest.approx(4.7 / 0.471666)
