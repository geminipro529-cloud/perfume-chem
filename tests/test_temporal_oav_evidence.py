from __future__ import annotations

import hashlib

import pytest

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.pipeline.oav_evidence import (
    OAVIntervalEvidence,
    OAVModelTier,
    OAVTimepointEvidenceInput,
    OAVTimepointKey,
    TemporalOAVEvidenceRequest,
    TemporalOAVEvidenceResult,
    TemporalOAVEvidenceState,
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
        source_sha256=hashlib.sha256(source_id.encode("utf-8")).hexdigest(),
    )


def _quantitative(
    value: float | None,
    *,
    basis: EvidenceBasis,
    unit: str = "ug/m3",
    context: str = "ethanol-air|25C|spray|odor",
    method: str,
    source_id: str,
) -> QuantitativeEvidence:
    if basis is EvidenceBasis.UNKNOWN:
        return QuantitativeEvidence(
            value=None,
            unit="",
            context="",
            method="",
            basis=basis,
            source=None,
        )
    return QuantitativeEvidence(
        value=value,
        unit=unit,
        context=context,
        method=method,
        basis=basis,
        source=_source(source_id),
    )


def _interval(
    values: tuple[float, float, float] = (8.0, 10.0, 12.0),
    *,
    basis: EvidenceBasis = EvidenceBasis.MEASURED,
    unit: str = "ug/m3",
    context: str = "ethanol-air|25C|spray|odor",
    method: str = "dynamic headspace",
    source_id: str = "headspace-run-1",
) -> OAVIntervalEvidence:
    return OAVIntervalEvidence(
        *(
            _quantitative(
                value,
                basis=basis,
                unit=unit,
                context=context,
                method=method,
                source_id=source_id,
            )
            for value in values
        )
    )


def _unknown_interval() -> OAVIntervalEvidence:
    return OAVIntervalEvidence(
        *(
            _quantitative(
                None,
                basis=EvidenceBasis.UNKNOWN,
                method="unknown",
                source_id="unknown",
            )
            for _ in range(3)
        )
    )


def _key(
    time_seconds: int = 0,
    *,
    material_id: str = "Hedione",
    sample_id: str = "S-001",
    endpoint: str = "odor threshold",
) -> OAVTimepointKey:
    return OAVTimepointKey(
        protocol_sha256=PROTOCOL_SHA,
        sample_id=sample_id,
        material_id=material_id,
        time_seconds=time_seconds,
        endpoint=endpoint,
    )


def _cell(
    time_seconds: int = 0,
    *,
    material_id: str = "Hedione",
    model_tier: OAVModelTier = OAVModelTier.T4_MEASURED,
    basis: EvidenceBasis = EvidenceBasis.MEASURED,
    exact_stock_ref: str | None = "stock:HEDIONE:lot-1",
    active_mass_g: float | None = 0.1,
    headspace_unit: str = "ug/m3",
    threshold_unit: str = "ug/m3",
    headspace_context: str = "ethanol-air|25C|spray|odor",
    threshold_context: str = "ethanol-air|25C|spray|odor",
    threshold_source_id: str = "threshold-study-1",
) -> OAVTimepointEvidenceInput:
    return OAVTimepointEvidenceInput(
        key=_key(time_seconds, material_id=material_id),
        exact_stock_ref=exact_stock_ref,
        active_mass_g=active_mass_g,
        headspace_interval=_interval(
            basis=basis,
            unit=headspace_unit,
            context=headspace_context,
            source_id=f"headspace-{model_tier.value}-{time_seconds}",
        ),
        threshold_interval=_interval(
            (2.0, 4.0, 8.0),
            basis=basis,
            unit=threshold_unit,
            context=threshold_context,
            method="ISO 13301 threshold",
            source_id=threshold_source_id,
        ),
        model_tier=model_tier,
        context_sha256=CONTEXT_SHA,
    )


def _unknown_cell(time_seconds: int = 0) -> OAVTimepointEvidenceInput:
    return OAVTimepointEvidenceInput(
        key=_key(time_seconds),
        exact_stock_ref=None,
        active_mass_g=None,
        headspace_interval=_unknown_interval(),
        threshold_interval=_unknown_interval(),
        model_tier=OAVModelTier.T0_UNKNOWN,
        context_sha256=CONTEXT_SHA,
    )


