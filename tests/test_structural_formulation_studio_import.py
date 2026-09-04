from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "data" / "governance" / "unified_import_structural_studio_20260904.json"
)
STUDIO_DIR = ROOT / "formulas" / "structural_formulation_studio"
README_PATH = STUDIO_DIR / "README.md"
METHOD_PATH = STUDIO_DIR / "METHOD.md"

EXPECTED_HISTORICAL_PATHS = {
    "formulas/structural_formulation_studio/AMBROFIX_STOCK_AUTHORITY_2026-08-29.md",
    "formulas/structural_formulation_studio/IMMORTELLE_AMBRE_FOSSILE_V1_30mL_24pct_THEORY.md",
    "formulas/structural_formulation_studio/IMMORTELLE_AMBRE_FOSSILE_V1_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_CLEAN_AROMATIC_SPORT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_1_YIELDING_MINERAL_WOOD_SPORT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_2_JAVANOL_VEIN_SPORT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_5_S1_1_LEMON_GINGER_PINK_PEPPER_HEART_RECUT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/PEPPER_CURRENT_PARFUM_V1_1_BLACK_PEPPER_PINK_FACET_HALO_30mL_22pct_THEORY.md",
    "formulas/structural_formulation_studio/PEPPER_CURRENT_PARFUM_V1_1_BLACK_PEPPER_PINK_FACET_HALO_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/PEPPER_CURRENT_PARFUM_V1_PINK_PEPPER_SPORT_30mL_22pct_THEORY.md",
    "formulas/structural_formulation_studio/PEPPER_CURRENT_PARFUM_V1_PINK_PEPPER_SPORT_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_2_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_2_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_1_EXACT_PINK_PEPPER_10pct_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_1_EXACT_PINK_PEPPER_10pct_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_3_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_4_AVENTUS_ABSOLU_HEDONIC_SPORT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_4_AVENTUS_ABSOLU_HEDONIC_SPORT_BLIND_VALIDATION.md",
    "formulas/structural_formulation_studio/SILVER_TRAVERSE_V1_BLIND_VALIDATION.md",
}

EXPECTED_UNLINKED_STUDIO_PATHS = {
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_5_S1_1_LEMON_GINGER_PINK_PEPPER_HEART_RECUT_30mL_20pct_THEORY.md",
    "formulas/structural_formulation_studio/LAVENDER_CURRENT_PARFUM_V1_5_S1_2_LEMON_GINGER_AERO_CEDAR_REBUILD_30mL_20pct_THEORY.md",
}


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_manifest_binds_all_53_imported_artifacts() -> None:
    manifest = _manifest()
    records = manifest["files"]
    record_paths = [record["destination_path"] for record in records]

    actual_paths = {
        "docs/superpowers/plans/2026-08-28-structural-formulation-studio.md",
        "docs/superpowers/specs/2026-08-28-structural-formulation-studio-design.md",
        *{
            path.relative_to(ROOT).as_posix()
            for path in STUDIO_DIR.glob("*.md")
            if path.is_file()
        },
    }

    assert manifest["schema_version"] == "unified_import_structural_studio_v1"
    assert manifest["scope"]["whole_module_import"] is True
    assert manifest["scope"]["plan_and_spec_file_count"] == 2
    assert manifest["scope"]["studio_markdown_file_count"] == 51
    assert manifest["scope"]["complete_package_file_count"] == 53
    assert len(records) == len(record_paths) == len(set(record_paths)) == 53
    assert set(record_paths) == actual_paths

    observed_total = 0
    for record in records:
        assert record["source_path"] == record["destination_path"]
        assert record["source_destination_match"] is True
        path = ROOT / record["destination_path"]
        payload = path.read_bytes()
        observed_total += len(payload)
        assert len(payload) == record["byte_size"]
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]

    assert observed_total == manifest["scope"]["complete_package_byte_count"]
    assert observed_total == 1_685_668


