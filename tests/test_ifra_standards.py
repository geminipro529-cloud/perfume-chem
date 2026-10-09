"""IFRA Category 4 table: validation, lookup and finished-product evaluation."""

import copy
import json
import re
from decimal import Decimal

import pytest

from engine.ifra_standards import (
    DEFAULT_TABLE_PATH,
    IFRATable,
    evaluate_ifra,
    load_ifra_table,
    stock_base_name,
)

BASE = {
    "schema_version": "ifra_cat4_table/1",
    "amendment_in_force": 51,
    "category": "4",
    "basis": "percent_w_w_finished_product",
    "library_url": "https://example.test/library",
    "verified_on": "2026-10-08",
    "standards": {
        "STD_A": {
            "name": "Alpha", "cas": ["1-1-1"], "kind": "restriction",
            "cat4_limit_pct": 0.1, "cat4_quote": "Category 4 0.10 %", "notes": [],
        },
        "STD_B": {
            "name": "Beta", "cas": ["2-2-2"], "kind": "restriction_specification",
            "cat4_limit_pct": 0.01, "cat4_quote": "Category 4 0.010 %", "notes": [],
        },
        "STD_SPEC": {"name": "Gamma grade", "kind": "specification", "cat4_limit_pct": None},
        "STD_UNV": {"name": "Delta", "kind": "restriction", "cat4_limit_pct": None},
        "STD_BAN": {"name": "Epsilon", "kind": "prohibition", "cat4_limit_pct": None},
    },
    "materials": {
        "Alpha Absolute": {
            "status": "restricted", "standard": "STD_A", "aliases": ["Alpha", "Alpha  Extract"],
        },
        "Beta Oil": {"status": "restricted", "standard": "STD_B", "aliases": ["Beta"]},
        "Gamma": {"status": "specification", "standard": "STD_SPEC", "aliases": ["Gamma Grade"]},
        "Delta": {"status": "restricted_unverified", "standard": "STD_UNV", "aliases": []},
        "Epsilon": {
            "status": "prohibited", "standard": "STD_BAN", "aliases": ["Eps"],
            "source_url": "https://example.test/ban",
        },
        "Zeta": {"status": "prohibited", "standard": None, "aliases": [], "authority": "EU"},
        "Hedione": {"status": "no_standard", "standard": None, "aliases": ["Hedione HC"]},
        "Rose Absolute": {"status": "natural_no_own_standard", "standard": None, "aliases": []},
    },
    "group_rules": [
        {
            "id": "alpha_beta_total", "standard": "STD_A", "rule": "sum_le_limit",
            "limit_pct": 0.1, "members": ["Alpha Absolute", "Beta Oil"], "quote": "q",
        },
        {
            "id": "alpha_beta_ratio", "standard": "STD_B", "rule": "sum_of_ratios_le_1",
            "limit_pct": None, "members": ["Alpha Absolute", "Beta Oil"], "quote": "q",
        },
    ],
}


def _write(tmp_path, doc):
    path = tmp_path / "table.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _doc(only_groups=None):
    doc = copy.deepcopy(BASE)
    if only_groups is not None:
        doc["group_rules"] = [g for g in doc["group_rules"] if g["id"] in only_groups]
    return doc


@pytest.fixture
def table(tmp_path):
    return load_ifra_table(_write(tmp_path, _doc(only_groups=())))


# ------------------------------------------------------------------ validation


