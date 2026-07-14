from engine.pipeline.gates import ReleaseGateConfig, gate_formula


def _gate_status(report, gate_name: str) -> str:
    for gate in report.gates:
        if gate.gate == gate_name:
            return gate.status
    raise AssertionError(f"Gate {gate_name!r} not found")


def test_nonmatching_family_skeleton_gates_become_not_applicable():
    formula = {
        "number": 1,
        "name": "Citrus Trial",
        "ingredients_ul": {
            "Bergamot FCF oil Sicilian": 900.0,
            "Grapefruit FCF": 180.0,
            "Hedione": 700.0,
            "Petitgrain EO": 240.0,
            "Iso E Super": 500.0,
            "Galaxolide": 400.0,
        },
        "dilutions": {
            "Galaxolide": 0.5,
        },
        "family_archetype": "citrus",
    }
    report = gate_formula(formula, ReleaseGateConfig(family_archetype="citrus", audit_enabled=False))

    assert _gate_status(report, "fougere_skeleton") == "PASS"
    assert _gate_status(report, "chypre_skeleton") == "PASS"
    assert _gate_status(report, "oriental_skeleton") == "PASS"
    assert _gate_status(report, "aquatic_skeleton") == "PASS"
    assert _gate_status(report, "gourmand_skeleton") == "PASS"


def test_specific_brand_archetype_only_checks_that_reference_skeleton():
    formula = {
        "number": 1,
        "name": "DHC Trial",
        "ingredients_ul": {
            "Bergamot FCF oil Sicilian": 900.0,
            "Grapefruit FCF": 120.0,
            "Hedione": 900.0,
            "Galaxolide": 400.0,
        },
        "dilutions": {
            "Galaxolide": 0.5,
        },
        "family_archetype": "dior_homme_cologne",
    }
    report = gate_formula(formula, ReleaseGateConfig(family_archetype="dior_homme_cologne", audit_enabled=False))

    assert _gate_status(report, "dior_homme_cologne_skeleton") == "PASS"
    assert _gate_status(report, "dior_homme_intense_skeleton") == "PASS"
    assert _gate_status(report, "dior_fahrenheit_skeleton") == "PASS"


def test_dotted_family_archetypes_skip_unrelated_brand_skeleton_gates():
    formula = {
        "number": 1,
        "name": "Classical Cologne Trial",
        "ingredients_ul": {
            "Bergamot FCF oil Sicilian": 420.0,
            "Lemon FCF oil Sicilian": 260.0,
            "Orange Peel EO": 240.0,
            "Aurantiol": 110.0,
            "Nerol": 80.0,
            "Lavender EO": 110.0,
            "Rosemary EO": 40.0,
            "Linalool": 70.0,
            "Oranger Crystals": 120.0,
            "Nerolin Bromelia": 80.0,
            "Ethylene Brassylate": 50.0,
            "Galaxolide": 100.0,
        },
        "dilutions": {
            "Oranger Crystals": 0.1,
            "Nerolin Bromelia": 0.1,
            "Galaxolide": 0.5,
        },
        "family_archetype": "citrus_classical.4711_reference",
    }
    report = gate_formula(
        formula,
        ReleaseGateConfig(
            brief="generic",
            family_archetype="citrus_classical.4711_reference",
            expected_concentrate_ul=1680.0,
            audit_enabled=False,
        ),
    )

    assert _gate_status(report, "allure_homme_sport_extreme_skeleton") == "PASS"
    assert _gate_status(report, "dior_homme_sport_skeleton") == "PASS"
