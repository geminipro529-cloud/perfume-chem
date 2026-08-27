from __future__ import annotations

import hashlib

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.fuckups.pre_mix_guard import evaluate_pre_mix_guard
from engine.pipeline.oav_evidence import (
    OAVIntervalEvidence,
    OAVModelTier,
    OAVTimepointEvidenceInput,
    OAVTimepointKey,
    TemporalOAVEvidenceRequest,
    TemporalOAVEvidenceResult,
    evaluate_temporal_oav_evidence,
)

FORMULA_SHA = "a" * 64
DOSE_SHA = "b" * 64
PROTOCOL_SHA = "c" * 64
CONTEXT_SHA = "d" * 64


def _source(source_id: str) -> EvidenceSourceRef:
    return EvidenceSourceRef(
        source_id=source_id,
        source_uri=f"https://example.test/{source_id}",
        retrieved_on="2026-08-26",
        source_sha256=hashlib.sha256(source_id.encode()).hexdigest(),
    )


def _interval(
    values: tuple[float, float, float],
    *,
    basis: EvidenceBasis,
    method: str,
    source_id: str,
) -> OAVIntervalEvidence:
    return OAVIntervalEvidence(
        *(
            QuantitativeEvidence(
                value=value,
                unit="ug/m3",
                context="ethanol-air|25C|spray|odor",
                method=method,
                basis=basis,
                source=_source(source_id),
            )
            for value in values
        )
    )


def _cell(
    material_id: str,
    time_seconds: int,
    median_headspace: float,
    *,
    tier: OAVModelTier = OAVModelTier.T4_MEASURED,
    basis: EvidenceBasis = EvidenceBasis.MEASURED,
    threshold_source: str = "threshold-source",
    exact_stock_ref: str | None = "stock:lot-1",
) -> OAVTimepointEvidenceInput:
    return OAVTimepointEvidenceInput(
        key=OAVTimepointKey(
            protocol_sha256=PROTOCOL_SHA,
            sample_id="S-001",
            material_id=material_id,
            time_seconds=time_seconds,
            endpoint="odor threshold",
        ),
        exact_stock_ref=exact_stock_ref,
        active_mass_g=0.1,
        headspace_interval=_interval(
            (median_headspace * 0.8, median_headspace, median_headspace * 1.2),
            basis=basis,
            method="dynamic headspace",
            source_id=f"headspace-{material_id}-{time_seconds}-{tier.value}",
        ),
        threshold_interval=_interval(
            (1.0, 1.0, 1.0),
            basis=basis,
            method="ISO 13301 threshold",
            source_id=threshold_source,
        ),
        model_tier=tier,
        context_sha256=CONTEXT_SHA,
    )


def _receipt(
    cells: tuple[OAVTimepointEvidenceInput, ...],
    *,
    formula_sha: str = FORMULA_SHA,
) -> TemporalOAVEvidenceResult:
    request = TemporalOAVEvidenceRequest(
        formula_sha256=formula_sha,
        dose_receipt_sha256=DOSE_SHA,
        protocol_sha256=PROTOCOL_SHA,
        measurement_context_sha256=CONTEXT_SHA,
        cells=cells,
    )
    return evaluate_temporal_oav_evidence(
        request, declared_cells=tuple(cell.key for cell in cells)
    )


def _guard(
    *,
    parent_receipt: TemporalOAVEvidenceResult | None,
    child_receipt: TemporalOAVEvidenceResult | None,
    parent_hash: str | None = None,
    child_hash: str | None = None,
    child_dose: float = 10.0,
) -> object:
    return evaluate_pre_mix_guard(
        parent_ingredients_ul={"Lemonile": 10.0},
        parent_dilutions={"Lemonile": 1.0},
        child_ingredients_ul={"Lemonile": child_dose},
        child_dilutions={"Lemonile": 1.0},
        parent_temporal_oav=parent_receipt,
        child_temporal_oav=child_receipt,
        parent_temporal_oav_sha256=parent_hash,
        child_temporal_oav_sha256=child_hash,
    )


def test_typed_receipts_bind_hashes_and_emit_warning_only_for_oav_jump() -> None:
    parent = _receipt((_cell("Lemonile", 0, 1.0),))
    child = _receipt((_cell("Lemonile", 0, 20.0),), formula_sha="e" * 64)

    report = _guard(
        parent_receipt=parent,
        child_receipt=child,
        parent_hash=parent.result_sha256,
        child_hash=child.result_sha256,
    )

    assert report.status == "WARN"
    assert report.temporal_evidence_mode == "TYPED_CANONICAL_RECEIPTS"
    assert report.parent_temporal_oav_sha256 == parent.result_sha256
    assert report.child_temporal_oav_sha256 == child.result_sha256
    assert report.temporal_comparison_available is True
    jump = next(
        finding
        for finding in report.findings
        if finding.code == "TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP"
    )
    assert jump.severity == "WARN"
    assert jump.max_temporal_oav_fold_change == 20.0
    interval_finding = next(
        finding
        for finding in report.findings
        if finding.code == "TEMPORAL_OAV_NONOVERLAPPING_INCREASE"
    )
    assert interval_finding.severity == "WARN"


