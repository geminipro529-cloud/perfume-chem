from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.oav_intelligence import analyze_oav_intelligence
from engine.pipeline.simulator import simulate_formula


def _analyze(ingredients, family_archetype=""):
    state = build_formula_state(
        ingredients,
        {},
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    frames = simulate_formula(
        ingredients,
        {},
        batch_volume_ml=30.0,
        temperature_K=305.0,
    )
    return analyze_oav_intelligence(state, frames, family_archetype)


def test_oav_intelligence_contract_and_family_mapping():
    result = _analyze(
        {
            "Bergamot FCF": 1200.0,
            "Lavender EO": 900.0,
            "Hedione": 1200.0,
            "Coumarin": 300.0,
            "Iso E Super": 1500.0,
        },
        family_archetype="aromatic_fougere",
    )

    payload = result.as_dict()

    assert payload["mapped_family"] == "aromatic_fougere"
    assert set(payload) == {
        "family_archetype",
        "mapped_family",
        "family_target_alignment",
        "material_cliff_findings",
        "shift_zone_findings",
        "balance_reports",
        "performance_projection",
        "synergy_findings",
        "intelligence_status",
        "intelligence_blocking_reasons",
        "intelligence_warning_reasons",
        "unmapped_materials",
    }
    assert payload["family_target_alignment"] == {
        "family": "aromatic_fougere",
        "state": "WITHHELD_LEGACY_HEDONIC_HEURISTIC",
        "materials": [],
        "reason": (
            "Family OAV targets, cliffs, pitfalls, and performance tips came from "
            "an unvalidated hedonic heuristic library."
        ),
    }
    assert payload["material_cliff_findings"] == []
    hedione = next(
        row
        for row in payload["performance_projection"]["materials"]
        if row["mapped_material"].casefold() == "hedione"
    )
    assert "bangkok_shift" not in hedione
    assert "paris_vp_pa" not in hedione
    assert "paris_half_life_min" not in hedione
    assert hedione["formula_temperature_shift"]["vp_ratio"] > 1.0
    assert hedione["formula_temperature_shift"]["half_life_projection"] is None
    assert "not rescaled" in hedione["formula_temperature_shift"]["limitation"]


def test_oav_intelligence_surfaces_shift_zone_failures():
    result = _analyze(
        {
            "Calone": 5000.0,
            "Dihydromyrcenol": 1000.0,
        },
        family_archetype="marine_aquatic",
    )

    assert result.intelligence_status == "FAIL"
    assert any(item["material"].lower() == "calone" for item in result.shift_zone_findings)
    assert result.intelligence_blocking_reasons


def test_oav_intelligence_surfaces_synergy_and_performance_warnings():
    result = _analyze(
        {
            "Dihydromyrcenol": 2500.0,
            "Hedione": 1500.0,
            "Bergamot FCF": 1200.0,
            "Iso E Super": 800.0,
        },
        family_archetype="citrus",
    )

    positive = result.synergy_findings["positive"]
    assert any(
        row["mapped_material_a"] == "Hedione" and row["mapped_material_b"] == "Bergamot FCF"
        for row in positive
    )
    assert result.performance_projection["warnings"]


def test_oav_intelligence_maps_historical_archetypes_to_supported_family_targets():
    cases = {
        "citrus_classical.4711_reference": "citrus",
        "citrus_aromatic.eau_sauvage_reference": "citrus",
        "floral_bouquet.quelques_fleurs_reference": "floral_jasmine",
        "floral_muguet.diorissimo_reference": "floral_jasmine",
        "fougere_classical.fougere_royale_reference": "aromatic_fougere",
        "chypre_classical.coty_reference": "chypre",
        "chypre_leathery.bandit_reference": "chypre",
        "oriental_classical.shalimar_reference": "amber_oriental",
        "oriental_soft.jicky_reference": "amber_oriental",
        "oriental_floral.lheure_bleue_reference": "amber_oriental",
    }

    for archetype, expected in cases.items():
        result = _analyze(
            {
                "Bergamot FCF oil Sicilian": 600.0,
                "Hedione": 500.0,
                "Patchouli EO": 300.0,
                "Iso E Super": 500.0,
            },
            family_archetype=archetype,
        )
        assert result.as_dict()["mapped_family"] == expected


def test_oav_intelligence_maps_woody_floral_musk_before_generic_floral():
    result = _analyze(
        {
            "Hedione": 900.0,
            "Iso E Super": 1500.0,
            "Ethylene Brassylate": 500.0,
        },
        family_archetype="woody_floral_musk.classic",
    )

    assert result.as_dict()["mapped_family"] == "woody_amber"


def test_gate_formula_exposes_oav_intelligence_gate():
    report = gate_formula(
        {
            "number": 1,
            "name": "Marine Intelligence Gate",
            "body": "Marine Intelligence Gate",
            "family_archetype": "marine_aquatic",
            "ingredients_ul": {
                "Calone": 5000.0,
                "Dihydromyrcenol": 1000.0,
            },
            "ingredients_pct": {
                "Calone": 83.333333,
                "Dihydromyrcenol": 16.666667,
            },
            "dilutions": {},
        },
        ReleaseGateConfig(brief="generic", family_archetype="marine_aquatic", audit_enabled=False),
    )

    gate_map = {gate.gate: gate for gate in report.gates}
    assert "oav_intelligence" in gate_map
    assert gate_map["oav_intelligence"].status in {"WARN", "FAIL"}
