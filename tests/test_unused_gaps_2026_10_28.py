"""Groups 1-4 of the least-used report (28 Oct 2026): sourced fixes, labelled threshold estimates and
Kenny's bottle answers from the "Fix gaps in unused materials" thread. Every source was re-opened
before loading. These pin the data and its sources; they make no sensory claim."""

from __future__ import annotations

import pytest

from engine import inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.ifra_standards import load_natural_constituents
from engine.inventory_parser import parse_current_inventory
from engine.odor_thresholds import ODT_DATA, ODT_VERIFICATION, lookup_odt_raw_name
from engine.skin_interaction import SKIN_PHYSCHEM


@pytest.fixture(scope="module")
def records():
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    return {r["record_id"]: r for r in overlay["delta_records"]}


@pytest.fixture(scope="module")
def stocks():
    return parse_current_inventory(unique=False)


def test_undecavertol_is_owned_neat_and_at_one_percent(records, stocks):
    record = records["INV-USER-20261014-STK-189"]
    assert record["source_quote"] == "I have both neat and 1%"
    rows = {s.name: s for s in stocks if s.name.startswith("Undecavertol")}
    assert (rows["Undecavertol"].dilution, rows["Undecavertol"].execution_ready) == (1.0, True)
    assert (rows["Undecavertol 1%"].dilution, rows["Undecavertol 1%"].carrier) == (0.01, "dpg")


def test_cedryl_acetate_leaves_its_intake_hold_as_a_neat_liquid(records, stocks):
    record = records["INV-USER-20261014-STK-190"]
    assert record["source_quote"] == "Liquid"
    assert record["stock"]["execution_basis"].startswith("INV-USER-20261007-PW-034_INTAKE_HOLD_CLEARED")
    (stock,) = [s for s in stocks if s.name == "Cedryl Acetate"]
    assert (stock.dilution, stock.execution_ready) == (1.0, True)


def test_kenyan_myrrh_tincture_doses_at_its_starting_charge(records, stocks):
    record = records["INV-USER-20261014-STK-191"]
    assert record["source_quote"] == "ye"
    assert record["authority_limits"]["final_filtrate_assayed"] is False
    (stock,) = [s for s in stocks if s.name == "Kenyan Myrrh Ethanol Tincture"]
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.2, "mass_fraction", "ethanol")
    assert stock.execution_ready is True


@pytest.mark.parametrize(
    ("name", "odt"),
    [("Cedroxyde", 8.0), ("Cedryl Acetate", 20.0), ("Anisyl Acetate", 9.0)],
)
def test_analogue_thresholds_are_tagged_unverified_with_their_inputs(name, odt):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == odt
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == "UNVERIFIED"
    assert any("Analogue estimate" in s for s in meta["sources"])
    assert any("PW Relative Odor Impact" in s for s in meta["sources"])
    spine = load_registry().get(name)
    assert spine.odt_air_ppb == odt
    assert spine.provenance["odt_air_ppb"].startswith("UNVERIFIED analogue estimate")


@pytest.mark.parametrize("name", ["Glycolierral", "Fructone B"])
def test_materials_with_no_measured_analogue_get_no_threshold(name):
    assert ODT_DATA[lookup_odt_raw_name(name)]["odt_air"] is None


def test_cabreuva_threshold_is_labelled_constituent_derived():
    assert ODT_VERIFICATION["cabreuva eo"]["vfy"] == "DERIVED"


def test_cedroxyde_skin_model_uses_the_producer_logp_and_formula_mass():
    assert SKIN_PHYSCHEM["Cedroxyde"]["logP"] == 4.88
    assert SKIN_PHYSCHEM["Cedroxyde"]["MW"] == 220.35


@pytest.mark.parametrize(
    ("name", "field", "value", "provenance_start"),
    [
        ("Glycolierral", "vp_25c_pa", 0.24, "Givaudan, Glycolierral"),
        ("Glycolierral", "density_25c_g_ml", 1.007, "Vigon SDS 500894"),
        ("Fructone B", "density_25c_g_ml", 1.039, "PerfumersWorld 3FG00196"),
        ("Anisyl Acetate", "vp_25c_pa", 1.33, "Givaudan, Anisyl Acetate"),
        ("Anisyl Acetate", "logp", 1.9, "RIFM 2024"),
    ],
)
def test_loaded_values_carry_a_dated_provenance(name, field, value, provenance_start):
    spine = load_registry().get(name)
    assert getattr(spine, field) == pytest.approx(value)
    assert spine.provenance[field].startswith(provenance_start)
    assert "Loaded 2026-10-28" in spine.provenance[field]


