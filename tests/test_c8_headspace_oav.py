from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

import engine.physics.headspace_oav as c8
from engine.physics.headspace_oav import (
    C8_SENSOMICS_SEQUENCE,
    PERMITTED_C8_CLAIMS,
    WITHHELD_C8_CLAIMS,
    BoundedQuantity,
    C8Claim,
    C8ClaimDecision,
    C8ClaimStatus,
    EvidenceReference,
    GasConcentrationEvidence,
    GasConcentrationOrigin,
    GasPhaseContext,
    HeadspaceOAVAssessment,
    HeadspaceOAVContractError,
    InteractionAdjustmentRequest,
    InteractionAdjustmentStatus,
    InteractionAdjustmentTarget,
    InteractionApplicableRange,
    InteractionCalibrationState,
    InteractionConcentration,
    InteractionEvidence,
    InteractionEvidenceKind,
    InteractionKind,
    InteractionNumericalEffect,
    OAVAssessmentStatus,
    OAVScreeningClass,
    OdorThresholdEvidence,
    SensomicsClaim,
    SensomicsProgram,
    SensomicsStage,
    SensomicsStageRecord,
    SensomicsStageStatus,
    ThresholdAuthority,
    ThresholdKind,
    authorize_interaction_adjustment,
    calculate_headspace_oav,
    evaluate_c8_claim,
    evaluate_sensomics_claim,
)

PUBLIC_C8_NAMES = {
    "C8_SENSOMICS_SEQUENCE",
    "PERMITTED_C8_CLAIMS",
    "WITHHELD_C8_CLAIMS",
    "BoundedQuantity",
    "C8Claim",
    "C8ClaimDecision",
    "C8ClaimStatus",
    "EvidenceReference",
    "GasConcentrationEvidence",
    "GasConcentrationOrigin",
    "GasPhaseContext",
    "HeadspaceOAVAssessment",
    "HeadspaceOAVContractError",
    "InteractionAdjustmentDecision",
    "InteractionAdjustmentRequest",
    "InteractionAdjustmentStatus",
    "InteractionAdjustmentTarget",
    "InteractionApplicableRange",
    "InteractionCalibrationState",
    "InteractionConcentration",
    "InteractionEvidence",
    "InteractionEvidenceKind",
    "InteractionKind",
    "InteractionNumericalEffect",
    "OAVAssessmentStatus",
    "OAVScreeningClass",
    "OdorThresholdEvidence",
    "SensomicsAssessment",
    "SensomicsClaim",
    "SensomicsProgram",
    "SensomicsStage",
    "SensomicsStageRecord",
    "SensomicsStageStatus",
    "ThresholdAuthority",
    "ThresholdKind",
    "authorize_interaction_adjustment",
    "calculate_headspace_oav",
    "evaluate_c8_claim",
    "evaluate_sensomics_claim",
}


def digest(character: str) -> str:
    return character * 64


def source(
    *,
    source_id: str = "source-1",
    source_kind: str = "PRIMARY_MEASUREMENT",
    citation: str = "run:headspace-1",
    version: str = "2026-08-03",
    source_sha256: str = digest("a"),
) -> EvidenceReference:
    return EvidenceReference(
        source_id=source_id,
        source_kind=source_kind,
        citation=citation,
        version=version,
        source_sha256=source_sha256,
    )


def context(**overrides: object) -> GasPhaseContext:
    values: dict[str, object] = {
        "context_id": "ctx-air-vial-25c",
        "phase_or_sampling_regime": "STATIC_HEADSPACE",
        "matrix_id": "matrix-ethanol-water-80-20",
        "temperature_k": 298.15,
        "pressure_pa": 101_325.0,
        "relative_humidity_fraction": 0.5,
        "exposure_route": "ORTHONASAL",
        "substrate_or_apparatus_id": "vial-20ml-method-1",
    }
    values.update(overrides)
    return GasPhaseContext(**values)  # type: ignore[arg-type]


def quantity(
    *,
    value: float = 10.0,
    unit: str = "ppb_vv",
    lower_bound: float | None = 8.0,
    upper_bound: float | None = 12.0,
    uncertainty_basis: str = "95 percent bounded measurement interval",
) -> BoundedQuantity:
    return BoundedQuantity(
        value=value,
        unit=unit,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        uncertainty_basis=uncertainty_basis,
    )


