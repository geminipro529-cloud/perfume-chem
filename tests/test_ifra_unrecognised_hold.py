"""A row the IFRA Category 4 table cannot recognise holds the safety gate.

An unrecognised row is never compared with a limit and drops out of the group sums, so a
restricted material under an unfamiliar stock name could otherwise pass with a warning.
"""

from engine.ifra_standards import evaluate_ifra, load_ifra_table
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


def test_unrecognised_row_holds_the_gate():
    # A trade name whose identity was not confirmed: it stays unrecognised. (Supplier
    # bases with no published composition are flagged instead; see
    # test_ifra_undisclosed_bases.py.)
    assert TABLE.lookup("Vertofix") is None
    gate = _gate({"Evernyl": 240.0, "Vertofix": 20.0})

    assert gate.status == "HOLD"
    assert "Vertofix" in gate.detail
    assert "To clear" in gate.detail
    assert gate.data["unchecked"] == ["Vertofix"]
    hold = next(h for h in gate.data["holds"] if h["material"] == "Vertofix")
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
# unrecognised on purpose: compounded bases, naturals and absolutes, a Schiff base,
# cedarwood-derived grades that may carry cedrene (IFRA_STD_197, Category 4 1.5 %), and
# trade names whose identity was not confirmed from a source. Each must keep holding,
# except the supplier bases with no published composition, which are flagged by name
# with a warning (Kenny, 2026-10-09), and Aurantiol, whose hydroxycitronellal share is
# counted as a Schiff base.
FLAGGED_BASES = {
    "Black Agarwood Artificial",
    "Black Tea Base",
    "Castoreum Synthetic",
    "Clearwood",
    "Costus Olifac",  # stock name since the 2026-10-15 10% in DPG record
    "Lilyreal ND",
    "Suederal",  # stock name since the 2026-10-14 DPG record
    "Tonkarome",
}
# Both Aurantiol stocks carry Kenny's word since 2026-10-15, so their display
# names say which bottle each is.
SCHIFF_BASES = {
    "Aurantiol (neat)",
    "Aurantiol 10%",
}
STILL_HELD = {
    "Ambrette Seed Absolute",
    "Aurantiol (neat)",
    "Aurantiol 10%",
    "Black Agarwood Artificial",
    "Black Tea Base",
    "Castoreum Synthetic",
    "Cedryl Acetate",
    # Added to the stock list on 2026-10-14; no IFRA standard names these woods.
    "Cedroxyde",
    "Clearwood",
    # Added 2026-10-15: plant part unknown, so its eugenol content is unknown.
    "Clove EO (India)",
    "Costus Olifac",  # stock name since the 2026-10-15 10% in DPG record
    "Frangipani Absolute",
    "Fructone B",
    "Hindinol",
    # New bottles of 2026-10-13: no IFRA standard names pomelo or ginger lily oil, and
    # neither bottle's species, plant part or furocoumarin content is recorded.
    "Ginger Lily Oil",
    "Lavandin Absolute",
    "Lemon Terpeneless Oil Sicilian",
    "Lilyreal ND",
    "Mate Absolute",
    # Added 2026-10-15 (neat); no IFRA table entry matches it.
    "Neryl Acetate",
    "Orris Concrete Orris Butter",
    # Kenny's 50% w/w ethanol dilution of orris butter (2026-10-20); orris has no IFRA standard.
    "Orris Butter 50% in EtOH",
    # 20 Oct 2026 email-sweep arrivals (Kenny's answers in "Check new ingredients in code"); no IFRA row yet.
    "Cabbage Rose Extract",
    # The other arrivals got IFRA rows on 2026-10-21 (Kenny chose "Load all"); these three extracts
    # and Dupical 10% still hold by name.
    "Dupical 10% in DPG",
    "Iris Florentina Root Extract",
    "Magnolia Flower Extract",
    "Pomelo EO",
    # Added 2026-10-15: a saturated saffron infusion in DPG of unknown strength.
    "Red Saffron Infusion",
    # Owned before, but undosable until 2026-10-14 gave it a strength (neat).
    "Sandalwood Base X3",
    "Suederal",  # stock name since the 2026-10-14 DPG record
    "Tonkarome",
    "Vanilla Absolute",
    "Vertofix",
    "Vertofix Coeur",
    # Recorded 2026-10-15 from Kenny's bottle answers and his w/w-in-DPG rule; no IFRA
    # table entry matches them yet, so they hold by name.
    "Benzoin Sumatra Resinoid 10%",
    "Cassis Base 345B",
    "Champignol 10% in DPG",
    "Cocoa Absolute",
    "Dihydrojasmone",
    "Dihydrojasmone 10% in DPG",
    "Jessemal",
    "Nerolin Bromelia 10% in DPG",
    "Pamzest",
    "Rhodinol ex Citronella",
    "Tuberlia Base",
    # MySkinRecipes order #2199302, arrived 2026-10-16; no IFRA table entry matches
    # these names yet, so they hold by name. (Cedarwood Texas, Geranium Bourbon,
    # Sweet Orange and both Isoraldeines were linked on 2026-10-16.)
    # 2026-10-21 ("Load all"): Rhodinol is checked against the geraniol standard; Para-Acetanisole,
    # Rum Ether and most sweep arrivals are recorded as having no IFRA standard.
    # 2026-10-23 ("Load it"): p-Cresyl Methyl Ether 10% is recorded as having no IFRA standard
    # (RIFM's assessment for CAS 104-93-8: "IFRA standard: None").
}


def test_every_owned_stock_is_matched_or_holds_by_name():
    stocks = {s.name: s for s in materialize_current_inventory().stocks}
    unmatched = sorted(
        name
        for name, s in stocks.items()
        if TABLE.lookup(name, s.identity_name, s.raw_name) is None
    )
    assert set(unmatched) == STILL_HELD

    gate = _gate({name: 10.0 for name in unmatched})
    assert gate.status == "HOLD"
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


def test_canthoxal_and_rhodinol_carry_their_ifra_limits():
    # Kenny chose "Load all" on 21 Oct 2026 for the ingredients research thread's findings.
    canthoxal = TABLE.lookup("Canthoxal")
    assert (canthoxal.standard, canthoxal.cat4_limit_pct) == ("IFRA_STD_057", 2.5)
    assert TABLE.lookup("Para-anisyl Propanal").name == "Canthoxal"
    # A citronellol/geraniol blend with up to 40 % geraniol: the stricter geraniol limit applies to the whole stock.
    rhodinol = TABLE.lookup("Rhodinol")
    assert (rhodinol.standard, rhodinol.cat4_limit_pct) == ("IFRA_STD_037", 4.7)
    assert TABLE.lookup("Rhodinol ex Citronella") is None
