"""Current full-system reconciliation, preserving history and uncertainty."""

import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

import engine.inventory_parser as inventory
from engine.data_spine.loader import load_registry
from engine.data_spine.reconciliation import reconcile
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import (
    _INVENTORY_ODT_UNAVAILABLE_20261007,
    ODT_DATA,
    oav_reliability,
    verify_odt,
)

ROOT = Path(__file__).resolve().parents[1]


def test_successor_preserves_unaffected_stock_bytes_and_all_requirement_rows():
    base = inventory.materialize_current_inventory(apply_user_overlay=False)
    prior = inventory._apply_current_user_inventory_overlay(
        base,
        inventory.load_current_user_inventory_overlay(inventory.NEROLI_USER_INVENTORY_OVERLAY_PATH),
    )
    # This test characterizes the September 7 transition; newer stock changes
    # have their own preservation tests and must not rewrite this predecessor.
    september7 = inventory.load_current_user_inventory_overlay(
        inventory.RECONCILED_USER_INVENTORY_OVERLAY_PATH
    )
    current = inventory._apply_current_user_inventory_overlay(base, september7)
    delta = september7["delta_records"]
    retired_rows = {s["source_row"] for r in delta for s in r["supersedes_parent_stocks"]}
    before = {s.stock_id: s for s in prior.stocks if not retired_rows.intersection(s.source_rows)}
    after = {s.stock_id: s for s in current.stocks if s.stock_id in before}
    assert before == after
    assert len(prior.requirements) == len(current.requirements) == 280
    assert {r.source_row: r for r in prior.requirements if r.source_row not in retired_rows} == {
        r.source_row: r for r in current.requirements if r.source_row not in retired_rows
    }


@pytest.mark.parametrize(
    "name,fraction,basis,carrier,ready",
    [
        ("Coumarin", 0.1, "mass_fraction", "dpg", True),
        # 2026-10-25: Kenny is out of Vetiveryl Acetate (overlay STK-169), so its neat row
        # is replaced by Manzanate, neat since his "All neat" card answer (STK-154).
        ("Manzanate", 1, "neat", "", True),
        ("Methyl Laitone", 0.2, "mass_fraction", "ethanol", True),
        # 2026-10-14: Kenny put the Guaiacwood EO stock in DPG.
        ("Guaiacwood EO", 1 / 3, "mass_fraction", "dpg", True),
        ("Bacdanol", 1, "neat", "", True),
    ],
)
def test_current_stock_contract(name, fraction, basis, carrier, ready):
    stocks = [
        s for s in inventory.materialize_current_inventory().stocks
        if s.identity_name == name and s.dilution == fraction
        and s.fraction_basis == basis and s.carrier == carrier
    ]
    assert len(stocks) == 1
    s = stocks[0]
    assert (s.dilution, s.fraction_basis, s.carrier, s.execution_ready) == (
        fraction,
        basis,
        carrier,
        ready,
    )


def test_retired_liquids_and_depleted_stocks_do_not_reappear():
    names = {s.identity_name for s in inventory.materialize_current_inventory().stocks}
    assert not names.intersection(
        {"Ambrofix", "Tonalide", "Musk Ketone", "Polysantol", "Nagamortha Oil"}
    )
    # Kenny used up the Ambrofix Crystals on 2026-10-29 ("ambrofi\ i5 out", STK-232).
    assert "Ambrofix Crystals" not in names
    kephalis = next(s for s in inventory.materialize_current_inventory().stocks
                    if s.identity_name == "Kephalis")
    # Kenny released Kephalis from its intake hold on 2026-10-14 (neat).
    assert kephalis.authority == "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY_20261014"
    assert kephalis.execution_ready is True
    old = inventory.load_current_user_inventory_overlay()["retired_records"][0]
    assert old["mass_balance"]["ambrofix_g"] == 0.192


def test_bottle_identity_is_not_a_chemical_alias():
    assert get_profile("Hydroxycitronellal").cas == "107-75-5"
    assert get_profile("Hydroxycitronellol").cas == "107-74-4"
    text = inventory.parse_inventory(include_unavailable=False)
    assert any(s.name == "Hydroxycitronellal" for s in text)
    assert not any(s.name == "Hydroxycitronellol" for s in text)