def gas_evidence(
    *,
    evidence_id: str = "gas-1",
    analyte_id: str = "cas:78-70-6",
    gas_quantity: BoundedQuantity | None = None,
    origin: GasConcentrationOrigin = GasConcentrationOrigin.MEASURED,
    gas_context: GasPhaseContext | None = None,
    evidence_source: EvidenceReference | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    model_release_sha256: str | None = None,
    within_model_domain: bool | None = None,
) -> GasConcentrationEvidence:
    if origin is GasConcentrationOrigin.PREDICTED:
        model_id = model_id or "c4-ideal-raoult"
        model_version = model_version or "c4-ideal-raoult-v1"
        model_release_sha256 = model_release_sha256 or digest("b")
        if within_model_domain is None:
            within_model_domain = True
    return GasConcentrationEvidence(
        evidence_id=evidence_id,
        analyte_id=analyte_id,
        quantity=gas_quantity or quantity(),
        origin=origin,
        context=gas_context or context(),
        source=evidence_source or source(),
        model_id=model_id,
        model_version=model_version,
        model_release_sha256=model_release_sha256,
        within_model_domain=within_model_domain,
    )


def threshold_evidence(
    *,
    threshold_id: str = "threshold-1",
    analyte_id: str = "cas:78-70-6",
    threshold_quantity: BoundedQuantity | None = None,
    kind: ThresholdKind = ThresholdKind.DETECTION,
    authority: ThresholdAuthority = ThresholdAuthority.DIRECT_CONTEXT_MEASUREMENT,
    threshold_context: GasPhaseContext | None = None,
    method: str = "three-alternative forced-choice ascending method",
    assessor_population: str = "trained adult panel",
    assessor_count: int = 24,
    evidence_source: EvidenceReference | None = None,
) -> OdorThresholdEvidence:
    return OdorThresholdEvidence(
        threshold_id=threshold_id,
        analyte_id=analyte_id,
        quantity=threshold_quantity
        or quantity(
            value=2.0,
            lower_bound=1.0,
            upper_bound=4.0,
            uncertainty_basis="95 percent threshold interval",
        ),
        kind=kind,
        authority=authority,
        context=threshold_context or context(context_id="ctx-threshold-study"),
        method=method,
        assessor_population=assessor_population,
        assessor_count=assessor_count,
        source=evidence_source
        or source(
            source_id="threshold-source-1",
            source_kind="PRIMARY_THRESHOLD_STUDY",
            citation="doi:10.example/threshold",
            source_sha256=digest("c"),
        ),
    )


def concentration(
    identity_id: str,
    *,
    value: float,
    lower: float,
    upper: float,
    unit: str = "ppb_vv",
) -> InteractionConcentration:
    return InteractionConcentration(
        identity_id=identity_id,
        quantity=quantity(
            value=value,
            lower_bound=lower,
            upper_bound=upper,
            unit=unit,
            uncertainty_basis="interaction concentration bounds",
        ),
    )


def applicable_range(
    identity_id: str,
    *,
    lower: float,
    upper: float,
    unit: str = "ppb_vv",
) -> InteractionApplicableRange:
    return InteractionApplicableRange(
        identity_id=identity_id,
        lower_bound=lower,
        upper_bound=upper,
        unit=unit,
    )


def numerical_effect(
    *,
    target: InteractionAdjustmentTarget = InteractionAdjustmentTarget.PERCEIVED_INTENSITY,
) -> InteractionNumericalEffect:
    return InteractionNumericalEffect(
        target=target,
        multiplier=quantity(
            value=1.5,
            unit="1",
            lower_bound=1.2,
            upper_bound=1.8,
            uncertainty_basis="held-out calibrated multiplier interval",
        ),
        formula="I_pair = calibrated_multiplier * I_reference",
    )


def interaction_evidence(
    *,
    interaction_id: str = "interaction-1",
    kind: InteractionKind = InteractionKind.SYNERGISTIC,
    evidence_kind: InteractionEvidenceKind = InteractionEvidenceKind.MODEL,
    identities: tuple[str, ...] = ("cas:a", "cas:b"),
    concentrations: tuple[InteractionConcentration, ...] | None = None,
    interaction_context: GasPhaseContext | None = None,
    attribute: str = "floral intensity",
    sensory_method: str = "randomized coded pair comparison",
    assessor_population: str = "trained adult panel",
    assessor_count: int = 20,
    model_or_formula: str | None = "context-calibrated interaction model v1",
    evidence_source: EvidenceReference | None = None,
    uncertainty_statement: str = "bounded held-out uncertainty retained",
    applicable_ranges: tuple[InteractionApplicableRange, ...] | None = None,
    calibration_state: InteractionCalibrationState = (
        InteractionCalibrationState.CONTEXT_CALIBRATED
    ),
    effect: InteractionNumericalEffect | None = None,
) -> InteractionEvidence:
    if concentrations is None:
        concentrations = (
            concentration("cas:a", value=1.0, lower=0.8, upper=1.2),
            concentration("cas:b", value=2.0, lower=1.7, upper=2.3),
        )
    if applicable_ranges is None:
        applicable_ranges = (
            applicable_range("cas:a", lower=0.5, upper=1.5),
            applicable_range("cas:b", lower=1.0, upper=3.0),
        )
    if effect is None and calibration_state is InteractionCalibrationState.CONTEXT_CALIBRATED:
        effect = numerical_effect()
    return InteractionEvidence(
        interaction_id=interaction_id,
        kind=kind,
        evidence_kind=evidence_kind,
        identities=identities,
        concentrations=concentrations,
        context=interaction_context or context(context_id="ctx-interaction"),
        attribute=attribute,
        sensory_method=sensory_method,
        assessor_population=assessor_population,
        assessor_count=assessor_count,
        model_or_formula=model_or_formula,
        source=evidence_source
        or source(
            source_id="interaction-source-1",
            source_kind="PRIMARY_SENSORY_STUDY",
            citation="study:interaction-1",
            source_sha256=digest("d"),
        ),
        uncertainty_statement=uncertainty_statement,
        applicable_ranges=applicable_ranges,
        calibration_state=calibration_state,
        numerical_effect=effect,
    )


