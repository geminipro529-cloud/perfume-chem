"""Restricted substances inside owned naturals count toward their Category 4 limits.

Levels come from IFRA Amendment 49 Annex I (data/regulatory/ifra_annex1_constituents.json):
a natural adds pct x level / 100 to the substance's total, summed with synthetic rows.
"""

import json

import pytest

from engine.ifra_standards import (
    DEFAULT_CONSTITUENTS_PATH,
    evaluate_ifra,
    load_ifra_table,
    load_natural_constituents,
)
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, _gate_safety

TABLE = load_ifra_table()
RAW = json.loads(DEFAULT_CONSTITUENTS_PATH.read_text(encoding="utf-8"))


def _gate(ingredients):
    state = build_formula_state(
        ingredients, {name: 1.0 for name in ingredients}, batch_volume_ml=30.0
    )
    return _gate_safety(state, ReleaseGateConfig(batch_volume_source="title"))


def _total(gate, standard):
    return next(t for t in gate.data["constituent_totals"] if t["standard"] == standard)


def test_tonka_alone_fails_on_coumarin():
    gate = _gate({"Tonka Bean Absolute": 950.0, "Evernyl": 240.0})

    assert gate.status == "FAIL"
    total = _total(gate, "IFRA_STD_023")
    assert total["substance"] == "Coumarin"
    [tonka] = total["contributors"]
    assert tonka["material"] == "Tonka Bean Absolute"
    assert tonka["kind"] == "natural"
    assert tonka["constituent_pct"] == 79.133  # PerfumersWorld certificate, above Annex I 46.7
    assert 3.5 < tonka["pct"] < 4.5
    assert tonka["contribution_pct"] == pytest.approx(tonka["pct"] * 0.79133)
    assert total["total_pct"] > 1.5
    group = next(v for v in gate.data["violations"] if v["group"] == "IFRA_STD_023_constituents")
    assert group["members"] == {"Tonka Bean Absolute": tonka["contribution_pct"]}
    assert "Coumarin" in gate.detail and "Tonka Bean Absolute" in gate.detail
    row = next(r for r in gate.data["rows"] if r["material"] == "Tonka Bean Absolute")
    assert row["verdict"] == "warn"
    assert "counted toward their Category 4 totals: Coumarin up to 79.13 %" in row["message"]


def test_natural_and_synthetic_eugenol_add_up():
    rose = {"Rose de Mai Absolute": 4500.0, "Evernyl": 240.0}
    eugenol = {"Eugenol": 520.0, "Evernyl": 240.0}
    # Each alone stays under the 2.5 % eugenol limit.
    assert _total(_gate(rose), "IFRA_STD_035")["total_pct"] < 2.5
    assert not [r for r in _gate(eugenol).data["rows"] if r["verdict"] == "fail"]

    gate = _gate({**rose, **eugenol})
    assert gate.status == "FAIL"
    total = _total(gate, "IFRA_STD_035")
    members = {c["material"]: c for c in total["contributors"]}
    assert set(members) == {"Eugenol", "Rose de Mai Absolute"}
    assert members["Eugenol"]["kind"] == "synthetic"
    assert members["Eugenol"]["contribution_pct"] < 2.5
    assert members["Rose de Mai Absolute"]["constituent_pct"] == 2.3
    assert total["total_pct"] == pytest.approx(
        sum(c["contribution_pct"] for c in total["contributors"])
    )
    assert total["total_pct"] > 2.5
    failed = [f["group"] for f in gate.data["headroom_violations"] if "group" in f]
    # Rose de Mai Absolute's methyl eugenol (0.709 % on PerfumersWorld's certificate) and its
    # certificate's isoeugenol (1.9907 % as printed) also exceed their own limits.
    assert failed == [
        "IFRA_STD_035_constituents", "IFRA_STD_048_constituents", "IFRA_STD_100_constituents",
    ]
    # Counted once: the synthetic-only eugenol total is not also built.
    assert "IFRA_STD_035_total" not in [g["group"] for g in gate.data["groups"]]


def test_two_synthetic_rows_still_total_without_a_natural():
    evaluation = evaluate_ifra({"Eugenol": 1.5, "Eugenol 10% in DPG": 1.5})
    group = next(g for g in evaluation.group_checks if g.id == "IFRA_STD_035_total")
    assert group.verdict == "fail"
    assert evaluation.constituent_totals == ()


