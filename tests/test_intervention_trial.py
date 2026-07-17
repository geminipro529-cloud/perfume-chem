import pytest

from engine.bottle_addition import BottleSnapshot, PipetteProfile, StockSolution
from engine.intervention_trial import InterventionTrialRequest, plan_intervention_trial


def _request(material: str = "Hedione", *, matrix: str = "ethanol"):
    return InterventionTrialRequest(
        brief_name="Iris Cathedral",
        material=material,
        bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
        stock=StockSolution(active_mass_fraction=0.10, density_g_ml=1.0),
        target_active_ppm_w_w=100.0,
        threshold_matrix=matrix,
        pipette=PipetteProfile(
            minimum_ul=1.0,
            increment_ul=1.0,
            maximum_single_step_ul=1000.0,
        ),
        evaluation_attribute="iris clarity",
        evaluation_times_seconds=(0, 300, 1800, 7200, 14400),
    )


def test_trial_plan_uses_rounded_mass_balance_ppm_odt_and_oav():
    result = plan_intervention_trial(_request())

    assert result.addition.pipette_feasible is True
    assert result.addition.rounded_stock_volume_ul == 10.0
    assert result.achieved_active_ppm_w_w == pytest.approx(99.9000999)
    assert result.odt_ethanol_ppm == 0.01
    assert result.oav == pytest.approx(9990.00999)
    assert result.safety_status.value == "unverified"
    assert result.evidence["odt_oav"].classification.value == "LITERATURE_DERIVED"
    assert result.evaluation_protocol.design == "paired_directional_comparison"
    assert result.evaluation_protocol.attribute == "iris clarity"
    assert result.evaluation_protocol.times_seconds[-1] == 14400


def test_trial_plan_withholds_monomolecular_oav_for_composite_materials():
    result = plan_intervention_trial(_request("Orris Liquid"))

    assert result.odt_ethanol_ppm is None
    assert result.oav is None
    assert result.evidence["odt_oav"].classification.value == "UNKNOWN"
    assert any("composite" in warning for warning in result.warnings)


def test_trial_plan_withholds_oav_when_threshold_matrix_is_unknown():
    result = plan_intervention_trial(_request(matrix="unknown"))

    assert result.odt_ethanol_ppm is None
    assert result.oav is None
    assert any("matrix" in warning for warning in result.warnings)


def test_trial_plan_rejects_invalid_target_ppm():
    with pytest.raises(ValueError, match="target_active_ppm_w_w"):
        InterventionTrialRequest(
            brief_name="Iris Cathedral",
            material="Hedione",
            bottle=BottleSnapshot(total_mass_g=10.0, active_material_mass_g=0.0),
            stock=StockSolution(active_mass_fraction=0.10),
            target_active_ppm_w_w=0.0,
            evaluation_attribute="iris clarity",
        )