def adjustment_request(
    *,
    request_id: str = "adjustment-request-1",
    identities: tuple[str, ...] = ("cas:a", "cas:b"),
    concentrations: tuple[InteractionConcentration, ...] | None = None,
    request_context: GasPhaseContext | None = None,
    target: InteractionAdjustmentTarget = InteractionAdjustmentTarget.PERCEIVED_INTENSITY,
) -> InteractionAdjustmentRequest:
    return InteractionAdjustmentRequest(
        request_id=request_id,
        identities=identities,
        concentrations=concentrations
        or (
            concentration("cas:a", value=1.0, lower=0.8, upper=1.2),
            concentration("cas:b", value=2.0, lower=1.7, upper=2.3),
        ),
        context=request_context or context(context_id="ctx-adjustment"),
        target=target,
    )


def sensomics_program(
    completed_stages: int,
    *,
    program_id: str = "sensomics-program-1",
) -> SensomicsProgram:
    records = []
    for index, stage in enumerate(C8_SENSOMICS_SEQUENCE):
        completed = index < completed_stages
        records.append(
            SensomicsStageRecord(
                stage=stage,
                status=(
                    SensomicsStageStatus.COMPLETED
                    if completed
                    else SensomicsStageStatus.NOT_PERFORMED
                ),
                evidence=(
                    (
                        source(
                            source_id=f"sensomics-stage-{index + 1}",
                            citation=f"activity:stage-{index + 1}",
                            source_sha256=f"{index + 1:x}" * 64,
                        ),
                    )
                    if completed
                    else ()
                ),
                notes=(f"stage {index + 1} record",),
            )
        )
    return SensomicsProgram(
        program_id=program_id,
        context=context(context_id="ctx-sensomics"),
        stages=tuple(records),
    )


def assert_round_trip(value: object) -> None:
    mapping = value.to_mapping()  # type: ignore[attr-defined]
    assert type(value).from_mapping(mapping) == value  # type: ignore[attr-defined]


def test_c8_public_exports_and_closed_vocabularies_are_exact() -> None:
    assert set(c8.__all__) == PUBLIC_C8_NAMES
    assert len(c8.__all__) == len(set(c8.__all__)) == 39
    assert [item.value for item in GasConcentrationOrigin] == ["MEASURED", "PREDICTED"]
    assert [item.value for item in ThresholdKind] == ["DETECTION", "RECOGNITION"]
    assert [item.value for item in ThresholdAuthority] == [
        "DIRECT_CONTEXT_MEASUREMENT",
        "PEER_REVIEWED_CONTEXT_MATCHED",
        "CONTEXT_MISMATCHED",
        "PROXY",
        "UNKNOWN",
    ]
    assert [item.value for item in OAVAssessmentStatus] == ["COMPUTED", "ABSTAINED"]
    assert [item.value for item in OAVScreeningClass] == [
        "ABOVE_THRESHOLD",
        "BELOW_THRESHOLD",
        "STRADDLES_THRESHOLD",
        "UNKNOWN",
    ]
    assert [item.value for item in InteractionKind] == [
        "ADDITIVE",
        "SYNERGISTIC",
        "MASKING",
        "SUPPRESSIVE",
        "QUALITATIVE_TRANSFORMATION",
        "UNKNOWN",
    ]
    assert [item.value for item in InteractionAdjustmentTarget] == [
        "HEADSPACE_CONCENTRATION",
        "PERCEIVED_INTENSITY",
    ]
    assert [item.value for item in InteractionAdjustmentStatus] == [
        "AUTHORIZED",
        "WITHHELD",
    ]
    assert [item.value for item in SensomicsStageStatus] == [
        "COMPLETED",
        "FAILED",
        "NOT_PERFORMED",
    ]
    assert [item.value for item in C8ClaimStatus] == [
        "PERMITTED_WITH_EVIDENCE",
        "WITHHELD",
    ]