def test_legacy_parser_keeps_rows_and_prefers_owned_stock():
    rows = inventory.parse_inventory(unique=False)
    assert len(rows) == len(inventory.parse_inventory(unique=False))
    assert len(rows) > 287  # The October receipt is additive, not a historical rewrite.
    assert all(s.source_rows and s.stock_id for s in rows)
    agar = next(s for s in inventory.parse_inventory() if s.name == "Black Agarwood Artificial")
    assert agar.status == "owned" and agar.dilution == 0.1
    kephalis = next(s for s in inventory.parse_inventory() if s.name == "Kephalis")
    assert kephalis.status == "owned"
    assert next(s for s in rows if s.name == "Methyl Laitone").execution_ready is True


@pytest.mark.parametrize("name", ["tuberose abs", "jasmine blossoms", "galbanum EO"])
def test_odt_metadata_never_uses_fuzzy_prefix_identity(name):
    assert verify_odt(name) is None


def test_conflicting_thresholds_are_not_promoted():
    # Exact metadata exists for Tonka Absolute and must not be discarded.
    assert verify_odt("tonka absolute")["vfy"] == "DERIVED"
    # Linalool's 0.51 vs 1.5 ppb conflict ended on 2026-10-25 when the literature batch
    # loaded Elsharif et al.'s 0.51 ppb; the old evidence stays under "superseded".
    assert verify_odt("Iso E Super")["vfy"] == "UNVERIFIED"
    assert "numeric_conflicts" in verify_odt("Iso E Super")
    assert verify_odt("Linalool")["vfy"] == "PEER_SINGLE"
    assert verify_odt("Linalool")["superseded"]["vfy"] == "PEER_CROSS"
    for name in ODT_DATA:
        assert isinstance(oav_reliability(name), str)