def _mutations():
    def schema(d):
        d["schema_version"] = "ifra_cat4_table/0"

    def status(d):
        d["materials"]["Gamma"]["status"] = "allowed"

    def kind(d):
        d["standards"]["STD_A"]["kind"] = "guideline"

    def rule(d):
        d["group_rules"][0]["rule"] = "max_of"

    def restricted_no_limit(d):
        d["materials"]["Delta"]["status"] = "restricted"

    def restricted_no_standard(d):
        d["materials"]["Hedione"]["status"] = "restricted"

    def bad_quote(d):
        d["standards"]["STD_A"]["cat4_quote"] = "Category 4 0.20 %"

    def unknown_standard(d):
        d["materials"]["Gamma"]["standard"] = "STD_NOPE"

    def alias_shared(d):
        d["materials"]["Beta Oil"]["aliases"].append("alpha   extract")

    def alias_is_other_name(d):
        d["materials"]["Beta Oil"]["aliases"].append("HEDIONE")

    def group_member_unknown(d):
        d["group_rules"][0]["members"].append("Omega")

    def ratio_member_not_restricted(d):
        d["group_rules"][1]["members"].append("Delta")

    def material_own_number(d):
        d["materials"]["Alpha Absolute"]["cat4_limit_pct"] = 0.1

    return [
        (schema, "schema_version"),
        (status, "unknown status"),
        (kind, "unknown kind"),
        (rule, "unknown rule"),
        (restricted_no_limit, "numeric cat4_limit_pct"),
        (restricted_no_standard, "numeric cat4_limit_pct"),
        (bad_quote, "does not state the limit"),
        (unknown_standard, "unknown standard"),
        (alias_shared, "collides"),
        (alias_is_other_name, "collides"),
        (group_member_unknown, "is not a material"),
        (ratio_member_not_restricted, "is not 'restricted'"),
        (material_own_number, "own cat4_limit_pct"),
    ]


@pytest.mark.parametrize(("mutate", "needle"), _mutations(), ids=lambda v: getattr(v, "__name__", v))
def test_invalid_table_is_rejected_with_named_problem(tmp_path, mutate, needle):
    doc = _doc()
    mutate(doc)
    with pytest.raises(ValueError, match=re.escape(needle)):
        load_ifra_table(_write(tmp_path, doc))


def test_quote_must_state_the_restricted_limit(tmp_path):
    doc = _doc()
    doc["standards"]["STD_B"]["cat4_quote"] = "Category 4 limit applies"
    with pytest.raises(ValueError, match="STD_B"):
        load_ifra_table(_write(tmp_path, doc))


@pytest.mark.parametrize("quote", ["Category 4 0.1 %", "Category 4 0.10%", "Category 4 0,100 %"])
def test_quote_number_is_compared_after_normalising(tmp_path, quote):
    doc = _doc()
    doc["standards"]["STD_A"]["cat4_quote"] = quote
    assert load_ifra_table(_write(tmp_path, doc)).materials["Alpha Absolute"].cat4_limit_pct == 0.1


def test_category_number_alone_does_not_satisfy_quote(tmp_path):
    doc = _doc()
    doc["standards"]["STD_A"]["cat4_limit_pct"] = 4
    doc["standards"]["STD_A"]["cat4_quote"] = "Category 4 0.10 %"
    with pytest.raises(ValueError, match="does not state the limit"):
        load_ifra_table(_write(tmp_path, doc))


# ------------------------------------------------------------------ lookup and views


def test_lookup_by_alias_case_and_whitespace(table):
    assert table.lookup("  ALPHA   extract ").name == "Alpha Absolute"
    assert table.lookup("beta").name == "Beta Oil"
    assert table.lookup("hedione hc").name == "Hedione"


def test_lookup_tries_names_in_order_and_skips_empty(table):
    assert table.lookup("", None, "   ", "Unknown", "Eps").name == "Epsilon"
    assert table.lookup("Beta", "Alpha").name == "Beta Oil"
    assert table.lookup("Unknown") is None
    assert table.lookup() is None


def test_material_limit_and_authority_resolve(table):
    assert table.materials["Beta Oil"].cat4_limit_pct == 0.01
    assert table.materials["Delta"].cat4_limit_pct is None
    assert table.materials["Epsilon"].authority == "IFRA"
    assert table.materials["Epsilon"].source_url == "https://example.test/ban"
    assert table.materials["Zeta"].authority == "EU"


