from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.data_spine.loader import load_registry
from engine.inventory_parser import (
    CURRENT_INVENTORY_AUTHORITY,
    CURRENT_INVENTORY_SNAPSHOT_SHA256,
    CURRENT_INVENTORY_WORKBOOK_SHA256,
    CURRENT_USER_INVENTORY_AUTHORITY,
    CURRENT_USER_INVENTORY_OVERLAY_SHA256,
    load_current_user_inventory_overlay,
    materialize_current_inventory,
    parse_current_inventory,
    parse_inventory,
)
from engine.name_utils import names_match
from engine.optimizer.gate_aware import _inventory_stock_dilutions
from engine.pipeline.preflight import _dilution_consistency_check

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RECONCILIATION_PATH = (
    PROJECT_ROOT / "data" / "governance" / "inventory_identity_reconciliation_20260809.json"
)

RESOLVED_LABELS = {
    "Hexyl Acetate 1%": "Hexyl Acetate",
    "Helional 10% v/v": "Helional",
    "PADMA": "Phenyl Acetaldehyde Dimethyl Acetal (padma)",
    "Cinnamyl alcohol 50% in DPG": "Cinnamyl Alcohol",
    "p-Cresyl Methyl Ether (PCME)": "Para-Cresyl Methyl Ether",
    "Cypress EO": "Cypress Essential Oil",
    "Cabreuva EO": "Cabreuva Essential Oil",
    "Anisaldehyde 10%": "Anisaldehyde",
    "Ethyl Maltol 1%": "Ethyl Maltol",
    "Vietnamese Benzoin Styrax Tonkinensis resin ethanol tincture": (
        "Vietnamese Benzoin Styrax Tonkinensis Tincture 20%"
    ),
    "Turkish Storax Liquidambar Orientalis resin ethanol tincture": (
        "Turkish Storax Tincture 20%"
    ),
    "Aldehyde C-18": "Aldehyde C-18 Gamma Nonalactone",
    "Caraway Seed Oil": "Caraway Seed Essential Oil",
}
UNKNOWN_LABELS = {"Tuberose Base"}


def _manifest() -> dict[str, object]:
    return json.loads(RECONCILIATION_PATH.read_text(encoding="utf-8"))


def test_reconciliation_manifest_closes_every_original_gap_explicitly() -> None:
    payload = _manifest()
    entries = payload["entries"]
    by_label = {entry["inventory_label"]: entry for entry in entries}

    assert payload["schema_version"] == 1
    assert payload["authority"] == "IDENTITY_LABEL_ONLY"
    assert set(by_label) == set(RESOLVED_LABELS) | UNKNOWN_LABELS
    assert payload["summary"] == {
        "owned_inventory_records": 235,
        "original_exact_registry_matches": 221,
        "original_gaps": 14,
        "resolved": 13,
        "unknown": 1,
    }

    for label, canonical_name in RESOLVED_LABELS.items():
        entry = by_label[label]
        assert entry["status"] == "RESOLVED"
        assert entry["canonical_name"] == canonical_name
        assert entry["decision_basis"]

    for label in UNKNOWN_LABELS:
        entry = by_label[label]
        assert entry["status"] == "UNKNOWN"
        assert entry["canonical_name"] is None
        assert entry["decision_basis"]


def test_resolved_inventory_labels_are_exact_data_spine_aliases() -> None:
    registry = load_registry()
    listed_names = {
        record.name
        for record in parse_inventory(
            unique=True,
            include_solvents=True,
            include_unavailable=True,
        )
    }

    for label, canonical_name in RESOLVED_LABELS.items():
        assert label in listed_names
        material = registry.get(label)
        assert material is not None
        assert material.canonical_name == canonical_name


def test_ambiguous_tuberose_trade_base_remains_unresolved() -> None:
    registry = load_registry()

    assert registry.get("Tuberose Base") is None
    assert registry.get("Tuberlia Base") is not None


def _stocks_for(identity: str):
    return [
        record
        for record in materialize_current_inventory().stocks
        if record.identity_name.casefold() == identity.casefold()
    ]


def _requirements_for(identity: str):
    return [
        record
        for record in materialize_current_inventory().requirements
        if record.identity_name.casefold() == identity.casefold()
    ]


