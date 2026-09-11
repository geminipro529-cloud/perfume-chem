"""Tests for the opt-in function-balance gate and its evidence-classed model.

The model is grounded in the practitioner function layer (Dowthwaite 1999) plus
peer-reviewed anchors recorded in
``engine.knowledge.performance_engineering.FUNCTIONAL_BALANCE_CITATIONS``.
"""
from __future__ import annotations

from types import SimpleNamespace

from engine.knowledge.performance_engineering import (
    BLENDER,
    EVIDENCE_DOMAINS,
    FIXATIVE,
    HEART,
    MODIFIER,
    X_FACTOR,
    evaluate_architecture,
    evaluate_function_balance,
    evaluate_hedonics,
    evaluate_neuroscience,
    get_citations_for_domain,
    get_functional_balance_citations,
)
from engine.pipeline.gates import ReleaseGateConfig, gate_formula


def _mat(name, *, role, active_g, oav, vp, note="heart", texture="neutral"):
    return SimpleNamespace(
        name=name,
        canonical_name=name,
        role=role,
        active_g=active_g,
        active_ul=active_g,
        oav=oav,
        vp_pure_pa=vp,
        note=note,
        texture=texture,
    )


def _roles(report):
    return {a.name: a.role for a in report.assignments}


def test_curated_function_layer_assigns_heart_blender_fixative():
    materials = [
        _mat("Alpha Isomethyl Ionone", role="character", active_g=45.0, oav=8.0, vp=0.4),
        _mat("Hedione", role="character", active_g=30.0, oav=5.0, vp=0.09),
        _mat("Galaxolide", role="fixative", active_g=25.0, oav=2.0, vp=0.001),
    ]

    report = evaluate_function_balance(materials, pw_data={})
    roles = _roles(report)

    assert roles["Alpha Isomethyl Ionone"] == HEART
    assert roles["Hedione"] == BLENDER
    assert roles["Galaxolide"] == FIXATIVE
    assert report.status != "FAIL"
    assert report.role_counts[HEART] == 1


def test_curated_signature_accent_at_trace_dose_is_x_factor():
    materials = [
        _mat("Alpha Isomethyl Ionone", role="character", active_g=90.0, oav=8.0, vp=0.4),
        _mat("Hedione", role="character", active_g=40.0, oav=5.0, vp=0.09),
        _mat("Galaxolide", role="fixative", active_g=30.0, oav=2.0, vp=0.001),
        _mat("Birch Tar", role="modifier", active_g=1.0, oav=4.0, vp=1.0),
    ]

    report = evaluate_function_balance(materials, pw_data={})
    roles = _roles(report)

    assert roles["Birch Tar"] == X_FACTOR
    assert report.present[X_FACTOR] is True


def test_modifier_overdose_reclassified_as_heart():
    # The modifier holds more active mass than the declared heart, so by the
    # Dowthwaite overdose rule it becomes the subject.
    materials = [
        _mat("Undecavertol", role="modifier", active_g=60.0, oav=6.0, vp=0.2, texture="accent"),
        _mat("Alpha Isomethyl Ionone", role="character", active_g=20.0, oav=5.0, vp=0.4),
        _mat("Galaxolide", role="fixative", active_g=20.0, oav=2.0, vp=0.001),
    ]

    report = evaluate_function_balance(materials, pw_data={})
    undecavertol = next(a for a in report.assignments if a.name == "Undecavertol")

    assert undecavertol.role == HEART
    assert undecavertol.source == "contextual:modifier_overdose"


def test_missing_core_functions_fail():
    materials = [
        _mat("Alpha Isomethyl Ionone", role="character", active_g=100.0, oav=8.0, vp=0.4),
    ]

    report = evaluate_function_balance(materials, pw_data={})

    assert report.status == "FAIL"
    assert report.present[BLENDER] is False
    assert report.present[FIXATIVE] is False
    assert any("blender" in f.lower() for f in report.findings)
    assert any("fixative" in f.lower() for f in report.findings)


def test_supplier_impact_and_odour_life_drive_classification():
    pw_data = {
        "mystery base": {"relative_impact": 50.0, "odour_life_hrs": 12.0},
    }
    materials = [
        _mat("Alpha Isomethyl Ionone", role="character", active_g=60.0, oav=8.0, vp=0.4),
        _mat("Mystery Base", role="unknown", active_g=40.0, oav=3.0, vp=0.5),
    ]

    report = evaluate_function_balance(materials, pw_data=pw_data)
    mystery = next(a for a in report.assignments if a.name == "Mystery Base")

    # Long odour life -> fixative function regardless of the raw declared role.
    assert mystery.role == FIXATIVE
    assert mystery.odour_life_hrs == 12.0