def test_cat4_limits_keys_are_restricted_names_and_aliases_as_written(table):
    assert table.cat4_limits() == {
        "Alpha Absolute": 0.1, "Alpha": 0.1, "Alpha  Extract": 0.1,
        "Beta Oil": 0.01, "Beta": 0.01,
    }


def test_prohibited_and_specification_names(table):
    assert table.prohibited_names() == frozenset({"Epsilon", "Eps", "Zeta"})
    assert table.specification_names() == frozenset({"Gamma", "Gamma Grade"})


# ------------------------------------------------------------------ per-row verdicts


@pytest.mark.parametrize(
    ("name", "pct", "verdict"),
    [
        ("Alpha", 0.05, "pass"),
        ("Alpha", 0.07, "warn"),
        ("Alpha", 0.1, "warn"),
        ("Alpha", 0.1000001, "fail"),
        ("Epsilon", 0.0001, "fail"),
        ("Eps", 0.0, "pass"),
        ("Gamma", 1.0, "note"),
        ("Delta", 0.001, "hold"),
        ("Hedione HC", 10.0, "pass"),
        ("Rose Absolute", 0.5, "warn"),
        ("Mystery Base", 0.5, "unchecked"),
    ],
)
def test_each_status_verdict(table, name, pct, verdict):
    (check,) = evaluate_ifra({name: pct}, table=table).checks
    assert check.verdict == verdict
    assert check.material == name


def test_restricted_check_fields_and_message(table):
    (check,) = evaluate_ifra({"Alpha Extract": 0.2}, table=table).checks
    assert check.matched_name == "Alpha Extract"
    assert check.status == "restricted"
    assert check.standard == "STD_A"
    assert check.limit_pct == 0.1
    assert check.ratio == pytest.approx(2.0)
    for part in ("Alpha Extract", "0.2 %", "0.1 %", "STD_A"):
        assert part in check.message


def test_limit_is_inclusive_within_float_tolerance(table):
    (check,) = evaluate_ifra({"Beta": 0.1 * 0.1}, table=table).checks
    assert check.verdict == "warn"


def test_headroom_tightens_the_fail_line(table):
    assert evaluate_ifra({"Alpha": 0.09}, table=table).checks[0].verdict == "warn"
    tight = evaluate_ifra({"Alpha": 0.09}, table=table, headroom=0.8).checks[0]
    assert tight.verdict == "fail"
    assert "headroom" in tight.message


def test_edge_ratio_controls_warning(table):
    assert evaluate_ifra({"Alpha": 0.05}, table=table, edge_ratio=0.5).checks[0].verdict == "warn"
    assert evaluate_ifra({"Alpha": 0.05}, table=table, edge_ratio=0.6).checks[0].verdict == "pass"


def test_alt_names_are_tried_after_the_row_name(table):
    result = evaluate_ifra(
        {"My Moss 10%": 0.02, "Plain": 0.01}, table=table,
        alt_names={"My Moss 10%": ["nothing", "Alpha"], "Plain": "Beta"},
    )
    moss, plain = result.checks
    assert (moss.material, moss.matched_name, moss.verdict) == ("My Moss 10%", "Alpha", "pass")
    assert (plain.matched_name, plain.verdict) == ("Beta", "warn")


def test_evaluation_convenience_tuples(table):
    result = evaluate_ifra(
        {"Alpha": 0.5, "Beta": 0.008, "Delta": 0.1, "Mystery": 1.0, "Gamma": 0.1},
        table=table,
    )
    assert [c.material for c in result.failures] == ["Alpha"]
    assert [c.material for c in result.warnings] == ["Beta"]
    assert [c.material for c in result.holds] == ["Delta"]
    assert [c.material for c in result.unchecked] == ["Mystery"]
    assert [c.material for c in result.notes] == ["Gamma"]
    for check in result.unchecked:
        assert "Mystery" in check.message


# ------------------------------------------------------------------ group rules


