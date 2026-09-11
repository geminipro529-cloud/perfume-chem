"""Regression tests for the extracted engine material data.

``ODT_DATA`` / ``ODT_VERIFICATION`` (odor_thresholds) and ``_PROFILES`` /
``_ALIASES`` / ... (ingredient_intelligence) were moved out of Python source into
``data/engine_data/*.json``. These tests lock the extraction so the datasets stay
present, loadable, and the expected size.
"""
from __future__ import annotations

from engine.material_data_loader import engine_data_path, load_engine_data

# Exact literal sizes captured at extraction time (2026-09-11).
ODOR_THRESHOLDS_SIZES = {
    "ODT_DATA": 301,
    "ODT_VERIFICATION": 276,
    "_VERIFIED_ODT": 102,
    "NOTE_TO_MATERIALS": 15,
}
INGREDIENT_INTELLIGENCE_SIZES = {
    "_PROFILES": 267,
    "_ALIASES": 110,
    "_TRANSPARENCY_SCORES": 104,
    "_CHEMICAL_FAMILY_MAP": 82,
    "_OR_FAMILY_OVERRIDES": 240,
    "_ACTIVITY_COEF_OVERRIDES": 207,
    "_HEDONIC_OVERRIDES": 98,
    "_CHAR_TO_FAMILY": 17,
    "_VERIFIED_VP": 21,
    "_VERIFIED_VP_SOURCE": 8,
}


def test_engine_data_files_exist():
    assert engine_data_path("odor_thresholds").exists()
    assert engine_data_path("ingredient_intelligence").exists()


def test_odor_thresholds_datasets_extracted_with_expected_size():
    for key, size in ODOR_THRESHOLDS_SIZES.items():
        data = load_engine_data("odor_thresholds", key)
        assert isinstance(data, dict)
        assert len(data) == size, key


def test_ingredient_intelligence_datasets_extracted_with_expected_size():
    for key, size in INGREDIENT_INTELLIGENCE_SIZES.items():
        data = load_engine_data("ingredient_intelligence", key)
        assert isinstance(data, dict)
        assert len(data) == size, key


def test_modules_expose_loaded_objects_with_runtime_mutations_applied():
    import engine.ingredient_intelligence as ii
    import engine.odor_thresholds as ot

    assert isinstance(ot.ODT_DATA, dict) and ot.ODT_DATA
    assert isinstance(ot.ODT_VERIFICATION, dict) and ot.ODT_VERIFICATION
    assert isinstance(ii._PROFILES, dict) and ii._PROFILES
    # Runtime mutations still apply on top of the loaded literals.
    assert len(ot.ODT_DATA) >= ODOR_THRESHOLDS_SIZES["ODT_DATA"]
    assert len(ii._PROFILES) >= INGREDIENT_INTELLIGENCE_SIZES["_PROFILES"]
    # Known sentinel entries survive the move.
    assert ot.lookup_odt_entry("Bergamot FCF") is not None
    assert ii.get_profile("Hedione") is not None
