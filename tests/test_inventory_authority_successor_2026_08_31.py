from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from engine.inventory_parser import (
    CURRENT_USER_INVENTORY_AUTHORITY,
    CURRENT_USER_INVENTORY_OVERLAY_PATH,
    CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    load_current_user_inventory_overlay,
    materialize_current_inventory,
    parse_inventory,
    select_material_property_stocks,
)

ROOT = Path(__file__).resolve().parents[1]
PREDECESSOR = (
    ROOT / "data" / "governance" / "inventory_user_authority_overlay_20260828.json"
)


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_successor_is_hash_pinned_to_immutable_predecessor_and_live_inventory() -> None:
    payload = load_current_user_inventory_overlay()
    raw = json.loads(CURRENT_USER_INVENTORY_OVERLAY_PATH.read_text(encoding="utf-8"))
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))

    assert payload["schema_version"] == (
        "perfume_chem_user_inventory_authority_successor_v2"
    )
    assert payload["effective_date"] == "2026-08-31"
    assert _normalized_sha256(CURRENT_USER_INVENTORY_OVERLAY_PATH) == (
        CURRENT_USER_INVENTORY_OVERLAY_SHA256
    )
    assert raw["predecessor"] == {
        "path": "data/governance/inventory_user_authority_overlay_20260828.json",
        "normalized_text_sha256": _normalized_sha256(PREDECESSOR),
        "authority": "USER_CURRENT_PHYSICAL_INVENTORY_AUTHORITY",
        "effective_date": "2026-08-28",
    }
    assert raw["source"]["inventory_text_sha256"] == _normalized_sha256(
        ROOT / "inventory.txt"
    )
    assert raw["historical_provenance"]["ambrofix_liquid"]["record_id"] == (
        "INV-USER-20260829-001"
    )
    assert raw["historical_provenance"]["ambrofix_liquid"]["mass_balance"][
        "nominal_whole_bottle_mass_fraction"
    ] == pytest.approx(0.07272727272727272)
    assert raw["carried_forward_record_ids"] == [
        record["record_id"]
        for record in predecessor["records"]
        if record["canonical_name"] != "Ambrofix"
    ]


def test_current_successor_materializes_exact_corrected_stock_contracts() -> None:
    materialized = materialize_current_inventory()
    by_name = {stock.name: stock for stock in materialized.stocks}

    magnolia = by_name["Magnolia EO"]
    assert (
        magnolia.dilution,
        magnolia.fraction_basis,
        magnolia.carrier,
        magnolia.execution_ready,
    ) == (pytest.approx(1.0), "neat", "", True)
    assert magnolia.authority == CURRENT_USER_INVENTORY_AUTHORITY
    assert magnolia.source_ref == (
        "data/governance/inventory_user_authority_overlay_20260831.json"
        "#INV-USER-20260831-001"
    )

    alpha = by_name["Alpha Irone"]
    assert (alpha.dilution, alpha.fraction_basis, alpha.carrier) == (
        pytest.approx(0.10),
        "mass_fraction",
        "dep",
    )
    predecessor_alpha_digest = hashlib.sha256(
        f"{_normalized_sha256(PREDECESSOR)}|INV-USER-20260828-003".encode()
    ).hexdigest()[:20]
    assert alpha.stock_id == f"inventory:user-20260828:{predecessor_alpha_digest}"
    black_agarwood = by_name["Black Agarwood Artificial"]
    assert (
        black_agarwood.dilution,
        black_agarwood.fraction_basis,
        black_agarwood.carrier,
    ) == (pytest.approx(0.10), "mass_fraction", "dpg")
    assert all(
        not (stock.name == "Black Agarwood Artificial" and stock.dilution == 1.0)
        for stock in materialized.stocks
    )

    castoreum = by_name["Castoreum Synthetic"]
    assert (
        castoreum.dilution,
        castoreum.fraction_basis,
        castoreum.carrier,
        castoreum.execution_ready,
        castoreum.execution_hold_reason,
    ) == (
        pytest.approx(0.10),
        "unspecified",
        "dep",
        False,
        "FRACTION_BASIS_UNSPECIFIED",
    )

    guaiacwood = by_name["Guaiacwood EO"]
    assert (
        guaiacwood.dilution,
        guaiacwood.fraction_basis,
        guaiacwood.carrier,
        guaiacwood.execution_ready,
        guaiacwood.execution_hold_reason,
    ) == (
        pytest.approx(0.33),
        "unspecified",
        "",
        False,
        "FRACTION_BASIS_AND_CARRIER_UNSPECIFIED",
    )
    assert guaiacwood.source_ref == (
        "data/governance/inventory_user_authority_overlay_20260828.json"
        "#INV-USER-20260829-003"
    )
    assert castoreum.source_ref == (
        "data/governance/inventory_user_authority_overlay_20260828.json"
        "#INV-USER-20260830-011"
    )

    assert "Ambrofix" not in by_name
    assert "Ambrofix 40%" not in by_name
    crystals = by_name["Ambrofix Crystals"]
    assert crystals.identity_name != "Ambrofix"
    assert crystals.dilution == pytest.approx(1.0)
    assert crystals.fraction_basis == "neat"
    assert crystals.execution_ready is False
    assert crystals.execution_hold_reason == "SOLID_STOCK_VOLUME_DOSING_UNBOUND"
    successor_crystals_digest = hashlib.sha256(
        f"{CURRENT_USER_INVENTORY_OVERLAY_SHA256}|INV-USER-20260831-003".encode()
    ).hexdigest()[:20]
    assert crystals.stock_id == (
        f"inventory:user-20260831:{successor_crystals_digest}"
    )

    ambergris = next(
        requirement
        for requirement in materialized.requirements
        if requirement.source_row == 24
    )
    assert ambergris.canonical_name == "Ambergris Accord"
    assert ambergris.disposition == "GAP"
    assert "LIQUID AMBROFIX OUT OF STOCK" in ambergris.status
    assert ambergris.can_prepare == ""