def test_sum_rule_fails_when_members_pass_individually(tmp_path):
    tbl = load_ifra_table(_write(tmp_path, _doc(only_groups={"alpha_beta_total"})))
    result = evaluate_ifra({"Alpha": 0.06, "Beta Oil": 0.005}, table=tbl, edge_ratio=0.9)
    assert [c.verdict for c in result.checks] == ["pass", "pass"]
    (group,) = result.group_checks
    assert group.verdict == "pass"
    result = evaluate_ifra({"Alpha": 0.096, "Beta Oil": 0.005}, table=tbl, edge_ratio=1.1)
    assert [c.verdict for c in result.checks] == ["pass", "pass"]
    (group,) = result.group_checks
    assert group.verdict == "fail"
    assert group.member_pcts == {"Alpha Absolute": 0.096, "Beta Oil": 0.005}
    assert group.total == pytest.approx(0.101)
    assert group.limit_pct == 0.1
    assert result.failures == (group,)
    for part in ("alpha_beta_total", "STD_A", "Alpha Absolute", "0.101 %", "0.1 %"):
        assert part in group.message


def test_sum_rule_warns_at_edge_and_respects_headroom(tmp_path):
    tbl = load_ifra_table(_write(tmp_path, _doc(only_groups={"alpha_beta_total"})))
    (group,) = evaluate_ifra({"Alpha": 0.05, "Beta": 0.003}, table=tbl).group_checks
    assert group.verdict == "pass"
    (group,) = evaluate_ifra({"Alpha": 0.065, "Beta": 0.006}, table=tbl).group_checks
    assert group.verdict == "warn"
    (group,) = evaluate_ifra({"Alpha": 0.065, "Beta": 0.006}, table=tbl, headroom=0.7).group_checks
    assert group.verdict == "fail"


def test_ratio_rule_fails_when_members_pass_individually(tmp_path):
    tbl = load_ifra_table(_write(tmp_path, _doc(only_groups={"alpha_beta_ratio"})))
    result = evaluate_ifra({"Alpha": 0.06, "Beta": 0.006}, table=tbl, edge_ratio=0.99)
    assert [c.verdict for c in result.checks] == ["pass", "pass"]
    (group,) = result.group_checks
    assert group.rule == "sum_of_ratios_le_1"
    assert group.total == pytest.approx(1.2)
    assert group.limit_pct is None
    assert group.verdict == "fail"
    (group,) = evaluate_ifra({"Alpha": 0.04, "Beta": 0.004}, table=tbl).group_checks
    assert (group.total, group.verdict) == (pytest.approx(0.8), "warn")
    (group,) = evaluate_ifra({"Alpha": 0.02, "Beta": 0.003}, table=tbl).group_checks
    assert group.verdict == "pass"


def test_group_counts_aliases_and_skips_absent_groups(tmp_path):
    tbl = load_ifra_table(_write(tmp_path, _doc(only_groups={"alpha_beta_total"})))
    (group,) = evaluate_ifra({"alpha extract": 0.08}, table=tbl).group_checks
    assert group.member_pcts == {"Alpha Absolute": 0.08}
    assert evaluate_ifra({"Hedione": 5.0, "Mystery": 1.0}, table=tbl).group_checks == ()


def test_two_rows_of_one_material_are_totalled_against_its_standard(table):
    # A stock suffix no longer hides the second row: it is a second Alpha row in the total.
    result = evaluate_ifra({"Alpha Absolute": 0.06, "Alpha (10% in DPG)": 0.06}, table=table)
    (group,) = result.group_checks
    assert (group.id, group.verdict) == ("STD_A_total", "fail")
    result = evaluate_ifra({"Alpha Absolute": 0.06, "alpha  extract": 0.06}, table=table)
    assert [c.verdict for c in result.checks] == ["pass", "pass"]
    (group,) = result.group_checks
    assert (group.id, group.standard, group.rule) == ("STD_A_total", "STD_A", "sum_le_limit")
    assert group.member_pcts == {"Alpha Absolute": pytest.approx(0.12)}
    assert group.limit_pct == 0.1
    assert result.failures == (group,)


