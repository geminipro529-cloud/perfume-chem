from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.bottle_addition import AdditionRequest, BottleSnapshot, StockSolution
from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "golden_formula_cases.json"


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _analyze(case: dict) -> dict:
    return PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name=case["formula_name"],
            ingredients_ul=case["ingredients_ul"],
            dilutions=case["dilutions"],
            stock_fraction_bases={
                name: "volume_fraction" for name in case["ingredients_ul"]
            },
            batch_volume_ml=case["batch_volume_ml"],
            windows=(("opening", 0.0), ("heart", 1800.0)),
        )
    ).as_dict()


def test_golden_formula_inventory_covers_phase_zero_scenarios():
    ids = {case["id"] for case in _fixture()["formula_cases"]}

    assert ids == {
        "simple_aromachemical",
        "natural_heavy",
        "iris",
        "leather",
        "citrus",
        "diluted_stock",
        "missing_physical_data",
        "near_ifra_boundary",
    }


@pytest.mark.parametrize("case", _fixture()["formula_cases"], ids=lambda case: case["id"])
def test_golden_formula_invariants(case):
    payload = _analyze(case)
    state = payload["formula_state"]

    assert state["total_raw_ul"] == pytest.approx(sum(case["ingredients_ul"].values()))
    assert state["total_active_ul"] == pytest.approx(
        sum(
            raw_ul * case["dilutions"][material]
            for material, raw_ul in case["ingredients_ul"].items()
        )
    )
    assert all("odt_air_ppm" in row and "oav" in row for row in payload["material_oav_table"])
    assert payload["evidence"]["dose_arithmetic"]["classification"] == "EXACT"
    assert payload["evidence"]["headspace"]["classification"] == "HEURISTIC"
    assert payload["estimated_longevity_hours"] is None
    assert payload["estimated_sillage"] is None
    assert payload["time_series"][0]["receptor_activation"] is None

    ppm_values = [
        row["active_concentrate_ppm_w_w"]
        for row in payload["material_oav_table"]
    ]
    if case["expected_ppm_status"] == "exact":
        assert all(value is not None for value in ppm_values)
        assert sum(ppm_values) == pytest.approx(1_000_000.0)
        assert payload["evidence"]["active_concentrate_ppm_w_w"]["classification"] == "EXACT"
    else:
        assert ppm_values == [None] * len(ppm_values)
        assert payload["evidence"]["active_concentrate_ppm_w_w"]["classification"] == "UNKNOWN"

    rows = {row["name"]: row for row in payload["material_oav_table"]}
    for material_name, expected in case["expected_material_outputs"].items():
        row = rows[material_name]
        assert row["vapor_ppm"] == pytest.approx(
            expected["vapor_ppm"], rel=case["modeled_output_relative_tolerance"]
        )
        if expected["oav"] is None:
            assert row["oav"] is None
        else:
            assert row["oav"] == pytest.approx(
                expected["oav"], rel=case["modeled_output_relative_tolerance"]
            )

    for material_name, expected_ppm in case.get(
        "expected_active_concentrate_ppm_w_w", {}
    ).items():
        assert rows[material_name]["active_concentrate_ppm_w_w"] == pytest.approx(
            expected_ppm, rel=1e-12
        )

    for material_name in case.get("expected_composite_materials", []):
        row = next(row for row in payload["material_oav_table"] if row["name"] == material_name)
        assert row["sources"]["oav_model"] == "modeled:natural_constituent_composite"
        assert row["oav"] is not None

    if "expected_regulatory_status" in case:
        assert payload["regulatory_assessment"]["status"] == case["expected_regulatory_status"]
        assert payload["regulatory_assessment"]["source_version"] is None


def test_diluted_stock_matches_neat_active_amount_and_headspace():
    cases = {case["id"]: case for case in _fixture()["formula_cases"]}
    neat = _analyze(cases["simple_aromachemical"])
    diluted = _analyze(cases["diluted_stock"])

    for material_name in ("Hedione", "Iso E Super"):
        neat_row = next(row for row in neat["material_oav_table"] if row["name"] == material_name)
        diluted_row = next(row for row in diluted["material_oav_table"] if row["name"] == material_name)
        assert diluted_row["active_ul"] == pytest.approx(neat_row["active_ul"])
        assert diluted_row["vapor_ppm"] == pytest.approx(neat_row["vapor_ppm"], rel=1e-9)
        assert diluted_row["oav"] == pytest.approx(neat_row["oav"], rel=1e-9)


def test_missing_density_refuses_to_invent_a_volume_plan():
    case = _fixture()["addition_cases"][0]
    result = PerfumeWorkbench().calculate_addition(
        AdditionRequest(
            bottle=BottleSnapshot(**case["bottle"]),
            stock=StockSolution(**case["stock"]),
            target_active_mass_fraction=case["target_active_mass_fraction"],
        )
    )

    assert result.exact_stock_mass_g == pytest.approx(case["expected_stock_mass_g"])
    assert result.exact_stock_volume_ul is None
    assert result.rounded_stock_volume_ul is None
    assert result.pipette_feasible is False
    assert "density" in " ".join(result.warnings).lower()


def test_missing_physical_data_is_exposed_in_formula_output():
    case = next(
        case
        for case in _fixture()["formula_cases"]
        if case["id"] == "missing_physical_data"
    )
    payload = _analyze(case)
    row = payload["material_oav_table"][0]

    assert {"density", "mw", "logp", "vp", "odt_air_ppm"} <= set(
        row["missing_fields"]
    )
    assert row["density_source"] == "fallback:default_1_g_ml"
    assert row["active_concentrate_ppm_w_w"] is None
    assert row["oav"] is None


def test_near_ifra_case_uses_a_restricted_inventory_material_at_its_limit():
    case = next(
        case
        for case in _fixture()["formula_cases"]
        if case["id"] == "near_ifra_boundary"
    )
    payload = _analyze(case)
    row = next(
        row
        for row in payload["material_oav_table"]
        if row["name"] == case["ifra_material"]
    )
    finished_pct = row["raw_ul"] / (case["batch_volume_ml"] * 1000.0) * 100.0

    assert row["ifra_limit_pct"] == pytest.approx(case["ifra_limit_pct"])
    assert finished_pct == pytest.approx(case["ifra_limit_pct"])
    assert payload["regulatory_assessment"]["status"] == "unverified"