def test_function_balance_gate_is_opt_in():
    formula = {
        "number": 1,
        "name": "Function balance wiring",
        "ingredients_ul": {
            "Hedione": 1800.0,
            "Iso E Super": 1500.0,
            "Galaxolide": 900.0,
            "Alpha Isomethyl Ionone": 700.0,
            "Ethylene Brassylate": 600.0,
            "Vanillin": 300.0,
            "Birch Tar": 50.0,
        },
        "dilutions": {},
        "body": "Function balance wiring",
    }

    off = gate_formula(formula, ReleaseGateConfig(expected_concentrate_ul=6000.0, brief="generic"))
    assert "function_balance" not in {g.gate for g in off.gates}

    on = gate_formula(
        formula,
        ReleaseGateConfig(
            expected_concentrate_ul=6000.0,
            brief="generic",
            function_balance_enabled=True,
        ),
    )
    gate = next(g for g in on.gates if g.gate == "function_balance")
    assert gate.status in {"PASS", "WARN", "FAIL"}
    assert gate.data["schema_version"] == "function_balance_v1"
    assert set(gate.data["present"]) == {HEART, MODIFIER, BLENDER, FIXATIVE, X_FACTOR}
    assert on.config_summary["function_balance_enabled"] is True
    assert off.config_summary["function_balance_enabled"] is False


def test_citation_registry_is_populated_and_tiered():
    citations = get_functional_balance_citations()
    assert citations["rodrigues_2021"]["tier"] == "A_peer_reviewed"
    assert citations["dowthwaite_1999"]["tier"] == "C_practitioner"
    assert "laing_francis_1989" in citations
    assert "cain_1969" in citations


def test_each_evidence_domain_has_at_least_five_peer_reviewed_sources():
    for domain in EVIDENCE_DOMAINS:
        domain_citations = get_citations_for_domain(domain)
        assert len(domain_citations) >= 5, (domain, len(domain_citations))
        peer_reviewed = [
            c for c in domain_citations.values() if c["tier"] == "A_peer_reviewed"
        ]
        # The bulk of every domain must be peer reviewed (practitioner/classical
        # codifications are allowed only as a minority).
        assert len(peer_reviewed) >= max(5, len(domain_citations) - 3), (domain, len(peer_reviewed))


def test_report_exposes_architecture_and_hedonics():
    materials = [
        _mat("Alpha Isomethyl Ionone", role="character", active_g=45.0, oav=8.0, vp=0.4),
        _mat("Hedione", role="character", active_g=30.0, oav=5.0, vp=0.09),
        _mat("Galaxolide", role="fixative", active_g=25.0, oav=2.0, vp=0.001, note="base"),
    ]
    report = evaluate_function_balance(materials, pw_data={})

    payload = report.as_dict()
    assert "architecture" in payload
    assert "hedonics" in payload
    assert "neuroscience" in payload
    assert payload["architecture"]["tier_coverage"] == {"top": 0, "heart": 2, "base": 1}
    assert payload["architecture"]["volatility_windows"]
    assert payload["hedonics"]["confidence"] in {"low", "none"}
    assert set(payload["evidence"]["domains"]) == set(EVIDENCE_DOMAINS)


def test_architecture_flags_olfactory_white_collapse():
    # Many balanced perceptible components with no dominant subject -> Weiss 2012.
    materials = [
        _mat(f"Material {i}", role="character", active_g=10.0, oav=2.0, vp=0.5)
        for i in range(8)
    ]
    assessment = evaluate_architecture(materials, max_oav=2.0)
    assert assessment.collapse_risk is True
    assert assessment.status == "WARN"


def test_hedonics_abstain_without_data():
    materials = [_mat("Alpha Isomethyl Ionone", role="character", active_g=50.0, oav=8.0, vp=0.4)]
    assessment = evaluate_hedonics(materials, hedonic_table={})
    assert assessment.status == "ABSTAIN"
    assert assessment.weighted_valence is None
    assert "khan_2007" in assessment.citations


def test_neuroscience_flags_integration_overload():
    # Eight materials above the OAV>=10 channel threshold -> exceeds ~5 capacity.
    materials = [
        _mat(f"Material {i}", role="character", active_g=10.0, oav=20.0, vp=0.5)
        for i in range(8)
    ]
    assessment = evaluate_neuroscience(materials)
    assert assessment.perceptible_channels == 8
    assert assessment.status == "WARN"
    assert any("integration capacity" in f for f in assessment.findings)


def test_neuroscience_flags_single_material_top_habituation():
    materials = [
        _mat("Bergamot FCF", role="character", active_g=90.0, oav=90.0, vp=40.0),
        _mat("Lemon", role="modifier", active_g=10.0, oav=5.0, vp=20.0),
    ]
    assessment = evaluate_neuroscience(materials)
    assert assessment.habituation_risk is True
    assert "bergamot" in " ".join(assessment.findings).lower()