def test_manifest_separates_working_set_from_historical_tombstones() -> None:
    manifest = _manifest()
    classes = Counter(record["classification"] for record in manifest["files"])
    historical_paths = {
        record["destination_path"]
        for record in manifest["files"]
        if record["classification"] == "historical_superseded_or_authority_old"
    }
    current_paths = {
        record["destination_path"]
        for record in manifest["files"]
        if record["classification"] == "current_or_supporting"
    }

    assert classes == {
        "current_or_supporting": 32,
        "historical_superseded_or_authority_old": 21,
    }
    assert historical_paths == EXPECTED_HISTORICAL_PATHS
    assert set(
        manifest["exclusions"]["excluded_from_current_or_supporting_classification"]
    ) == EXPECTED_HISTORICAL_PATHS
    assert current_paths.isdisjoint(historical_paths)
    assert manifest["exclusions"]["package_members_omitted"] == []

    current_bytes = sum(
        record["byte_size"]
        for record in manifest["files"]
        if record["classification"] == "current_or_supporting"
    )
    historical_bytes = sum(
        record["byte_size"]
        for record in manifest["files"]
        if record["classification"] == "historical_superseded_or_authority_old"
    )
    assert current_bytes == manifest["scope"]["current_or_supporting_byte_count"]
    assert historical_bytes == manifest["scope"][
        "historical_superseded_or_authority_old_byte_count"
    ]


def test_readme_link_topology_is_preserved_without_dangling_targets() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]+\]\(([^)]+\.md)(?:#[^)]+)?\)", text)
    resolved_targets: set[Path] = set()

    for target in targets:
        assert "://" not in target
        resolved = (README_PATH.parent / target).resolve()
        assert resolved.is_file(), f"dangling README target: {target}"
        resolved_targets.add(resolved)

    expected_studio_targets = {
        path.resolve() for path in STUDIO_DIR.glob("*.md") if path != README_PATH
    }
    linked_studio_targets = {
        path for path in resolved_targets if path.parent == STUDIO_DIR.resolve()
    }
    assert linked_studio_targets <= expected_studio_targets
    assert {
        path.relative_to(ROOT).as_posix()
        for path in expected_studio_targets - linked_studio_targets
    } == EXPECTED_UNLINKED_STUDIO_PATHS
    assert len(expected_studio_targets) == 50


def test_theory_hold_and_immutable_control_authority_ceiling_is_preserved() -> None:
    manifest = _manifest()
    readme = README_PATH.read_text(encoding="utf-8")
    method = METHOD_PATH.read_text(encoding="utf-8")

    assert manifest["package_status"] == "THEORY_ONLY"
    assert manifest["admission_status"] == "HOLD"
    assert manifest["physical_test_status"] == "NOT_TESTED"
    assert manifest["runtime_status"] == "DOCUMENTATION_ONLY"
    assert all(value is False for value in manifest["authority"].values())
    assert manifest["transfer_policy"] == {
        "byte_exact": True,
        "rewritten": False,
        "compressed": False,
        "flattened": False,
        "formula_recomputed": False,
        "pipeline_rerun": False,
        "inventory_or_stock_authority_updated": False,
        "runtime_admission": False,
        "unrelated_source_changes_imported": False,
    }
    assert manifest["preservation"]["historical_formula_bytes_immutable"] is True
    assert manifest["preservation"]["historical_controls_preserved"] is True
    assert manifest["preservation"]["historical_or_rejected_artifacts_promoted"] is False
    assert manifest["preservation"]["eclipse_v4_controls_remain_immutable"] is True
    assert manifest["preservation"]["ambrofix_20260829_record_is_historical_only"] is True
    assert manifest["preservation"]["ambrofix_current_stock_authority_promoted"] is False

    assert "**Status:** THEORY ONLY / NOT TESTED / NO COMPOUNDING AUTHORIZED" in readme
    assert "**Status:** THEORY METHOD / NOT A COMPOUNDING AUTHORIZATION" in method
    assert "V4-U and V4-F remain immutable architecture-forward controls" in readme
    assert "every historical 30% Ambrofix pipeline result are HOLD/stale" in readme
    assert "visible crystals remained" in readme
    assert _sha256(README_PATH) == next(
        record["sha256"]
        for record in manifest["files"]
        if record["destination_path"]
        == "formulas/structural_formulation_studio/README.md"
    )