def test_c8_claim_sets_are_exact_disjoint_and_complete() -> None:
    assert PERMITTED_C8_CLAIMS == (
        C8Claim.PREDICTED_EQUILIBRIUM_HEADSPACE,
        C8Claim.PREDICTED_PHYSICAL_RELEASE,
        C8Claim.ABOVE_THRESHOLD_SCREENING,
        C8Claim.CANDIDATE_ODORANT_PRIORITIZATION,
        C8Claim.EXPERIMENT_SELECTION,
    )
    assert WITHHELD_C8_CLAIMS == (
        C8Claim.EXACT_PERCEIVED_INTENSITY,
        C8Claim.PERCENT_MIXTURE_CONTRIBUTION,
        C8Claim.PLEASANTNESS,
        C8Claim.TARGET_SIMILARITY,
        C8Claim.FAMILY_IDENTITY,
        C8Claim.LONGEVITY,
        C8Claim.SILLAGE,
        C8Claim.CONSUMER_PREFERENCE,
    )
    assert set(PERMITTED_C8_CLAIMS).isdisjoint(WITHHELD_C8_CLAIMS)
    assert set(PERMITTED_C8_CLAIMS) | set(WITHHELD_C8_CLAIMS) == set(C8Claim)


def test_evidence_reference_is_strict_hashed_and_round_trips() -> None:
    record = source()
    assert record.to_mapping()["schema"] == "c8-evidence-reference-v1"
    assert len(record.content_sha256) == 64
    assert_round_trip(record)
    assert replace(record, version="2026-08-04").content_sha256 != record.content_sha256
    with pytest.raises(HeadspaceOAVContractError, match="source_sha256"):
        replace(record, source_sha256="not-a-hash")
    tampered = record.to_mapping()
    tampered["content_sha256"] = digest("f")
    with pytest.raises(HeadspaceOAVContractError, match="content_sha256"):
        EvidenceReference.from_mapping(tampered)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"temperature_k": 0.0}, "temperature"),
        ({"pressure_pa": 0.0}, "pressure"),
        ({"relative_humidity_fraction": -0.01}, "humidity"),
        ({"relative_humidity_fraction": 1.01}, "humidity"),
        ({"phase_or_sampling_regime": ""}, "phase"),
        ({"matrix_id": ""}, "matrix"),
    ],
)
def test_gas_phase_context_rejects_malformed_conditions(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(HeadspaceOAVContractError, match=message):
        context(**overrides)


def test_gas_phase_context_separates_record_identity_from_compatibility() -> None:
    first = context(context_id="measurement-context")
    second = context(context_id="threshold-context")
    changed = context(context_id="changed", matrix_id="other-matrix")
    assert first.content_sha256 != second.content_sha256
    assert first.compatibility_sha256 == second.compatibility_sha256
    assert first.is_compatible_with(second) is True
    assert first.is_compatible_with(changed) is False
    assert_round_trip(first)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"value": 0.0},
        {"value": float("inf")},
        {"lower_bound": None, "upper_bound": 12.0},
        {"lower_bound": 8.0, "upper_bound": None},
        {"value": 7.0, "lower_bound": 8.0, "upper_bound": 12.0},
        {"value": 13.0, "lower_bound": 8.0, "upper_bound": 12.0},
        {"lower_bound": 12.0, "upper_bound": 8.0},
        {"unit": ""},
        {"uncertainty_basis": ""},
    ],
)
def test_bounded_quantity_rejects_nonphysical_or_partial_bounds(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises(HeadspaceOAVContractError):
        quantity(**kwargs)  # type: ignore[arg-type]


def test_bounded_quantity_preserves_known_and_unknown_uncertainty() -> None:
    bounded = quantity()
    unknown = quantity(
        lower_bound=None,
        upper_bound=None,
        uncertainty_basis="UNKNOWN",
    )
    assert bounded.has_numeric_bounds is True
    assert unknown.has_numeric_bounds is False
    assert_round_trip(bounded)
    assert_round_trip(unknown)


def test_measured_gas_evidence_forbids_model_metadata() -> None:
    measured = gas_evidence()
    assert measured.origin is GasConcentrationOrigin.MEASURED
    assert measured.model_id is None
    assert measured.within_model_domain is None
    assert_round_trip(measured)
    with pytest.raises(HeadspaceOAVContractError, match="measured"):
        gas_evidence(model_id="model-that-must-not-exist")


def test_predicted_gas_evidence_requires_complete_model_and_domain_metadata() -> None:
    predicted = gas_evidence(origin=GasConcentrationOrigin.PREDICTED)
    assert predicted.within_model_domain is True
    assert predicted.model_release_sha256 == digest("b")
    assert_round_trip(predicted)
    with pytest.raises(HeadspaceOAVContractError, match="predicted"):
        GasConcentrationEvidence(
            evidence_id="gas-bad",
            analyte_id="cas:78-70-6",
            quantity=quantity(),
            origin=GasConcentrationOrigin.PREDICTED,
            context=context(),
            source=source(),
            model_id="model",
            model_version=None,
            model_release_sha256=digest("b"),
            within_model_domain=True,
        )


def test_threshold_evidence_preserves_method_population_context_and_authority() -> None:
    threshold = threshold_evidence()
    assert threshold.kind is ThresholdKind.DETECTION
    assert threshold.authority is ThresholdAuthority.DIRECT_CONTEXT_MEASUREMENT
    assert threshold.assessor_count == 24
    assert threshold.context.matrix_id == "matrix-ethanol-water-80-20"
    assert_round_trip(threshold)
    with pytest.raises(HeadspaceOAVContractError, match="assessor_count"):
        threshold_evidence(assessor_count=0)


def test_headspace_oav_propagates_conservative_ratio_bounds() -> None:
    result = calculate_headspace_oav(gas_evidence(), threshold_evidence())
    assert result.status is OAVAssessmentStatus.COMPUTED
    assert result.claim is C8Claim.ABOVE_THRESHOLD_SCREENING
    assert result.oav_point == pytest.approx(5.0)
    assert result.oav_lower == pytest.approx(2.0)
    assert result.oav_upper == pytest.approx(12.0)
    assert result.screening_class is OAVScreeningClass.ABOVE_THRESHOLD
    assert result.reasons == ()
    assert result.gas_evidence_sha256 == gas_evidence().content_sha256
    assert result.threshold_evidence_sha256 == threshold_evidence().content_sha256
    assert_round_trip(result)


@pytest.mark.parametrize(
    ("gas_quantity", "expected"),
    [
        (
            quantity(value=0.2, lower_bound=0.1, upper_bound=0.3),
            OAVScreeningClass.BELOW_THRESHOLD,
        ),
        (
            quantity(value=1.5, lower_bound=0.5, upper_bound=2.5),
            OAVScreeningClass.STRADDLES_THRESHOLD,
        ),
        (
            quantity(value=4.0, lower_bound=4.0, upper_bound=5.0),
            OAVScreeningClass.ABOVE_THRESHOLD,
        ),
    ],
)
def test_headspace_oav_classifies_only_from_complete_interval(
    gas_quantity: BoundedQuantity,
    expected: OAVScreeningClass,
) -> None:
    result = calculate_headspace_oav(
        gas_evidence(gas_quantity=gas_quantity),
        threshold_evidence(),
    )
    assert result.status is OAVAssessmentStatus.COMPUTED
    assert result.screening_class is expected


def test_peer_reviewed_context_matched_threshold_can_support_screening() -> None:
    result = calculate_headspace_oav(
        gas_evidence(),
        threshold_evidence(authority=ThresholdAuthority.PEER_REVIEWED_CONTEXT_MATCHED),
    )
    assert result.status is OAVAssessmentStatus.COMPUTED


@pytest.mark.parametrize(
    ("gas", "threshold", "claim", "reason_fragment"),
    [
        (
            gas_evidence(origin=GasConcentrationOrigin.PREDICTED, within_model_domain=False),
            threshold_evidence(),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "outside model domain",
        ),
        (
            gas_evidence(analyte_id="cas:other"),
            threshold_evidence(),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "analyte",
        ),
        (
            gas_evidence(gas_context=context(matrix_id="matrix-other")),
            threshold_evidence(),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "context",
        ),
        (
            gas_evidence(gas_quantity=quantity(unit="ug_m3")),
            threshold_evidence(),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "unit",
        ),
        (
            gas_evidence(),
            threshold_evidence(authority=ThresholdAuthority.PROXY),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "authority",
        ),
        (
            gas_evidence(),
            threshold_evidence(kind=ThresholdKind.RECOGNITION),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "detection threshold",
        ),
        (
            gas_evidence(
                gas_quantity=quantity(
                    lower_bound=None,
                    upper_bound=None,
                    uncertainty_basis="UNKNOWN",
                )
            ),
            threshold_evidence(),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "uncertainty",
        ),
        (
            gas_evidence(),
            threshold_evidence(
                threshold_quantity=quantity(
                    value=2.0,
                    lower_bound=None,
                    upper_bound=None,
                    uncertainty_basis="UNKNOWN",
                )
            ),
            C8Claim.ABOVE_THRESHOLD_SCREENING,
            "uncertainty",
        ),
        (
            gas_evidence(),
            threshold_evidence(),
            C8Claim.EXACT_PERCEIVED_INTENSITY,
            "claim",
        ),
    ],
)
def test_headspace_oav_abstains_answerlessly_on_every_failed_precondition(
    gas: GasConcentrationEvidence,
    threshold: OdorThresholdEvidence,
    claim: C8Claim,
    reason_fragment: str,
) -> None:
    result = calculate_headspace_oav(gas, threshold, claim=claim)
    assert result.status is OAVAssessmentStatus.ABSTAINED
    assert result.oav_point is None
    assert result.oav_lower is None
    assert result.oav_upper is None
    assert result.screening_class is OAVScreeningClass.UNKNOWN
    assert any(reason_fragment in reason.casefold() for reason in result.reasons)


def test_computed_oav_never_claims_intensity_contribution_or_similarity() -> None:
    result = calculate_headspace_oav(gas_evidence(), threshold_evidence())
    limitations = " ".join(result.limitations).casefold()
    assert "screening" in limitations
    assert "not exact perceived intensity" in limitations
    assert "not percent mixture contribution" in limitations
    assert "not target similarity" in limitations
    assert "not consumer preference" in limitations
    assert not hasattr(result, "perceived_intensity")
    assert not hasattr(result, "percent_contribution")


def test_oav_mapping_rejects_answer_bearing_abstention_and_hash_tampering() -> None:
    abstained = calculate_headspace_oav(
        gas_evidence(),
        threshold_evidence(authority=ThresholdAuthority.UNKNOWN),
    )
    payload = abstained.to_mapping()
    payload["oav_point"] = 5.0
    payload.pop("content_sha256")
    with pytest.raises(HeadspaceOAVContractError, match="abstained"):
        HeadspaceOAVAssessment.from_mapping(payload)
    computed = calculate_headspace_oav(gas_evidence(), threshold_evidence())
    tampered = computed.to_mapping()
    tampered["content_sha256"] = digest("e")
    with pytest.raises(HeadspaceOAVContractError, match="content_sha256"):
        HeadspaceOAVAssessment.from_mapping(tampered)


@pytest.mark.parametrize("kind", tuple(InteractionKind))
def test_all_interaction_kinds_are_context_specific_records(kind: InteractionKind) -> None:
    record = interaction_evidence(kind=kind)
    assert record.kind is kind
    assert record.identities == ("cas:a", "cas:b")
    assert tuple(item.identity_id for item in record.concentrations) == record.identities
    assert tuple(item.identity_id for item in record.applicable_ranges) == record.identities
    assert record.context.matrix_id == "matrix-ethanol-water-80-20"
    assert record.attribute == "floral intensity"
    assert record.sensory_method == "randomized coded pair comparison"
    assert record.assessor_population == "trained adult panel"
    assert record.assessor_count == 20
    assert record.source.source_kind == "PRIMARY_SENSORY_STUDY"
    assert record.uncertainty_statement
    assert_round_trip(record)


def test_interaction_identity_concentration_and_range_coverage_is_exact() -> None:
    with pytest.raises(HeadspaceOAVContractError, match="duplicate"):
        interaction_evidence(identities=("cas:a", "cas:a"))
    with pytest.raises(HeadspaceOAVContractError, match="concentration"):
        interaction_evidence(
            concentrations=(
                concentration("cas:a", value=1.0, lower=0.8, upper=1.2),
                concentration("cas:c", value=2.0, lower=1.7, upper=2.3),
            )
        )
    with pytest.raises(HeadspaceOAVContractError, match="applicable"):
        interaction_evidence(
            applicable_ranges=(
                applicable_range("cas:a", lower=0.5, upper=1.5),
                applicable_range("cas:c", lower=1.0, upper=3.0),
            )
        )


def test_observation_only_interaction_rejects_a_numerical_effect() -> None:
    with pytest.raises(HeadspaceOAVContractError, match="observation"):
        interaction_evidence(
            evidence_kind=InteractionEvidenceKind.OBSERVATION,
            calibration_state=InteractionCalibrationState.OBSERVED_ONLY,
            model_or_formula=None,
            effect=numerical_effect(),
        )


def test_uncalibrated_generic_interaction_rejects_a_numerical_effect() -> None:
    with pytest.raises(HeadspaceOAVContractError, match="uncalibrated"):
        interaction_evidence(
            calibration_state=InteractionCalibrationState.UNCALIBRATED_GENERIC,
            model_or_formula="generic pair table",
            effect=numerical_effect(),
        )


def test_context_calibrated_model_requires_formula_ranges_and_bounded_effect() -> None:
    record = interaction_evidence()
    assert record.calibration_state is InteractionCalibrationState.CONTEXT_CALIBRATED
    assert record.numerical_effect is not None
    assert record.numerical_effect.multiplier.has_numeric_bounds is True
    assert record.numerical_effect.multiplier.unit == "1"
    with pytest.raises(HeadspaceOAVContractError, match="model_or_formula"):
        interaction_evidence(model_or_formula="")
    with pytest.raises(HeadspaceOAVContractError, match="dimensionless"):
        numerical_effect().__class__(
            target=InteractionAdjustmentTarget.PERCEIVED_INTENSITY,
            multiplier=quantity(unit="ppm"),
            formula="invalid-unit formula",
        )


def test_calibrated_interaction_authorization_exposes_but_does_not_apply_effect() -> None:
    evidence = interaction_evidence()
    request = adjustment_request()
    decision = authorize_interaction_adjustment(evidence, request)
    assert decision.status is InteractionAdjustmentStatus.AUTHORIZED
    assert decision.numerical_effect == evidence.numerical_effect
    assert decision.reasons == ()
    assert not hasattr(decision, "adjusted_headspace")
    assert not hasattr(decision, "adjusted_intensity")
    assert_round_trip(request)
    assert_round_trip(decision)


@pytest.mark.parametrize(
    ("evidence", "adjustment", "reason_fragment"),
    [
        (
            interaction_evidence(
                calibration_state=InteractionCalibrationState.UNCALIBRATED_GENERIC,
                model_or_formula="generic pair table",
                effect=None,
            ),
            adjustment_request(),
            "calibration",
        ),
        (
            interaction_evidence(),
            adjustment_request(
                identities=("cas:a", "cas:c"),
                concentrations=(
                    concentration("cas:a", value=1.0, lower=0.8, upper=1.2),
                    concentration("cas:c", value=2.0, lower=1.7, upper=2.3),
                ),
            ),
            "identit",
        ),
        (
            interaction_evidence(),
            adjustment_request(request_context=context(matrix_id="different-matrix")),
            "context",
        ),
        (
            interaction_evidence(),
            adjustment_request(target=InteractionAdjustmentTarget.HEADSPACE_CONCENTRATION),
            "target",
        ),
        (
            interaction_evidence(),
            adjustment_request(
                concentrations=(
                    concentration("cas:a", value=2.0, lower=1.6, upper=2.2),
                    concentration("cas:b", value=2.0, lower=1.7, upper=2.3),
                )
            ),
            "range",
        ),
        (
            interaction_evidence(),
            adjustment_request(
                concentrations=(
                    concentration("cas:a", value=1.0, lower=0.8, upper=1.2, unit="ug_m3"),
                    concentration("cas:b", value=2.0, lower=1.7, upper=2.3),
                )
            ),
            "unit",
        ),
    ],
)
def test_interaction_authorization_withholds_answer_on_every_mismatch(
    evidence: InteractionEvidence,
    adjustment: InteractionAdjustmentRequest,
    reason_fragment: str,
) -> None:
    decision = authorize_interaction_adjustment(evidence, adjustment)
    assert decision.status is InteractionAdjustmentStatus.WITHHELD
    assert decision.numerical_effect is None
    assert any(reason_fragment in reason.casefold() for reason in decision.reasons)


def test_interaction_mapping_rejects_generic_numeric_effect_tampering() -> None:
    generic = interaction_evidence(
        calibration_state=InteractionCalibrationState.UNCALIBRATED_GENERIC,
        model_or_formula="generic pair table",
        effect=None,
    )
    payload = generic.to_mapping()
    payload["numerical_effect"] = numerical_effect().to_mapping()
    payload.pop("content_sha256")
    with pytest.raises(HeadspaceOAVContractError, match="uncalibrated"):
        InteractionEvidence.from_mapping(payload)


def test_sensomics_sequence_is_exact_and_complete() -> None:
    assert C8_SENSOMICS_SEQUENCE == (
        SensomicsStage.REPRESENTATIVE_SAMPLING_EXTRACTION,
        SensomicsStage.ODOR_ACTIVE_SCREENING,
        SensomicsStage.IDENTITY_CONFIRMATION,
        SensomicsStage.QUANTITATIVE_MEASUREMENT,
        SensomicsStage.CONTEXT_MATCHED_OAV_PRIORITIZATION,
        SensomicsStage.FULL_RECOMBINATION,
        SensomicsStage.OMISSION_ADDITION_EXPERIMENTS,
        SensomicsStage.SENSORY_COMPARISON,
    )
    assert len(C8_SENSOMICS_SEQUENCE) == len(set(C8_SENSOMICS_SEQUENCE)) == 8


def test_completed_sensomics_stage_requires_immutable_evidence() -> None:
    with pytest.raises(HeadspaceOAVContractError, match="completed"):
        SensomicsStageRecord(
            stage=SensomicsStage.IDENTITY_CONFIRMATION,
            status=SensomicsStageStatus.COMPLETED,
            evidence=(),
            notes=("identity complete",),
        )


def test_sensomics_program_requires_exact_order_and_contiguous_completion() -> None:
    valid = sensomics_program(5)
    assert_round_trip(valid)
    reordered = list(valid.stages)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    with pytest.raises(HeadspaceOAVContractError, match="order"):
        SensomicsProgram(
            program_id="reordered",
            context=valid.context,
            stages=tuple(reordered),
        )
    skipped = list(sensomics_program(4).stages)
    skipped[5] = SensomicsStageRecord(
        stage=SensomicsStage.FULL_RECOMBINATION,
        status=SensomicsStageStatus.COMPLETED,
        evidence=(source(source_id="late-completion"),),
        notes=("invalid skipped stage",),
    )
    with pytest.raises(HeadspaceOAVContractError, match="contiguous"):
        SensomicsProgram(
            program_id="skipped",
            context=valid.context,
            stages=tuple(skipped),
        )


def test_oav_prioritization_requires_first_five_sensomics_stages() -> None:
    blocked = evaluate_sensomics_claim(
        sensomics_program(4), SensomicsClaim.CANDIDATE_ODORANT_PRIORITIZATION
    )
    permitted = evaluate_sensomics_claim(
        sensomics_program(5), SensomicsClaim.CANDIDATE_ODORANT_PRIORITIZATION
    )
    assert blocked.status is C8ClaimStatus.WITHHELD
    assert permitted.status is C8ClaimStatus.PERMITTED_WITH_EVIDENCE
    assert_round_trip(permitted)


@pytest.mark.parametrize(
    "claim",
    (
        SensomicsClaim.RECOMBINATION_MATCH_IN_TESTED_CONTEXT,
        SensomicsClaim.MATERIAL_EFFECT_IN_TESTED_CONTEXT,
    ),
)
def test_recombination_and_material_effect_require_complete_sensomics_sequence(
    claim: SensomicsClaim,
) -> None:
    blocked = evaluate_sensomics_claim(sensomics_program(7), claim)
    permitted = evaluate_sensomics_claim(sensomics_program(8), claim)
    assert blocked.status is C8ClaimStatus.WITHHELD
    assert permitted.status is C8ClaimStatus.PERMITTED_WITH_EVIDENCE
    limitations = " ".join(permitted.limitations).casefold()
    assert "tested context" in limitations
    if claim is SensomicsClaim.MATERIAL_EFFECT_IN_TESTED_CONTEXT:
        assert "does not mean" in limitations


@pytest.mark.parametrize("claim", PERMITTED_C8_CLAIMS)
def test_permitted_c8_claims_require_evidence(claim: C8Claim) -> None:
    blocked = evaluate_c8_claim(claim, evidence=())
    permitted = evaluate_c8_claim(claim, evidence=(source(),))
    assert blocked.status is C8ClaimStatus.WITHHELD
    assert permitted.status is C8ClaimStatus.PERMITTED_WITH_EVIDENCE
    assert permitted.evidence_sha256 == (source().content_sha256,)
    assert_round_trip(permitted)


@pytest.mark.parametrize("claim", WITHHELD_C8_CLAIMS)
def test_unsupported_c8_claims_are_withheld_even_when_evidence_is_supplied(
    claim: C8Claim,
) -> None:
    decision = evaluate_c8_claim(claim, evidence=(source(),))
    assert decision.status is C8ClaimStatus.WITHHELD
    assert decision.evidence_sha256 == ()
    assert any("outside build c8" in reason.casefold() for reason in decision.reasons)
    assert_round_trip(decision)


def test_claim_mapping_rejects_answer_bearing_withheld_tampering() -> None:
    decision = evaluate_c8_claim(C8Claim.CONSUMER_PREFERENCE, evidence=(source(),))
    payload = decision.to_mapping()
    payload["evidence_sha256"] = [source().content_sha256]
    payload.pop("content_sha256")
    with pytest.raises(HeadspaceOAVContractError, match="withheld"):
        C8ClaimDecision.from_mapping(payload)


def test_c8_module_has_no_legacy_oav_synergy_database_or_production_dependency() -> None:
    module_path = Path(c8.__file__ or "")
    source_text = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(module_path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden_prefixes = (
        "backend",
        "sqlite3",
        "sqlalchemy",
        "engine.perception",
        "engine.thermo",
        "engine.pipeline",
        "engine.optimizer",
        "engine.synergy_graph",
        "engine.interaction_graph",
        "engine.material_interactions",
        "engine.workbench",
        "future_modules",
    )
    assert not sorted(name for name in imported if name.startswith(forbidden_prefixes))
    assert "mixture_shifted_odt" not in source_text
    assert "perceived_intensity_stevens" not in source_text
    assert "perceived_intensity_weber" not in source_text
    assert "synergy_factor" not in source_text

    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not call_names.intersection({"open", "exec", "eval", "__import__"})
