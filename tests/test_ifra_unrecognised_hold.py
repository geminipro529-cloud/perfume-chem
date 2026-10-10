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
    "Costus Olifac 10%",
    "Lilyreal ND",
    "Suederal 10%",
    "Tonkarome",
}
SCHIFF_BASES = {"Aurantiol 10% in DPG"}
STILL_HELD = {
    "Ambrette Seed Absolute",
    "Aurantiol 10% in DPG",
    "Black Agarwood Artificial",
    "Black Tea Base",
    "Castoreum Synthetic",
    "Cedryl Acetate",
    "Clearwood",
    "Costus Olifac 10%",
    "Frangipani Absolute",
    "Fructone B",
    "Lavandin Absolute",
    "Lemon Terpeneless Oil Sicilian",
    "Lilyreal ND",
    "Mate Absolute",
    "Orris Concrete Orris Butter",
    "Saffranal",
    "Suederal 10%",
    "Tonkarome",
    "Vanilla Absolute",
    "Vertofix",
    "Vertofix Coeur",
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
