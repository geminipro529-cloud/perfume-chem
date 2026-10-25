"""IFRA batch, 25 Oct 2026 (stock thread). Kenny: "parse all the information that is
missing into the engine". Every owned stock the Category 4 table could not recognise got a
row, except Orange Flower Absolute (Kenny: "Keep the hold") and the bases and extracts whose
composition is not published (flagged, never blocked). Values come from the IFRA standards
and Annex I, from PerfumersWorld's certificates for Kenny's own SKUs, from SDS section 3
bands where a certificate leaves a restricted substance out, and, for bottles with no
certificate of their own, from another supplier's certificate; a second reader re-opened
each source.
"""

from __future__ import annotations

import json

import pytest

from engine.ifra_standards import (
    DEFAULT_CONSTITUENTS_PATH,
    evaluate_ifra,
    load_ifra_table,
    load_undisclosed_bases,
    single_material_limit_pct,
)

TABLE = load_ifra_table()
RAW = json.loads(DEFAULT_CONSTITUENTS_PATH.read_text(encoding="utf-8"))

NEW_STANDARDS = {
    "IFRA_STD_202": ("Farnesal", 0.6),
    "IFRA_STD_194": ("p-Isopropylbenzyl alcohol", 2.5),
    "IFRA_STD_079": ("Tea leaf absolute", 0.21),
    "IFRA_STD_027": ("Dibenzyl ether", 0.012),
    "IFRA_STD_260": ("p-Cresol", 0.005),
    "IFRA_STD_098": ("Furfural", 0.001),
    "IFRA_STD_199": ("Longifolene", 1.5),
    "IFRA_STD_061": ("6-Methyl-3,5-heptadien-2-one", 0.047),
}


@pytest.mark.parametrize(("sid", "name", "limit"), [(k, *v) for k, v in NEW_STANDARDS.items()])
def test_new_standard_carries_its_category_4_limit(sid, name, limit):
    standard = TABLE.standards[sid]
    assert (standard.name, standard.cat4_limit_pct, standard.kind) == (name, limit, "restriction")
    assert standard.url.endswith(f"{sid}.pdf")


# Highest finished-product % at which the stock alone passes Category 4, and what binds it.
LIMITS = [
    # PerfumersWorld 8FB00063 (neat): dibenzyl ether 0.1815 % against 0.012 %.
    ("Blackcurrant Absolute", 0.012 / 0.001815),
    # PerfumersWorld 3RB07724: geraniol 47.1666 % against 4.7 % (its own 9.96 %).
    ("Rhodinol ex Citronella", 4.7 / 0.471666),
    # PerfumersWorld's product page: about 30 % benzyl benzoate, against 4.8 %.
    ("Olibanum Resinoid", 4.8 / 0.30),
    # Plant part unknown: clove stem oil's 88 % eugenol (Annex I) against 2.5 %.
    ("Clove EO (India)", 2.5 / 0.88),
    # SDS band: isoeugenol up to 1.0 % against 0.11 %.
    ("Tuberlia Base", 0.11 / 0.010),
    # SDS band: Sandalore up to 10 % against 1.2 %.
    ("Sandalwood Base X3", 1.2 / 0.10),
    # Grapefruit oil's CAS on PerfumersWorld's SDS: IFRA_STD_091's 4 %.
    ("Pomelo EO", 4.0),
    # PerfumersWorld 6CN23709: 2-hexenal 0.0556 % against 0.0077 % (its own 13.85 %).
    ("Pamzest", 0.0077 / 0.000556),
    # PerfumersWorld 2QV08253: benzyl benzoate 89.2386 % against 4.8 %.
    ("Benzoin Sumatra Resinoid", 4.8 / 0.892386),
    # PerfumersWorld 8HY00554: coumarin 7.0 % against 1.5 %.
    ("Lavandin Absolute", 1.5 / 0.07),
    # SDS band: farnesol up to 10 % against 1.2 %.
    ("Neroli EO", 1.2 / 0.10),
    # PerfumersWorld 8HE00557: 6-methyl-3,5-heptadien-2-one 0.2256 % against 0.047 %.
    ("Mate Absolute", 0.047 / 0.002256),
    # Annex I: citral 40 % in terpeneless lemon oil against 0.6 %.
    ("Lemon Terpeneless Oil Sicilian", 0.6 / 0.40),
]


