"""Opt-in caller wiring and fail-closed provenance, not release acceptance."""

from dataclasses import replace

import pytest

from engine.formulation_intelligence import deep_plane_diagnostics as diagnostics
from engine.pipeline import gates
from engine.pipeline.formula_state import build_formula_state
from engine.pipeline.preflight import build_formula_dose_receipt, resolve_inventory_stock_contract
from engine.pipeline.simulator import simulate_formula


def _formula(amount=100.0, name="Pipeline binding regression"):
    return {"number": 1, "name": name, "ingredients_ul": {"Hedione": amount},
            "dilutions": {"Hedione": 1.0}, "body": "Diagnostic fixture only"}


def _bound(formula):
    contract = resolve_inventory_stock_contract(formula)
    assert contract.status == "PASS"
    receipt = build_formula_dose_receipt(formula, contract)
    state = build_formula_state(
        formula["ingredients_ul"], formula["dilutions"],
        stock_specs=contract.data["resolved_stock_specs"], temperature_K=305.0,
    )
    state = replace(state, dose_receipt_sha256=receipt.receipt_sha256,
                    dose_receipt_status=receipt.status)
    frames = tuple(simulate_formula(
        formula["ingredients_ul"], formula["dilutions"], initial_state=state,
        bind_provenance=True,
    ))
    return state, frames, receipt


@pytest.fixture
def bound():
    formula = _formula()
    return formula, *_bound(formula)


def _evaluate(bound, **kwargs):
    formula, state, frames, receipt = bound
    return diagnostics.evaluate_deep_plane_gate(
        formula, state, frames, dose_receipt=receipt,
        require_calculation_provenance=True, **kwargs,
    )