@pytest.mark.parametrize(
    ("name", "producer"),
    [("Glycolierral", "Givaudan"), ("Fructone B", "IFF"), ("Cedryl Acetate", "IFF")],
)
def test_producer_odour_text(name, producer):
    spine = load_registry().get(name)
    assert spine.character
    assert spine.provenance["character"].startswith(producer)


def test_undecavertol_records_rifms_measured_20c_vapour_pressure_without_replacing_the_25c_field():
    spine = load_registry().get("Undecavertol")
    assert spine.vp_25c_pa == pytest.approx(2.93)
    assert "1.1 Pa at 20 C" in spine.notes
    assert "Loaded 2026-10-25" in spine.provenance["logp"]
    assert "3.9 at 30 C (RIFM, 1996)" in spine.provenance["logp"]


def test_magnolia_eo_counts_the_higher_published_methyl_eugenol():
    levels = load_natural_constituents().stocks["Magnolia EO"]
    assert levels["IFRA_STD_100"][0] == pytest.approx(3.59)
    assert levels["IFRA_STD_037"][0] == pytest.approx(0.4)


# ── Group 2 (same thread, 28 Oct 2026) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("record_id", "quote"),
    [
        ("INV-USER-20261014-STK-192", "I have a solution"),
        ("INV-USER-20261014-STK-193", "Yes"),
        ("INV-USER-20261014-STK-194", "hye"),
        ("INV-USER-20261014-STK-195", "1 g"),
        ("INV-USER-20261014-STK-196", "Neat"),
    ],
)
def test_group2_bottle_answers_quote_kenny(records, record_id, quote):
    assert records[record_id]["source_quote"] == quote


def test_group2_new_dilutions_are_ten_percent_in_dpg(stocks):
    rows = {s.name: s for s in stocks}
    for name in ("Melonal 10%", "Para-Acetanisole 10%", "Aldehyde C16 EMPG 10%"):
        assert (rows[name].dilution, rows[name].carrier) == (0.1, "dpg"), name


def test_methyl_nonyl_ketone_has_no_one_percent_stock(stocks):
    assert not [s for s in stocks if s.name == "Methyl Nonyl Ketone 1%" and s.execution_ready]


@pytest.mark.parametrize(
    ("name", "odt"),
    [
        ("Dimethyl Benzyl Carbinol", 12.0),
        ("Caryophyllene Acetate", 6.0),
        ("Hindinol", 7.0),
        ("Para-Acetanisole", 30.0),
        ("Methyl Nonyl Ketone", 5.5),
    ],
)
def test_group2_analogue_thresholds_are_tagged_unverified(name, odt):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == odt
    assert ODT_VERIFICATION[key]["vfy"] == "UNVERIFIED"
    assert load_registry().get(name).odt_air_ppb == odt


@pytest.mark.parametrize("name", ["Diethyl Malonate", "Aldehyde C16 EMPG"])
def test_pw_fit_alone_loads_no_threshold(name):
    key = lookup_odt_raw_name(name)
    assert key is None or ODT_VERIFICATION.get(key, {}).get("note", "").find("2026-10-28") == -1


def test_sandalwood_base_x3_carries_no_invented_physics():
    key = lookup_odt_raw_name("Sandalwood Base X3")
    assert (ODT_DATA[key]["odt_air"], ODT_DATA[key]["odt_eth"]) == (None, None)
    assert ODT_VERIFICATION[key]["vfy"] == "UNAVAILABLE"
    spine = load_registry().get("Sandalwood Base 3X")
    assert (spine.mw_g_mol, spine.logp, spine.vp_25c_pa, spine.odt_air_ppb) == (None, None, None, None)


def test_himalayan_cedarwood_threshold_is_labelled_copied():
    assert ODT_VERIFICATION["himalayan cedarwood eo"]["vfy"] == "UNVERIFIED"


