"""Catalogue projection must not erase exact synthetic KG metadata."""

from copy import deepcopy

import pytest

import engine.confidence as confidence_module
import engine.ingredient_catalog as catalog_module
import engine.ingredient_intelligence as intelligence_module
import engine.optimizer.models as models


def _synthetic_record(name, formula):
    return {
        "name": name.upper(),
        "formula_str": formula,
        "material_kind": "UNRESOLVED",
        "mw": 999.0,
        "vp": 9.0,
        "clp": 9.0,
        "odt": 9.0,
        "carles_position": "older position",
        "bp": 285.0,
        "sar_class": "existing class",
        "odor_family": "existing family",
        "roudnitska_function": "existing function",
        "jellinek_quadrant": "existing quadrant",
    }


def _catalog_record(name, **overrides):
    return {
        "name": name,
        "alt_name": name,
        "best_with": [],
        "avoid": [],
        "mw": 226.31,
        "vp": 0.1,
        "clp": 2.7,
        "odt": 0.5,
        "carles_position": "catalogue position",
        "source": "ingredient_catalog",
        **overrides,
    }


def _supplement(monkeypatch, records, catalog_record, aliases=()):
    # Isolate the two input projections; the real supplement/alias code runs.
    monkeypatch.setattr(intelligence_module, "get_all_profiles", lambda: {})
    key = catalog_record["name"].lower()
    payload = {
        "material": catalog_record,
        "catalog": {
            "identity_key": key,
            "aliases": list(aliases),
            "ground_truth_identity": {},
        },
    }
    monkeypatch.setattr(
        catalog_module, "load_ingredient_catalog_index", lambda: {key: payload}
    )
    return models._supplement_material_index(
        {record["name"].lower(): record for record in records}
    )


@pytest.mark.parametrize(
    "name,formula",
    [("Hedione", "C\u2081\u2083H\u2082\u2082O\u2083"), ("Iso E Super", "C\u2081\u2086H\u2082\u2086O")],
)
def test_exact_synthetic_retains_missing_fields_without_changing_catalogue_values(
    monkeypatch, name, formula
):
    original = _synthetic_record(name, formula)
    original_before = deepcopy(original)
    catalog = _catalog_record(name)
    catalog_before = deepcopy(catalog)

    index = _supplement(monkeypatch, [original], catalog)
    material = index[name.lower()]

    assert material["bp"] == 285.0
    assert material["sar_class"] == "existing class"
    assert material["odor_family"] == "existing family"
    assert material["roudnitska_function"] == "existing function"
    assert material["jellinek_quadrant"] == "existing quadrant"
    assert {key: material[key] for key in catalog_before} == catalog_before
    assert original == original_before
    assert catalog == catalog_before


def test_explicit_catalogue_nulls_and_semantics_are_not_backfilled(monkeypatch):
    original = _synthetic_record("Hedione", "C13H22O3")
    catalog = _catalog_record(
        "Hedione", mw=None, odt=None, bp=None, sar_class=None,
        odor_family="catalogue family",
    )

    material = _supplement(monkeypatch, [original], catalog)["hedione"]

    assert material["mw"] is None
    assert material["odt"] is None
    assert material["bp"] is None
    assert material["sar_class"] is None
    assert material["odor_family"] == "catalogue family"
    assert material["roudnitska_function"] == "existing function"


@pytest.mark.parametrize(
    "name,kind,formula",
    [
        ("Geranium EO", "NATURAL_MIXTURE", "C10H18O"),
        ("Lilyreal ND", "OPAQUE_PREBLEND", "C12H16O2"),
        ("Lavender EO (BONTAUX SAS)", "UNRESOLVED", "C10H18O"),
        ("Unresolved material", "UNRESOLVED", ""),
    ],
)
def test_natural_opaque_and_unknown_chemistry_are_not_enriched(
    monkeypatch, name, kind, formula
):
    original = _synthetic_record(name, formula)
    original["material_kind"] = kind
    catalog = _catalog_record(name, mw=None, vp=None, clp=None, odt=None)

    material = _supplement(monkeypatch, [original], catalog)[name.lower()]

    assert material == catalog
    assert "bp" not in material
    assert "sar_class" not in material


@pytest.mark.parametrize(
    "donor_name,catalogue_name",
    [("Geranium Flower EO", "Geranium EO"), ("Hedione", "Hedione HC")],
)
def test_nearby_natural_and_trade_grade_names_do_not_supply_fields(
    monkeypatch, donor_name, catalogue_name
):
    original = _synthetic_record(donor_name, "C13H22O3")
    catalog = _catalog_record(catalogue_name, mw=None, vp=None, clp=None)

    material = _supplement(monkeypatch, [original], catalog)[catalogue_name.lower()]

    assert material == catalog
    assert "bp" not in material


def test_catalogue_aliases_use_the_same_enriched_exact_record(monkeypatch):
    original = _synthetic_record("Hedione", "C13H22O3")
    catalog = _catalog_record("Hedione")

    index = _supplement(
        monkeypatch, [original], catalog, aliases=("methyl dihydrojasmonate",)
    )

    assert index["methyl dihydrojasmonate"] is index["hedione"]
    assert index["methyl dihydrojasmonate"]["bp"] == 285.0


def test_catalogue_only_records_and_aliases_still_resolve(monkeypatch):
    catalog = _catalog_record("Catalogue Only Material")

    index = _supplement(monkeypatch, [], catalog, aliases=("catalogue only alias",))

    assert index["catalogue only alias"] == catalog
    assert index["catalogue only material"] is index["catalogue only alias"]
    assert "bp" not in index["catalogue only material"]


def test_metadata_retention_does_not_create_prediction_calibration(
    monkeypatch, tmp_path
):
    original = _synthetic_record("Hedione", "C13H22O3")
    index = _supplement(monkeypatch, [original], _catalog_record("Hedione"))
    monkeypatch.setattr(models, "_MATERIALS_BY_NAME", index)
    models._lookup_material.cache_clear()
    monkeypatch.setattr(confidence_module, "DB_PATH", tmp_path / "absent.sqlite")
    monkeypatch.setenv("PERFUME_CALIBRATION_PATH", str(tmp_path / "absent.jsonl"))
    try:
        scorer = confidence_module.ConfidenceScorer()
        score = scorer.score({"Hedione": 1.0})
        readiness = scorer.outcome_readiness()
    finally:
        models._lookup_material.cache_clear()

    assert score["data_confidence"] == 100.0
    assert score["prediction_confidence"] == 5.0
    assert readiness["outcome_count"] == 0
    assert readiness["calibration_ready"] is False
    assert readiness["calibration_practical"] is False