def test_runtime_odt_numeric_map_is_unchanged():
    values = {
        k: {"odt_air": v.get("odt_air"), "odt_eth": v.get("odt_eth")}
        for k, v in ODT_DATA.items() if k not in _INVENTORY_ODT_UNAVAILABLE_20261007
    }
    digest = hashlib.sha256(
        json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    # Geranyl acetate air ODT added from Elsharif & Buettner (2018); the
    # digest without that one entry is master's 2505240f… value.
    # 2026-10-08: cited air ODTs for octanal/nonanal (Cometto-Muniz & Abraham
    # 2010: aldehyde c8 5.7 -> 0.17, aldehyde c9 8.5 -> 0.53, plus keys octanal,
    # nonanal, aldehyde c-8 octanal, aldehyde c-9 nonanal) and butyl butyrate
    # (Nagata 2003, 4.8 ppb); reverting those seven gives 35b7d603….
    # Musk fix 2026-10-08: Macrolide odt_air 2.0 -> 3.2 (Exaltolide's value, same
    # molecule) and Helvetolide 0.146 (Armanino 2020) added; with only the musk
    # change on top of 35b7d603… the digest is 7bca0ddc…, with only the aldehyde
    # and ester change it is d4bcca51….
    # Geraniol air ODT 0.04 -> 2.22 ppb (Elsharif & Buettner 2018, 14 ng/L);
    # reverting only that value gives 667ba337….
    # Vertofix Coeur odt_air 240 (unsourced) -> 6.3 ppb, Vertofix's van Gemert
    # value for the same molecule; reverting only that value gives 37f940a3….
    # 2026-10-09: key "stralyl acetate" renamed to the correct "styralyl acetate"
    # (same values 40.0/1.0); with the old key the digest is 9ec89ee9….
    # 2026-10-15: citronellol odt_air 40 -> 1.6 and rhodinol / rhodinol ex
    # citronella 0.3 -> 1.6 (Elsharif & Buettner 2017, 10 ng/L air); reverting
    # only those three gives aa5581d0….
    # 2026-10-23: ethyl butyrate air ODT 0.04 ppb added (Nagata 2003); without that one
    # entry the digest is 1b161002….
    # 2026-10-25: Ambrocenide odt_air 0.02 -> 0.00176 ppb (Elterlein et al., Chem. Eur. J.
    # 2024, 0.02 ng/L air; the old 0.02 was ng/L stored as ppb); reverting only that value
    # gives 31c5f96c….
    # 2026-10-25 fruit batch (engine/odor_thresholds.py FRUIT_ODT_BATCH_2026_10_25):
    # air ODTs for cis-3 hexenyl acetate 2.67, manzanate 0.0515, ethyl 2-methylbutyrate
    # 0.06 -> 0.676, phenoxy ethyl isobutyrate 2.88 (Givaudan US 12,340,876 Table 1),
    # hexyl acetate 2.0 -> 2.9 (Physiol. Behav. 2008; Nagata 1.8), allyl amyl glycolate
    # 2.0 -> 0.172 and verdyl acetate 10 -> 0.134 (Givaudan patent estimates), delta
    # damascone 0.02 -> 0.00267 and alpha damascone 0.04 -> 0.0178 (Firmenich, P&F 2002);
    # odt_eth unchanged. Without those nine the digest is master's b43b04fc….
    # 2026-10-25 literature batch (engine/odor_thresholds.py LITERATURE_ODT_BATCH_2026_10_25):
    # 55 air ODTs from producer figures, measured literature and labelled Givaudan PROC
    # estimates, each re-opened by a second reader (list and sources in that block and in
    # tests/test_literature_odt_batch_2026_10_25.py); odt_eth unchanged. Without those 55
    # the digest is 5c7d84b5….
    # 2026-10-28 analogue estimates (engine/odor_thresholds.py ANALOGUE_ODT_BATCH_2026_10_28):
    # UNVERIFIED air ODTs for cedroxyde 8, cedryl acetate 20 and anisyl acetate 9 ppb (Kenny's
    # card choice, 28 Oct 08:39 UTC); odt_eth unchanged. Without those three the digest is 1be5f1c5….
    # Groups 2 and 3 the same day add more on the same rule (DMBC 12, caryophyllene acetate 6,
    # hindinol 7, para-acetanisole 30, methyl nonyl ketone 5.5; canthoxal 1.4, cinnamyl acetate
    # 3, PEDMC acetate 2.7, acetoin 3, parmavert 15 -> 7.7, cassia 1.5 -> 78, turkish storax
    # 20 -> 35), drop the invented sandalwood base x3 value and the typo key "azhrbre", and load
    # sourced values for azarbre 2.0 -> 1.569 (Givaudan SDS), beta-pinene 3 -> 33 (Nagata 2003)
    # and ethyl linalyl acetate 14.42 (Givaudan PROC). Group 2 alone gave d57c0a18….
    # Group 4 adds 2-acetyl pyrazine 0.3 -> 0.40, allyl ionone 1.0 -> 0.035, cade 3.0 -> 0.05
    # (UNVERIFIED analogues; maltol 1.0 relabelled) and methyl laitone 0.0303 (Givaudan SDS).
    # Groups 1-3 alone gave 9b2c3880…. Group 5 adds sweet orange essential oil 23 (UNVERIFIED
    # constituent estimate) and retires the unsourced costus olifac 5.0; groups 1-4 gave 5531c14a….
    # 2026-10-28 group 6: rum ether 160 ppb (UNVERIFIED constituent estimate) and the stale static rows
    # triplal 0.5 -> 0.582 and florhydral 0.3 -> 0.008995 aligned to their literature values; group 5 gave bdcd5e59….
    # Group 7: Givaudan PROC values for peach ketone 0.0117, veloutone 1.62 and beta caryophyllene 49.0,
    # Symrise buccoxime 5.818, and UNVERIFIED analogues pear valerate 2.1, cis-3 hexenyl hexanoate 3.1,
    # isolongifolanone 9, rhubofix 6 and linalool oxide 2.3; group 6 gave ed3945b0….
    # The VP-tied rows then moved with ECHA's measured VPs: peach ketone 0.0140, veloutone 6.85.
    assert digest == "e90a945349d83f82e75821e6c369df0ff3a3abc2daf6d9f2140cfeab1f71341a"
    # The receipt adds explicit unknowns; none is a measured threshold.
    assert all(row["odt_air"] is None and row["odt_eth"] is None
               for row in _INVENTORY_ODT_UNAVAILABLE_20261007.values())


def test_new_profiles_do_not_invent_unknown_physics():
    ml = get_profile("Methyl Laitone")
    assert ml.mw == 168.23 and ml.vp is None and ml.odt is None
    guaiac = get_profile("Guaiacwood EO")
    assert guaiac.material_kind == "NATURAL_MIXTURE"
    assert guaiac.mw is None and guaiac.vp is None and guaiac.odt is None
    assert load_registry().get("Methyl Laitone 10% DPG").user_in_inventory is False
    assert load_registry().get("Methyl Laitone").user_in_inventory is True


def test_generator_import_does_not_write_or_request_network(monkeypatch):
    import requests

    def forbidden(*args, **kwargs):
        raise AssertionError("Import must not request network or write files")

    monkeypatch.setattr(requests, "get", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    importlib.import_module("_generate_material_properties")


def test_offline_rebuild_is_lossless_and_idempotent(monkeypatch):
    import requests

    monkeypatch.setattr(requests, "get", lambda *a, **k: pytest.fail("Network prohibited"))
    old = [
        {
            "name": "Florol",
            "mw": 138.21,
            "cas": "68039-49-6",
            "pubchem_cid": 93375,
            "odor_profile": "Keep the full authored description.",
            "bespoke": {"all": [1, 2, 3]},
        },
        {"name": "FLOROL", "distinct_history": "Do not collapse this record."},
        {"name": "Bacdanol", "oav_dose_pct": 3, "oav_typical": 375000},
    ]
    original = copy.deepcopy(old)
    first, report = reconcile(old)
    second, _ = reconcile(first)
    assert old == original and first == second
    assert [r["name"] for r in first[:3]] == [r["name"] for r in old]
    assert first[0]["mw"] == 172.26 and first[0]["pubchem_cid"] == 3017432
    assert (
        first[0]["odor_profile"] == old[0]["odor_profile"]
        and first[0]["bespoke"] == old[0]["bespoke"]
    )
    assert first[2]["oav_typical"] is None  # unresolved product class is not a pure-entity proof
    assert report["counts"]["inventory_text_rows"] == len(
        inventory.parse_inventory(unique=False)
    )


def test_physical_stock_identity_and_mixture_firewall():
    rows, _ = reconcile(
        [
            {"name": n, "oav_dose_pct": 2}
            for n in (
                "Geranium Flower EO",
                "Geranium EO",
                "Jasmine Absolute",
                "Jasmine Sambac Absolute",
                "Bergamot FCF oil Sicilian",
                "BERGAMOT FCF",
                "Black Agarwood Artificial",
                "Castoreum Synthetic",
                "Tonka Bean FO",
                "Tobacco Absolute",
                "Exaltolide",
            )
        ]
    )
    by_name = {r["name"]: r for r in rows}
    assert by_name["Geranium Flower EO"]["current_stocks"] == []
    for name in ("Jasmine Absolute", "Jasmine Sambac Absolute"):
        assert all(s["identity_name"] == name for s in by_name[name]["current_stocks"])
    for name in (
        "Bergamot FCF oil Sicilian",
        "BERGAMOT FCF",
        "Black Agarwood Artificial",
        "Castoreum Synthetic",
        "Tonka Bean FO",
    ):
        assert by_name[name]["oav_typical"] is None
    # 2026-10-08 overlay retires the duplicate Tobacco row: one stock remains.
    assert by_name["Tobacco Absolute"]["dilution_pct"] == 0.1
    assert by_name["Tobacco Absolute"]["quantitative_stock_ready"] is True
    for name in ("Exaltolide",):
        assert by_name[name]["dilution_pct"] is None
        assert by_name[name]["quantitative_stock_ready"] is False
