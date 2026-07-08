from engine.families.registry import all_archetypes
from engine.pipeline.gates import ReleaseGateConfig, gate_formula


EXPECTED_ARCHETYPES = {
    "aromatic_fougere.classic_reference",
    "aromatic_fougere.modern_mineral",
    "aromatic_fougere.modern_tonka_mass",
    "layton_dna.fresh_thai",
    "layton_dna.indoor_amber",
    "layton_dna.night_intense",
}


def _formula(ingredients, archetype, brief):
    total = sum(ingredients.values()) or 1.0
    return {
        "number": 1,
        "name": "Archetype Test",
        "body": "Archetype Test",
        "family_archetype": archetype,
        "ingredients_ul": dict(ingredients),
        "ingredients_pct": {k: v / total * 100.0 for k, v in ingredients.items()},
        "dilutions": {},
    }


def _gate_map(report):
    return {gate.gate: gate for gate in report.gates}


def test_family_registry_has_required_archetype_specs():
    specs = {spec.key: spec for spec in all_archetypes()}

    assert EXPECTED_ARCHETYPES <= set(specs)
    for key in EXPECTED_ARCHETYPES:
        spec = specs[key]
        assert spec.anchors
        assert spec.drift_limits
        assert spec.repair_pool
        assert spec.oav_targets


def test_classic_fougere_passes_drift_but_warns_low_novelty():
    formula = _formula(
        {
            "Bergamot FCF": 1200.0,
            "Lavender EO": 700.0,
            "Linalyl Acetate": 600.0,
            "Hedione": 900.0,
            "Coumarin": 300.0,
            "Evernyl": 10.0,
            "Iso E Super": 1500.0,
            "Vetiver EO": 300.0,
            "Habanolide": 490.0,
        },
        "aromatic_fougere.classic_reference",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "PASS"
    assert gates["novelty_vs_reference"].status == "WARN"


def test_mineral_fougere_fails_when_marine_fresh_floods_backbone():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Lavender EO": 200.0,
            "Coumarin": 50.0,
            "Evernyl": 10.0,
            "Iso E Super": 500.0,
            "Dihydromyrcenol": 3000.0,
            "Calone": 1000.0,
            "Floralozone": 640.0,
        },
        "aromatic_fougere.modern_mineral",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "FAIL"
    assert "marine_not_shower_gel" in gates["family_drift_detector"].detail


def test_tonka_fougere_fails_when_it_becomes_fruity_gourmand_amber():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Lavender EO": 400.0,
            "Coumarin": 500.0,
            "Evernyl": 10.0,
            "Iso E Super": 700.0,
            "Apritone": 1500.0,
            "Hexyl Acetate": 800.0,
            "Vanillin": 800.0,
            "Ethyl Vanillin": 690.0,
        },
        "aromatic_fougere.modern_tonka_mass",
        "aromatic_fougere",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="aromatic_fougere", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "FAIL"
    assert "fruit_not_amber_fruity" in gates["family_drift_detector"].detail


def test_layton_fails_when_moss_coumarin_turns_it_into_fougere():
    formula = _formula(
        {
            "Bergamot FCF": 600.0,
            "Apritone": 80.0,
            "Hexyl Acetate": 50.0,
            "Ethyl 2-Methylbutyrate": 20.0,
            "Terpinyl Acetate": 100.0,
            "Eugenol": 20.0,
            "Hedione": 500.0,
            "Iso E Super": 1000.0,
            "Ambrox Super": 1000.0,
            "Sandalore": 500.0,
            "Habanolide": 500.0,
            "Vanillin": 300.0,
            "Coumarin": 700.0,
            "Evernyl": 200.0,
            "Vetiver EO": 430.0,
        },
        "layton_dna.fresh_thai",
        "layton_dna",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="layton_dna", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "FAIL"
    assert "fougere_shadow_not_mossy" in gates["family_drift_detector"].detail


def test_layton_fails_when_signature_top_and_base_disappear():
    formula = _formula(
        {
            "Bergamot FCF": 2000.0,
            "Lavender EO": 1000.0,
            "Hedione": 1000.0,
            "Vanillin": 100.0,
            "Ethyl Vanillin": 100.0,
            "Linalyl Acetate": 900.0,
            "Dihydromyrcenol": 900.0,
        },
        "layton_dna.fresh_thai",
        "layton_dna",
    )
    gates = _gate_map(gate_formula(formula, ReleaseGateConfig(brief="layton_dna", audit_enabled=False)))

    assert gates["family_drift_detector"].status == "FAIL"
    assert "layton_apple_hook" in gates["family_drift_detector"].detail
    assert "layton_cardamom_like_spice" in gates["family_drift_detector"].detail
