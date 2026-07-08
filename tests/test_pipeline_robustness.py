from copy import deepcopy

from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.robustness import audit_formula_robustness


def _fougere_formula(evernyl_ul=20.0):
    ingredients = {
        "Bergamot FCF": 1200.0,
        "Lavender EO": 700.0,
        "Linalyl Acetate": 600.0,
        "Hedione": 900.0,
        "Coumarin": 300.0,
        "Evernyl": evernyl_ul,
        "Iso E Super": 1500.0,
        "Vetiver EO": 300.0,
        "Habanolide": 500.0 - evernyl_ul,
    }
    total = sum(ingredients.values())
    return {
        "number": 1,
        "name": "Robust Fougere",
        "body": "aromatic fougere",
        "ingredients_ul": ingredients,
        "dilutions": {},
        "ingredients_pct": {name: amount / total * 100 for name, amount in ingredients.items()},
    }


def test_robustness_warns_when_evernyl_plus_perturbation_breaks_ifra():
    formula = _fougere_formula(evernyl_ul=30.0)
    report = audit_formula_robustness(
        formula,
        ReleaseGateConfig(brief="aromatic_fougere"),
    )

    assert report.status == "WARN"
    assert any(
        issue.material == "Evernyl"
        and issue.direction == "up"
        and issue.safety_failed
        for issue in report.issues
    )


def test_robustness_audit_preserves_original_formula_and_gate_is_nonblocking():
    formula = _fougere_formula(evernyl_ul=20.0)
    before = deepcopy(formula)
    gate_report = gate_formula(
        formula,
        ReleaseGateConfig(brief="aromatic_fougere"),
    )
    gates = {gate.gate: gate for gate in gate_report.gates}

    assert formula == before
    assert "robustness_perturbation" in gates
    assert gates["robustness_perturbation"].status in {"PASS", "WARN"}
    assert gate_report.status in {"PASS", "WARN"}