def test_hash_mismatch_cannot_suppress_active_dose_failure() -> None:
    parent = _receipt((_cell("Lemonile", 0, 1.0),))
    child = _receipt((_cell("Lemonile", 0, 1.0),), formula_sha="e" * 64)

    report = _guard(
        parent_receipt=parent,
        child_receipt=child,
        parent_hash="f" * 64,
        child_hash=child.result_sha256,
        child_dose=100.0,
    )

    codes = {finding.code for finding in report.findings}
    assert report.status == "FAIL"
    assert "ACTIVE_DOSE_REVISION_JUMP" in codes
    assert "TEMPORAL_OAV_RECEIPT_HASH_MISMATCH" in codes
    assert report.temporal_comparison_available is False


def test_threshold_cancellation_mismatch_prevents_typed_fold_comparison() -> None:
    parent = _receipt(
        (_cell("Lemonile", 0, 1.0, threshold_source="threshold-A"),)
    )
    child = _receipt(
        (_cell("Lemonile", 0, 20.0, threshold_source="threshold-B"),),
        formula_sha="e" * 64,
    )

    report = _guard(parent_receipt=parent, child_receipt=child)

    codes = {finding.code for finding in report.findings}
    assert "THRESHOLD_CANCELLATION_INCOMPATIBLE" in codes
    assert "TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP" not in codes
    assert report.temporal_comparison_available is False


def test_nonoverlapping_timepoints_are_not_nearest_label_matched() -> None:
    parent = _receipt((_cell("Lemonile", 0, 1.0),))
    child = _receipt((_cell("Lemonile", 60, 20.0),), formula_sha="e" * 64)

    report = _guard(parent_receipt=parent, child_receipt=child)

    codes = {finding.code for finding in report.findings}
    assert "NO_EXACT_TEMPORAL_OAV_MATCH" in codes
    assert "TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP" not in codes
    assert report.temporal_comparison_available is False


def test_measured_and_modeled_cells_are_not_cross_compared() -> None:
    parent = _receipt((_cell("Lemonile", 0, 1.0),))
    child = _receipt(
        (
            _cell(
                "Lemonile",
                0,
                20.0,
                tier=OAVModelTier.T2_MODELED,
                basis=EvidenceBasis.MODELED,
            ),
        ),
        formula_sha="e" * 64,
    )

    report = _guard(parent_receipt=parent, child_receipt=child)

    codes = {finding.code for finding in report.findings}
    assert "TEMPORAL_OAV_SERIES_BASIS_MISMATCH" in codes
    assert "TEMPORAL_OAV_ORDER_OF_MAGNITUDE_JUMP" not in codes
    assert report.temporal_comparison_available is False


def test_partial_receipt_cannot_suppress_active_dose_failure() -> None:
    partial_parent = _receipt(
        (_cell("Lemonile", 0, 1.0, exact_stock_ref=None),)
    )
    child = _receipt((_cell("Lemonile", 0, 1.0),), formula_sha="e" * 64)

    report = _guard(
        parent_receipt=partial_parent,
        child_receipt=child,
        child_dose=100.0,
    )

    codes = {finding.code for finding in report.findings}
    assert report.status == "FAIL"
    assert "ACTIVE_DOSE_REVISION_JUMP" in codes
    assert "TEMPORAL_OAV_RECEIPT_NOT_ADMISSIBLE" in codes


def test_invalid_receipt_cannot_suppress_active_dose_failure() -> None:
    duplicate = _cell("Lemonile", 0, 1.0)
    invalid_request = TemporalOAVEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        protocol_sha256=PROTOCOL_SHA,
        measurement_context_sha256=CONTEXT_SHA,
        cells=(duplicate, duplicate),
    )
    invalid_parent = evaluate_temporal_oav_evidence(
        invalid_request, declared_cells=(duplicate.key,)
    )
    child = _receipt((_cell("Lemonile", 0, 1.0),), formula_sha="e" * 64)

    report = _guard(
        parent_receipt=invalid_parent,
        child_receipt=child,
        child_dose=100.0,
    )

    codes = {finding.code for finding in report.findings}
    assert report.status == "FAIL"
    assert "ACTIVE_DOSE_REVISION_JUMP" in codes
    assert "TEMPORAL_OAV_RECEIPT_NOT_ADMISSIBLE" in codes


def test_persistent_dominance_from_typed_modeled_cells_is_warning_only() -> None:
    modeled_cells = (
        _cell(
            "Lemonile",
            0,
            1000.0,
            tier=OAVModelTier.T2_MODELED,
            basis=EvidenceBasis.MODELED,
        ),
        _cell(
            "Hedione",
            0,
            20.0,
            tier=OAVModelTier.T2_MODELED,
            basis=EvidenceBasis.MODELED,
        ),
        _cell(
            "Lemonile",
            60,
            600.0,
            tier=OAVModelTier.T2_MODELED,
            basis=EvidenceBasis.MODELED,
        ),
        _cell(
            "Hedione",
            60,
            20.0,
            tier=OAVModelTier.T2_MODELED,
            basis=EvidenceBasis.MODELED,
        ),
    )
    child = _receipt(modeled_cells, formula_sha="e" * 64)

    report = evaluate_pre_mix_guard(
        child_ingredients_ul={"Lemonile": 10.0, "Hedione": 10.0},
        child_dilutions={"Lemonile": 1.0, "Hedione": 1.0},
        child_temporal_oav=child,
    )

    finding = next(
        item
        for item in report.findings
        if item.code == "PERSISTENT_MODELED_OAV_DOMINANCE"
    )
    assert report.status == "WARN"
    assert finding.severity == "WARN"