def test_v5_current_inventory_master_is_the_pinned_physical_authority() -> None:
    materialized = materialize_current_inventory()

    assert materialized.source_workbook_sha256 == CURRENT_INVENTORY_WORKBOOK_SHA256
    assert materialized.snapshot_sha256 == CURRENT_INVENTORY_SNAPSHOT_SHA256
    assert materialized.overlay_sha256 == CURRENT_USER_INVENTORY_OVERLAY_SHA256
    assert len(materialized.requirements) == 280
    assert materialized.stocks
    assert {record.authority for record in materialized.stocks} == {
        CURRENT_INVENTORY_AUTHORITY,
        CURRENT_USER_INVENTORY_AUTHORITY,
    }


def test_v5_javanol_and_user_overlay_alpha_irone_never_promote_wrong_stock() -> None:
    javanol = _stocks_for("Javanol")
    alpha = _stocks_for("Alpha Irone")

    assert len(javanol) == 1
    assert javanol[0].dilution == pytest.approx(0.20)
    assert (javanol[0].carrier, javanol[0].execution_ready) == ("dpg", True)
    assert len(alpha) == 1
    assert alpha[0].dilution == pytest.approx(0.10)
    assert (alpha[0].fraction_basis, alpha[0].carrier) == (
        "mass_fraction",
        "dep",
    )
    assert any(
        row.requested_fraction == pytest.approx(1.0) and row.disposition == "GAP"
        for row in _requirements_for("Javanol")
    )
    alpha_requirements = _requirements_for("Alpha Irone")
    assert any(
        row.requested_fraction == pytest.approx(0.10) and row.disposition == "OWNED"
        for row in alpha_requirements
    )
    assert any(
        row.requested_fraction == pytest.approx(0.30) and row.disposition == "GAP"
        for row in alpha_requirements
    )


def test_user_inventory_overlay_is_parent_pinned_and_non_rebasing() -> None:
    payload = load_current_user_inventory_overlay()

    assert payload["parent"] == {
        "authority": CURRENT_INVENTORY_AUTHORITY,
        "workbook_sha256": CURRENT_INVENTORY_WORKBOOK_SHA256,
        "snapshot_sha256": CURRENT_INVENTORY_SNAPSHOT_SHA256,
    }
    assert payload["policy"]["merge_other_task_branch"] is False
    assert payload["policy"]["formula_rebase_authorized"] is False
    assert payload["policy"]["general_substitution_authorized"] is False
    assert payload["policy"]["preserve_exact_ap_t1_cinnamon_substitution"] is True
    assert payload["policy"]["require_sub_10_ul_working_stock"] is True


def test_user_inventory_overlay_reconciles_exact_stocks_and_lost_tinctures() -> None:
    materialized = materialize_current_inventory()
    stocks = {record.identity_name.casefold(): record for record in materialized.stocks}

    expected = {
        "ethylene brassylate": (1.0, "neat", ""),
        "amber xtreme": (0.10, "mass_fraction", "dep"),
        "alpha irone": (0.10, "mass_fraction", "dep"),
        "opoponax resinoid": (0.50, "unspecified", "dep"),
        "myrrh eo": (0.50, "unspecified", "dep"),
        "osmanthus absolute": (0.10, "unspecified", "dpg"),
        "rose de mai absolute": (0.10, "unspecified", "dpg"),
        "clearwood": (1.0, "neat", ""),
        "givaudan aimi": (1.0, "neat", ""),
        "red mandarin eo": (1.0, "neat", ""),
        "rose essential oil (rosa damascena, india)": (1.0, "neat", ""),
        "benzyl salicylate": (1.0, "neat", ""),
    }
    for identity, (fraction, basis, carrier) in expected.items():
        stock = stocks[identity]
        assert stock.dilution == pytest.approx(fraction)
        assert (stock.fraction_basis, stock.carrier) == (basis, carrier)
        assert stock.authority == CURRENT_USER_INVENTORY_AUTHORITY

    assert not any(
        record.identity_name == "Alpha Irone" and record.dilution == pytest.approx(0.30)
        for record in materialized.stocks
    )
    assert not any(
        "tincture" in record.identity_name.casefold()
        or (record.source_rows == (222,) and record.dilution == pytest.approx(0.20))
        for record in materialized.stocks
    )


