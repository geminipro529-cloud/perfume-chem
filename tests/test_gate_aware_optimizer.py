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


def test_gate_aware_optimizer_caps_evernyl_below_cat4_limit():
    raw_pct = {
        "Hedione": 25.0,
        "Iso E Super": 20.0,
        "Habanolide": 12.0,
        "Bergamot FCF": 10.0,
        "Linalool": 8.0,
        "Lavender EO": 7.0,
        "Coumarin": 3.0,
        "Vetiver EO": 4.0,
        "Patchouli EO": 3.0,
        "Evernyl": 8.0,
    }

    result = optimize_until_release_ready(
        "Thai Aromatic Fougere Test",
        raw_pct,
        config=_config("aromatic_fougere"),
        repair_pool={"Iso E Super": 2.0, "Vetiver EO": 1.0, "Patchouli EO": 1.0},
    )

    evernyl_ul = result.raw_concentrate_pct["Evernyl"] / 100.0 * 6000.0
    safety_gate = {gate.gate: gate for gate in result.gate_report.gates}["safety_ifra_allergen"]

    assert evernyl_ul <= 30.0
    assert safety_gate.status != "FAIL"
    assert any(
        action.gate == "safety_ifra_allergen"
        and action.action == "cap_ifra_finished_product_limit"
        and action.material == "Evernyl"
        for action in result.repair_actions
    )


def test_wrong_brief_advisory_does_not_trigger_automatic_rerun():
    bad_raw_pct = {
        "Iso E Super": 25.0,
        "Ambrox Super": 20.0,
        "Hedione": 20.0,
        "Habanolide": 15.0,
        "Vanillin": 10.0,
        "Ethyl Vanillin": 3.0,
        "Bergamot FCF": 7.0,
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
        "Habanolide": 9.5,
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

    assert calls == []
    assert not any(action.gate == "optimizer_rerun" for action in result.repair_actions)
    assert gates["perfumer_logic"].status == "WARN"
    assert gates["perfumer_logic"].data["original_status"] == "FAIL"
    assert gates["family_drift_detector"].status == "WARN"
    assert gates["family_drift_detector"].data["original_status"] == "FAIL"


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
        "Habanolide": 9.5,
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
        "Aldehyde C10": 20.0,
        "Indole": 2.0,
        "Hedione": 38.0,
        "Iso E Super": 30.0,
        "Habanolide": 10.0,
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
