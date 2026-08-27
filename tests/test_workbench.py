import pytest

from engine.bottle_addition import AdditionRequest, BottleSnapshot, StockSolution
from engine.intervention_hypotheses import InterventionHypothesisRequest
from engine.intervention_trial import InterventionTrialRequest
from engine.interventions import BriefConstraints, InterventionRequest
from engine.mixture import MixtureComponent, MixtureRole
from engine.quantities import Density, MolarMass, Volume
from engine.safety_assessment import SafetyAssessmentRequest
from engine.workbench import CalculationMode, PerfumeWorkbench, WorkbenchFormulaRequest


def test_workbench_analysis_exposes_canonical_state_and_truth_labels():
    result = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Workbench smoke",
            ingredients_ul={"Hedione": 1000.0, "Iso E Super": 1000.0},
            dilutions={"Hedione": 1.0, "Iso E Super": 1.0},
            stock_fraction_bases={
                "Hedione": "volume_fraction",
                "Iso E Super": "volume_fraction",
            },
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
    assert payload["evidence"]["note_distribution"]["classification"] == "HEURISTIC"
    assert payload["evidence"]["estimated_longevity_hours"]["classification"] == "UNKNOWN"
    assert payload["evidence"]["estimated_sillage"]["classification"] == "UNKNOWN"
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
    assert result.evidence["dose_arithmetic"].classification.value == "HEURISTIC"
    assert result.formula_state.materials[0].active_finished_product_ppm_w_w is None


def test_strict_workbench_requires_explicit_stock_fraction_and_matrix():
    with pytest.raises(ValueError, match="strict mode requires explicit dilutions"):
        WorkbenchFormulaRequest(
            formula_name="Strict missing dilution",
            ingredients_ul={"Hedione": 100.0},
            batch_volume_ml=10.0,
            mode=CalculationMode.STRICT,
        )

    with pytest.raises(ValueError, match="strict mode requires an explicit finished-product matrix"):
        WorkbenchFormulaRequest(
            formula_name="Strict missing matrix",
            ingredients_ul={"Hedione": 100.0},
            dilutions={"Hedione": 1.0},
            batch_volume_ml=10.0,
            mode=CalculationMode.STRICT,
        )


def test_strict_workbench_requires_fraction_basis_and_decomposed_stock_carrier():
    ethanol = MixtureComponent(
        name="Ethanol",
        role=MixtureRole.SOLVENT,
        volume=Volume.from_ml(9.0),
        density=Density.from_g_ml(0.789),
        molar_mass=MolarMass.from_g_mol(46.06844),
    )
    with pytest.raises(ValueError, match="stock fraction basis"):
        WorkbenchFormulaRequest(
            formula_name="Strict missing fraction basis",
            ingredients_ul={"Alpha Irone": 100.0},
            dilutions={"Alpha Irone": 1.0},
            batch_volume_ml=10.0,
            matrix_components=(ethanol,),
            mode=CalculationMode.STRICT,
        )
    with pytest.raises(ValueError, match="carrier decomposition"):
        WorkbenchFormulaRequest(
            formula_name="Strict undecomposed stock",
            ingredients_ul={"Alpha Irone": 1000.0},
            dilutions={"Alpha Irone": 0.10},
            stock_fraction_bases={"Alpha Irone": "volume_fraction"},
            batch_volume_ml=10.0,
            matrix_components=(ethanol,),
            mode=CalculationMode.STRICT,
        )


def test_workbench_delegates_exact_addition():
    result = PerfumeWorkbench().calculate_addition(
        AdditionRequest(
            bottle=BottleSnapshot(total_mass_g=30.0, active_material_mass_g=0.03),
            stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
            target_active_mass_fraction=0.002,
        )
    )

    assert result.evidence["stock_mass_arithmetic"].classification.value == "EXACT"
    assert result.evidence["uncertainty_propagation"].classification.value == (
        "LITERATURE_DERIVED"
    )


def test_workbench_delegates_safety_and_intervention_contracts():
    workbench = PerfumeWorkbench()

    safety = workbench.assess_safety(
        SafetyAssessmentRequest(category="4", concentrations={}, dataset=None)
    )
    interventions = workbench.rank_interventions(
        InterventionRequest(
            batch_mass_g=10.0,
            brief=BriefConstraints(name="Empty brief"),
            inventory={},
            candidates=(),
        )
    )

    assert safety.status.value == "unverified"
    assert interventions.ranked == ()


