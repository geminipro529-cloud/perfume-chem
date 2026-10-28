"""IFRA batch, 25 Oct 2026 (stock thread). Kenny: "parse all the information that is
missing into the engine". Every owned stock the Category 4 table could not recognise got a
row, except Orange Flower Absolute (Kenny: "Keep the hold"; lifted 28 Oct, "Use orange flower
absolute freely") and the bases and extracts whose
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


def test_diluted_product_certificates_are_scaled_to_the_neat_material():
    rows = [r for r in RAW["rows"] if "printed_for_dilution_pct" in r]
    dilution = {r["ncs_name"].split(",")[0]: r["printed_for_dilution_pct"] for r in rows}
    assert dilution == {
        "Ambrette seed absolute": 10.0, "Frangipani absolute": 10.0, "Tobacco absolute": 10.0,
        "Vanilla absolute": 10.0, "Siam benzoin resinoid": 50.0,
        # 2026-10-28: Kenny's Orange Flower Absolute 10% in DPG (5NC07544), hold lifted.
        "Orange flower absolute": 10.0,
    }
    for row in rows:
        factor = 100.0 / row["printed_for_dilution_pct"]
        assert row["max_pct"] == pytest.approx(float(row["max_pct_as_printed"]) * factor)


def test_other_lot_and_sds_rows_say_where_they_come_from():
    kinds = {r.get("source_kind") for r in RAW["rows"]}
    assert {
        "supplier_ifra_certificate", "supplier_ifra_certificate_other_lot",
        "supplier_ifra_certificate_reference_product",
        "supplier_sds_band_upper_bound", "supplier_product_page", "reseller_ifra_sheet",
    } <= kinds
    for row in RAW["rows"]:
        if row.get("source_kind") == "supplier_ifra_certificate_other_lot":
            assert "another supplier's lot" in row["note"]
            assert row["source_url"].startswith("https://shop.perfumersapprentice.com/")
        if row.get("source_kind") == "supplier_sds_band_upper_bound":
            assert "Upper bound" in row["note"]
        if row.get("source_kind") == "supplier_ifra_certificate_reference_product":
            assert "the supplier of Kenny's bottle is not recorded" in row["note"]
            assert row["source_url"].startswith("https://www.perfumersworld.com/")


def test_bases_without_a_composition_stay_flagged_and_castoreum_is_unchanged():
    names = {b.name for b in load_undisclosed_bases()}
    assert names == {
        "Castoreum Synthetic", "Costus Olifac", "Lilyreal ND",
        "Cabbage Rose Extract", "Iris Florentina Root Extract", "Magnolia Flower Extract",
    }
    # Kenny: "Keep warning". Castoreum Synthetic keeps no table row and no certificate rows.
    assert TABLE.lookup("Castoreum Synthetic") is None
    assert "Castoreum Synthetic" not in RAW["stocks"]


def test_orange_flower_absolute_warns_with_its_prohibited_traces():
    # Kenny, 28 Oct 2026 12:37 UTC: "Use orange flower absolute freely" (his 25 Oct hold lifted).
    material = TABLE.lookup("Orange Flower Absolute 10% in DPG")
    assert material is not None and material.status == "natural_no_own_standard"
    assert "benzyl cyanide" in material.identity_note and "7-methoxycoumarin" in material.identity_note
    assert RAW["unmapped_owned_naturals"] == {}
    [row] = evaluate_ifra({"Orange Flower Absolute 10% in DPG": 1.0}).checks
    assert row.verdict == "warn"
    assert "Farnesol up to 8 %" in row.message and "not a block" in row.message


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


# Second pass: recognised stocks whose PerfumersWorld certificate prints a restricted
# constituent above the counted rows. Each limit equals the Category 4 figure PerfumersWorld
# prints on that certificate, where it prints one below its 25 % ceiling.
SECOND_PASS_LIMITS = [
    # 7SB00041: estragole 15.3291 % against 0.014 % (PerfumersWorld prints 0.09 %).
    ("Anise EO", 0.014 / 0.153291),
    # 7KQ07511: longifolene 8.8795 % against 1.5 % (PerfumersWorld prints 16.89 %).
    ("Pine EO", 1.5 / 0.088795),
    # 7IS00086: asarone 0.2818 % against the 0.01 % note box (PerfumersWorld prints 3.55 %).
    ("Carrot Seed EO", 0.01 / 0.002818),
    # Annex I elemi oil's methyl eugenol 0.4 % stays above 7QC00902's 0.3068 % (PW prints 3.59 %).
    ("Elemi EO", 0.011 / 0.004),
    # 8RM00395: methyl eugenol 0.709 % against 0.011 % (PerfumersWorld prints 1.55 %).
    ("Rose de Mai Absolute", 0.011 / 0.00709),
]


@pytest.mark.parametrize(("stock", "limit"), SECOND_PASS_LIMITS)
def test_certificate_constituents_now_bind_recognised_stocks(stock, limit):
    status, value = single_material_limit_pct(stock)
    assert status == "restricted"
    assert value == pytest.approx(limit, rel=1e-6)


def test_asarone_standard_is_the_note_box_limit():
    standard = TABLE.standards["IFRA_STD_110"]
    assert standard.name == "cis- and trans-Asarone"
    assert standard.cat4_limit_pct == 0.01
    assert "100ppm (0.01 %)" in standard.cat4_quote


def test_own_standards_stay_stricter_than_their_certificates():
    # Jasmine grandiflorum (0.6 %) and Peru balsam (0.41 %) keep their own standards' limits.
    assert single_material_limit_pct("Jasmine Absolute") == ("restricted", pytest.approx(0.6))
    assert single_material_limit_pct("Peru Balsam Resinoid") == ("restricted", pytest.approx(0.41))