@pytest.mark.parametrize(
    ("name", "field", "value", "provenance_start"),
    [
        ("Dimethyl Benzyl Carbinol", "density_25c_g_ml", 0.972, "TGSC, dimethyl benzyl carbinol"),
        ("Hindinol", "logp", 3.8, "RIFM fragrance ingredient safety assessment"),
        ("Para-Acetanisole", "inchikey", "NTPLXRHDUXRPNE-UHFFFAOYSA-N", "NIST Chemistry WebBook"),
        ("Red Saffron Infusion", "cas", "8022-19-3", "PerfumersWorld 5ES18560 SDS"),
    ],
)
def test_group2_loaded_values_carry_a_dated_provenance(name, field, value, provenance_start):
    spine = load_registry().get(name)
    assert getattr(spine, field) == (pytest.approx(value) if isinstance(value, float) else value)
    assert spine.provenance[field].startswith(provenance_start)
    assert "Loaded 2026-10-28" in spine.provenance[field]


def test_cabbage_rose_extract_is_not_aliased_to_rosa_centifolia():
    spine = load_registry().get("Cabbage Rose Extract")
    assert "rosa centifolia extract" not in [a.lower() for a in spine.aliases]
    assert "Propylene Glycol + Fragrance" in spine.notes


def _gates_for(rows):
    from engine.pipeline.gates import ReleaseGateConfig, gate_formula

    total = sum(rows.values())
    formula = {
        "number": 1,
        "name": "Bases",
        "ingredients_ul": rows,
        "dilutions": {},
        "ingredients_pct": {k: v / total * 100 for k, v in rows.items()},
        "body": "Bases",
    }
    report = gate_formula(formula, ReleaseGateConfig(expected_concentrate_ul=sum(rows.values()), brief="generic"))
    return {g.gate: g for g in report.gates}


def test_partly_declared_bases_warn_with_their_undeclared_part_instead_of_failing():
    gates = _gates_for({
        "Iso E Super": 1500.0, "Hedione": 1500.0, "Black Tea Base": 300.0,
        "Palm Dates Base": 300.0, "Sandalwood Base 3X": 400.0,
    })
    for gate in ("opaque_preblends", "physics_data_coverage", "odt_coverage"):
        assert gates[gate].status == "WARN", (gate, gates[gate].detail)
    assert "undeclared part" in gates["opaque_preblends"].detail
    assert "Sandalwood Base 3X" in gates["opaque_preblends"].data["partly_declared_bases"]
    assert gates["osmotheque_archivability"].status == "WARN"
    assert "opaque preblend" not in gates["master_perfumer_gate"].detail
    allergens = gates["safety_ifra_allergen"].data["partly_declared_base_allergens"]
    assert {(a["base"], a["allergen"]) for a in allergens} == {
        ("Black Tea Base", "Linalool"), ("Black Tea Base", "Benzyl Benzoate"), ("Sandalwood Base X3", "Limonene"),
    }


def test_other_opaque_preblends_still_fail_beside_a_partly_declared_base():
    gates = _gates_for({"Hedione": 3000.0, "Iso E Super": 2000.0, "Cardamom FTEC": 1000.0, "Black Tea Base": 300.0})
    assert gates["opaque_preblends"].status == "FAIL"
    assert gates["opaque_preblends"].data["materials"] == ["Cardamom FTEC"]
    assert "Black Tea Base" in gates["opaque_preblends"].data["partly_declared_bases"]


def test_partly_declared_bases_load_with_their_undeclared_part():
    from engine.ifra_standards import load_partly_declared_bases, partly_declared_base

    names = {b.name for b in load_partly_declared_bases()}
    assert names == {"Black Tea Base", "Palm Dates Base", "Sandalwood Base X3"}
    assert partly_declared_base(["Sandalwood Base 3X"]).sku == "6WX24054"
    assert partly_declared_base(["Black Tea Base (neat / as supplied)"]).allergens_pct["Linalool"] == 0.2189
    assert partly_declared_base(["Suederal"]) is None
    assert "undeclared part" in partly_declared_base(["Palm Dates Base"]).warning()