def test_pipeline_connection_is_disabled_by_default(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("disabled adapter must not be called")

    monkeypatch.setattr(gates, "_gate_deep_plane_diagnostics", forbidden)
    report = gates.gate_formula(_formula(), gates.ReleaseGateConfig(audit_enabled=False))
    assert not any(g.gate == "deep_plane_diagnostics" for g in report.gates)
    assert report.config_summary["deep_plane_diagnostics_enabled"] is False
    # The stock/dose receipt identity is bound by default (accepted-pipeline
    # behaviour); only the Deep Plane diagnostic itself stays opt-in. Frames
    # carry provenance whenever the state is bound, so the exact OAV replay in
    # engine/pipeline/oav_authority.py reproduces them bit-for-bit.
    assert report.formula_state.dose_receipt_status == "BOUND"
    assert all("provenance" in f.as_dict() for f in report.simulation)


def test_opt_in_pipeline_passes_receipt_and_existing_child_calculations(monkeypatch):
    original = diagnostics.evaluate_deep_plane_gate
    seen = {}

    def capture(formula, state, frames, **kwargs):
        seen.update(state=state, frames=frames, receipt=kwargs["dose_receipt"])
        return original(formula, state, frames, **kwargs)

    monkeypatch.setattr(diagnostics, "evaluate_deep_plane_gate", capture)
    report = gates.gate_formula(_formula(), gates.ReleaseGateConfig(
        audit_enabled=False, deep_plane_diagnostics_enabled=True,
    ))
    rows = [g for g in report.gates if g.gate == "deep_plane_diagnostics"]
    assert len(rows) == 1
    assert rows[0].status == "FAIL", rows[0].as_dict()
    assert {b["code"] for b in rows[0].data["blockers"]} == {"REQUIRED_PHYSICS_MISSING"}
    assert seen["state"] is report.formula_state
    assert seen["frames"] is report.simulation
    assert seen["receipt"].receipt_sha256 == report.formula_state.dose_receipt_sha256
    checks = {c["check_name"]: c for c in report.preflight["checks"]}
    assert checks["formula_dose_receipt"]["status"] == "PASS"
    assert rows[0].data["calculation_reuse"]["provenance_verified"] is True
    assert rows[0].data["authority_status"] == "HOLD"
    assert report.commercial_readiness == "NOT_RELEASE_READY"


def test_opt_in_adapter_binds_parent_independently(bound):
    formula, state, frames, receipt = bound
    parent = _formula(90.0, "Immediate parent fixture")
    result = gates._gate_deep_plane_diagnostics(
        formula, state, frames, receipt,
        gates.ReleaseGateConfig(deep_plane_diagnostics_enabled=True), parent_formula=parent,
    )
    assert result.status == "FAIL", result.as_dict()
    assert {b["code"] for b in result.data["blockers"]} == {"REQUIRED_PHYSICS_MISSING"}
    assert result.data["calculation_reuse"]["parent_provenance_verified"] is True


@pytest.mark.parametrize("kind", ["missing", "reordered", "altered_time", "altered_content", "foreign_origin"])
def test_simulation_corruption_is_rejected(bound, kind):
    formula, state, frames, receipt = bound
    if kind == "missing":
        changed = frames[:-1]
    elif kind == "reordered":
        changed = tuple(reversed(frames))
    elif kind == "altered_time":
        changed = (replace(frames[0], t_seconds=1.0), *frames[1:])
    elif kind == "foreign_origin":
        _, changed, _ = _bound(_formula(99.0))
    else:
        different_state = replace(frames[1].state, total_raw_ul=17.0)
        changed = (frames[0], replace(frames[1], state=different_state), *frames[2:])
    with pytest.raises(diagnostics.DeepPlaneRuntimeError):
        _evaluate((formula, state, changed, receipt))


def test_unstamped_frames_are_rejected_even_when_state_matches(bound):
    formula, state, _, receipt = bound
    unstamped = tuple(simulate_formula(formula["ingredients_ul"], formula["dilutions"], initial_state=state))
    with pytest.raises(diagnostics.DeepPlaneRuntimeError, match="origin"):
        _evaluate((formula, state, unstamped, receipt))


@pytest.mark.parametrize("kind", ["missing_receipt", "swapped_formula", "swapped_frames"])
def test_parent_mismatch_is_rejected(bound, kind):
    parent = _formula(90.0, "Parent fixture")
    p_state, p_frames, p_receipt = _bound(parent)
    if kind == "missing_receipt":
        p_receipt = None
    elif kind == "swapped_formula":
        parent = _formula(80.0, "Different parent")
    else:
        _, p_frames, _ = _bound(_formula(80.0, "Different parent"))
    with pytest.raises(diagnostics.DeepPlaneRuntimeError, match="parent"):
        _evaluate(bound, parent_formula=parent, parent_state=p_state,
                  parent_simulation=p_frames, parent_dose_receipt=p_receipt)


def test_direct_adapter_failure_remains_a_hard_blocker(bound):
    formula, state, frames, _ = bound
    result = gates._safe_gate(
        lambda: gates._gate_deep_plane_diagnostics(
            formula, state, frames, None, gates.ReleaseGateConfig(deep_plane_diagnostics_enabled=True)
        ), "deep_plane_diagnostics",
    )
    assert result.status == "FAIL"
    assert gates._apply_guideline_policy(result).status == "FAIL"


def test_orphan_parent_receipt_is_rejected(bound):
    with pytest.raises(diagnostics.DeepPlaneRuntimeError, match="parent_formula"):
        _evaluate(bound, parent_dose_receipt=bound[3])


def test_parent_context_mismatch_is_rejected(bound):
    parent = _formula(90.0, "Parent fixture")
    state, _, receipt = _bound(parent)
    state = replace(state, temperature_K=300.0)
    frames = tuple(simulate_formula(parent["ingredients_ul"], parent["dilutions"],
                                   initial_state=state, bind_provenance=True))
    with pytest.raises(diagnostics.DeepPlaneRuntimeError, match="contexts differ"):
        _evaluate(bound, parent_formula=parent, parent_state=state,
                  parent_simulation=frames, parent_dose_receipt=receipt)


@pytest.mark.parametrize("kind", ["authority", "schema", "status", "provenance", "missing_plane", "receipt"])
def test_malformed_diagnostic_cannot_be_promoted(bound, monkeypatch, kind):
    formula, state, frames, receipt = bound
    payload = _evaluate(bound)
    if kind == "authority":
        payload["authority_flags"]["release"] = True
    elif kind == "schema":
        payload["schema_version"] = "unknown"
    elif kind == "status":
        payload["gate_status"] = "PASS"
        payload["blockers"] = [{"code": "TEST_FAILURE"}]
    elif kind == "provenance":
        payload["calculation_reuse"]["provenance_verified"] = False
    elif kind == "receipt":
        payload["inventory_evidence"]["dose_receipt_sha256"] = "0" * 64
    else:
        del payload["plane_statuses"]["inventory_build"]
    monkeypatch.setattr(diagnostics, "evaluate_deep_plane_gate", lambda *a, **kw: payload)
    with pytest.raises(ValueError):
        gates._gate_deep_plane_diagnostics(formula, state, frames, receipt, gates.ReleaseGateConfig())


def test_provenance_does_not_change_modeled_values(bound):
    formula, state, frames, _ = bound
    plain = simulate_formula(formula["ingredients_ul"], formula["dilutions"], initial_state=state)
    for before, after in zip(plain, frames, strict=True):
        assert before.state == after.state
        stamped = after.as_dict()
        assert stamped.pop("provenance")["frame_content_sha256"] == after.frame_content_sha256
        assert before.as_dict() == stamped


def test_diagnostic_pass_remains_non_promoting_warning(bound, monkeypatch):
    formula, state, frames, receipt = bound
    # Exercise adapter policy with synthetic input-quality PASS, not a claim
    # that this physical fixture has resolved its missing-data hold.
    payload = _evaluate(bound)
    payload.update(gate_status="PASS", blockers=[], warnings=[])
    payload["physicochemical_findings"]["missing_physics_materials"] = []
    payload["plane_statuses"]["physicochemical"] = "MODELED"
    for plane in payload["planes"]:
        if plane["plane_id"] == "physicochemical":
            plane.update(status="MODELED", authority_ceiling="hypothesis_only")
    monkeypatch.setattr(diagnostics, "evaluate_deep_plane_gate", lambda *a, **kw: payload)
    result = gates._gate_deep_plane_diagnostics(formula, state, frames, receipt, gates.ReleaseGateConfig())
    assert result.status == "WARN"
    assert result.data["authority_status"] == "HOLD"


@pytest.mark.parametrize("commercial,trial", [(False, False), (True, False), (True, True)])
def test_candidate_never_becomes_commercially_ready(commercial, trial):
    config = gates.ReleaseGateConfig(
        deep_plane_diagnostics_enabled=True, commercial_mode=commercial,
        commercial_confidence_policy="warn" if trial else "block",
    )
    assert gates._commercial_readiness("PASS", [], {"combined_confidence": 100.0}, config) == "NOT_RELEASE_READY"
