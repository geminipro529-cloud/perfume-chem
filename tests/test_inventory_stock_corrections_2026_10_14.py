"""Kenny's stock corrections of 2026-10-14: Paradisamide 10%, Caryophyllene Acetate in DEP,
Sandalwood Base X3 and Kephalis neat, and Cedroxyde and Hindinol added neat."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

import engine.inventory_parser as inventory
from engine.pipeline.preflight import _dilution_consistency_check

OVERLAY_NAME = "inventory_user_authority_overlay_20261014_paradisamide_caryophyllene_acetate_woods.json"
# record id -> (identity name, fraction, fraction basis, carrier)
RECORDS = {
    "INV-USER-20261014-STK-001": ("Paradisamide", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-002": ("Sandalwood Base X3", 1.0, "neat", ""),
    "INV-USER-20261014-STK-003": ("Caryophyllene Acetate", 0.2, "mass_fraction", "dep"),
    "INV-USER-20261014-STK-004": ("Kephalis", 1.0, "neat", ""),
    "INV-USER-20261014-STK-005": ("Cedroxyde", 1.0, "neat", ""),
    "INV-USER-20261014-STK-006": ("Hindinol", 1.0, "neat", ""),
    "INV-USER-20261014-STK-007": ("Beta Damascone", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-008": ("Damascenone", 0.01, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-009": ("Anise EO", 0.01, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-010": ("Immortelle Absolute", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-011": ("Oakmoss Absolute", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-012": ("Violet Leaf Absolute", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-013": ("Neroli EO", 0.1, "mass_fraction", "jojoba"),
    "INV-USER-20261014-STK-014": ("Myrrh EO", 0.5, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-015": ("Guaiacwood EO", 1 / 3, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-016": ("Suederal", 0.1, "mass_fraction", "dpg"),
}
# Kenny's 15 Oct answers, recorded after the neat-Neroli record.
ADDED_20261015 = {
    "INV-USER-20261014-STK-018": ("Aurantiol", 1.0, "neat", ""),
    "INV-USER-20261014-STK-019": ("Vietnamese Benzoin Tincture", 0.4, "mass_fraction", "ethanol"),
    "INV-USER-20261014-STK-020": ("Oman Frankincense Ethanol Tincture", 0.33, "mass_fraction", "ethanol"),
    "INV-USER-20261014-STK-021": ("Cedrat FCF Sicilian", 1.0, "neat", ""),
    "INV-USER-20261014-STK-022": ("Red Saffron Infusion", 1.0, "neat", ""),
    "INV-USER-20261014-STK-023": ("Alpha Damascone", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-024": ("Aurantiol", 0.1, "mass_fraction", "dpg"),
}
# Kenny's answers to the small-jobs stock questions, 15 Oct 15:33 and 15:40 UTC.
ADDED_20261015_PM = {
    "INV-USER-20261014-STK-025": ("Damascol", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-026": ("Cade Oil Rectified", 0.01, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-027": ("Sandalwood EO", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-028": ("Javanol", 1.0, "neat", ""),
    "INV-USER-20261014-STK-029": ("Costus Olifac", 0.1, "mass_fraction", "dpg"),
    "INV-USER-20261014-STK-030": ("Clove EO (India)", 1.0, "neat", ""),
    "INV-USER-20261014-STK-031": ("Freesia HDI", 1.0, "neat", ""),
    "INV-USER-20261014-STK-032": ("Geranyl Acetate", 1.0, "neat", ""),
    "INV-USER-20261014-STK-033": ("Citronellyl Acetate", 1.0, "neat", ""),
    "INV-USER-20261014-STK-034": ("Neryl Acetate", 1.0, "neat", ""),
}
# Kenny has no neat Neroli (2026-10-15); this record holds no stock.
NEAT_NEROLI_NOT_OWNED = "INV-USER-20261014-STK-017"
# EO dilutions recorded in another solvent stay as they were.
OTHER_SOLVENT_EOS = {
    "Peppermint EO": (0.1, "volume_fraction", "ethanol"),
}
# Beta Damascone also has a neat V5 stock, which this record leaves alone.
V5_BETA_DAMASCONE_NEAT_STOCK_ID = "inventory:v5:5b2f689456cc631e984d"
V5_PARADISAMIDE_NEAT_STOCK_ID = "inventory:v5:8a702d0134e5d3f69e8b"


def _head() -> dict:
    return json.loads(inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))


def _stocks(identity_name: str):
    return [
        stock for stock in inventory.parse_current_inventory(unique=False)
        if stock.identity_name == identity_name
    ]


def _record(name: str) -> dict:
    (record,) = [r for r in _head()["records"] if r["canonical_name"] == name]
    return record


def test_v26_is_current_and_pinned_to_v25_and_live_inventory() -> None:
    path = inventory.CURRENT_USER_INVENTORY_OVERLAY_PATH
    assert path.name == OVERLAY_NAME
    normalized = path.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(normalized).hexdigest() == inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    head = _head()
    assert head["schema_version"].endswith("_v26")
    assert head["predecessor"] == {
        "path": "data/governance/inventory_user_authority_overlay_20261013_pomelo_ginger_lily_exaltolide.json",
        "normalized_text_sha256": inventory.NEW_STOCK_20261013_USER_INVENTORY_OVERLAY_SHA256,
    }
    raw = inventory.INVENTORY_PATH.read_bytes().replace(b"\r\n", b"\n")
    assert head["source"]["inventory_text_sha256"] == hashlib.sha256(raw).hexdigest()
    assert head["source"]["inventory_text_size_bytes"] == len(raw)
    assert [s["text"] for s in head["source"]["verbatim_user_statements"]] == [
        "paradisaminde is 10%",
        "You record it",
        "What about sandalwood base x3? If they aren’t in, add them along with lephalis "
        "and carophylene acetate",
        "Kephalis",
        "Add the other two woods you said were missing as well",
        "All are neat",
        "No that one is not neat",
        "Dep",
        "All the Damascones, etc stock dilution bases are in DPG",
        "As well as the EOs and absolutes",
        "Neroli 10% is from aroma&more",
        "It\u2019s not in ethanol check the web",
        "Myrrh EO and guaiacwood EO is, I can mix 10% Alpha Damascobe 10% in DPG",
        "Suederal 10% yes",
        "Yes.",
        "1. Both 2. Yes 3. about that much or more",
        "Cedrat is in inventory, Red Saffron is maxed in DPG",
        "it is mixed",
        "8. 10% 9. unknown'10. yes 11. not sure but very high ethyl benzoate smell not good\\",
        "1. yes 2. no idea, its neat 3. DPG 3. Check Sandalwood EO 10% in DPG on PW 5. the incoming "
        "one will be sweet orange, but sour version from china. 6. Yes. Javanol has both neat and 20%, . "
        "Ambretteolide is neat but you tell me if you need a solitin prepared. 7 do it",
        "I have geranyl acetate and citronellyl acetate as well",
        "Citronellal acetate is neat. Ambrettolide is neat but can be diluted if must.",
        "I have neryl acetate",
        "it is neat",
        # 2026-10-15 evening: the Tonka source, the w/w-in-DPG rule card and the
        # one-by-one bottle answers.
        "Tonka Bean Absolute 10% in DPG comes directly from PW (also diluted by PW)",
        "Load the rule",
        "I only have the 10%, the other is volume grade and not so good, and the other is tubrrlia base",
        "Yes",
        "Yes",
        "I have both",
        "Yes",
        "Neat",
        "Yes neat",
        "Yes it is neat. I also have cis jasmone neat, should I dilute it to 10% in DPG? "
        "What should I dilute it to?",
        "Add cis-3-hexenol to inventory, does Chimie need this?",
        "It is diluted to 1% In EtOH",
        "Yes, ad ye",
        "yes, it is neat",
        "YEs it is",
        "Yes",
    ]
    superseded = [
        "INV-USER-20260830-010",
        "INV-USER-20261007-PW-023",
        "INV-USER-20260908-AHSEE-002",
        "INV-USER-20260828-005",
        "INV-USER-20260901-002",
        "INV-USER-20260906-001",
        "INV-USER-20260915-STOCK-014",
        "INV-USER-20260915-STOCK-016",
        "INV-USER-20260924-R5-018",
        "INV-USER-20260924-R5-013",
        # 2026-10-15 evening: records whose basis was unrecorded, re-issued w/w under
        # Kenny's rule, and the Tonka receipt hold.
        "INV-USER-20260915-STOCK-005",
        "INV-USER-20260915-STOCK-006",
        "INV-USER-20260915-STOCK-012",
        "INV-USER-20260828-007",
        *(f"INV-USER-20261007-PW-{n:03d}" for n in (1, 8, 21, 22, 25, 26, 27, 36, 49, 52, 53)),
        "INV-USER-20260830-009",
        "INV-USER-20260924-R5-019",
    ]
    assert head["superseded_record_ids"] == superseded
    overlay = inventory.load_current_user_inventory_overlay(require_live_inventory_binding=True)
    assert [r["record_id"] for r in overlay["delta_records"]] == [
        *RECORDS,
        NEAT_NEROLI_NOT_OWNED,
        *ADDED_20261015,
        *ADDED_20261015_PM,
        *(f"INV-USER-20261014-STK-{n:03d}" for n in range(35, 105)),
    ]
    retired = {r["record_id"] for r in overlay["retired_records"]}
    assert set(superseded) <= retired
    live = {r["record_id"] for r in overlay["records"]}
    assert not live & set(superseded)
    assert overlay["policy"]["compounding_authorized"] is False
    assert overlay["policy"]["formula_rebase_authorized"] is False
    assert overlay["policy"]["safety_or_release_asserted"] is False


@pytest.mark.parametrize(
    "record_id,expected",
    [*RECORDS.items(), *ADDED_20261015.items(), *ADDED_20261015_PM.items()],
)
def test_each_material_is_one_execution_ready_stock(record_id: str, expected: tuple) -> None:
    name, fraction, basis, carrier = expected
    stocks = [
        stock for stock in _stocks(name)
        if stock.dilution == pytest.approx(fraction) and stock.status == "owned"
    ]
    assert len(stocks) == 1
    stock = stocks[0]
    assert stock.status == "owned"
    assert stock.dilution == pytest.approx(fraction)
    assert (stock.fraction_basis, stock.carrier) == (basis, carrier)
    assert stock.execution_ready is True
    assert stock.execution_hold_reason == ""
    assert stock.stock_id.startswith("inventory:user-20261014:")
    assert stock.authority == inventory.STOCK_CORRECTIONS_20261014_USER_INVENTORY_AUTHORITY
    assert stock.source_ref == f"data/governance/{OVERLAY_NAME}#{record_id}"


def test_paradisamide_v5_neat_stock_is_replaced() -> None:
    ids = {stock.stock_id for stock in _stocks("Paradisamide")}
    assert V5_PARADISAMIDE_NEAT_STOCK_ID not in ids
    limits = _record("Paradisamide")["authority_limits"]
    assert limits["fraction_from_user_message"] is True
    assert limits["basis_and_carrier_are_project_defaults"] is True


def test_damascone_dilutions_replace_their_v5_stocks_and_keep_the_neat_one() -> None:
    beta = {(stock.dilution, stock.stock_id.split(":")[1]) for stock in _stocks("Beta Damascone")}
    assert beta == {(1.0, "v5"), (0.1, "user-20261014")}
    assert V5_BETA_DAMASCONE_NEAT_STOCK_ID in {stock.stock_id for stock in _stocks("Beta Damascone")}
    assert [stock.dilution for stock in _stocks("Damascenone")] == [0.01]
    for name in ("Beta Damascone", "Damascenone"):
        limits = _record(name)["authority_limits"]
        assert limits["carrier_from_user_message"] is True
        assert limits["basis_is_project_default"] is True


@pytest.mark.parametrize("name,expected", list(OTHER_SOLVENT_EOS.items()))
def test_eo_dilutions_in_another_solvent_are_unchanged(name: str, expected: tuple) -> None:
    fraction, basis, carrier = expected
    (stock,) = [s for s in _stocks(name) if s.dilution == pytest.approx(fraction)]
    assert (stock.fraction_basis, stock.carrier) == (basis, carrier)
    assert not stock.stock_id.startswith("inventory:user-20261014:")


def test_neroli_10pct_is_aroma_and_more_in_jojoba_not_ethanol() -> None:
    record = _record("Neroli EO")
    assert record["supplier_product"]["supplier"] == "Aroma & More"
    assert record["authority_limits"]["user_said_not_ethanol"] is True
    assert not [s for s in _stocks("Neroli EO") if s.carrier == "ethanol"]


def test_alpha_damascone_10pct_is_owned_once_mixed() -> None:
    # 14 Oct "I can mix 10% Alpha Damascone" was not ownership; 15 Oct "it is mixed" is.
    owned = sorted(s.dilution for s in _stocks("Alpha Damascone") if s.status == "owned")
    assert owned == [pytest.approx(0.1), 1.0]


def test_caryophyllene_acetate_carrier_is_kennys_dep() -> None:
    limits = _record("Caryophyllene Acetate")["authority_limits"]
    assert limits["carrier_from_user_message"] is True
    assert limits["fraction_and_basis_from_prior_user_stock_record"] is True


@pytest.mark.parametrize("name", ["Sandalwood Base X3", "Kephalis", "Cedroxyde", "Hindinol"])
def test_woods_are_neat_by_kennys_word(name: str) -> None:
    assert _record(name)["authority_limits"]["fraction_basis_from_user_message"] is True


@pytest.mark.parametrize("name", ["Cedroxyde", "Hindinol"])
def test_added_woods_assert_no_supplier_or_quantity(name: str) -> None:
    limits = _record(name)["authority_limits"]
    assert limits["supplier_asserted"] is False
    assert limits["remaining_quantity_asserted"] is False


def test_sandalwood_base_requirement_row_is_owned() -> None:
    rows = [
        row for row in inventory.materialize_current_inventory().requirements
        if row.source_row == 220
    ]
    assert rows
    assert {row.disposition for row in rows} == {"OWNED"}


@pytest.mark.parametrize(
    "record_id,expected",
    [*RECORDS.items(), *ADDED_20261015.items(), *ADDED_20261015_PM.items()],
)
def test_preflight_resolves_each_stock(record_id: str, expected: tuple) -> None:
    name, fraction, basis, carrier = expected
    (stock,) = [
        s for s in _stocks(name)
        if s.dilution == pytest.approx(fraction) and s.status == "owned"
    ]
    check = _dilution_consistency_check(
        {
            "ingredients_ul": {name: 50.0},
            "dilutions": {name: fraction},
            "stock_specs": {
                name: {"fraction": fraction, "fraction_basis": basis, "carrier": carrier, "declared": True}
            },
        }
    )
    assert check.status == "PASS"
    assert check.data["issues"] == []
    assert check.data["resolved_stock_specs"][name]["stock_id"] == stock.stock_id


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c["records"][0]["stock"].__setitem__("fraction", 1.0),
        lambda c: c["records"][2]["stock"].__setitem__("carrier", "dpg"),
        lambda c: c["source"]["verbatim_user_statements"][7].__setitem__("text", "DPG"),
        lambda c: c["predecessor"].__setitem__("normalized_text_sha256", "0" * 64),
        lambda c: c["records"][4].__setitem__("record_id", "INV-USER-20261013-NEW-001"),
        lambda c: c["superseded_record_ids"].append("INV-USER-NOT-A-RECORD"),
    ],
    ids=["fraction", "carrier", "statement", "predecessor_hash", "reused_id", "superseded_missing"],
)
def test_v26_loader_rejects_mutation(mutate) -> None:
    candidate = copy.deepcopy(_head())
    mutate(candidate)
    with pytest.raises(inventory.InventoryAuthorityError):
        inventory._load_20261014_stock_corrections_successor(
            candidate, require_live_inventory_binding=False
        )


def test_v26_loader_rejects_kephalis_disagreeing_with_receipt() -> None:
    """The exact-hash check is the first guard; the receipt check must also hold on its own."""
    candidate = copy.deepcopy(_head())
    candidate["records"][3]["received_quantity_g"] = "50"
    encoded = (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    sha = hashlib.sha256(encoded).hexdigest()
    original = inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256
    try:
        inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256 = sha
        with pytest.raises(inventory.InventoryAuthorityError, match="source receipt"):
            inventory._load_20261014_stock_corrections_successor(
                candidate, require_live_inventory_binding=False
            )
    finally:
        inventory.CURRENT_USER_INVENTORY_OVERLAY_SHA256 = original


def test_neat_neroli_is_not_owned_and_only_the_jojoba_stock_remains() -> None:
    (record,) = [r for r in _head()["records"] if r["record_id"] == NEAT_NEROLI_NOT_OWNED]
    assert record["state"] == "NOT_OWNED"
    assert record["stock"] is None
    assert record["source_quote"] == "Yes."
    owned = [s for s in _stocks("Neroli EO") if s.status == "owned"]
    assert [(s.dilution, s.fraction_basis, s.carrier) for s in owned] == [
        (pytest.approx(0.1), "mass_fraction", "jojoba")
    ]
    (row,) = [
        r for r in inventory.materialize_current_inventory().requirements
        if r.source_row == 180
    ]
    assert row.disposition == "GAP"
    assert "NO NEAT NEROLI" in row.status


def test_aurantiol_ten_percent_dpg_and_neat_bottle_both_carry_his_word() -> None:
    owned = sorted(
        (s.dilution, s.fraction_basis, s.carrier, s.stock_id.split(":")[1])
        for s in _stocks("Aurantiol") if s.status == "owned"
    )
    assert owned == [
        (pytest.approx(0.1), "mass_fraction", "dpg", "user-20261014"),
        (1.0, "neat", "", "user-20261014"),
    ]


def test_damascol_and_javanol_keep_their_other_bottle() -> None:
    damascol = sorted((s.dilution, s.stock_id.split(":")[1]) for s in _stocks("Damascol") if s.status == "owned")
    assert damascol == [(pytest.approx(0.1), "user-20261014"), (1.0, "v5")]
    javanol = sorted((s.dilution, s.carrier) for s in _stocks("Javanol") if s.status == "owned")
    assert javanol == [(pytest.approx(0.2), "dpg"), (1.0, "")]
    (row,) = [r for r in inventory.materialize_current_inventory().requirements if r.source_row == 149]
    assert row.disposition == "OWNED"


def test_unknown_species_and_plant_part_are_not_asserted() -> None:
    sandalwood = _record_by_id("INV-USER-20261014-STK-027")
    assert sandalwood["authority_limits"]["botanical_species_asserted"] is False
    assert sandalwood["authority_limits"]["sku_from_catalogue_match_not_user"] is True
    assert "not stated" in sandalwood["supplier_product"]["botanical_species"]
    clove = _record_by_id("INV-USER-20261014-STK-030")
    assert clove["authority_limits"]["plant_part_asserted"] is False
    assert clove["authority_limits"]["eugenol_content_asserted"] is False


def test_freesia_hdi_is_owned_as_perfumersworld_freesia_hdl() -> None:
    (stock,) = [s for s in _stocks("Freesia HDI") if s.status == "owned"]
    record = _record_by_id("INV-USER-20261014-STK-031")
    assert record["aliases"] == ["Freesia HDL"]
    assert record["supplier_product"] == {"supplier": "PerfumersWorld", "product_name": "Freesia HDL"}
    check = _dilution_consistency_check(
        {
            "ingredients_ul": {"Freesia HDI": 20.0},
            "dilutions": {"Freesia HDI": 1.0},
            "stock_specs": {"Freesia HDI": {"fraction": 1.0, "fraction_basis": "neat", "carrier": "", "declared": True}},
        }
    )
    assert check.status == "PASS"
    assert check.data["resolved_stock_specs"]["Freesia HDI"]["stock_id"] == stock.stock_id


def _record_by_id(record_id: str) -> dict:
    (record,) = [r for r in _head()["records"] if r["record_id"] == record_id]
    return record
