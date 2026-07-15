import pytest

from engine.bottle_addition import AdditionRequest, BottleSnapshot, StockSolution
from engine.workbench import PerfumeWorkbench, WorkbenchFormulaRequest


def test_workbench_analysis_exposes_canonical_state_and_truth_labels():
    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Workbench smoke",
            ingredients_ul={"Hedione": 1000.0, "Iso E Super": 1000.0},
            dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
            batch_volume_ml=10.0,
            windows=(("opening", 0.0), ("heart", 1800.0)),
        )
    )

    payload = result.as_dict()
    assert payload["analysis_engine"] == "engine.workbench.PerfumeWorkbench"
    assert payload["formula_name"] == "Workbench smoke"
    assert payload["formula_state"]["total_raw_ul"] == 2000.0
    assert len(payload["material_oav_table"]) == 2
    assert payload["note_distribution"] == result.formula_state.note_distribution()
    assert payload["evidence"]["dose_arithmetic"]["classification"] == "EXACT"
    assert payload["evidence"]["headspace"]["classification"] == "HEURISTIC"
    assert payload["evidence"]["threshold_visibility"]["classification"] in {
        "LITERATURE_DERIVED",
        "HEURISTIC",
    }
    assert payload["evidence"]["temporal_evolution"]["classification"] == "HEURISTIC"
    assert payload["evidence"]["receptor_activation"]["classification"] == "UNKNOWN"
    assert payload["time_series"][0]["receptor_activation"] is None
    assert payload["estimated_longevity_hours"] is None
    assert payload["estimated_sillage"] is None
    assert any("solvent matrix" in item for item in payload["limitations"])


def test_workbench_discloses_unspecified_dilution_default():
    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Neat default",
            ingredients_ul={"Hedione": 100.0},
            batch_volume_ml=10.0,
            windows=(("opening", 0.0),),
        )
    )

    assert any("1.0 active fraction" in item for item in result.assumptions)


def test_workbench_delegates_exact_addition():
    result = PerfumeWorkbench().calculate_addition(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=30.0, active_material_mass_g=0.03),
            stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
            target_active_mass_fraction=0.002,
        )
    )

    assert result.evidence.classification.value == "EXACT"


@pytest.mark.parametrize(
    "request_kwargs",
    [
        dict(
            formula_name="Empty",
            ingredients_ul={},
            batch_volume_ml=10.0,
        ),
        dict(
            formula_name="Bad dose",
            ingredients_ul={"Hedione": -1.0},
            batch_volume_ml=10.0,
        ),
        dict(
            formula_name="Bad dilution",
            ingredients_ul={"Hedione": 1.0},
            dilutions={"Hedione": 1.1},
            batch_volume_ml=10.0,
        ),
    ],
)
def test_workbench_rejects_invalid_formula_inputs(request_kwargs):
    with pytest.raises(ValueError):
        WorkbenchFormulaRequest(**request_kwargs)