@pytest.mark.parametrize(("stock", "limit"), LIMITS)
def test_stock_alone_is_limited_by_its_recorded_constituent(stock, limit):
    status, value = single_material_limit_pct(stock)
    assert status == "restricted"
    assert value == pytest.approx(limit, rel=1e-6)


@pytest.mark.parametrize(
    "stock",
    [
        "Ambrette Seed Absolute", "Anisyl Acetate", "Black Agarwood Artificial",
        "Black Tea Base", "Cassis Base 345B", "Cedroxyde", "Cedryl Acetate", "Clearwood",
        "Cocoa Absolute", "Dihydrojasmone", "Ethyl Acetoacetate", "Ethyl Butyrate",
        "Frangipani Absolute", "Fructone B", "Ginger Lily Oil", "Jessemal", "Neryl Acetate",
        "Orris Butter 50% in EtOH", "Orris Concrete Orris Butter", "Palm Dates Base",
        "Phenyl Ethyl Dimethyl Carbinyl Acetate", "Red Saffron Infusion", "Vanilla Absolute",
        "Vertofix", "Vertofix Coeur",
    ],
)
def test_previously_held_stock_is_recognised(stock):
    assert TABLE.lookup(stock) is not None, stock


def test_ten_percent_certificates_are_scaled_to_the_neat_material():
    rows = [r for r in RAW["rows"] if "printed_for_dilution_pct" in r]
    assert {r["ncs_name"].split(",")[0] for r in rows} == {
        "Ambrette seed absolute", "Frangipani absolute", "Tobacco absolute", "Vanilla absolute",
    }
    for row in rows:
        assert row["printed_for_dilution_pct"] == 10.0
        assert row["max_pct"] == pytest.approx(float(row["max_pct_as_printed"]) * 10)


def test_other_lot_and_sds_rows_say_where_they_come_from():
    kinds = {r.get("source_kind") for r in RAW["rows"]}
    assert {
        "supplier_ifra_certificate", "supplier_ifra_certificate_other_lot",
        "supplier_sds_band_upper_bound", "supplier_product_page", "reseller_ifra_sheet",
    } <= kinds
    for row in RAW["rows"]:
        if row.get("source_kind") == "supplier_ifra_certificate_other_lot":
            assert "another supplier's lot" in row["note"]
            assert row["source_url"].startswith("https://shop.perfumersapprentice.com/")
        if row.get("source_kind") == "supplier_sds_band_upper_bound":
            assert "Upper bound" in row["note"]


def test_bases_without_a_composition_stay_flagged_and_castoreum_is_unchanged():
    names = {b.name for b in load_undisclosed_bases()}
    assert names == {
        "Suederal", "Castoreum Synthetic", "Costus Olifac", "Lilyreal ND",
        "Cabbage Rose Extract", "Iris Florentina Root Extract", "Magnolia Flower Extract",
    }
    # Kenny: "Keep warning". Castoreum Synthetic keeps no table row and no certificate rows.
    assert TABLE.lookup("Castoreum Synthetic") is None
    assert "Castoreum Synthetic" not in RAW["stocks"]


def test_orange_flower_absolute_keeps_its_hold():
    assert TABLE.lookup("Orange Flower Absolute") is None
    assert "Orange Flower Absolute" not in RAW["stocks"]
    assert "Kenny's decision" in RAW["unmapped_owned_naturals"]["Orange Flower Absolute"]


def test_kenyan_myrrh_names_the_opoponax_limit_without_applying_it():
    [row] = evaluate_ifra({"Kenyan Myrrh Ethanol Tincture": 1.0}).checks
    assert row.verdict == "warn"
    assert "IFRA_STD_070 limits it to 0.43 %" in row.message
    assert single_material_limit_pct("Kenyan Myrrh Ethanol Tincture") == (
        "natural_no_own_standard", None
    )


def test_birch_tar_row_carries_the_certificate_cap_for_kennys_sku():
    [row] = evaluate_ifra({"Birch Tar Rectified": 0.05}).checks
    assert "5TP11094" in row.message and "0.1 % of that stock" in row.message


def test_pomelo_joins_the_phototoxic_citrus_sum():
    group = next(g for g in TABLE.group_rules if g.id == "phototoxic_citrus_ratio")
    assert "Pomelo EO" in group.members
    evaluation = evaluate_ifra({"Pomelo EO": 2.0, "Lime Oil Expressed": 0.35})
    ratio = next(g for g in evaluation.group_checks if g.id == "phototoxic_citrus_ratio")
    assert ratio.total == pytest.approx(2.0 / 4.0 + 0.35 / 0.7)
