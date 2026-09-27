from copy import deepcopy
from dataclasses import replace

import pytest

import engine.pipeline.robustness as robustness
from engine.ifra_safety import score_ifra_compliance
from engine.pipeline.formula_state import FormulaState, build_formula_state
from engine.pipeline.gates import ReleaseGateConfig, gate_formula
from engine.pipeline.robustness import audit_formula_robustness
from engine.pipeline.simulator import simulate_formula


def _fougere_formula(evernyl_ul=100.0):
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
    total = sum(ingredients.values())
    return {
        "number": 1,
        "name": "Robust Fougere",
        "body": "aromatic fougere",
        "ingredients_ul": ingredients,
        "dilutions": {
            name: (
                0.3
                if name == "Coumarin"
                else 0.2
                if name == "Evernyl"
                else 1.0
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
    formula = _fougere_formula(evernyl_ul=100.0)
    before = deepcopy(formula)
    gate_report = gate_formula(
        formula,
        ReleaseGateConfig(brief="aromatic_fougere"),
    )
    gates = {gate.gate: gate for gate in gate_report.gates}

    assert formula == before
    assert "robustness_perturbation" in gates
    assert gates["robustness_perturbation"].status in {"PASS", "WARN"}


def test_robustness_builds_one_baseline_and_keeps_all_perturbations(monkeypatch):
    formula = _fougere_formula(evernyl_ul=100.0)
    before = deepcopy(formula)
    real_build_formula_state = robustness.build_formula_state
    build_calls = 0

    def counted_build_formula_state(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return real_build_formula_state(*args, **kwargs)

    monkeypatch.setattr(robustness, "build_formula_state", counted_build_formula_state)
    report = audit_formula_robustness(
        formula,
        ReleaseGateConfig(brief="aromatic_fougere"),
    )

    assert build_calls == 1
    assert report.checked == 2 * len(formula["ingredients_ul"])
    assert len(report.perturbations) == report.checked
    assert formula == before


def test_bound_gate_state_and_top_frame_skip_fresh_baseline_work(monkeypatch):
    formula = _fougere_formula(evernyl_ul=100.0)
    config = ReleaseGateConfig(brief="aromatic_fougere")
    fresh_report = audit_formula_robustness(formula, config)
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
    )
    simulation = tuple(
        simulate_formula(
            formula["ingredients_ul"],
            formula["dilutions"],
            batch_volume_ml=float(config.batch_volume_ml),
            temperature_K=float(config.temperature_K),
            initial_state=state,
        )
    )
    real_simulate_formula = robustness.simulate_formula
    baseline_simulations = 0

    def reject_fresh_build(*_args, **_kwargs):
        raise AssertionError("bound gate state must replace the fresh baseline build")

    def counted_simulate_formula(ingredients_ul, *args, **kwargs):
        nonlocal baseline_simulations
        if dict(ingredients_ul) == formula["ingredients_ul"]:
            baseline_simulations += 1
        return real_simulate_formula(ingredients_ul, *args, **kwargs)

    monkeypatch.setattr(robustness, "build_formula_state", reject_fresh_build)
    monkeypatch.setattr(robustness, "simulate_formula", counted_simulate_formula)

    report = audit_formula_robustness(
        formula,
        config,
        gate_state=state,
        gate_simulation=simulation,
    )

    assert report.checked == 2 * len(formula["ingredients_ul"])
    assert baseline_simulations == 0
    assert report == fresh_report


@pytest.mark.parametrize("tamper", ("window", "state"))
def test_mismatched_gate_reuse_falls_back_to_fresh_baseline(monkeypatch, tamper):
    formula = _fougere_formula(evernyl_ul=100.0)
    config = ReleaseGateConfig(brief="aromatic_fougere")
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
    )
    simulation = list(
        simulate_formula(
            formula["ingredients_ul"],
            formula["dilutions"],
            batch_volume_ml=float(config.batch_volume_ml),
            temperature_K=float(config.temperature_K),
            initial_state=state,
        )
    )
    if tamper == "window":
        simulation[1] = replace(simulation[1], t_seconds=301.0)
    else:
        simulation[1] = replace(simulation[1], state=state)

    real_build_formula_state = robustness.build_formula_state
    build_calls = 0

    def counted_build_formula_state(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return real_build_formula_state(*args, **kwargs)

    monkeypatch.setattr(robustness, "build_formula_state", counted_build_formula_state)
    report = audit_formula_robustness(
        formula,
        config,
        gate_state=state,
        gate_simulation=tuple(simulation),
    )

    assert build_calls == 1
    assert report.checked == 2 * len(formula["ingredients_ul"])


def test_malformed_gate_reuse_packet_falls_back_to_fresh_baseline(monkeypatch):
    formula = _fougere_formula(evernyl_ul=100.0)
    config = ReleaseGateConfig(brief="aromatic_fougere")
    state = build_formula_state(
        formula["ingredients_ul"],
        formula["dilutions"],
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
    )
    real_build_formula_state = robustness.build_formula_state
    build_calls = 0

    class BrokenSimulation:
        def __iter__(self):
            raise RuntimeError("malformed optional reuse packet")

    def counted_build_formula_state(*args, **kwargs):
        nonlocal build_calls
        build_calls += 1
        return real_build_formula_state(*args, **kwargs)

    monkeypatch.setattr(robustness, "build_formula_state", counted_build_formula_state)
    report = audit_formula_robustness(
        formula,
        config,
        gate_state=state,
        gate_simulation=BrokenSimulation(),  # type: ignore[arg-type]
    )

    assert build_calls == 1
    assert report.checked == 2 * len(formula["ingredients_ul"])


@pytest.mark.parametrize(
    ("ingredients_ul", "dilutions"),
    (
        (
            {"Hedione": 100.0, "Coumarin": 50.0},
            {"Hedione": 1.0, "Coumarin": 0.3},
        ),
        (
            {"Cedarwood oil Virginia": 100.0, "Hedione": 50.0},
            {"Cedarwood oil Virginia": 1.0, "Hedione": 0.3},
        ),
    ),
)
def test_reused_state_matches_fresh_build_for_diluted_and_natural_inputs(
    ingredients_ul, dilutions
):
    config = ReleaseGateConfig(brief="generic")
    base_state = build_formula_state(
        ingredients_ul,
        dilutions,
        batch_volume_ml=float(config.batch_volume_ml),
        temperature_K=float(config.temperature_K),
    )
    changed = dict(ingredients_ul)
    changed["Hedione"] += 5.0
    changed[next(name for name in changed if name != "Hedione")] -= 5.0
    reused_state = FormulaState.from_base(base_state, new_raw_ul=changed)

    optimized = robustness._top_envelope_and_leader(
        changed,
        dilutions,
        config,
        initial_state=reused_state,
    )
    fresh = robustness._top_envelope_and_leader(changed, dilutions, config)

    assert optimized == fresh


@pytest.mark.parametrize(
    ("ingredients", "dilutions"),
    (
        ({"Hedione": 100.0, "Evernyl": 100.0}, {"Evernyl": 0.2}),
        ({"Hedione": 100.0, "Evernyl": 200.0}, {"Evernyl": 0.2}),
        ({"Hedione": 100.0, "Lilial": 1.0}, {}),
        ({"Hedione": 100.0, "Unknown material": 1.0}, {}),
    ),
)
def test_narrow_robustness_safety_check_matches_consumed_full_report_fields(
    ingredients, dilutions
):
    config = ReleaseGateConfig(batch_volume_ml=30.0)
    full = score_ifra_compliance(
        ingredients,
        dilutions,
        total_volume_ml=float(config.batch_volume_ml),
    )
    expected = bool(full.ifra_violations or full.banned_flags)

    assert robustness._has_ifra_or_banned_failure(
        ingredients,
        dilutions,
        config,
    ) is expected
