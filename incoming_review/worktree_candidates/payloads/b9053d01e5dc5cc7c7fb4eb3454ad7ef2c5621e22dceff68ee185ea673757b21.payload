from __future__ import annotations

from dataclasses import replace

import pytest

from engine.evidence.unsupported_science import SOLFORGE_AUTHORITY_CLASSIFICATIONS
from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
    canonical_json_bytes,
    sha256_hex,
)
from engine.hedonic_evidence import (
    HedonicEvidenceRequest,
    HedonicEvidenceResult,
    HedonicEvidenceState,
    HedonicScope,
    evaluate_hedonic_evidence,
)
from engine.pipeline.oav_evidence import (
    OAVEvidenceRequest,
    OAVEvidenceState,
    OAVMaterialEvidenceInput,
    evaluate_oav_evidence,
)
from engine.pipeline.release_evidence import (
    EvidenceAxisState,
    ReleaseEvidenceAxis,
    ReleaseEvidenceRequest,
    ReleaseEvidenceStatus,
    evaluate_release_evidence,
    release_axis_from_hedonic,
    release_axis_from_oav,
)
from scripts.scientific_truth_inventory import SOLFORGE_RUNTIME_AUTHORITY

FORMULA_SHA = "a" * 64
SOURCE_SHA = "b" * 64


def _source() -> EvidenceSourceRef:
    return EvidenceSourceRef(
        source_id="test",
        source_uri="https://example.test/source",
        retrieved_on="2026-08-26",
        source_sha256=SOURCE_SHA,
    )


def _value(
    value: float | None,
    basis: EvidenceBasis,
    *,
    unit: str = "ppm",
    context: str = "air at 25 C",
) -> QuantitativeEvidence:
    return QuantitativeEvidence(
        value=value,
        unit=unit if basis is not EvidenceBasis.UNKNOWN else "",
        context=context if basis is not EvidenceBasis.UNKNOWN else "",
        method="test method" if basis is not EvidenceBasis.UNKNOWN else "",
        basis=basis,
        source=None if basis is EvidenceBasis.UNKNOWN else _source(),
    )


def _row(**overrides) -> OAVMaterialEvidenceInput:
    payload = {
        "material_name": "Hedione",
        "canonical_name": "Hedione",
        "exact_stock_ref": "stock-1",
        "supplied_strength_fraction": 0.5,
        "carrier": "DPG",
        "active_mass_g": 0.1,
        "formula_matrix": "ethanol-air",
        "headspace": _value(2.0, EvidenceBasis.MODELED),
        "threshold": _value(1.0, EvidenceBasis.TRANSFERRED),
    }
    payload.update(overrides)
    return OAVMaterialEvidenceInput(**payload)


def _receipt(**line_overrides) -> dict[str, object]:
    line = {
        "material_name": "Hedione",
        "stock_id": "stock-1",
        "stock_fraction": 0.5,
        "carrier": "DPG",
    }
    line.update(line_overrides)
    core: dict[str, object] = {"schema": "test-dose-v1", "lines": [line]}
    return {**core, "receipt_sha256": sha256_hex(canonical_json_bytes(core))}


def _oav_request(row: OAVMaterialEvidenceInput, receipt=None) -> OAVEvidenceRequest:
    receipt_payload = receipt or _receipt()
    return OAVEvidenceRequest(
        formula_sha256=FORMULA_SHA,
        dose_receipt_sha256=receipt_payload["receipt_sha256"],
        measurement_context="air at 25 C",
        rows=(row,),
        dose_receipt=receipt_payload,
    )


@pytest.mark.parametrize(
    ("row", "receipt", "blocker"),
    [
        (_row(supplied_strength_fraction=0.1), _receipt(), "stock strength"),
        (_row(carrier="TEC"), _receipt(), "carrier"),
        (_row(), {**_receipt(), "receipt_sha256": "c" * 64}, "receipt hash"),
        (
            _row(
                constituent_evidence=(_value(0.2, EvidenceBasis.TRANSFERRED),)
            ),
            _receipt(),
            "monomolecular",
        ),
        (
            _row(threshold=_value(1.0, EvidenceBasis.TRANSFERRED, unit="ppb")),
            _receipt(),
            "units",
        ),
        (
            _row(
                headspace=_value(
                    2.0,
                    EvidenceBasis.MEASURED,
                    context="different apparatus",
                )
            ),
            _receipt(),
            "context",
        ),
    ],
)
def test_oav_adversarial_inputs_fail_closed(row, receipt, blocker) -> None:
    result = evaluate_oav_evidence(_oav_request(row, receipt))
    assert result.state is OAVEvidenceState.INVALID
    assert any(blocker in value for value in result.blockers)
    assert result.sensory_authority is False
    assert result.hedonic_authority is False
    assert result.release_authority is False


