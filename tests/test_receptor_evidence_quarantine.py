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