def test_ambrofix_recovered_bottle_is_owned_but_not_executable() -> None:
    payload = load_current_user_inventory_overlay()
    record = next(
        row for row in payload["records"] if row["record_id"] == "INV-USER-20260829-001"
    )
    mass = record["mass_balance"]

    assert mass == {
        "empty_bottle_g": 11.45,
        "final_bottle_g": 14.09,
        "contents_g": 2.64,
        "added_ethanol_g": 2.0,
        "original_30pct_stock_g": 0.64,
        "ambrofix_g": 0.192,
        "dep_g": 0.448,
        "ethanol_g": 2.0,
        "nominal_whole_bottle_mass_fraction": pytest.approx(0.192 / 2.64),
        "prior_withdrawal": False,
    }
    assert record["stock"]["execution_ready"] is False
    assert record["authority_limits"]["liquid_phase_strength_known"] is False
    assert record["authority_limits"]["active_ul_ppm_oav_math_authorized"] is False
    assert record["authority_limits"]["volume_dose_math_authorized"] is False
    assert record["authority_limits"]["formula_rebase_authorized"] is False

    ambrofix = _stocks_for("Ambrofix")
    corrected = [row for row in ambrofix if row.authority == CURRENT_USER_INVENTORY_AUTHORITY]
    assert len(corrected) == 1
    assert corrected[0].dilution == pytest.approx(0.192 / 2.64)
    assert corrected[0].fraction_basis == "mass_fraction"
    assert corrected[0].carrier == "dep + ethanol"
    assert corrected[0].execution_ready is False
    assert corrected[0].execution_hold_reason == "VISIBLE_CRYSTALS_LIQUID_PHASE_STRENGTH_UNKNOWN"
    assert corrected[0].stock_id.startswith("inventory:user-20260829:")
    assert not any(row.dilution == pytest.approx(0.30) for row in ambrofix)

    legacy_all = [row for row in parse_inventory(unique=False) if row.name == "Ambrofix"]
    legacy_available = {
        row.name for row in parse_inventory(unique=False, include_unavailable=False)
    }
    assert len(legacy_all) == 1
    assert legacy_all[0].status == "owned_non_executable"
    assert legacy_all[0].execution_ready is False
    assert "Ambrofix" not in legacy_available

    ambrox_super = _stocks_for("Ambrox Super")
    assert any(row.dilution == pytest.approx(0.33) for row in ambrox_super)
    assert not names_match("Ambrofix", "Ambrox Super")
    assert not names_match("Ambrofix", "Ambrofix Crystals")