def _request(
    cells: tuple[OAVTimepointEvidenceInput, ...],
) -> TemporalOAVEvidenceRequest:
    return TemporalOAVEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=DOSE_SHA,
        protocol_sha256=PROTOCOL_SHA,
        measurement_context_sha256=CONTEXT_SHA,
        cells=cells,
    )


def test_strict_measured_series_computes_interval_without_perceptual_authority() -> None:
    cells = (_cell(0), _cell(60))
    result = evaluate_temporal_oav_evidence(
        _request(cells), declared_cells=tuple(cell.key for cell in cells)
    )

    assert result.state is TemporalOAVEvidenceState.STRICT_MEASURED_TIME_SERIES
    assert result.modeled_cells == ()
    assert result.missing_cells == ()
    assert tuple(cell.oav_interval for cell in result.measured_cells) == (
        (1.0, 2.5, 6.0),
        (1.0, 2.5, 6.0),
    )
    assert result.measured_cells[0].evidence.headspace_interval.p50.value == 10.0
    assert result.measured_cells[0].evidence.threshold_interval.p50.value == 4.0
    assert result.lineage_hashes
    assert all(value is False for value in result.authority.values())
    assert {
        "compounding",
        "formula",
        "hedonic",
        "liking",
        "physical_execution",
        "purchase",
        "release",
        "runtime",
        "safety",
        "scientific_claim",
        "sensory",
        "stability",
    }.issubset(result.authority)


