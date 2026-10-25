"""Seven IFRA standards that were missing (carvone, alpha-bisabolol, cuminaldehyde, perilla
aldehyde, 2-methoxy-4-propylphenol, 2-hexenal, thujone), their Annex I rows for owned
naturals, supplier-certificate rows, and Heliotropal split from Heliotropin (25 Oct 2026)."""

from __future__ import annotations

import json

import pytest

from engine.ifra_standards import (
    DEFAULT_CONSTITUENTS_PATH,
    evaluate_ifra,
    load_ifra_table,
    load_natural_constituents,
    single_material_limit_pct,
)

TABLE = load_ifra_table()
RAW = json.loads(DEFAULT_CONSTITUENTS_PATH.read_text(encoding="utf-8"))


def _group(evaluation, standard):
    return next(g for g in evaluation.group_checks if g.id == f"{standard}_constituents")


@pytest.mark.parametrize(
    ("standard", "name", "limit"),
    [
        ("IFRA_STD_016", "Carvone", 0.59),
        ("IFRA_STD_192", "alpha-Bisabolol", 2.4),
        ("IFRA_STD_024", "Cuminaldehyde", 0.47),
        ("IFRA_STD_052", "Perilla aldehyde", 0.30),
        ("IFRA_STD_191", "2-Methoxy-4-propylphenol", 0.73),
        ("IFRA_STD_039", "2-Hexenal", 0.0077),
        ("IFRA_STD_102", "Thujone", 1.4),
    ],
)
def test_the_seven_standards_carry_their_category_4_limits(standard, name, limit):
    std = TABLE.standards[standard]
    assert std.name == name
    assert std.cat4_limit_pct == pytest.approx(limit)


def test_caraway_fails_on_its_carvone_and_passes_below_the_limit():
    # Annex I: caraway seed oil up to 59 % carvone; 0.59 % / 0.59 = 1 % of the product.
    status, limit = single_material_limit_pct("Caraway Seed EO 10% in DPG")
    assert status == "restricted"
    assert limit == pytest.approx(1.0)
    over = evaluate_ifra({"Caraway Seed EO": 1.59})
    assert _group(over, "IFRA_STD_016").verdict == "fail"
    assert _group(over, "IFRA_STD_016").total == pytest.approx(1.59 * 0.59)
    assert _group(evaluate_ifra({"Caraway Seed EO": 0.5}), "IFRA_STD_016").verdict == "pass"


def test_blue_chamomile_counts_its_annex_alpha_bisabolol():
    [total] = evaluate_ifra({"Blue Chamomile EO": 10.0}).constituent_totals
    assert total.standard == "IFRA_STD_192"
    assert total.total == pytest.approx(0.4)  # 10 % x 4 % (Annex I, Matricaria chamomilla)


def test_cabreuva_takes_the_higher_certificate_levels():
    levels = load_natural_constituents().stocks["Cabreuva EO"]
    assert levels["IFRA_STD_192"][0] == pytest.approx(4.6708)  # certificate, above Annex I 2
    assert levels["IFRA_STD_036"][0] == pytest.approx(2.1867)  # certificate, above Annex I 0.1
    assert "7LW00863" in levels["IFRA_STD_192"][1]


def test_thujone_and_propylphenol_come_from_their_naturals():
    stocks = load_natural_constituents().stocks
    assert stocks["Juniper Berry EO"]["IFRA_STD_102"][0] == pytest.approx(0.05)
    assert stocks["Birch Tar Rectified"]["IFRA_STD_191"][0] == pytest.approx(0.9)
    assert stocks["Cade Oil Rectified"]["IFRA_STD_191"][0] == pytest.approx(0.5)


def test_heliotropal_is_its_own_compound_not_heliotropin():
    for name in ("Heliotropal", "Heliotropal (neat)", "Heliotropal (Piperonal)", "Heliotropal 10%"):
        assert TABLE.lookup(name).name == "Heliotropal", name
    for name in ("Heliotropin", "Piperonal"):
        assert TABLE.lookup(name).name == "Heliotropin", name
    assert single_material_limit_pct("Heliotropin") == ("no_standard", None)
    # Its certificate coumarin (4.1584 %) binds: 1.5 / 0.041584.
    status, limit = single_material_limit_pct("Heliotropal (neat)")
    assert status == "restricted"
    assert limit == pytest.approx(1.5 / 0.041584)


def test_heliotropal_coumarin_adds_to_synthetic_coumarin():
    evaluation = evaluate_ifra({"Heliotropal (neat)": 12.1, "Coumarin": 1.21})
    group = _group(evaluation, "IFRA_STD_023")
    assert group.verdict == "fail"
    assert group.total == pytest.approx(1.21 + 12.1 * 0.041584)
    row = next(c for c in evaluation.checks if c.material == "Heliotropal (neat)")
    assert "not pure piperonal" in row.message


def test_every_certificate_row_names_its_perfumersworld_document():
    rows = [r for r in RAW["rows"] if r.get("source_kind") == "supplier_ifra_certificate"]
    assert len(rows) > 5
    for row in rows:
        assert "certificate" in row["ncs_name"]
        assert row["source_url"].startswith("https://www.perfumersworld.com/document-list.php")
        assert row["note"].startswith("Not an Annex I row.")
        # A 10% product's certificate is printed for the dilution; the row holds the neat level.
        scale = 100.0 / row.get("printed_for_dilution_pct", 100.0)
        assert float(row["max_pct_as_printed"]) * scale == pytest.approx(row["max_pct"])


def test_two_hexenal_has_no_annex_rows_and_thujone_rows_are_not_double_counted():
    # Only supplier certificates (Lavandin, Pamzest) give 2-hexenal levels.
    assert not [r for r in RAW["rows"] if r["standard"] == "IFRA_STD_039" and "source_kind" not in r]
    thujone = [r for r in RAW["rows"] if r["standard"] == "IFRA_STD_102"]
    assert len({r["ncs_name"] for r in thujone}) == len(thujone)