def test_legacy_inventory_text_reports_liquid_ambrofix_gone_but_keeps_crystals() -> None:
    records = parse_inventory(unique=False, include_unavailable=True)
    ambrofix = next(record for record in records if record.name == "Ambrofix")
    crystals = next(record for record in records if record.name == "Ambrofix Crystals")

    assert ambrofix.status == "out_of_stock"
    assert ambrofix.execution_ready is False
    assert crystals.status == "owned_non_executable"
    assert crystals.dilution == pytest.approx(1.0)
    assert crystals.execution_ready is False
    assert crystals.execution_hold_reason == "LEGACY_TEXT_CURRENT_STOCK_HOLD"


def test_magnolia_data_surfaces_resolve_only_neat_stock_and_preserve_science_holds() -> None:
    rows = yaml.safe_load((ROOT / "data" / "materials" / "M.yaml").read_text(encoding="utf-8"))
    magnolia = next(row for row in rows if row.get("canonical_name") == "Magnolia EO")

    assert magnolia["user_stock_dilution"] == "100% neat/as supplied"
    assert magnolia["user_in_inventory"] is True
    assert magnolia["cas"] is None
    assert magnolia["mw_g_mol"] is None
    assert magnolia["density_25c_g_ml"] is None
    assert magnolia["vp_25c_pa"] is None
    assert magnolia["odt_air_ppb"] is None
    assert magnolia["odt_eth_ppm"] is None
    assert magnolia["hedonic_valence"] is None
    assert magnolia["ifra_max_pct_edp"] is None
    assert magnolia["provenance"]["current_inventory_successor"] == (
        "data/governance/inventory_user_authority_overlay_20260831.json"
    )
    assert magnolia["provenance"]["stock_record"] == (
        "data/governance/inventory_user_authority_overlay_20260831.json"
        "#INV-USER-20260831-001"
    )

    properties = json.loads(
        (ROOT / "data" / "knowledge_graph" / "material_properties.json").read_text(
            encoding="utf-8"
        )
    )
    legacy = next(row for row in properties if row.get("name") == "Magnolia EO")
    assert legacy["dilution_pct"] == pytest.approx(1.0)
    assert legacy["stock_form"] == "neat/as supplied"
    assert legacy["current_inventory_successor"] == (
        "data/governance/inventory_user_authority_overlay_20260831.json"
    )
    assert legacy["stock_authority_source"].endswith("#INV-USER-20260831-001")
    assert legacy.get("mw") is None
    assert legacy.get("vp") is None
    for unresolved_field in (
        "oav_typical",
        "oav_dose_pct",
        "typical_pct_range",
        "ifra_cat4_limit_pct",
        "ifra_banned",
        "ifra_restricted",
        "ifra_standard_type",
        "max_safe_pct",
    ):
        assert legacy.get(unresolved_field) is None
    assert legacy.get("odt") is None


def test_material_property_stock_selection_is_explicit_and_prefers_execution_ready() -> None:
    materialized = materialize_current_inventory()
    selected = select_material_property_stocks(materialized.stocks)

    assert len(selected) == len({stock.name for stock in materialized.stocks})
    assert selected["Black Agarwood Artificial"].dilution == pytest.approx(0.10)
    assert selected["Black Agarwood Artificial"].execution_ready is True
    assert selected["Cashmeran 20%"].dilution == pytest.approx(1.0)
    assert selected["Cashmeran 20%"].execution_ready is True
    assert selected["Birch Tar 1%"].dilution == pytest.approx(0.10)
    assert selected["Birch Tar 1%"].execution_ready is False
