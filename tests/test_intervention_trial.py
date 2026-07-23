import pytest

from engine.bottle_addition import BottleSnapshot, PipetteProfile, StockSolution
from engine.intervention_trial import (
    BatchRescueContext,
    InterventionTrialRequest,
    plan_finished_batch_rescue,
    plan_intervention_trial,
)


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


def _rescue_context(**overrides):
    values = {
        "batch_id": "batch-001",
        "formula_state_sha256": "a" * 64,
        "immutable_ledger_complete": True,
        "previous_additions_complete": True,
        "observed_defect": "iris heart is too quiet",
        "preserve_attributes": ("clean opening", "dry woody base"),
        "stock_identity": "Hedione",
        "stock_fraction_basis": "mass_fraction",
        "stock_fraction_source": "gravimetric preparation record",
        "stock_carrier": "DPG",
        "stock_density_source": "measured at 25 C",
        "bottle_mass_source": "calibrated balance",
        "product_category": "fine fragrance leave-on",
    }
    values.update(overrides)
    return BatchRescueContext(**values)


def test_finished_batch_rescue_only_authorizes_a_separate_aliquot():
    plan = plan_finished_batch_rescue(_rescue_context(), _request())

    assert plan.readiness.status == "ALIQUOT_TRIAL_READY"
    assert plan.readiness.separate_aliquot_plan_authorized is True
    assert plan.readiness.source_bottle_addition_authorized is False
    assert plan.readiness.skin_application_authorized is False
    assert plan.trial is not None
    assert plan.trial.evaluation_protocol.control == "unaltered bottle aliquot"


def test_finished_batch_rescue_withholds_dose_when_provenance_is_incomplete():
    context = _rescue_context(
        formula_state_sha256="unknown",
        immutable_ledger_complete=False,
        previous_additions_complete=False,
        stock_fraction_basis="unspecified",
        stock_density_source="",
    )

    plan = plan_finished_batch_rescue(context, _request())

    assert plan.readiness.status == "NEEDS_INPUT"
    assert plan.trial is None
    assert plan.readiness.source_bottle_addition_authorized is False
    assert {
        "formula_state_sha256",
        "immutable_ledger_complete",
        "previous_additions_complete",
        "stock_fraction_basis",
        "stock_density_source",
    } <= set(plan.readiness.missing_inputs)


def test_finished_batch_rescue_rejects_candidate_stock_identity_mismatch():
    plan = plan_finished_batch_rescue(
        _rescue_context(stock_identity="Alpha Irone"),
        _request(material="Hedione"),
    )

    assert plan.trial is None
    assert "stock_identity_matches_candidate" in plan.readiness.missing_inputs
