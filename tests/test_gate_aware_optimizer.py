import pytest

from engine.optimizer.gate_aware import optimize_until_release_ready, render_gate_audit_markdown
from engine.pipeline.gates import ReleaseGateConfig


def _config(brief="generic"):
    return ReleaseGateConfig(
        expected_concentrate_ul=6000.0,
        batch_volume_ml=30.0,
        brief=brief,
        allow_preblends=True,
        min_confidence_score=0.0,
        audit_enabled=False,
    )


def test_gate_aware_optimizer_caps_oakmoss_below_cat4_limit():
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 20.0,
        "Zenolide": 12.0,
        "Bergamot FCF": 10.0,
        "Linalool": 8.0,
        "Lavender EO": 7.0,
        "Coumarin": 3.0,
        "Vetiver EO": 4.0,
        "Patchouli EO": 3.0,
        "Oakmoss Absolute": 8.0,
    }

    result = optimize_until_release_ready(
        "Thai Aromatic Fougere Test",
        raw_pct,
        stock_dilutions={"Oakmoss Absolute": 0.2},
        config=_config("aromatic_fougere"),
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.0, "Patchouli EO": 1.0},
    )

    oakmoss_ul = result.raw_concentrate_pct["Oakmoss Absolute"] / 100.0 * 6000.0
    oakmoss_active_ul = oakmoss_ul * 0.2
    safety_gate = {gate.gate: gate for gate in result.gate_report.gates}["safety_ifra_allergen"]

    assert oakmoss_ul <= 150.0
    assert oakmoss_active_ul <= 30.0
    assert safety_gate.status != "FAIL"
    assert any(
        action.gate == "safety_ifra_allergen"
        and action.action == "cap_ifra_finished_product_limit"
        and action.material == "Oakmoss Absolute"
        for action in result.repair_actions
    )


def test_screening_family_architecture_does_not_gain_optimizer_authority():
    bad_raw_pct = {
        "Iso E Super": 25.0,
        "Ambrox Super": 20.0,
        "Hedione": 20.0,
        "Ambrettolide": 15.0,
        "Tonkarome": 10.0,
        "Alpha Ionone": 3.0,
        "Linalyl Acetate": 7.0,
    }
    repaired_raw_pct = {
        "Bergamot FCF": 20.0,
        "Lavender EO": 10.0,
        "Linalyl Acetate": 10.0,
        "Hedione": 15.0,
        "Coumarin": 5.0,
        "Evernyl": 0.5,
        "Iso E Super": 25.0,
        "Vetiver EO": 5.0,
        "Zenolide": 9.5,
    }
    calls = []

    def rerun(_constraints, actions):
        calls.append(actions)
        return repaired_raw_pct

    result = optimize_until_release_ready(
        "Wrong Brief Candidate",
        bad_raw_pct,
        config=_config("aromatic_fougere"),
        max_passes=3,
        rerun_optimizer=rerun,
    )
    gates = {gate.gate: gate for gate in result.gate_report.gates}

    assert calls
    assert any(action.gate == "optimizer_rerun" for action in result.repair_actions)
    # The callback is reached through a genuinely blocking physical-data gate.
    # OAV-derived family skeletons and perfumery guidelines remain advisory and
    # may not become optimizer instructions under the full-potential contract.
    assert any(action.gate == "phase_compatibility" for action in calls[0])
    assert not any(action.gate == "fougere_skeleton" for action in calls[0])
    # The callback supplies a different, structurally closer formula. Its
    # final report must not be mistaken for the rejected starting formula.
    assert gates["perfumer_logic"].status == "PASS"
    assert not any(action.gate in {"perfumer_logic", "family_drift_detector"}
                   for action in calls[0])


def test_optimized_markdown_requires_embedded_gate_audit():
    raw_pct = {
        "Bergamot FCF": 20.0,
        "Lavender EO": 10.0,
        "Linalyl Acetate": 10.0,
        "Hedione": 15.0,
        "Coumarin": 5.0,
        "Evernyl": 0.5,
        "Iso E Super": 25.0,
        "Vetiver EO": 5.0,
        "Zenolide": 9.5,
    }
    result = optimize_until_release_ready(
        "Audit Required Fougere",
        raw_pct,
        config=_config("aromatic_fougere"),
    )

    markdown = "\n".join(render_gate_audit_markdown(result))

    assert "### Release Gate Audit" in markdown
    assert "**Gate status:**" in markdown
    assert "**Commercial readiness:**" in markdown
    assert "### Gate Time-Series OAV Leaders" in markdown
    assert result.interventions is not None
    assert "blocking_issues" in result.interventions