@pytest.mark.parametrize("formula_fraction", [0.30, 0.192 / 2.64])
def test_ambrofix_release_preflight_holds_old_and_nominal_bottle_strengths(
    formula_fraction: float,
) -> None:
    formula = {
        "ingredients_ul": {"Ambrofix": 10.0},
        "dilutions": {"Ambrofix": formula_fraction},
        "stock_specs": {
            "Ambrofix": {
                "fraction": formula_fraction,
                "fraction_basis": "mass_fraction",
                "carrier": "dep + ethanol",
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "FAIL"
    assert check.data["issues"][0]["reason"] == "inventory_stock_non_executable"
    assert check.data["issues"][0]["execution_holds"] == [
        "VISIBLE_CRYSTALS_LIQUID_PHASE_STRENGTH_UNKNOWN"
    ]
    assert "Ambrofix" not in check.data["resolved_stock_specs"]


def test_bacdanol_clearwood_and_guaiacwood_current_authority_is_exact() -> None:
    payload = load_current_user_inventory_overlay()
    by_id = {record["record_id"]: record for record in payload["records"]}
    bacdanol_authority = by_id["INV-USER-20260829-002"]
    guaiacwood_authority = by_id["INV-USER-20260829-003"]

    assert bacdanol_authority["aliases"] == ["Bacnadol"]
    assert bacdanol_authority["stock"]["fraction"] == pytest.approx(1.0)
    assert bacdanol_authority["stock"]["fraction_basis"] == "neat"
    assert bacdanol_authority["stock"]["carrier"] == ""
    assert bacdanol_authority["stock"]["execution_ready"] is True
    assert bacdanol_authority["stock"]["execution_hold_reason"] == ""
    assert bacdanol_authority["authority_limits"]["formulation_selection_ready"] is True
    assert bacdanol_authority["authority_limits"]["quantitative_dosing_ready"] is True
    assert bacdanol_authority["superseded_declaration"] == {
        "fraction": None,
        "fraction_basis": "unspecified",
        "execution_hold_reason": "STOCK_FRACTION_UNSPECIFIED",
        "recorded_date": "2026-08-29",
    }

    assert guaiacwood_authority["stock"]["fraction"] == pytest.approx(1.0 / 3.0)
    assert guaiacwood_authority["stock"]["fraction_exact"] == "1/3"
    assert guaiacwood_authority["stock"]["fraction_basis"] == "mass_fraction"
    assert guaiacwood_authority["stock"]["carrier"] == "ethanol + dep"
    assert guaiacwood_authority["stock"]["nominal_components"] == [
        {
            "component": "Guaiacwood EO",
            "fraction": 1.0 / 3.0,
            "fraction_exact": "1/3",
            "role": "odorant_active",
        },
        {
            "component": "ethanol",
            "fraction": 1.0 / 3.0,
            "fraction_exact": "1/3",
            "role": "solvent",
        },
        {
            "component": "DEP",
            "fraction": 1.0 / 3.0,
            "fraction_exact": "1/3",
            "role": "carrier",
        },
    ]
    assert guaiacwood_authority["stock"]["nominal_component_fraction_basis"] == (
        "mass_fraction"
    )
    assert guaiacwood_authority["stock"]["nominal_component_total"] == pytest.approx(
        1.0
    )
    assert guaiacwood_authority["stock"]["nominal_unresolved_remainder"] == pytest.approx(
        0.0
    )
    assert guaiacwood_authority["stock"]["execution_ready"] is True
    assert guaiacwood_authority["stock"]["execution_hold_reason"] == ""
    assert guaiacwood_authority["authority_limits"]["carrier_known"] is True
    assert guaiacwood_authority["authority_limits"]["component_total_complete"] is True
    assert guaiacwood_authority["authority_limits"]["formulation_selection_ready"] is True
    assert guaiacwood_authority["authority_limits"]["quantitative_dosing_ready"] is True
    assert guaiacwood_authority["superseded_declaration"] == {
        "fraction": 0.33,
        "fraction_basis": "unspecified",
        "nominal_component_total": 0.99,
        "nominal_unresolved_remainder": 0.01,
        "execution_hold_reason": (
            "FRACTION_BASIS_UNSPECIFIED_AND_NOMINAL_COMPONENT_TOTAL_99_PERCENT"
        ),
        "recorded_date": "2026-08-30",
    }

    bacdanol = _stocks_for("Bacdanol")
    guaiacwood = _stocks_for("Guaiacwood EO")
    clearwood = _stocks_for("Clearwood")
    clearwood_authority = by_id["INV-USER-20260828-009"]
    assert len(bacdanol) == 1
    assert (bacdanol[0].dilution, bacdanol[0].fraction_basis, bacdanol[0].carrier) == (
        1.0,
        "neat",
        "",
    )
    assert bacdanol[0].status == "owned"
    assert bacdanol[0].execution_ready is True
    assert bacdanol[0].execution_hold_reason == ""
    assert len(guaiacwood) == 1
    assert guaiacwood[0].dilution == pytest.approx(1.0 / 3.0)
    assert (guaiacwood[0].fraction_basis, guaiacwood[0].carrier) == (
        "mass_fraction",
        "ethanol + dep",
    )
    assert guaiacwood[0].status == "owned"
    assert guaiacwood[0].execution_ready is True
    assert guaiacwood[0].execution_hold_reason == ""
    assert len(clearwood) == 1
    assert clearwood_authority["effective_date"] == "2026-08-29"
    assert clearwood_authority["source_thread_id"] == (
        "01a041bd-477c-75e3-be6b-7e3136bf5990"
    )
    assert clearwood_authority["authority_limits"]["quantitative_dosing_ready"] is True
    assert (clearwood[0].dilution, clearwood[0].fraction_basis, clearwood[0].carrier) == (
        1.0,
        "neat",
        "",
    )
    assert clearwood[0].execution_ready is True

    legacy_available = {
        row.name: row
        for row in parse_inventory(unique=False, include_unavailable=False)
        if row.name in {"Bacdanol", "Clearwood", "Guaiacwood EO"}
    }
    assert set(legacy_available) == {"Bacdanol", "Clearwood", "Guaiacwood EO"}
    assert legacy_available["Bacdanol"].dilution == pytest.approx(1.0)
    assert legacy_available["Bacdanol"].fraction_basis == "neat"
    assert legacy_available["Bacdanol"].execution_ready is True
    assert legacy_available["Guaiacwood EO"].dilution == pytest.approx(1.0 / 3.0)
    assert legacy_available["Guaiacwood EO"].fraction_basis == "mass_fraction"
    assert legacy_available["Guaiacwood EO"].carrier == "ethanol + dep"
    assert legacy_available["Guaiacwood EO"].execution_ready is True
    assert legacy_available["Clearwood"].execution_ready is True
    assert names_match("Bacnadol", "Bacdanol")

    guaiacwood_requirements = _requirements_for("Guaiacwood EO")
    assert any(
        row.source_row == 125
        and row.requested_fraction == pytest.approx(1.0)
        and row.disposition == "GAP"
        for row in guaiacwood_requirements
    )


@pytest.mark.parametrize(
    ("material", "fraction", "fraction_basis", "carrier"),
    [
        ("Bacnadol", 1.0, "neat", ""),
        ("Guaiacwood EO", 1.0 / 3.0, "mass_fraction", "ethanol + dep"),
    ],
)
def test_corrected_wood_stock_authority_supports_quantitative_mass_basis(
    material: str,
    fraction: float,
    fraction_basis: str,
    carrier: str,
) -> None:
    formula = {
        "ingredients_ul": {material: 10.0},
        "dilutions": {material: fraction},
        "stock_specs": {
            material: {
                "fraction": fraction,
                "fraction_basis": fraction_basis,
                "carrier": carrier,
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "PASS"
    assert check.data["resolved_stock_specs"][material]["inventory_authority"] == (
        CURRENT_USER_INVENTORY_AUTHORITY
    )


def test_clearwood_neat_current_authority_remains_quantitatively_executable() -> None:
    formula = {
        "ingredients_ul": {"Clearwood": 10.0},
        "dilutions": {"Clearwood": 1.0},
        "stock_specs": {
            "Clearwood": {
                "fraction": 1.0,
                "fraction_basis": "neat",
                "carrier": "",
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "PASS"
    assert check.data["resolved_stock_specs"]["Clearwood"]["inventory_authority"] == (
        CURRENT_USER_INVENTORY_AUTHORITY
    )

    inferred = _inventory_stock_dilutions(
        ["Bacdanol", "Guaiacwood EO", "Clearwood"],
        {},
    )
    assert inferred == {
        "Bacdanol": 1.0,
        "Guaiacwood EO": pytest.approx(1.0 / 3.0),
        "Clearwood": 1.0,
    }
    myrrh_resinoid = _requirements_for("Myrrh Resinoid")
    assert myrrh_resinoid and all(row.disposition == "GAP" for row in myrrh_resinoid)


def test_legacy_inventory_text_matches_user_overlay_availability() -> None:
    available = {
        record.identity_name: record
        for record in parse_inventory(unique=False, include_unavailable=False)
    }

    assert available["Alpha Irone"].dilution == pytest.approx(0.10)
    assert (available["Alpha Irone"].fraction_basis, available["Alpha Irone"].carrier) == (
        "mass_fraction",
        "dep",
    )
    assert available["Opoponax Resinoid"].carrier == "dep"
    assert available["Myrrh EO"].carrier == "dep"
    assert available["Red Mandarin EO"].dilution == pytest.approx(1.0)
    assert not any("tincture" in name.casefold() for name in available)


def test_v5_preserves_beta_ionone_multiple_stocks_and_preparation_state() -> None:
    beta = _stocks_for("Beta Ionone")

    assert {row.dilution for row in beta} == {1.0, 0.001}
    assert len({row.stock_id for row in beta}) == 2
    assert next(row for row in beta if row.dilution == pytest.approx(0.001)).execution_ready is False
    assert any(
        row.requested_fraction == pytest.approx(0.01)
        and row.disposition == "PREPARATION_REQUIRED"
        for row in _requirements_for("Beta Ionone")
    )


@pytest.mark.parametrize(
    ("identity", "owned_fractions", "prepared_fractions"),
    [
        ("Carrot Seed EO", {1.0}, {0.01, 0.10}),
        ("Heliotropal", {1.0}, {0.10}),
        ("Citronellol", {1.0}, {0.10}),
        ("Dihydro Beta Ionone", {1.0}, {0.10}),
    ],
)
def test_v5_neat_only_materials_require_preparation_receipts(
    identity: str,
    owned_fractions: set[float],
    prepared_fractions: set[float],
) -> None:
    stocks = _stocks_for(identity)
    requirements = _requirements_for(identity)

    assert {row.dilution for row in stocks} == owned_fractions
    assert len({row.stock_id for row in stocks}) == len(stocks)
    assert {
        row.requested_fraction
        for row in requirements
        if row.disposition == "PREPARATION_REQUIRED"
    } == prepared_fractions


def test_v5_neroli_is_owned_only_as_ten_percent_dpg() -> None:
    neroli = _stocks_for("Neroli EO")

    assert len(neroli) == 1
    assert neroli[0].dilution == pytest.approx(0.10)
    assert (neroli[0].carrier, neroli[0].execution_ready) == ("dpg", True)
    assert not any(row.dilution == pytest.approx(1.0) for row in neroli)


def test_current_inventory_parser_deduplicates_ids_not_highest_concentration() -> None:
    beta = [
        record
        for record in parse_current_inventory(unique=True, include_unavailable=False)
        if record.identity_name == "Beta Ionone"
    ]

    assert {record.dilution for record in beta} == {0.001, 1.0}
    assert len({record.stock_id for record in beta}) == 2


def test_direct_user_galbanum_correction_removes_v5_owned_stock() -> None:
    assert _stocks_for("Galbanum EO") == []

    galbanum = [
        record
        for record in parse_current_inventory(unique=False, include_unavailable=True)
        if record.identity_name == "Galbanum EO"
    ]
    assert len(galbanum) == 1
    assert galbanum[0].status == "gap"
    assert galbanum[0].execution_ready is False
    assert galbanum[0].source_rows == (114,)
    assert "USER CONFIRMED NO GALBANUM 2026-09-02" in galbanum[0].raw_name


@pytest.mark.parametrize(
    ("material", "fraction", "reason"),
    [
        ("Javanol", 1.0, "inventory_gap"),
        ("Carrot Seed EO", 0.10, "preparation_required"),
        ("Citronellol", 0.10, "preparation_required"),
        ("Dihydro Beta Ionone", 0.10, "preparation_required"),
    ],
)
def test_preflight_reports_v5_gap_or_preparation_instead_of_assuming_neat(
    material: str,
    fraction: float,
    reason: str,
) -> None:
    formula = {
        "ingredients_ul": {material: 10.0},
        "dilutions": {material: fraction},
        "stock_specs": {
            material: {
                "fraction": fraction,
                "fraction_basis": "unspecified",
                "carrier": "",
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "FAIL"
    assert check.data["issues"][0]["reason"] == reason


def test_preflight_accepts_exact_user_overlay_alpha_irone_stock() -> None:
    formula = {
        "ingredients_ul": {"Alpha Irone": 10.0},
        "dilutions": {"Alpha Irone": 0.10},
        "stock_specs": {
            "Alpha Irone": {
                "fraction": 0.10,
                "fraction_basis": "mass_fraction",
                "carrier": "dep",
                "declared": True,
            }
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "PASS"
    spec = check.data["resolved_stock_specs"]["Alpha Irone"]
    assert spec["inventory_authority"] == CURRENT_USER_INVENTORY_AUTHORITY
    assert spec["stock_id"].startswith("inventory:user-20260828:")


def test_preflight_accepts_exact_v5_neroli_and_javanol_stocks() -> None:
    formula = {
        "ingredients_ul": {"Neroli EO": 10.0, "Javanol": 5.0},
        "dilutions": {"Neroli EO": 0.10, "Javanol": 0.20},
        "stock_specs": {
            "Neroli EO": {
                "fraction": 0.10,
                "fraction_basis": "unspecified",
                "carrier": "dpg",
                "declared": True,
            },
            "Javanol": {
                "fraction": 0.20,
                "fraction_basis": "unspecified",
                "carrier": "dpg",
                "declared": True,
            },
        },
    }

    check = _dilution_consistency_check(formula)

    assert check.status == "PASS"
    assert check.data["inventory_source_workbook_sha256"] == (
        CURRENT_INVENTORY_WORKBOOK_SHA256
    )
    assert {row["material"] for row in check.data["matched_stocks"]} == {
        "Neroli EO",
        "Javanol",
    }
    for spec in check.data["resolved_stock_specs"].values():
        assert spec["authority"] == "formula_row+inventory_snapshot"
        assert spec["inventory_authority"] == CURRENT_INVENTORY_AUTHORITY
        assert spec["stock_id"].startswith("inventory:v5:")