def test_two_materials_under_one_standard_are_totalled(tmp_path):
    doc = _doc(only_groups=())
    doc["materials"]["Alpha Resinoid"] = {"status": "restricted", "standard": "STD_A"}
    tbl = load_ifra_table(_write(tmp_path, doc))
    result = evaluate_ifra({"Alpha Absolute": 0.06, "Alpha Resinoid": 0.06}, table=tbl)
    assert [c.verdict for c in result.checks] == ["pass", "pass"]
    (group,) = result.failures
    assert group.member_pcts == {"Alpha Absolute": 0.06, "Alpha Resinoid": 0.06}
    assert group.total == pytest.approx(0.12)
    single = evaluate_ifra({"Alpha Absolute": 0.06, "Beta Oil": 0.005}, table=tbl)
    assert single.group_checks == ()


def test_explicit_sum_rule_replaces_the_automatic_standard_total(tmp_path):
    tbl = load_ifra_table(_write(tmp_path, _doc(only_groups={"alpha_beta_total"})))
    result = evaluate_ifra({"Alpha Absolute": 0.06, "Alpha": 0.06}, table=tbl)
    (group,) = result.group_checks
    assert group.id == "alpha_beta_total"
    assert group.verdict == "fail"


# ------------------------------------------------------------------ the real data file


def test_real_table_loads_with_seeded_contents():
    tbl = load_ifra_table()
    assert isinstance(tbl, IFRATable)
    assert load_ifra_table() is tbl  # default path is cached
    assert tbl.amendment_in_force == 51
    assert tbl.lookup("oak moss").cat4_limit_pct == 0.1
    assert tbl.lookup("MOC").cat4_limit_pct == 0.01
    assert tbl.lookup("Methyl 2-Octynoate").cat4_limit_pct == 0.047
    assert tbl.lookup("Hedione HC").status == "no_standard"
    assert {g.id for g in tbl.group_rules} == {
        "oakmoss_treemoss_total", "mhc_moc_total", "methyl_ionones_total", "rose_ketones_total",
        "phototoxic_citrus_ratio", "safrole_isosafrole_dihydrosafrole_total",
    }
    assert load_ifra_table(DEFAULT_TABLE_PATH) == tbl


@pytest.mark.parametrize(
    ("name", "status", "limit"),
    [
        ("Treemoss Absolute", "restricted", 0.1),
        ("Coumarin", "restricted", 1.5),
        ("Cinnamaldehyde", "restricted", 0.25),
        ("Hydroxycitronellal", "restricted", 2.1),
        ("Bergamot EO", "restricted", 0.4),
        ("Hedione", "no_standard", None),  # the old 40 % was an internal ceiling, not IFRA
        ("Evernyl", "no_standard", None),  # the old 0.1 % had no IFRA source
        ("Diethyl Phthalate", "no_standard", None),
        ("Bergamot FCF Oil Sicilian", "specification", None),
        ("Birch Tar Rectified", "specification", None),  # only crude birch tar is prohibited
        ("Lilial", "prohibited", None),
        ("Lyral", "prohibited", None),
        ("Tonka Bean Absolute", "natural_no_own_standard", None),
    ],
)
def test_real_table_pins_reviewed_decisions(name, status, limit):
    material = load_ifra_table().lookup(name)
    assert (material.status, material.cat4_limit_pct) == (status, limit)


def test_real_table_eu_bans_name_their_authority_and_source():
    tbl = load_ifra_table()
    for name in ("Lilial", "Lyral"):
        material = tbl.lookup(name)
        assert material.authority.startswith("EU Cosmetics Regulation"), name
        assert material.source_url.startswith("https://"), name