def test_gate_aware_optimizer_records_chemistry_specific_block_actions():
    reactive = {
        # Live stocks are Aldehyde C10 1% and Indole 10%; load enough raw
        # stock for the active mixture to exercise the chemistry blocker.
        "Aldehyde C10": 70.0,
        "Indole": 20.0,
        "Hedione": 5.0,
        "Iso E Super": 4.0,
        "Zenolide": 1.0,
    }
    phase_clash = {
        "Vanillin": 30.0,
        "D-Limonene": 30.0,
        "Galaxolide": 30.0,
        "Hedione": 10.0,
    }

    reactive_result = optimize_until_release_ready(
        "Reactive Block Test",
        reactive,
        config=_config("generic"),
        max_passes=1,
    )
    phase_result = optimize_until_release_ready(
        "Phase Block Test",
        phase_clash,
        config=_config("generic"),
        max_passes=1,
    )

    assert any(
        action.gate == "chemistry_stability"
        and action.action == "rerun_with_stability_constraints"
        for action in reactive_result.repair_actions
    )
    assert any(
        action.gate == "phase_compatibility"
        and action.action == "rerun_with_phase_compatibility_constraints"
        for action in phase_result.repair_actions
    )


def test_exact_final_gate_report_is_reused_by_oav_authority(monkeypatch):
    from engine.optimizer import gate_aware

    gate_calls = []
    authority_reports = []
    real_gate = gate_aware.gate_formula
    real_authority = gate_aware.analyze_oav_authority

    def counted_gate(formula, config, *, parent_formula=None):
        gate_calls.append((formula, parent_formula))
        return real_gate(formula, config, parent_formula=parent_formula)

    def counted_authority(request, *, gate_report=None):
        authority_reports.append(gate_report)
        return real_authority(request, gate_report=gate_report)

    monkeypatch.setattr(gate_aware, "gate_formula", counted_gate)
    monkeypatch.setattr(gate_aware, "analyze_oav_authority", counted_authority)
    result = optimize_until_release_ready(
        "Exact Report Reuse",
        {"Hedione": 50.0, "Iso E Super": 50.0},
        config=_config(),
        max_passes=1,
    )

    assert len(gate_calls) == 1
    assert authority_reports == [result.gate_report]


def test_changed_final_formula_is_gated_once_against_exact_parent(monkeypatch):
    from engine.optimizer import gate_aware

    gate_calls = []
    authority_reports = []
    real_gate = gate_aware.gate_formula
    real_authority = gate_aware.analyze_oav_authority

    def counted_gate(formula, config, *, parent_formula=None):
        gate_calls.append((formula, parent_formula))
        return real_gate(formula, config, parent_formula=parent_formula)

    def counted_authority(request, *, gate_report=None):
        authority_reports.append(gate_report)
        return real_authority(request, gate_report=gate_report)

    monkeypatch.setattr(gate_aware, "gate_formula", counted_gate)
    monkeypatch.setattr(gate_aware, "analyze_oav_authority", counted_authority)
    result = optimize_until_release_ready(
        "Changed Final Candidate",
        {
            "Hedione": 25.0, "Iso E Super": 20.0, "Zenolide": 12.0,
            "Bergamot FCF": 10.0, "Linalool": 8.0, "Lavender EO": 7.0,
            "Coumarin": 3.0, "Vetiver EO": 4.0, "Patchouli EO": 3.0,
            "Oakmoss Absolute": 8.0,
        },
        stock_dilutions={"Oakmoss Absolute": 0.2},
        config=_config("aromatic_fougere"),
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.0},
        max_passes=1,
    )

    assert len(gate_calls) == 2
    assert gate_calls[1][1] == gate_calls[0][0]
    assert gate_calls[1][0] != gate_calls[0][0]
    assert authority_reports == [result.gate_report]


def _safety(result):
    return {gate.gate: gate for gate in result.gate_report.gates}["safety_ifra_allergen"]