def test_duplicate_cells_fail_closed_in_the_evaluator() -> None:
    cell = _cell()
    request = _request((cell, cell))
    result = evaluate_temporal_oav_evidence(
        request, declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.INVALID
    assert any(blocker.startswith("DUPLICATE_CELL:") for blocker in result.blockers)


def test_undeclared_cell_is_invalid_and_declared_absence_stays_missing() -> None:
    declared = (_key(0), _key(60))
    result = evaluate_temporal_oav_evidence(
        _request((_cell(120),)), declared_cells=declared
    )

    assert result.state is TemporalOAVEvidenceState.INVALID
    assert result.missing_cells == declared
    assert any(blocker.startswith("UNDECLARED_CELL:") for blocker in result.blockers)


def test_one_declared_missing_cell_makes_valid_series_partial() -> None:
    declared = (_key(0), _key(60))
    result = evaluate_temporal_oav_evidence(
        _request((_cell(0),)), declared_cells=declared
    )

    assert result.state is TemporalOAVEvidenceState.PARTIAL
    assert result.missing_cells == (_key(60),)
    assert any(blocker.startswith("MISSING_DECLARED_CELL:") for blocker in result.blockers)


@pytest.mark.parametrize("time_seconds", [-1, 0.5])
def test_noncanonical_time_is_rejected_by_the_frozen_key(time_seconds: object) -> None:
    with pytest.raises(ValueError, match="nonnegative integer seconds"):
        OAVTimepointKey(
            protocol_sha256=PROTOCOL_SHA,
            sample_id="S-001",
            material_id="Hedione",
            time_seconds=time_seconds,  # type: ignore[arg-type]
            endpoint="odor threshold",
        )


def test_incompatible_headspace_and_threshold_units_are_invalid() -> None:
    cell = _cell(threshold_unit="ppb")
    result = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.INVALID
    assert result.measured_cells == ()
    assert any(blocker.startswith("INCOMPATIBLE_UNITS:") for blocker in result.blockers)


def test_incompatible_threshold_context_is_invalid() -> None:
    cell = _cell(threshold_context="water-air|20C|dip|odor")
    result = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.INVALID
    assert any(blocker.startswith("INCOMPATIBLE_CONTEXT:") for blocker in result.blockers)


def test_threshold_source_change_blocks_relative_cancellation_without_erasing_cells() -> None:
    cells = (
        _cell(0, threshold_source_id="threshold-study-1"),
        _cell(60, threshold_source_id="threshold-study-2"),
    )
    result = evaluate_temporal_oav_evidence(
        _request(cells), declared_cells=tuple(cell.key for cell in cells)
    )

    assert result.state is TemporalOAVEvidenceState.PARTIAL
    assert len(result.measured_cells) == 2
    assert any(
        blocker.startswith("THRESHOLD_CANCELLATION_INCOMPATIBLE:")
        for blocker in result.blockers
    )


def test_invalid_interval_values_are_rejected_before_evaluation() -> None:
    with pytest.raises(ValueError, match="positive"):
        _interval((0.0, 1.0, 2.0))
    with pytest.raises(ValueError, match="P05 <= P50 <= P95"):
        _interval((2.0, 1.0, 3.0))
    known = _quantitative(
        1.0,
        basis=EvidenceBasis.MEASURED,
        method="test",
        source_id="test",
    )
    unknown = _quantitative(
        None,
        basis=EvidenceBasis.UNKNOWN,
        method="unknown",
        source_id="unknown",
    )
    with pytest.raises(ValueError, match="mix known and unknown"):
        OAVIntervalEvidence(unknown, known, known)


def test_natural_or_preblend_remains_a_whole_material_screen() -> None:
    cell = _cell(material_id="Bergamot FCF")
    result = evaluate_temporal_oav_evidence(
        _request((cell,)),
        declared_cells=(cell.key,),
        natural_or_preblend_material_ids=("Bergamot FCF",),
    )

    assert result.state is TemporalOAVEvidenceState.PARTIAL
    assert result.measured_cells[0].whole_material_screen is True
    assert "constituent_oav" not in result.measured_cells[0].as_dict()
    assert any(
        blocker.startswith("NATURAL_PREBLEND_WHOLE_MATERIAL_ONLY:")
        for blocker in result.blockers
    )


@pytest.mark.parametrize(
    "cell",
    [
        _cell(exact_stock_ref=None),
        _cell(active_mass_g=None),
    ],
)
def test_missing_stock_or_active_dose_lineage_cannot_be_strict(
    cell: OAVTimepointEvidenceInput,
) -> None:
    result = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.PARTIAL
    assert len(result.measured_cells) == 1
    assert any(
        blocker.startswith("MISSING_STOCK_LINEAGE:") for blocker in result.blockers
    )


def test_measured_and_modeled_series_remain_separate_and_mixed_is_partial() -> None:
    measured = _cell(0)
    modeled = _cell(
        60,
        model_tier=OAVModelTier.T2_MODELED,
        basis=EvidenceBasis.MODELED,
    )
    result = evaluate_temporal_oav_evidence(
        _request((modeled, measured)),
        declared_cells=(measured.key, modeled.key),
    )

    assert result.state is TemporalOAVEvidenceState.PARTIAL
    assert tuple(cell.key.time_seconds for cell in result.measured_cells) == (0,)
    assert tuple(cell.key.time_seconds for cell in result.modeled_cells) == (60,)
    assert any(
        blocker == "MIXED_MEASURED_MODELED_SERIES" for blocker in result.blockers
    )


def test_all_modeled_cells_produce_only_a_modeled_screen() -> None:
    cell = _cell(
        model_tier=OAVModelTier.T3_CALIBRATED_MODELED,
        basis=EvidenceBasis.MODELED,
    )
    result = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.MODELED_SCREEN
    assert result.measured_cells == ()
    assert len(result.modeled_cells) == 1


def test_unknown_cells_abstain_and_are_not_filled_from_other_series() -> None:
    cell = _unknown_cell()
    result = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )

    assert result.state is TemporalOAVEvidenceState.ABSTAINED
    assert result.measured_cells == ()
    assert result.modeled_cells == ()
    assert result.missing_cells == (cell.key,)


def test_result_bytes_and_hash_are_deterministic_under_input_order() -> None:
    cells = (
        _cell(0),
        _cell(
            60,
            model_tier=OAVModelTier.T2_MODELED,
            basis=EvidenceBasis.MODELED,
        ),
    )
    declared = tuple(cell.key for cell in cells)
    first = evaluate_temporal_oav_evidence(
        _request(cells), declared_cells=declared
    )
    second = evaluate_temporal_oav_evidence(
        _request(tuple(reversed(cells))), declared_cells=tuple(reversed(declared))
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert first.result_sha256 == hashlib.sha256(first.canonical_bytes()).hexdigest()


def test_result_export_import_round_trip_is_exact_and_closed() -> None:
    cell = _cell()
    original = evaluate_temporal_oav_evidence(
        _request((cell,)), declared_cells=(cell.key,)
    )
    restored = TemporalOAVEvidenceResult.from_dict(original.as_dict())

    assert restored == original
    assert restored.canonical_bytes() == original.canonical_bytes()
    assert all(value is False for value in restored.authority.values())

    malformed = original.as_dict()
    malformed["authority"] = {"sensory": True}
    with pytest.raises(ValueError, match="all-false"):
        TemporalOAVEvidenceResult.from_dict(malformed)
