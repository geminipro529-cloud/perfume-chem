from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.calibration.hashing import stable_json_hash
from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.fuckups.pre_mix_guard import evaluate_pre_mix_guard
from engine.pipeline.oav_evidence import (
    OAVEvidenceRequest,
    OAVEvidenceState,
    OAVIntervalEvidence,
    OAVMaterialEvidenceInput,
    OAVModelTier,
    OAVTimepointEvidenceInput,
    OAVTimepointKey,
    TemporalOAVEvidenceRequest,
    TemporalOAVEvidenceResult,
    TemporalOAVEvidenceState,
    evaluate_oav_evidence,
    evaluate_temporal_oav_evidence,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "data"
    / "benchmarks"
    / "solforge"
    / "evidence_foundation_recovery_v1"
    / "manifest.json"
)
FORMULA_SHA = "a" * 64
DOSE_SHA = "b" * 64
PROTOCOL_SHA = "c" * 64
CONTEXT_SHA = "d" * 64


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _source(source_id: str) -> EvidenceSourceRef:
    return EvidenceSourceRef(
        source_id=source_id,
        source_uri=f"https://example.test/{source_id}",
        retrieved_on="2026-08-26",
        source_sha256=hashlib.sha256(source_id.encode()).hexdigest(),
    )


def _quantity(
    value: float,
    *,
    basis: EvidenceBasis,
    unit: str,
    context: str,
    method: str,
    source_id: str,
) -> QuantitativeEvidence:
    return QuantitativeEvidence(
        value=value,
        unit=unit,
        context=context,
        method=method,
        basis=basis,
        source=_source(source_id),
    )


