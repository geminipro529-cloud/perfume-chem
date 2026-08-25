from __future__ import annotations

from dataclasses import replace

import pytest

from engine.hedonic_evidence import HedonicEvidenceResult, HedonicEvidenceState, HedonicScope
from engine.pipeline.oav_evidence import OAVEvidenceResult, OAVEvidenceState
from engine.pipeline.release_evidence import (
    EvidenceAxisState,
    ReleaseEvidenceAxis,
    ReleaseEvidenceRequest,
    ReleaseEvidenceStatus,
    evaluate_release_evidence,
    release_axes_from_gate_report,
    release_axis_from_hedonic,
    release_axis_from_oav,
)

FORMULA_SHA = "a" * 64
DOSE_SHA = "b" * 64
SOURCE_SHA = "c" * 64


def _axis(axis_id: str, state: EvidenceAxisState = EvidenceAxisState.PASS):
    return ReleaseEvidenceAxis(
        axis_id=axis_id,
        state=state,
        source_sha256=SOURCE_SHA,
        scope={"formula_sha256": FORMULA_SHA},
    )


def _all_axes() -> tuple[ReleaseEvidenceAxis, ...]:
    return tuple(_axis(axis_id) for axis_id in ReleaseEvidenceAxis.required_axis_ids())


def _request(
    *,
    axes: tuple[ReleaseEvidenceAxis, ...] | None = None,
    diagnostics: dict[str, object] | None = None,
) -> ReleaseEvidenceRequest:
    return ReleaseEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        axes=axes or _all_axes(),
        diagnostics=diagnostics or {},
    )


def _oav(state: OAVEvidenceState) -> OAVEvidenceResult:
    return OAVEvidenceResult(
        state=state,
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        measurement_context="air / declared protocol",
        rows=(),
        blockers=(),
        limitations=(),
    )


def _hedonic(state: HedonicEvidenceState) -> HedonicEvidenceResult:
    return HedonicEvidenceResult(
        state=state,
        criterion_id="LIKING",
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_SHA,
        fit_receipt_sha256=SOURCE_SHA,
        utility_intervals={},
        tie_rate=None,
        directional_comparison_count=0,
        assessor_heterogeneity={},
        order_effect=None,
        blockers=(),
        limitations=(),
    )


def test_one_failed_axis_cannot_be_compensated_by_perfect_diagnostics() -> None:
    axes = tuple(
        replace(axis, state=EvidenceAxisState.HOLD)
        if axis.axis_id == "safety_ifra"
        else axis
        for axis in _all_axes()
    )
    result = evaluate_release_evidence(
        _request(axes=axes, diagnostics={"legacy_total": 100.0, "luxury": 100.0})
    )
    assert result.status is ReleaseEvidenceStatus.HOLD
    assert result.release_authority is False
    assert any("safety_ifra" in blocker for blocker in result.blockers)


def test_not_tested_hedonic_evidence_remains_visible_and_holds() -> None:
    hedonic = release_axis_from_hedonic(_hedonic(HedonicEvidenceState.NOT_TESTED))
    axes = tuple(
        hedonic if axis.axis_id == "hedonic_evidence" else axis
        for axis in _all_axes()
    )
    result = evaluate_release_evidence(_request(axes=axes))
    assert result.status is ReleaseEvidenceStatus.HOLD
    assert {axis.axis_id: axis.state for axis in result.axes}[
        "hedonic_evidence"
    ] is EvidenceAxisState.NOT_TESTED


def test_invalid_oav_result_invalidates_the_release_evaluation() -> None:
    oav = release_axis_from_oav(_oav(OAVEvidenceState.INVALID))
    axes = tuple(
        oav if axis.axis_id == "oav_evidence" else axis for axis in _all_axes()
    )
    result = evaluate_release_evidence(_request(axes=axes))
    assert result.status is ReleaseEvidenceStatus.INVALID
    assert result.release_authority is False


def test_all_required_axes_pass_only_reaches_human_review() -> None:
    result = evaluate_release_evidence(_request())
    assert result.status is ReleaseEvidenceStatus.READY_FOR_HUMAN_REVIEW
    assert result.release_authority is False
    assert not hasattr(result, "total")
    assert not hasattr(result, "beauty")
    assert not hasattr(result, "hedonic_score")