# ── Group 3 (same thread, 28 Oct 2026) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("record_id", "quote", "superseded"),
    [
        ("INV-USER-20261014-STK-197", "Storax yes continue to 4", "INV-USER-20260915-STOCK-013"),
        ("INV-USER-20261014-STK-198", "liquid", "INV-USER-20261007-PW-018"),
        ("INV-USER-20261014-STK-199", "ye", "INV-USER-20261007-PW-038"),
        ("INV-USER-20261014-STK-200", "ye", "INV-USER-20261007-PW-017"),
    ],
)
def test_group3_bottle_answers_quote_kenny_and_replace_the_held_record(records, record_id, quote, superseded):
    assert records[record_id]["source_quote"] == quote
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    assert superseded in {r["record_id"] for r in overlay["retired_records"]}


def test_turkish_storax_tincture_is_one_row_at_its_starting_charge(stocks):
    rows = [s for s in stocks if s.name == "Turkish Storax Tincture"]
    assert len(rows) == 1
    (stock,) = rows
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.2, "mass_fraction", "ethanol")
    assert stock.execution_ready is True


@pytest.mark.parametrize(
    ("name", "odt"),
    [
        ("Canthoxal", 1.4),
        ("Cinnamyl Acetate", 3.0),
        ("Phenyl Ethyl Dimethyl Carbinyl Acetate", 2.7),
        ("Acetoin", 3.0),
        ("Parmavert", 7.7),
        ("Cassia Essential Oil", 78.0),
        ("turkish storax", 35.0),
    ],
)
def test_group3_analogue_thresholds_are_tagged_unverified(name, odt):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == odt
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == "UNVERIFIED"
    assert "not a measurement" in meta["note"]


@pytest.mark.parametrize(
    ("name", "odt", "vfy", "source"),
    [
        ("Azarbre", 1.569, "PEER_SINGLE", "'Odour Threshold : 11,5686 ng/l'"),
        ("Beta Pinene", 33.0, "PEER_SINGLE", "'beta-Pinene 0.033'"),
        ("Ethyl Linalyl Acetate", 14.42, "PEER_EST", "| 5526' (PROC)"),
    ],
)
def test_group3_sourced_thresholds(name, odt, vfy, source):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == pytest.approx(odt)
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == vfy
    assert any(source in s for s in meta["sources"])
    assert load_registry().get(name).odt_air_ppb == pytest.approx(odt)


def test_azarbre_typo_key_is_gone_and_cedar_amber_stays_first():
    assert "azhrbre" not in ODT_DATA and "azhrbre" not in ODT_VERIFICATION
    spine = load_registry().get("Azarbre")
    assert (spine.mw_g_mol, spine.vp_25c_pa, spine.logp) == (pytest.approx(180.29), 4.0, 3.1)
    assert spine.character.startswith("Cedar-amber")
    assert "both but it i i cedar amber  mell" in spine.provenance["character"]


def test_vetikon_is_the_symrise_aryl_ketone_not_methyl_cedryl_ketone():
    spine = load_registry().get("Vetikon")
    assert spine.smiles == "CC(=O)CC(C)(C)c1ccccc1"
    assert "methyl cedryl ketone" not in [a.lower() for a in spine.aliases]
    assert spine.vp_25c_pa == pytest.approx(3.72)
    assert ODT_DATA["vetikon"]["odt_air"] == pytest.approx(87.53)
    assert "No peer-reviewed air-phase ODT found" not in str(ODT_VERIFICATION["vetikon"])


def test_parmavert_physics_agrees_across_the_engine():
    from engine.diffusion_model import DIFFUSION_DATA  # noqa: PLC0415
    from engine.ingredient_intelligence import _PROFILES  # noqa: PLC0415

    spine = load_registry().get("Parmavert")
    assert (spine.cas, spine.mw_g_mol, spine.logp, spine.vp_25c_pa) == ("13257-44-8", 184.28, 3.6, 6.7)
    assert (_PROFILES["Parmavert"]["mw"], _PROFILES["Parmavert"]["vp"]) == (184.28, 6.7)
    assert DIFFUSION_DATA["Parmavert"]["MW"] == 184.28
    assert SKIN_PHYSCHEM["Parmavert"]["logP"] == 3.6


