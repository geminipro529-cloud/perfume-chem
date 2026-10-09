from engine.emotional_mapping import score_emotional
from engine.pipeline import gates as gates_module
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig
from engine.pipeline.simulator import simulate_formula


def test_simulation_does_not_emit_family_proxy_receptor_numbers():
    frame = simulate_formula(
        {"Hedione": 1000.0},
        windows=(("opening", 0.0),),
    )[0]

    payload = frame.as_dict()
    assert payload["receptor_activation"] is None
    assert (
        payload["receptor_source"]
        == "unavailable:material_specific_assay_required"
    )
    # Model id bumped by the mass-balanced loss law (diagnosis M3), then to v4
    # because the declared matrix now evaporates (diagnosis M1a), then to v5
    # because an undeclared matrix is simulated as a default ethanol fill.
    assert payload["temporal_model"] == "dynamic_headspace_mass_balanced_loss_v6"
    assert payload["temporal_authority"] == "HEURISTIC_UNCALIBRATED"
    assert (
        payload["remaining_quantity_basis"]
        == "heuristic_remaining_stock_volume_equivalent_ul"
    )


def test_emotional_mapping_withholds_numeric_truth_without_human_observations():
    report = score_emotional({"Hedione": 1000.0, "Bergamot FCF": 500.0})

    assert report.status == "UNKNOWN"
    assert report.score is None
    assert report.mood_vector == {}
    assert report.release_authority is False
    assert report.evidence_class == "HYPOTHESIS_PRIOR_ONLY"


def test_family_and_somatosensory_libraries_cannot_authorize_release():
    state = build_formula_state({"Black Pepper EO": 100.0, "Hedione": 900.0})
    config = ReleaseGateConfig(
        audit_enabled=False,
        family_archetype="aromatic_fougere",
    )

    family = gates_module._gate_family_hedonic(state, config)
    somatic = gates_module._gate_somatosensory(state, config)

    assert family.status == "WARN"
    assert family.data["release_authority"] is False
    assert "tips" not in family.data
    assert somatic.status == "WARN"
    assert somatic.data["release_authority"] is False
    assert somatic.data["formula_effects"] is None