def test_changing_legacy_scores_cannot_change_status() -> None:
    low = evaluate_release_evidence(
        _request(diagnostics={"legacy_total": 0.0, "hedonic": 0.0})
    )
    high = evaluate_release_evidence(
        _request(diagnostics={"legacy_total": 100.0, "hedonic": 100.0})
    )
    assert low.status is high.status is ReleaseEvidenceStatus.READY_FOR_HUMAN_REVIEW
    assert low.axes == high.axes


def test_axis_payload_binds_source_hash_and_exact_scope() -> None:
    result = evaluate_release_evidence(_request())
    payload = result.as_dict()
    first = payload["axes"][0]
    assert first["source_sha256"] == SOURCE_SHA
    assert first["scope"] == {"formula_sha256": FORMULA_SHA}
    assert payload["schema_version"] == "release_evidence_v2"


@pytest.mark.parametrize(
    "axes",
    [
        lambda values: values[:-1],
        lambda values: values + (values[0],),
        lambda values: values
        + (_axis("unknown_axis", EvidenceAxisState.PASS),),
    ],
)
def test_missing_duplicate_or_unknown_axes_are_invalid(axes) -> None:
    result = evaluate_release_evidence(_request(axes=axes(_all_axes())))
    assert result.status is ReleaseEvidenceStatus.INVALID
    assert result.blockers


def test_axis_formula_scope_mismatch_is_invalid() -> None:
    axes = tuple(
        replace(axis, scope={"formula_sha256": "d" * 64})
        if axis.axis_id == "inventory_lineage"
        else axis
        for axis in _all_axes()
    )
    result = evaluate_release_evidence(_request(axes=axes))
    assert result.status is ReleaseEvidenceStatus.INVALID
    assert any("formula" in blocker for blocker in result.blockers)


@pytest.mark.parametrize(
    ("oav_state", "axis_state"),
    [
        (OAVEvidenceState.STRICT_MEASURED, EvidenceAxisState.PASS),
        (OAVEvidenceState.MODELED_SCREEN, EvidenceAxisState.HOLD),
        (OAVEvidenceState.PARTIAL, EvidenceAxisState.HOLD),
        (OAVEvidenceState.ABSTAINED, EvidenceAxisState.NOT_TESTED),
        (OAVEvidenceState.INVALID, EvidenceAxisState.INVALID),
    ],
)
def test_oav_adapter_preserves_evidence_posture(oav_state, axis_state) -> None:
    assert release_axis_from_oav(_oav(oav_state)).state is axis_state


@pytest.mark.parametrize(
    ("hedonic_state", "axis_state"),
    [
        (HedonicEvidenceState.VALIDATED_EXACT_SCOPE, EvidenceAxisState.PASS),
        (HedonicEvidenceState.NOT_TESTED, EvidenceAxisState.NOT_TESTED),
        (HedonicEvidenceState.INSUFFICIENT_EVIDENCE, EvidenceAxisState.HOLD),
        (HedonicEvidenceState.DIAGNOSTIC, EvidenceAxisState.HOLD),
        (HedonicEvidenceState.FAILED_HELDOUT_BASELINE, EvidenceAxisState.HOLD),
        (HedonicEvidenceState.INVALID_OR_CONFOUNDED, EvidenceAxisState.INVALID),
    ],
)
def test_hedonic_adapter_preserves_evidence_posture(
    hedonic_state, axis_state
) -> None:
    assert release_axis_from_hedonic(_hedonic(hedonic_state)).state is axis_state


def test_gate_report_adapter_preserves_fail_missing_and_malformed_states() -> None:
    axes = release_axes_from_gate_report(
        {
            "gates": [
                {"gate": "source_rights", "status": "PASS"},
                {"gate": "target_formula_identity", "status": "FAIL"},
                {"gate": "inventory_stock_contract", "status": "BROKEN"},
            ]
        },
        formula_sha256=FORMULA_SHA,
    )
    states = {axis.axis_id: axis.state for axis in axes}
    assert states["source_rights"] is EvidenceAxisState.PASS
    assert states["target_formula_identity"] is EvidenceAxisState.HOLD
    assert states["inventory_lineage"] is EvidenceAxisState.INVALID
    assert states["laboratory_execution"] is EvidenceAxisState.NOT_TESTED