def test_cassia_profile_follows_the_lot_gc_without_unsourced_linalool():
    from engine.pipeline.natural_absolute_decomposition import get_constituents  # noqa: PLC0415

    rows = {row[0]: row for row in get_constituents("Cassia Essential Oil")}
    assert set(rows) == {"cinnamaldehyde", "coumarin", "benzaldehyde"}
    assert rows["cinnamaldehyde"][1:5] == (0.7905, 132.16, 3.85, 62.0)


def test_storax_profile_carries_styrene():
    from engine.pipeline.natural_absolute_decomposition import get_constituents  # noqa: PLC0415

    rows = {row[0]: row for row in get_constituents("Turkish Storax Tincture")}
    assert rows["styrene"][1:5] == (0.005, 104.15, 853.0, 35.0)


def test_beta_pinene_has_the_pinaceae_peroxide_specification():
    import json  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    table = json.loads((Path(__file__).resolve().parents[1] / "data/regulatory/ifra_cat4_51.json").read_text(encoding="utf-8"))
    entry = table["materials"]["Beta Pinene"]
    assert (entry["status"], entry["standard"]) == ("specification", "IFRA_STD_184")


@pytest.mark.parametrize(
    ("name", "field", "value", "provenance_start"),
    [
        ("Ethyl Acetoacetate", "logp", 0.25, "OECD SIDS initial assessment"),
        ("Phenyl Ethyl Dimethyl Carbinyl Acetate", "inchikey", "ZXFNOEJFYLQUSB-UHFFFAOYSA-N", "NIST Chemistry WebBook"),
        ("Canthoxal", "logp", 2.5, "RIFM fragrance ingredient safety assessment"),
        ("Cade Oil Rectified", "density_25c_g_ml", 0.95, "PerfumersWorld 7TW00076"),
    ],
)
def test_group3_loaded_values_carry_a_dated_provenance(name, field, value, provenance_start):
    spine = load_registry().get(name)
    assert getattr(spine, field) == (pytest.approx(value) if isinstance(value, float) else value)
    assert spine.provenance[field].startswith(provenance_start)
    assert "Loaded 2026-10-28" in spine.provenance[field]


def test_cade_keeps_the_lower_ifra_figure_until_the_p_cresol_check():
    spine = load_registry().get("Cade Oil Rectified")
    assert spine.ifra_max_pct_edp == 0.1
    assert "'dilute'" in spine.notes and "0.83 %" in spine.notes


# ── Group 4 (same thread, 28 Oct 2026) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "odt"),
    [("2-Acetyl Pyrazine", 0.40), ("Allyl Ionone", 0.035), ("Maltol", 1.0)],
)
def test_group4_analogue_thresholds_are_tagged_unverified(name, odt):
    key = lookup_odt_raw_name(name)
    assert ODT_DATA[key]["odt_air"] == pytest.approx(odt)
    meta = ODT_VERIFICATION[key]
    assert meta["vfy"] == "UNVERIFIED"
    assert "not a measurement" in meta["note"]
    assert load_registry().get(name).odt_air_ppb == pytest.approx(odt)


def test_methyl_laitone_takes_the_givaudan_sds_threshold_and_the_lactone_vapour_pressure():
    key = lookup_odt_raw_name("Methyl Laitone")
    assert ODT_DATA[key]["odt_air"] == pytest.approx(0.0303)
    assert ODT_VERIFICATION[key]["vfy"] == "PEER_SINGLE"
    assert any("'Odour Threshold : 0,2085 ng/l'" in s for s in ODT_VERIFICATION[key]["sources"])
    spine = load_registry().get("Methyl Laitone")
    assert spine.vp_25c_pa == pytest.approx(0.6)
    assert "Loaded 2026-10-28" in spine.provenance["vp_25c_pa"]


def test_allyl_ionone_has_no_ifra_limit_from_a_usage_figure():
    spine = load_registry().get("Allyl Ionone")
    assert spine.ifra_max_pct_edp is None
    assert "not an IFRA limit" in spine.provenance["ifra_max_pct_edp"]


# ── Second batch of bottle answers (28 Oct 2026, 10:44-10:49 UTC) ────────────────────