# Gate result at 7dea1163 (before naturals' constituents were counted) for a formula
# with no mapped natural: Black Pepper EO is a natural with no Annex I mapping.
# 22 Oct 2026: Black Pepper EO got a sourced density (Biolandes spec), so the
# density/carrier assumptions drop from 3 to 2 and its 100 uL weighs 0.877 g/mL
# instead of the 1.0 fallback (0.421 % -> 0.3694 %); the verdicts are unchanged.
# 25 Oct 2026: Black Pepper EO's constituents are now counted from another supplier's
# certificate, so the unmapped natural here is Spike Lavender EO (0.3753 %; coumarin
# 0.08423 % with its density); the verdicts are unchanged.
BASE_NO_MAPPED_NATURAL = {
    "status": "WARN",
    "detail": (
        "1 natural(s) without their own IFRA standard (constituents not summed); 2 EU "
        "allergen declarations; basis finished_product_w_w_estimate (2 density/carrier "
        "assumption(s))"
    ),
    "rows": [
        ("Coumarin", "pass",
         "Coumarin at 0.08423 % is within the IFRA Category 4 limit of 1.5 % (IFRA_STD_023)."),
        ("Eugenol", "pass",
         "Eugenol at 0.1344 % is within the IFRA Category 4 limit of 2.5 % (IFRA_STD_035)."),
        ("Evernyl", "pass",
         "Evernyl (Evernyl Crystals) at 1.011 % has no IFRA standard of its own."),
        ("Spike Lavender EO", "warn",
         "Spike Lavender EO at 0.3753 % is a natural with no IFRA standard of its own; its "
         "restricted constituents are not summed here."),
    ],
    "groups": [],
}


def test_formula_without_a_mapped_natural_is_unchanged():
    assert "Spike Lavender EO" not in RAW["stocks"]
    gate = _gate({"Coumarin": 20.0, "Eugenol": 30.0, "Spike Lavender EO": 100.0, "Evernyl": 240.0})

    assert gate.status == BASE_NO_MAPPED_NATURAL["status"]
    assert gate.detail == BASE_NO_MAPPED_NATURAL["detail"]
    rows = [(r["material"], r["verdict"], r["message"]) for r in gate.data["rows"]]
    assert rows == [tuple(r) for r in BASE_NO_MAPPED_NATURAL["rows"]]
    assert gate.data["groups"] == BASE_NO_MAPPED_NATURAL["groups"]
    assert gate.data["constituent_totals"] == []
    assert f"{len(load_natural_constituents().standards)} substances" in gate.data["constituent_coverage"]
    assert "not been checked by a person" in gate.data["constituent_coverage"]


@pytest.mark.parametrize("stock", sorted(RAW["stocks"]))
def test_every_mapped_stock_resolves_and_names_known_rows(stock):
    ncs_names = {row["ncs_name"] for row in RAW["rows"]}
    assert set(RAW["stocks"][stock]["ncs_names"]) <= ncs_names
    for name in (stock, f"{stock} 10% in DPG", f"{stock} 20% EtOH"):
        material = TABLE.lookup(name)
        assert material is not None and material.name == stock, name
    assert stock in load_natural_constituents().stocks


def test_diluted_tonka_stock_name_is_counted():
    evaluation = evaluate_ifra({"Tonka Bean Absolute 10% in DPG": 2.0})
    totals = {t.standard: t.total for t in evaluation.constituent_totals}
    # Coumarin, plus phenylacetaldehyde from PerfumersWorld's 8VQ00445 certificate.
    assert set(totals) == {"IFRA_STD_023", "IFRA_STD_073"}
    assert totals["IFRA_STD_023"] == pytest.approx(2.0 * 0.79133)


def test_candidate_rows_take_the_highest_level_not_the_sum():
    loaded = load_natural_constituents().stocks
    several = 0
    for stock, rec in RAW["stocks"].items():
        by_standard: dict[str, list[float]] = {}
        for row in RAW["rows"]:
            if row["ncs_name"] in rec["ncs_names"]:
                by_standard.setdefault(row["standard"], []).append(row["max_pct"])
        assert {sid: lv[0] for sid, lv in loaded[stock].items()} == {
            sid: max(levels) for sid, levels in by_standard.items()
        }
        several += sum(1 for levels in by_standard.values() if len(levels) > 1)
    assert several > 0  # some stock has several candidate rows for one substance