def test_perceptible_count_cannot_upgrade_modeled_screen() -> None:
    single = evaluate_oav_evidence(
        OAVEvidenceRequest(
            formula_sha256=FORMULA_SHA,
            dose_receipt_sha256="d" * 64,
            measurement_context="air at 25 C",
            rows=(_row(),),
        )
    )
    many = evaluate_oav_evidence(
        OAVEvidenceRequest(
            formula_sha256=FORMULA_SHA,
            dose_receipt_sha256="d" * 64,
            measurement_context="air at 25 C",
            rows=tuple(
                replace(_row(), material_name=f"row-{index}", canonical_name=f"row-{index}")
                for index in range(20)
            ),
        )
    )
    assert single.state is many.state is OAVEvidenceState.PARTIAL


def test_synthetic_validated_liking_without_receipt_is_invalid() -> None:
    forged = HedonicEvidenceResult(
        state=HedonicEvidenceState.VALIDATED_EXACT_SCOPE,
        criterion_id="LIKING",
        scope=HedonicScope.TRAINED_PANEL,
        formula_build_sha256=FORMULA_SHA,
        fit_receipt_sha256=None,
        utility_intervals={"A": (0.1, 0.2)},
        tie_rate=0.0,
        directional_comparison_count=10,
        assessor_heterogeneity={},
        order_effect=0.0,
        blockers=(),
        limitations=(),
    )
    axis = release_axis_from_hedonic(forged)
    assert axis.state is EvidenceAxisState.INVALID
    assert axis.blockers


def test_criterion_substitution_is_invalid_not_neutral() -> None:
    result = evaluate_hedonic_evidence(
        HedonicEvidenceRequest(
            criterion_id="RICHNESS",
            scope=HedonicScope.OWNER,
            formula_build_sha256=FORMULA_SHA,
            sample_sha256=("e" * 64,),
            protocol_sha256="f" * 64,
            assessor_ids=("owner",),
            repeat_ids=("repeat-1",),
            time_seconds=300,
            schedule_sha256="1" * 64,
        )
    )
    assert result.state is HedonicEvidenceState.INVALID_OR_CONFOUNDED
    assert result.release_authority is False


def test_perfect_diagnostics_cannot_compensate_for_missing_evidence() -> None:
    oav = evaluate_oav_evidence(
        OAVEvidenceRequest(
            formula_sha256=FORMULA_SHA,
            dose_receipt_sha256="d" * 64,
            measurement_context="air at 25 C",
            rows=(_row(),),
        )
    )
    required = []
    for axis_id in ReleaseEvidenceAxis.required_axis_ids():
        if axis_id == "oav_evidence":
            required.append(release_axis_from_oav(oav))
        else:
            required.append(
                ReleaseEvidenceAxis(
                    axis_id=axis_id,
                    state=(
                        EvidenceAxisState.NOT_TESTED
                        if axis_id == "hedonic_evidence"
                        else EvidenceAxisState.PASS
                    ),
                    source_sha256=SOURCE_SHA,
                    scope={"formula_sha256": FORMULA_SHA},
                )
            )
    result = evaluate_release_evidence(
        ReleaseEvidenceRequest(
            formula_sha256=FORMULA_SHA,
            axes=tuple(required),
            diagnostics={"legacy_total": 100, "beauty": 100, "rank_score": 100},
        )
    )
    assert result.status is ReleaseEvidenceStatus.HOLD
    assert result.release_authority is False


def test_scientific_truth_registry_distinguishes_legacy_and_v2_authority() -> None:
    assert SOLFORGE_AUTHORITY_CLASSIFICATIONS["fixed_valence_hedonic_scorer"][
        "classification"
    ] == "LEGACY_HEURISTIC_PROVENANCE"
    assert SOLFORGE_AUTHORITY_CLASSIFICATIONS["oav_authority_rank"][
        "classification"
    ] == "LEGACY_HEURISTIC_PROVENANCE"
    assert SOLFORGE_RUNTIME_AUTHORITY["oav_evidence_v2"]["classification"] == (
        "COMPUTATIONAL_OR_MEASURED_EVIDENCE_STATE"
    )
    assert SOLFORGE_RUNTIME_AUTHORITY["hedonic_evidence_v2"]["classification"] == (
        "OBSERVED_EXACT_SCOPE_ONLY"
    )
    assert SOLFORGE_RUNTIME_AUTHORITY["release_evidence_v2"]["classification"] == (
        "NONCOMPENSATORY_DECISION_SUPPORT"
    )