def _one(stocks, name):
    rows = [s for s in stocks if s.name == name]
    assert len(rows) == 1, [(s.name, s.source_ref) for s in rows]
    return rows[0]


def test_neat_cade_is_owned_next_to_the_one_percent(records, stocks):
    record = records["INV-USER-20261014-STK-201"]
    assert (record["source_quote"], record["source_message_timestamp_utc"]) == ("Yes", "2026-10-28T10:44:15Z")
    neat = _one(stocks, "Cade Oil Rectified (neat)")
    assert (neat.dilution, neat.fraction_basis, neat.identity_name) == (1.0, "neat", "Cade Oil Rectified")
    spine = load_registry().get("Cade Oil Rectified")
    assert spine.vp_25c_pa == pytest.approx(5.4) and spine.vp_source == "constituent_raoult_estimate"
    assert spine.odt_air_ppb == pytest.approx(0.05)
    assert ODT_VERIFICATION[lookup_odt_raw_name("cade oil rectified") or "cade oil rectified"]["vfy"] == "UNVERIFIED"
    assert "placeholders" not in spine.notes


def test_methyl_laitone_twenty_percent_is_mass_basis_from_crystals(records, stocks):
    record = records["INV-USER-20261014-STK-202"]
    assert record["source_quote"] == "Dissolve crystals"
    assert record["stock"]["approximate"] is True
    stock = _one(stocks, "Methyl Laitone")
    assert (stock.dilution, stock.fraction_basis, stock.carrier) == (0.2, "mass_fraction", "ethanol")
    head = inventory.load_current_user_inventory_overlay(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH)
    assert "INV-USER-20260915-STOCK-003" in head["superseded_record_ids"]


def test_cassia_is_owned_as_a_labelled_closest_identity(records, stocks):
    record = records["INV-USER-20261014-STK-203"]
    assert record["source_quote"] == "I have no idea"
    assert record["stock"]["identity_status"] == "PROXY_IDENTITY_UNCONFIRMED"
    assert record["supplier_product"]["supplier"] == "unknown"
    stock = _one(stocks, "Cassia Essential Oil")
    assert (stock.dilution, stock.fraction_basis, stock.execution_ready) == (1.0, "neat", True)


def test_beta_pinene_is_owned_neat_with_source_unknown(records, stocks):
    record = records["INV-USER-20261014-STK-204"]
    assert record["source_kind"] == "USER_INVENTORY_LISTING"
    assert "Standard 184" in record["note"]
    stock = _one(stocks, "Beta-Pinene")
    assert (stock.dilution, stock.fraction_basis) == (1.0, "neat")


def test_maltol_is_a_weighed_solid_after_its_intake_hold(records, stocks):
    record = records["INV-USER-20261014-STK-205"]
    assert record["source_quote"] == "Yes"
    assert record["stock"]["execution_scope"] == "WEIGHED_SOLID_OR_PREPARED_SOLUTION_ONLY"
    stock = _one(stocks, "Maltol")
    assert (stock.dilution, stock.execution_ready) == (1.0, True)


def test_vetikon_supplier_is_simple_scents_diy():
    notes = load_registry().get("Vetikon").notes
    assert "Simple Scents DIY" in notes and "'It just says Vetikon, check on ssdiy'" in notes


def test_ginger_lily_is_modeled_as_ginger_root_oil():
    from engine.pipeline.natural_absolute_decomposition import get_composite_metadata, get_constituents

    rows = {row[0]: row[1] for row in get_constituents("Ginger Lily Oil")}
    assert rows["1,8-cineole"] == pytest.approx(0.5387)
    assert sum(rows.values()) == pytest.approx(0.6325)
    meta = get_composite_metadata("Ginger Lily Oil")
    assert meta.composition_authority == "LITERATURE_PARTIAL_PROXY"
    assert meta.input_authority["composition"]["owned_lot_match"] == "PROXY_IDENTITY_UNCONFIRMED"
    assert any("Ginger root, check on msr" in line for line in meta.limitations)
    spine = load_registry().get("Ginger Lily Oil")
    assert spine.cas is None and "Proprietary Perfume Compound" in spine.notes and "boilerplate" in spine.notes