def test_workbench_delegates_inventory_grounded_hypotheses():
    result = PerfumeWorkbench().generate_intervention_hypotheses(
        InterventionHypothesisRequest(
            brief_name="Iris Cathedral",
            observations=("needs texture",),
            family="iris",
            available_materials=("Heliotropal",),
        )
    )

    assert result.brief_name == "Iris Cathedral"
    assert result.evidence.classification.value == "HEURISTIC"
    assert all(item.materials == ("Heliotropal",) for item in result.hypotheses)


def test_workbench_delegates_intervention_trial_planning():
    result = PerfumeWorkbench().plan_intervention_trial(
        InterventionTrialRequest(
            brief_name="Iris Cathedral",
            material="Hedione",
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=0.10),
            target_active_ppm_w_w=100.0,
            evaluation_attribute="iris clarity",
        )
    )

    assert result.achieved_active_ppm_w_w == pytest.approx(100.0)
    assert result.oav is None
    assert result.safety_status.value == "unverified"


def test_workbench_rejects_material_names_that_collide_after_normalization():
    with pytest.raises(ValueError, match="collide after trimming"):
        WorkbenchFormulaRequest(
            formula_name="Collision",
            ingredients_ul={"Hedione": 60.0, " Hedione ": 40.0},
            batch_volume_ml=10.0,
        )


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


def test_workbench_explicit_solvent_changes_finished_mixture_headspace():
    workbench = PerfumeWorkbench()
    legacy = workbench.analyze(
        WorkbenchFormulaRequest(
            formula_name="Odorant-only compatibility",
            ingredients_ul={"Alpha Irone": 1000.0},
            dilutions={"Alpha Irone": 1.0},
            stock_fraction_bases={"Alpha Irone": "volume_fraction"},
            batch_volume_ml=10.0,
            windows=(("opening", 0.0),),
        )
    ).as_dict()
    finished = workbench.analyze(
        WorkbenchFormulaRequest(
            formula_name="Finished mixture",
            ingredients_ul={"Alpha Irone": 1000.0},
            dilutions={"Alpha Irone": 1.0},
            batch_volume_ml=10.0,
            matrix_components=(
                MixtureComponent(
                    name="Ethanol",
                    role=MixtureRole.SOLVENT,
                    volume=Volume.from_ml(9.0),
                    density=Density.from_g_ml(0.789),
                    molar_mass=MolarMass.from_g_mol(46.06844),
                ),
            ),
            windows=(("opening", 0.0),),
        )
    ).as_dict()

    legacy_row = legacy["material_oav_table"][0]
    finished_row = finished["material_oav_table"][0]
    assert finished_row["mole_fraction"] < legacy_row["mole_fraction"]
    assert finished_row["vapor_ppm"] < legacy_row["vapor_ppm"]
    assert finished_row["active_finished_product_ppm_w_w"] < 200_000.0
    assert finished["formula_state"]["matrix_moles"] > 0
    assert finished["mixture_state"]["complete"] is True
    assert finished["evidence"]["finished_mixture"]["classification"] == "EXACT"
    assert finished["calculation_mode"] == "compatibility"


def test_workbench_withholds_matrix_physics_when_solvent_data_is_missing():
    payload = PerfumeWorkbench().analyze(
        WorkbenchFormulaRequest(
            formula_name="Incomplete matrix",
            ingredients_ul={"Hedione": 1000.0},
            batch_volume_ml=10.0,
            matrix_components=(
                MixtureComponent(
                    name="Unknown solvent",
                    role=MixtureRole.SOLVENT,
                    volume=Volume.from_ml(9.0),
                    density=None,
                    molar_mass=None,
                ),
            ),
            windows=(("opening", 0.0),),
        )
    ).as_dict()

    assert payload["mixture_state"]["complete"] is False
    assert payload["evidence"]["finished_mixture"]["classification"] == "UNKNOWN"
    assert any("Unknown solvent.density_g_ml" in item for item in payload["limitations"])