def test_no_mapped_stock_also_counts_its_own_standard_as_a_constituent():
    # A stock restricted under a standard would enter that total twice if one of its own
    # constituent rows named the same standard: once as a synthetic member and once
    # through its constituent level. (Rhodinol ex Citronella counts whole as citronellol
    # under IFRA_STD_022, and its certificate rows leave citronellol out.)
    data = load_natural_constituents()
    for stock, levels in data.stocks.items():
        material = TABLE.lookup(stock)
        assert material is not None
        assert material.standard is None or material.standard not in levels, stock


def test_rhodinol_counts_citronellol_once_and_geraniol_from_its_certificate():
    evaluation = evaluate_ifra({"Rhodinol ex Citronella": 2.0, "Cassis Base 345B": 5.0})
    citronellol = next(t for t in evaluation.constituent_totals if t.standard == "IFRA_STD_022")
    assert {c.material: c.kind for c in citronellol.contributors} == {
        "Rhodinol ex Citronella": "synthetic",
        "Cassis Base 345B": "natural",
    }
    assert citronellol.total == pytest.approx(2.0 + 5.0 * 0.03)
    geraniol = next(t for t in evaluation.constituent_totals if t.standard == "IFRA_STD_037")
    assert geraniol.total == pytest.approx(2.0 * 0.471666 + 5.0 * 0.00021)


def test_compliance_check_says_where_mapped_constituents_are_counted():
    from engine.safety.regulatory import check_compliance, make_snapshot

    snapshot = make_snapshot(
        jurisdiction="EU",
        product_category="Cat4",
        rule_set="IFRA_51st_2025",
        effective_date="2025-01-01",
    )
    [tonka, spike] = check_compliance(
        [
            {"name": "Tonka Bean Absolute", "active_ul": 300.0, "finished_product_volume_ml": 30.0},
            {"name": "Spike Lavender EO", "active_ul": 300.0, "finished_product_volume_ml": 30.0},
        ],
        jurisdiction="EU",
        product_category="Cat4",
        snapshot=snapshot,
    )
    assert "release gate's IFRA check counts its IFRA Annex I constituents" in tonka.detail
    assert "its restricted constituents are not summed here." in spike.detail


def test_optimizer_repairs_a_natural_driven_constituent_total():
    from engine.optimizer.gate_aware import optimize_until_release_ready

    config = ReleaseGateConfig(
        expected_concentrate_ul=6000.0,
        batch_volume_ml=30.0,
        brief="generic",
        allow_preblends=True,
        min_confidence_score=0.0,
        audit_enabled=False,
    )
    # Cinnamon bark oil has no IFRA standard of its own; the cinnamal it carries
    # (Annex I, up to 95 %) takes the cinnamal total over its limit, so only the
    # constituent total can fail. (Tonka Bean Absolute, the earlier example, is a 10%
    # stock that is now ready to dose, so its coumarin is counted at 10% strength and
    # can no longer reach 1.5 %.)
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 25.0,
        "Zenolide": 12.0,
        "Linalool": 8.0,
        "Phenyl Ethyl Alcohol": 10.0,
        "Cinnamon Bark EO (Telvada)": 2.0,
    }
    pool = {"Iso E Super": 2.0, "Hedione": 1.0}

    def safety(result):
        return {g.gate: g for g in result.gate_report.gates}["safety_ifra_allergen"]

    start = optimize_until_release_ready(
        "Cinnamon Constituent Test", raw_pct, config=config, repair_pool=pool, max_passes=0
    )
    assert safety(start).status == "FAIL"
    assert [v["material"] for v in safety(start).data["headroom_violations"]] == [
        "IFRA_STD_018_constituents"
    ]

    result = optimize_until_release_ready(
        "Cinnamon Constituent Test", raw_pct, config=config, repair_pool=pool
    )
    caps = [a for a in result.repair_actions if a.action == "cap_ifra_finished_product_limit"]
    assert safety(result).status != "FAIL"
    assert {a.material for a in caps} == {"Cinnamon Bark EO (Telvada)"}
    total = next(
        t for t in safety(result).data["constituent_totals"] if t["standard"] == "IFRA_STD_018"
    )
    assert total["total_pct"] <= total["limit_pct"]