def test_gate_aware_optimizer_repairs_failing_ifra_group_total():
    # Each rose ketone passes its own 0.043 % limit; together they exceed the
    # IFRA_STD_077 group limit, so only a group repair can clear the FAIL.
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 25.0,
        "Zenolide": 12.0,
        "Linalool": 8.0,
        "Geraniol": 5.0,
        "Phenyl Ethyl Alcohol": 8.0,
        "Vetiver EO": 4.0,
        "Bergamot FCF": 10.0,
        "Alpha Damascone": 1.5,
        "Damascone Beta": 1.5,
    }
    dilutions = {"Alpha Damascone": 0.1, "Damascone Beta": 0.1}
    pool = {"Iso E Super": 2.0, "Hedione": 1.0}

    start = optimize_until_release_ready(
        "Rose Ketone Group Test", raw_pct, stock_dilutions=dilutions,
        config=_config(), repair_pool=pool, max_passes=0,
    )
    start_safety = _safety(start)
    assert start_safety.status == "FAIL"
    assert [v["material"] for v in start_safety.data["headroom_violations"]] == [
        "rose_ketones_total"
    ]
    assert all(
        row["verdict"] != "fail"
        for row in start_safety.data["rows"]
        if row["ifra_name"] in {"Alpha Damascone", "Beta Damascone"}
    )

    result = optimize_until_release_ready(
        "Rose Ketone Group Test", raw_pct, stock_dilutions=dilutions,
        config=_config(), repair_pool=pool,
    )
    safety = _safety(result)
    caps = [
        action for action in result.repair_actions
        if action.action == "cap_ifra_finished_product_limit"
    ]

    assert safety.status != "FAIL"
    assert {action.material for action in caps} == {"Alpha Damascone", "Damascone Beta"}
    assert all("rose_ketones_total" in action.detail for action in caps)
    group = {g["group"]: g for g in safety.data["groups"]}["rose_ketones_total"]
    assert group["actual_pct"] <= group["limit_pct"]


def test_gate_aware_optimizer_caps_a_row_once_at_the_smaller_of_its_factors():
    # Alpha Damascone is over its own 0.043 % limit and is also a member of the failing
    # rose_ketones_total group, so two violations ask for a cap; the group's is the smaller.
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 25.0,
        "Zenolide": 12.0,
        "Linalool": 8.0,
        "Geraniol": 5.0,
        "Phenyl Ethyl Alcohol": 8.0,
        "Vetiver EO": 4.0,
        "Bergamot FCF": 10.0,
        "Alpha Damascone": 2.0,
        "Damascone Beta": 1.5,
    }
    dilutions = {"Alpha Damascone": 0.1, "Damascone Beta": 0.1}
    pool = {"Iso E Super": 2.0, "Hedione": 1.0}

    start = optimize_until_release_ready(
        "Rose Ketone Row And Group Test", raw_pct, stock_dilutions=dilutions,
        config=_config(), repair_pool=pool, max_passes=0,
    )
    safety = _safety(start)
    rows = {row["material"]: row for row in safety.data["rows"]}
    alpha = rows["Alpha Damascone"]
    assert alpha["actual_pct"] > alpha["limit_pct"]
    violations = {v["material"]: v for v in safety.data["headroom_violations"]}
    group = violations["rose_ketones_total"]
    assert "Alpha Damascone" in violations
    headroom = _config().effective_ifra_headroom()

    first = optimize_until_release_ready(
        "Rose Ketone Row And Group Test", raw_pct, stock_dilutions=dilutions,
        config=_config(), repair_pool=pool, max_passes=1,
    )
    caps = [
        a for a in first.repair_actions
        if a.action == "cap_ifra_finished_product_limit" and a.material == "Alpha Damascone"
    ]
    assert len(caps) == 1
    (cap,) = caps
    assert "rose_ketones_total" in cap.detail
    group_factor = group["limit_pct"] * headroom / group["actual_pct"]
    own_factor = alpha["limit_pct"] * headroom / alpha["actual_pct"]
    assert group_factor < own_factor
    assert cap.after_ul == pytest.approx(cap.before_ul * group_factor * 0.995, rel=1e-4)


def test_gate_aware_optimizer_single_cap_clears_row_in_one_pass():
    # The displaced oakmoss volume goes to Bacdanol, which is lighter than the oakmoss
    # stock, so the finished mass falls after the cap; a cap aimed exactly at the limit
    # lands a hair over it.
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 25.0,
        "Bacdanol": 20.0,
        "Zenolide": 12.0,
        "Linalool": 8.0,
        "Vetiver EO": 6.0,
        "Oakmoss Absolute": 4.0,
    }
    config = _config()
    result = optimize_until_release_ready(
        "One Pass Oakmoss Test", raw_pct,
        stock_dilutions={"Oakmoss Absolute": 0.2},
        config=config, repair_pool={"Bacdanol": 1.0}, max_passes=1,
    )
    # With one pass, the final report is the gate result that follows the first cap.
    caps = [
        action for action in result.repair_actions
        if action.action == "cap_ifra_finished_product_limit"
    ]
    assert [(a.pass_index, a.material) for a in caps] == [(1, "Oakmoss Absolute")]
    safety = _safety(result)
    row = {r["material"]: r for r in safety.data["rows"]}["Oakmoss Absolute"]
    assert row["actual_pct"] <= row["limit_pct"] * config.effective_ifra_headroom()
    assert safety.status != "FAIL"
