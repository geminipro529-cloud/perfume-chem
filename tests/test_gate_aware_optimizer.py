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