def test_real_table_every_restricted_limit_appears_in_its_standard_quote():
    tbl = load_ifra_table()
    restricted = [m for m in tbl.materials.values() if m.status == "restricted"]
    assert restricted
    for material in restricted:
        std = tbl.standards[material.standard]
        stated = {
            Decimal(n.replace(",", ".")).normalize()
            for n in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", std.cat4_quote)
        }
        assert Decimal(repr(material.cat4_limit_pct)).normalize() in stated, material.name


def test_real_table_mhc_moc_group_catches_combined_excess():
    result = evaluate_ifra({"MHC": 0.04, "MOC": 0.009})
    assert {c.verdict for c in result.checks} == {"warn"}
    (group,) = result.group_checks
    assert (group.id, group.verdict) == ("mhc_moc_total", "fail")


# ------------------------------------------------------------------ stock-name suffixes


@pytest.mark.parametrize(
    ("name", "base"),
    [
        ("Coumarin 20% EtOH", "Coumarin"),
        ("Coumarin (20%)", "Coumarin"),
        ("Coumarin 10 % in DPG", "Coumarin"),
        ("Coumarin 1,5%", "Coumarin"),
        ("Ylang Comoros Complete EO F3255", "Ylang Comoros Complete EO"),
        ("Coumarin 20% (EtOH) F3255", "Coumarin"),
        ("Vetiver EO (India)", "Vetiver EO"),
        ("20%", "20%"),
        ("Aldehyde C10", "Aldehyde C10"),
    ],
)
def test_stock_base_name_strips_strength_parenthetical_and_lot_code(name, base):
    assert stock_base_name(name) == base


@pytest.mark.parametrize(
    ("name", "material"),
    [
        ("Coumarin 20% EtOH", "Coumarin"),
        ("Coumarin (20%)", "Coumarin"),
        ("Oakmoss Absolute 10%", "Oakmoss Absolute"),
        ("Ylang Comoros Complete EO F3255", "Ylang Ylang EO"),
        ("Ethanol 96%", "Ethanol"),
        ("Vetiver EO (India)", "Vetiver EO (India)"),
    ],
)
def test_real_table_lookup_sees_through_stock_suffixes(name, material):
    assert load_ifra_table().lookup(name).name == material


def test_a_bare_strength_matches_nothing():
    assert load_ifra_table().lookup("20%") is None


def test_exact_alt_name_wins_over_the_stripped_row_name():
    # Stripped, the row would be the generic "Vetiver EO"; its exact alt name is the Indian oil.
    result = evaluate_ifra({"Vetiver EO 10%": 0.5}, alt_names={"Vetiver EO 10%": "Vetiver EO (India)"})
    (check,) = result.checks
    assert check.matched_name == "Vetiver EO (India)"
    assert load_ifra_table().lookup("Vetiver EO 10%", "Vetiver EO (India)").name == "Vetiver EO (India)"


# ------------------------------------------------- least-stripped form wins


@pytest.mark.parametrize(
    "name",
    ["Vetiver EO (Haiti) 10%", "Vetiver EO (Haiti) F3255", "Vetiver EO 10% (Haiti)"],
)
def test_a_qualified_name_with_a_suffix_finds_its_specific_entry(name):
    table = load_ifra_table()
    specific = table.lookup("Vetiver EO (Haiti)")
    assert specific is not None
    assert table.lookup(name) is specific
    assert specific is not table.lookup("Vetiver EO")


def test_cinnamon_bark_telvada_with_a_strength_finds_its_entry():
    table = load_ifra_table()
    specific = table.lookup("Cinnamon Bark EO (Telvada)")
    assert specific is not None
    assert table.lookup("Cinnamon Bark EO (Telvada) 10%") is specific


def test_evaluate_ifra_reports_the_specific_entry_for_a_suffixed_row():
    result = evaluate_ifra({"Vetiver EO (Haiti) 10%": 0.5})
    (check,) = result.checks
    assert check.ifra_name == "Vetiver EO (Haiti)"