def _interval(
    values: tuple[float, float, float],
    *,
    basis: EvidenceBasis = EvidenceBasis.MEASURED,
    unit: str = "ug/m3",
    context: str = "ethanol-air|25C|spray|odor",
    method: str = "dynamic headspace",
    source_id: str = "headspace-1",
) -> OAVIntervalEvidence:
    return OAVIntervalEvidence(
        *(
            _quantity(
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


def _key(time_seconds: int, material: str = "Hedione") -> OAVTimepointKey:
    return OAVTimepointKey(
        protocol_sha256=PROTOCOL_SHA,
        sample_id="S-001",
        material_id=material,
        time_seconds=time_seconds,
        endpoint="odor threshold",
    )


def _cell(
    time_seconds: int,
    *,
    material: str = "Hedione",
    tier: OAVModelTier = OAVModelTier.T4_MEASURED,
    basis: EvidenceBasis = EvidenceBasis.MEASURED,
    headspace_unit: str = "ug/m3",
    threshold_unit: str = "ug/m3",
    headspace_context: str = "ethanol-air|25C|spray|odor",
    threshold_context: str = "ethanol-air|25C|spray|odor",
    threshold_source: str = "threshold-1",
    exact_stock_ref: str | None = "stock:HEDIONE:lot-1",
    active_mass_g: float | None = 0.1,
    context_sha256: str = CONTEXT_SHA,
) -> OAVTimepointEvidenceInput:
    return OAVTimepointEvidenceInput(
        key=_key(time_seconds, material),
        exact_stock_ref=exact_stock_ref,
        active_mass_g=active_mass_g,
        headspace_interval=_interval(
            (8.0, 10.0, 12.0),
            basis=basis,
            unit=headspace_unit,
            context=headspace_context,
            source_id=f"headspace-{time_seconds}-{tier.value}",
        ),
        threshold_interval=_interval(
            (2.0, 4.0, 8.0),
            basis=basis,
            unit=threshold_unit,
            context=threshold_context,
            method="ISO 13301 threshold",
            source_id=threshold_source,
        ),
        model_tier=tier,
        context_sha256=context_sha256,
    )


def _result(
    cells: tuple[OAVTimepointEvidenceInput, ...],
    declared: tuple[OAVTimepointKey, ...],
    *,
    natural: tuple[str, ...] = (),
    formula_sha256: str = FORMULA_SHA,
    dose_sha256: str = DOSE_SHA,
) -> TemporalOAVEvidenceResult:
    request = TemporalOAVEvidenceRequest(
        formula_sha256=formula_sha256,
        dose_receipt_sha256=dose_sha256,
        protocol_sha256=PROTOCOL_SHA,
        measurement_context_sha256=CONTEXT_SHA,
        cells=cells,
    )
    return evaluate_temporal_oav_evidence(
        request,
        declared_cells=declared,
        natural_or_preblend_material_ids=natural,
    )


def recovery_case_results() -> dict[str, TemporalOAVEvidenceResult]:
    strict_cells = (_cell(0), _cell(60))
    duplicate = _cell(0)
    measured = _cell(0)
    modeled = _cell(
        60,
        tier=OAVModelTier.T2_MODELED,
        basis=EvidenceBasis.MODELED,
    )
    natural = _cell(0, material="Bergamot FCF")
    return {
        "STRICT_MEASURED": _result(
            strict_cells,
            tuple(cell.key for cell in strict_cells),
        ),
        "UNIT_MISMATCH": _result(
            (_cell(0, threshold_unit="ppb"),),
            (_key(0),),
        ),
        "MATRIX_MISMATCH": _result(
            (_cell(0, threshold_context="water-air|20C|dip|odor"),),
            (_key(0),),
        ),
        "MISSING_TIMEPOINT": _result((_cell(0),), (_key(0), _key(60))),
        "DUPLICATE_TIMEPOINT": _result((duplicate, duplicate), (_key(0),)),
        "MIXED_MEASURED_MODELED": _result(
            (measured, modeled),
            (measured.key, modeled.key),
        ),
        "THRESHOLD_CANCELLATION": _result(
            (
                _cell(0, threshold_source="threshold-A"),
                _cell(60, threshold_source="threshold-B"),
            ),
            (_key(0), _key(60)),
        ),
        "NATURAL_CONSTITUENT_AMBIGUITY": _result(
            (natural,),
            (natural.key,),
            natural=("Bergamot FCF",),
        ),
    }


@pytest.mark.parametrize(
    "case_id",
    (
        "STRICT_MEASURED",
        "UNIT_MISMATCH",
        "MATRIX_MISMATCH",
        "MISSING_TIMEPOINT",
        "DUPLICATE_TIMEPOINT",
        "MIXED_MEASURED_MODELED",
        "THRESHOLD_CANCELLATION",
        "NATURAL_CONSTITUENT_AMBIGUITY",
    ),
)
def test_frozen_temporal_oav_cases(case_id: str) -> None:
    result = recovery_case_results()[case_id]
    expected = _manifest()["oav_cases"][case_id]

    assert result.state.value == expected["state"]
    assert result.result_sha256 == expected["result_sha256"]
    assert all(value is False for value in result.authority.values())


def test_row_order_and_irrelevant_material_labels_do_not_change_invariants() -> None:
    cells = (_cell(0), _cell(60))
    first = _result(cells, tuple(cell.key for cell in cells))
    second = _result(tuple(reversed(cells)), tuple(reversed([cell.key for cell in cells])))
    renamed_cells = (
        _cell(0, material="BLIND-X"),
        _cell(60, material="BLIND-X"),
    )
    renamed = _result(
        renamed_cells,
        tuple(cell.key for cell in renamed_cells),
    )

    assert first.canonical_bytes() == second.canonical_bytes()
    assert tuple(cell.oav_interval for cell in first.measured_cells) == tuple(
        cell.oav_interval for cell in renamed.measured_cells
    )
    assert first.state is renamed.state


def test_equal_observed_intervals_remain_a_null_change_without_sensory_authority() -> None:
    result = recovery_case_results()["STRICT_MEASURED"]

    assert len(result.measured_cells) == 2
    assert result.measured_cells[0].oav_interval == result.measured_cells[1].oav_interval
    assert result.state is TemporalOAVEvidenceState.STRICT_MEASURED_TIME_SERIES
    assert all(value is False for value in result.authority.values())


def test_formula_dose_and_context_hash_drift_cannot_reuse_a_receipt() -> None:
    cell = _cell(0)
    baseline = _result((cell,), (cell.key,))
    formula_drift = _result(
        (cell,),
        (cell.key,),
        formula_sha256="e" * 64,
    )
    dose_drift = _result(
        (cell,),
        (cell.key,),
        dose_sha256="f" * 64,
    )

    assert len(
        {
            baseline.result_sha256,
            formula_drift.result_sha256,
            dose_drift.result_sha256,
        }
    ) == 3
    with pytest.raises(ValueError, match="context_sha256"):
        TemporalOAVEvidenceRequest(
            formula_sha256=FORMULA_SHA,
            dose_receipt_sha256=DOSE_SHA,
            protocol_sha256=PROTOCOL_SHA,
            measurement_context_sha256=CONTEXT_SHA,
            cells=(replace(cell, context_sha256="9" * 64),),
        )


def test_interval_inversion_is_rejected_before_calculation() -> None:
    with pytest.raises(ValueError, match="P05 <= P50 <= P95"):
        _interval((2.0, 1.0, 3.0))


def test_active_dose_rebase_remains_a_hard_pre_mix_failure() -> None:
    parent_cell = _cell(0, material="Lemonile")
    child_cell = replace(parent_cell, key=_key(0, "Lemonile"))
    parent = _result((parent_cell,), (parent_cell.key,))
    child = _result(
        (child_cell,),
        (child_cell.key,),
        formula_sha256="e" * 64,
    )
    report = evaluate_pre_mix_guard(
        parent_ingredients_ul={"Lemonile": 10.0},
        parent_dilutions={"Lemonile": 1.0},
        child_ingredients_ul={"Lemonile": 100.0},
        child_dilutions={"Lemonile": 1.0},
        parent_temporal_oav=parent,
        child_temporal_oav=child,
    )

    assert report.status == "FAIL"
    assert "ACTIVE_DOSE_REVISION_JUMP" in {
        finding.code for finding in report.findings
    }


def test_stock_strength_substitution_fails_the_dose_binding() -> None:
    receipt_core = {
        "lines": [
            {
                "material_name": "Hedione",
                "stock_id": "stock:HEDIONE:lot-1",
                "stock_fraction": 1.0,
                "carrier": None,
            }
        ]
    }
    receipt_sha256 = stable_json_hash(receipt_core)
    receipt = {**receipt_core, "receipt_sha256": receipt_sha256}
    headspace = _quantity(
        2.0,
        basis=EvidenceBasis.MEASURED,
        unit="ppm",
        context="air at 25 C",
        method="measured headspace",
        source_id="headspace-stock-test",
    )
    threshold = _quantity(
        1.0,
        basis=EvidenceBasis.MEASURED,
        unit="ppm",
        context="air at 25 C",
        method="GC-O threshold",
        source_id="threshold-stock-test",
    )
    request = OAVEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=receipt_sha256,
        measurement_context="air at 25 C",
        rows=(
            OAVMaterialEvidenceInput(
                material_name="Hedione",
                canonical_name="Hedione",
                exact_stock_ref="stock:HEDIONE:lot-1",
                supplied_strength_fraction=0.1,
                carrier=None,
                active_mass_g=0.1,
                formula_matrix="air at 25 C",
                headspace=headspace,
                threshold=threshold,
            ),
        ),
        dose_receipt=receipt,
    )

    result = evaluate_oav_evidence(request)

    assert result.state is OAVEvidenceState.INVALID
    assert "Hedione: stock strength mismatch" in result.blockers
