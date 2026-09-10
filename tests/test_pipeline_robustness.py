from copy import deepcopy

from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.robustness import audit_formula_robustness


def _fougere_formula(evernyl_ul=100.0, *, stock_valid: bool = False):
    """Fougère probe formula.

    ``stock_valid`` swaps in materials that resolve cleanly against the current
    inventory authority, so advisory gate behavior can be tested without the
    stock contract failing first. The default keeps Evernyl for the
    IFRA-perturbation case, which does not run the release gate.
    """
    ingredients = {
        "Cedrat FCF oil Sicilian": 1200.0,
        "Lavender EO (BONTAUX SAS)": 700.0,
        "Linalyl Acetate": 600.0,
        "Hedione": 900.0,
        "Coumarin": 300.0,
        "Evernyl": evernyl_ul,
        "Iso E Super": 1500.0,
        "Cedarwood oil Virginia": 300.0,
        "Zenolide": 500.0 - evernyl_ul,
    }
    if stock_valid:
        ingredients["Bergamot FCF oil Sicilian"] = ingredients.pop(
            "Cedrat FCF oil Sicilian"
        )
        ingredients["Patchouli EO"] = ingredients.pop("Evernyl")
    total = sum(ingredients.values())
    return {
        "number": 1,
        "name": "Robust Fougere",
        "body": "aromatic fougere",
        "ingredients_ul": ingredients,
        "dilutions": {
            name: (
                (0.1 if name == "Coumarin" else 1.0)
                if stock_valid
                else (0.3 if name == "Coumarin" else 0.2 if name == "Evernyl" else 1.0)
            )
            for name in ingredients
        },
        "ingredients_pct": {name: amount / total * 100 for name, amount in ingredients.items()},
    }


def test_robustness_warns_when_evernyl_plus_perturbation_breaks_ifra():
    formula = _fougere_formula(evernyl_ul=150.0)
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
    formula = _fougere_formula(evernyl_ul=100.0, stock_valid=True)
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
