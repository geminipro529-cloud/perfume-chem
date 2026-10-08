from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from engine.physics.calibration_program import (
    C5_INVENTORY_SHA256,
    LEAKAGE_DIMENSIONS,
    REQUIRED_GROUP_DIMENSIONS,
    REQUIRED_METRICS,
    AcceptanceCriterion,
    B5AuthorityReceipt,
    B5MethodBinding,
    CalibrationObservation,
    CalibrationProgram,
    CalibrationProgramContractError,
    Comparator,
    EmpiricalStatus,
    EvaluationDecision,
    EvaluationPlan,
    EvidenceOrigin,
    ExperimentalProtocol,
    HeldOutRelease,
    MatrixAvailability,
    MetricName,
    MetricScale,
    ModelLockReceipt,
    ObservationDescriptor,
    ObservationOutcome,
    ObservationState,
    Partition,
    ReportAuthority,
    SplitAssignment,
    SplitManifest,
    assess_empirical_readiness,
    build_c5_program,
    evaluate_real_held_out,
    evaluate_simulation_smoke,
    import_real_measurements_jsonl,
    lock_model,
    release_held_out,
)

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
T0 = datetime(2026, 8, 3, 0, 0, tzinfo=UTC)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _method_binding() -> B5MethodBinding:
    return B5MethodBinding(
        method_authority_id="b5-method-hs-spme-1",
        method_authority_sha256=_digest("method"),
        method_validation_id="b5-validation-hs-spme-1",
        method_validation_sha256=_digest("validation"),
        validation_scope_sha256=_digest("validation-scope"),
        technique="HS_SPME_GCMS",
        validation_decision="PASS",
    )


def _program() -> CalibrationProgram:
    return build_c5_program()


def _protocol(program: CalibrationProgram | None = None) -> ExperimentalProtocol:
    program = program or _program()
    return ExperimentalProtocol(
        protocol_id="c5-hs-spme-protocol-1",
        program_sha256=program.content_sha256,
        matrix_id="HIGH_ETHANOL_STOCK",
        matrix_batch_id="matrix-batch-protocol-1",
        method_binding=_method_binding(),
        sample_mass_value=1.0,
        sample_mass_unit="g",
        sample_volume_value=1.0,
        sample_volume_unit="mL",
        vial_volume_ml=20.0,
        headspace_volume_ml=19.0,
        temperature_k=298.15,
        equilibration_seconds=1800.0,
        extraction_sampling="HS-SPME static headspace extraction",
        spme_fiber="DVB/CAR/PDMS 50/30 um",
        spme_conditioning="condition per manufacturer and validated B5 method",
        spme_fiber_age_injections=10,
        agitation="500 rpm orbital during incubation and extraction",
        desorption="250 C for 5 min in splitless inlet",
        internal_standard="validated isotopically labeled internal standard",
        calibration_plan="matrix-matched multipoint calibration within validated range",
        blanks="solvent blank and method blank at start and after highest standard",
        carryover_control="blank after highest standard; block if method criterion fails",
        qc_plan="B5 BLANK, DRIFT_CHECK, CALIBRATION_VERIFICATION, INTERNAL_STANDARD",
        replicate_count=3,
        randomization_algorithm="sha256-block-randomization-v1",
        randomization_seed="c5-prespecified-seed-1",
        instrument_drift_control="bracketing calibration verification every ten injections",
        reviewed_at=T0,
    )


def _receipt(index: int, descriptor: ObservationDescriptor) -> B5AuthorityReceipt:
    binding = _method_binding()
    return B5AuthorityReceipt(
        method_authority_id=binding.method_authority_id,
        method_authority_sha256=binding.method_authority_sha256,
        method_validation_id=binding.method_validation_id,
        method_validation_sha256=binding.method_validation_sha256,
        validation_scope_sha256=binding.validation_scope_sha256,
        run_authority_id=f"b5-run-{index}",
        run_authority_sha256=_digest(f"run-{index}"),
        peak_authority_id=f"b5-peak-{index}",
        peak_authority_sha256=_digest(f"peak-{index}"),
        claim_assessment_id=f"b5-claim-{index}",
        claim_assessment_sha256=_digest(f"claim-{index}"),
        claim_decision="SUPPORTED_FOR_SCOPE",
        matrix_calibration_id=binding.validation_scope_sha256,
        analyte_calibration_id=descriptor.material_id,
        method_calibration_id=binding.method_authority_id,
        raw_vendor_sha256=_digest(f"vendor-{index}"),
        open_export_sha256=_digest(f"open-{index}"),
        blocking_qc_clear=True,
        measurement_uncertainty_declared=True,
    )


_MATERIALS = (
    "D-Limonene",
    "Linalool",
    "Citral",
    "Alpha Ionone",
    "Linalyl Acetate",
    "Eugenol",
)


def _descriptor(index: int, protocol: ExperimentalProtocol | None = None) -> ObservationDescriptor:
    protocol = protocol or _protocol()
    return ObservationDescriptor(
        observation_id=f"observation-{index}",
        protocol_sha256=protocol.content_sha256,
        material_id=_MATERIALS[index % len(_MATERIALS)],
        matrix_id=protocol.matrix_id,
        condition_id=f"condition-{index}",
        chemical_identity_group=f"identity-group-{index}",
        close_analog_group=f"analog-group-{index}",
        formula_id=f"formula-{index}",
        supplier_lot=f"supplier-lot-{index}",
        matrix_batch_id=f"matrix-batch-{index}",
        measurement_session_id=f"session-{index}",
        replicate_id=f"replicate-{index}",
    )


def _outcome(
    index: int,
    *,
    origin: EvidenceOrigin = EvidenceOrigin.REAL_INSTRUMENT,
    observed: float = 10.0,
    predicted: float | None = 10.0,
    baseline: float | None = 20.0,
    state: ObservationState = ObservationState.VALUE,
    lower: float | None = 5.0,
    upper: float | None = 15.0,
) -> ObservationOutcome:
    reason = None
    if state is ObservationState.ABSTAINED:
        reason = "outside declared model applicability domain"
        predicted = None
        lower = None
        upper = None
    elif state is ObservationState.MISSING:
        reason = "instrument outcome unavailable"
        observed = math.nan
        predicted = None
        baseline = None
        lower = None
        upper = None
    return ObservationOutcome(
        origin=origin,
        state=state,
        observed_value=None if state is ObservationState.MISSING else observed,
        predicted_value=predicted,
        baseline_prediction=baseline,
        prediction_interval_lower=lower,
        prediction_interval_upper=upper,
        value_unit="ng/L_headspace",
        observed_standard_uncertainty=(
            None if state is ObservationState.MISSING else observed * 0.05
        ),
        disposition_reason=reason,
    )


def _observation(
    index: int,
    *,
    protocol: ExperimentalProtocol | None = None,
    origin: EvidenceOrigin = EvidenceOrigin.REAL_INSTRUMENT,
    observed: float = 10.0,
    predicted: float | None = 10.0,
    baseline: float | None = 20.0,
    state: ObservationState = ObservationState.VALUE,
    lower: float | None = 5.0,
    upper: float | None = 15.0,
) -> CalibrationObservation:
    descriptor = _descriptor(index, protocol)
    outcome = _outcome(
        index,
        origin=origin,
        observed=observed,
        predicted=predicted,
        baseline=baseline,
        state=state,
        lower=lower,
        upper=upper,
    )
    receipt = _receipt(index, descriptor) if origin is EvidenceOrigin.REAL_INSTRUMENT else None
    return CalibrationObservation(descriptor=descriptor, outcome=outcome, b5_receipt=receipt)


def _assignments(protocol: ExperimentalProtocol | None = None) -> tuple[SplitAssignment, ...]:
    observations = tuple(_observation(index, protocol=protocol) for index in range(6))
    partitions = (
        Partition.CALIBRATION,
        Partition.CALIBRATION,
        Partition.VALIDATION,
        Partition.VALIDATION,
        Partition.HELD_OUT_TEST,
        Partition.HELD_OUT_TEST,
    )
    return tuple(
        SplitAssignment(partition=partition, descriptor=observation.descriptor)
        for observation, partition in zip(observations, partitions, strict=True)
    )


def _split(protocol: ExperimentalProtocol | None = None) -> SplitManifest:
    return SplitManifest(
        manifest_id="c5-split-1",
        assignments=_assignments(protocol),
        locked_at=T0 + timedelta(hours=1),
    )


def _criterion(
    metric: MetricName = MetricName.MAE,
    comparator: Comparator = Comparator.LESS_THAN_OR_EQUAL,
    threshold: float = 0.01,
) -> AcceptanceCriterion:
    return AcceptanceCriterion(
        criterion_id=f"criterion-{metric.value}",
        metric=metric,
        comparator=comparator,
        threshold=threshold,
        group_dimension=None,
        group_id=None,
    )


def _plan(
    *,
    scale: MetricScale = MetricScale.LOG10,
    criteria: tuple[AcceptanceCriterion, ...] | None = None,
) -> EvaluationPlan:
    return EvaluationPlan(
        plan_id="c5-evaluation-plan-1",
        scale=scale,
        metric_names=REQUIRED_METRICS,
        group_dimensions=REQUIRED_GROUP_DIMENSIONS,
        catastrophic_fold_threshold=10.0,
        criteria=criteria or (_criterion(),),
        locked_at=T0 + timedelta(hours=2),
    )


def _model_lock(
    observations: tuple[CalibrationObservation, ...],
    *,
    split: SplitManifest | None = None,
    plan: EvaluationPlan | None = None,
) -> ModelLockReceipt:
    split = split or _split()
    plan = plan or _plan()
    validation_ids = {
        item.descriptor.observation_id
        for item in split.assignments
        if item.partition is Partition.VALIDATION
    }
    validation = tuple(
        item for item in observations if item.descriptor.observation_id in validation_ids
    )
    return lock_model(
        model_id="c4-ideal-raoult-plus-c5-correction-1",
        model_sha256=_digest("model-1"),
        split_manifest=split,
        evaluation_plan=plan,
        validation_observations=validation,
        locked_at=T0 + timedelta(hours=3),
    )


def _released_real_set(
    *,
    observed_values: tuple[float, float] = (10.0, 100.0),
    predicted_values: tuple[float, float] = (10.0, 100.0),
    baseline_values: tuple[float, float] = (20.0, 200.0),
    plan: EvaluationPlan | None = None,
) -> tuple[
    CalibrationProgram,
    EvaluationPlan,
    ModelLockReceipt,
    HeldOutRelease,
]:
    program = _program()
    protocol = _protocol(program)
    split = _split(protocol)
    all_observations = tuple(_observation(index, protocol=protocol) for index in range(4)) + tuple(
        _observation(
            index + 4,
            protocol=protocol,
            observed=observed_values[index],
            predicted=predicted_values[index],
            baseline=baseline_values[index],
            lower=predicted_values[index] * 0.5,
            upper=predicted_values[index] * 1.5,
        )
        for index in range(2)
    )
    plan = plan or _plan()
    model_lock = _model_lock(all_observations, split=split, plan=plan)
    held_out_ids = {
        item.descriptor.observation_id
        for item in split.assignments
        if item.partition is Partition.HELD_OUT_TEST
    }
    held_out = tuple(
        item for item in all_observations if item.descriptor.observation_id in held_out_ids
    )
    release = release_held_out(
        release_id="c5-held-out-release-1",
        observations=held_out,
        split_manifest=split,
        model_lock=model_lock,
        released_at=T0 + timedelta(hours=4),
    )
    return program, plan, model_lock, release


def test_material_panel_preserves_frozen_parent_and_required_domains() -> None:
    program = _program()
    assessment = json.loads(
        (ROOT / "docs/verification/c5/inventory_v5_rebase_assessment.json").read_text(
            encoding="utf-8",
        )
    )
    parent = assessment["parent_program"]
    assert program.inventory_sha256 == C5_INVENTORY_SHA256
    assert parent["inventory_sha256"] == C5_INVENTORY_SHA256
    assert program.content_sha256 == parent["content_sha256"]
    assert parent["preserved_unchanged"] is True
    assert assessment["decision"] == "HOLD_REDESIGN_REQUIRED"
    assert {entry.inventory_name for entry in program.materials} == {
        row["parent_inventory_name"] for row in assessment["material_diffs"]
    }
    assert {
        "HYDROCARBON_TERPENE",
        "ALCOHOL",
        "ALDEHYDE",
        "KETONE_IONONE",
        "ESTER",
        "LACTONE",
        "PHENOL",
        "ACID",
        "MUSK",
        "WOODY_AMBER",
    } <= {entry.chemical_class for entry in program.materials}
    tags = {tag for entry in program.materials for tag in entry.coverage_tags}
    assert {
        "HIGH_VAPOR_PRESSURE",
        "LOW_VAPOR_PRESSURE",
        "HIGH_POLARITY",
        "LOW_POLARITY",
        "H_BOND_DONOR",
        "H_BOND_ACCEPTOR",
        "TRACE_POTENT",
        "BULK_STRUCTURAL",
    } <= tags
    assert program.empirical_status is EmpiricalStatus.BLOCKED_PENDING_DATA
    assert program.actual_instrument_record_count == 0


def test_matrix_panel_covers_required_matrices_and_source_holds() -> None:
    program = _program()
    matrix_ids = {entry.matrix_id for entry in program.matrices}
    assert matrix_ids == {
        "CURRENT_DECLARED_STOCK",
        "FINISHED_10_PERCENT",
        "FINISHED_20_PERCENT",
        "HIGH_ETHANOL_STOCK",
        "DPG_HEAVY",
        "TEC_HEAVY",
        "DEP_HEAVY",
        "IPM_OIL",
    }
    for matrix in program.matrices:
        assert math.fsum(component.fraction for component in matrix.components) == pytest.approx(1.0)
    dep = next(item for item in program.matrices if item.matrix_id == "DEP_HEAVY")
    assert dep.availability is MatrixAvailability.REQUIRES_DECLARED_SOURCE
    assert "DEP" in dep.missing_sources
    finished = next(item for item in program.matrices if item.matrix_id == "FINISHED_10_PERCENT")
    assert finished.availability is MatrixAvailability.REQUIRES_DECLARED_SOURCE
    assert "WATER" in finished.missing_sources


def test_program_mapping_round_trip_is_canonical_and_tamper_evident() -> None:
    program = _program()
    assert CalibrationProgram.from_mapping(program.to_mapping()) == program
    reversed_program = replace(
        program,
        materials=tuple(reversed(program.materials)),
        matrices=tuple(reversed(program.matrices)),
    )
    assert reversed_program.content_sha256 == program.content_sha256
    tampered = program.to_mapping()
    tampered["inventory_sha256"] = _digest("tampered-inventory")
    with pytest.raises(CalibrationProgramContractError, match="content_sha256"):
        CalibrationProgram.from_mapping(tampered)


@pytest.mark.parametrize(
    ("field_name", "bad_value", "message"),
    (
        ("sample_mass_value", 0.0, "sample_mass_value"),
        ("sample_volume_unit", "", "sample_volume_unit"),
        ("vial_volume_ml", 1.0, "headspace"),
        ("headspace_volume_ml", 20.0, "headspace"),
        ("temperature_k", math.nan, "temperature_k"),
        ("equilibration_seconds", -1.0, "equilibration_seconds"),
        ("spme_fiber", "", "spme_fiber"),
        ("spme_fiber_age_injections", -1, "spme_fiber_age_injections"),
        ("replicate_count", 1, "replicate_count"),
        ("randomization_seed", "", "randomization_seed"),
        ("instrument_drift_control", "", "instrument_drift_control"),
    ),
)
def test_protocol_rejects_incomplete_or_nonphysical_fields(
    field_name: str,
    bad_value: object,
    message: str,
) -> None:
    with pytest.raises(CalibrationProgramContractError, match=message):
        replace(_protocol(), **{field_name: bad_value})


def test_protocol_requires_passed_hs_spme_b5_binding() -> None:
    with pytest.raises(CalibrationProgramContractError, match="validation_decision"):
        replace(_method_binding(), validation_decision="INCOMPLETE")
    with pytest.raises(CalibrationProgramContractError, match="technique"):
        replace(_method_binding(), technique="GCMS")


def test_protocol_hash_is_deterministic_and_mapping_round_trips() -> None:
    protocol = _protocol()
    assert ExperimentalProtocol.from_mapping(protocol.to_mapping()) == protocol
    assert replace(protocol).content_sha256 == protocol.content_sha256
    tampered = protocol.to_mapping()
    tampered["temperature_k"] = 310.0
    with pytest.raises(CalibrationProgramContractError, match="content_sha256"):
        ExperimentalProtocol.from_mapping(tampered)


def test_real_jsonl_import_accepts_exact_b5_bound_record() -> None:
    program = _program()
    protocol = _protocol(program)
    observation = _observation(0, protocol=protocol)
    payload = json.dumps(observation.to_mapping(), sort_keys=True)
    imported = import_real_measurements_jsonl(
        payload,
        program=program,
        protocols=(protocol,),
    )
    assert imported == (observation,)


def test_real_import_rejects_simulation_unknown_fields_and_scope_mismatch() -> None:
    program = _program()
    protocol = _protocol(program)
    simulation = _observation(
        0,
        protocol=protocol,
        origin=EvidenceOrigin.SIMULATED_SMOKE,
    )
    with pytest.raises(CalibrationProgramContractError, match="REAL_INSTRUMENT"):
        import_real_measurements_jsonl(
            json.dumps(simulation.to_mapping()),
            program=program,
            protocols=(protocol,),
        )
    real = _observation(0, protocol=protocol)
    unknown = real.to_mapping()
    unknown["pseudo_calibration"] = True
    with pytest.raises(CalibrationProgramContractError, match="unknown fields"):
        import_real_measurements_jsonl(
            json.dumps(unknown),
            program=program,
            protocols=(protocol,),
        )
    assert real.b5_receipt is not None
    mismatched = replace(
        real,
        b5_receipt=replace(
            real.b5_receipt,
            analyte_calibration_id="wrong-material",
        ),
    )
    with pytest.raises(CalibrationProgramContractError, match="analyte calibration"):
        import_real_measurements_jsonl(
            json.dumps(mismatched.to_mapping()),
            program=program,
            protocols=(protocol,),
        )


def test_real_import_rejects_duplicate_ids_and_malformed_jsonl() -> None:
    program = _program()
    protocol = _protocol(program)
    row = json.dumps(_observation(0, protocol=protocol).to_mapping())
    with pytest.raises(CalibrationProgramContractError, match="duplicate observation_id"):
        import_real_measurements_jsonl(
            f"{row}\n{row}\n",
            program=program,
            protocols=(protocol,),
        )
    with pytest.raises(CalibrationProgramContractError, match="line 1"):
        import_real_measurements_jsonl(
            "{not-json}\n",
            program=program,
            protocols=(protocol,),
        )


def test_observation_outcome_states_are_fail_closed() -> None:
    with pytest.raises(CalibrationProgramContractError, match="predicted_value"):
        replace(_outcome(0), predicted_value=None)
    with pytest.raises(CalibrationProgramContractError, match="disposition_reason"):
        replace(
            _outcome(0, state=ObservationState.ABSTAINED),
            disposition_reason=None,
        )
    with pytest.raises(CalibrationProgramContractError, match="must be absent"):
        replace(
            _outcome(0, state=ObservationState.MISSING),
            observed_value=1.0,
        )


def test_split_manifest_is_deterministic_and_requires_three_partitions() -> None:
    assignments = _assignments()
    manifest = _split()
    reversed_manifest = replace(manifest, assignments=tuple(reversed(assignments)))
    assert reversed_manifest.content_sha256 == manifest.content_sha256
    assert SplitManifest.from_mapping(manifest.to_mapping()) == manifest
    missing_held_out = tuple(
        assignment
        for assignment in assignments
        if assignment.partition is not Partition.HELD_OUT_TEST
    )
    with pytest.raises(CalibrationProgramContractError, match="HELD_OUT_TEST"):
        SplitManifest(
            manifest_id="missing-held-out",
            assignments=missing_held_out,
            locked_at=T0,
        )


@pytest.mark.parametrize("dimension", LEAKAGE_DIMENSIONS)
def test_split_rejects_each_cross_partition_leakage_dimension(dimension: str) -> None:
    assignments = list(_assignments())
    source = assignments[0]
    target = assignments[2]
    leaking_descriptor = replace(
        target.descriptor,
        **{dimension: getattr(source.descriptor, dimension)},
    )
    assignments[2] = replace(target, descriptor=leaking_descriptor)
    with pytest.raises(CalibrationProgramContractError, match=dimension):
        SplitManifest(
            manifest_id=f"leak-{dimension}",
            assignments=tuple(assignments),
            locked_at=T0,
        )


def test_evaluation_plan_requires_all_metrics_and_group_dimensions() -> None:
    missing_metric = tuple(item for item in REQUIRED_METRICS if item is not MetricName.RMSE)
    with pytest.raises(CalibrationProgramContractError, match="RMSE"):
        replace(_plan(), metric_names=missing_metric)
    with pytest.raises(CalibrationProgramContractError, match="condition"):
        replace(
            _plan(),
            group_dimensions=("material_class", "matrix"),
        )
    assert "R_SQUARED" not in MetricName.__members__


def test_model_lock_binds_validation_only_and_all_authority_hashes() -> None:
    observations = tuple(_observation(index) for index in range(6))
    split = _split()
    plan = _plan()
    receipt = _model_lock(observations, split=split, plan=plan)
    assert receipt.split_manifest_sha256 == split.content_sha256
    assert receipt.evaluation_plan_sha256 == plan.content_sha256
    assert ModelLockReceipt.from_mapping(receipt.to_mapping()) == receipt
    held_out = tuple(observations[4:])
    with pytest.raises(CalibrationProgramContractError, match="validation partition"):
        lock_model(
            model_id="bad-lock",
            model_sha256=_digest("bad-model"),
            split_manifest=split,
            evaluation_plan=plan,
            validation_observations=held_out,
            locked_at=T0 + timedelta(hours=3),
        )


def test_held_out_release_requires_matching_pre_release_model_lock() -> None:
    observations = tuple(_observation(index) for index in range(6))
    split = _split()
    plan = _plan()
    model_lock = _model_lock(observations, split=split, plan=plan)
    held_out = observations[4:]
    with pytest.raises(CalibrationProgramContractError, match="after model lock"):
        release_held_out(
            release_id="early-release",
            observations=held_out,
            split_manifest=split,
            model_lock=model_lock,
            released_at=model_lock.locked_at,
        )
    with pytest.raises(CalibrationProgramContractError, match="split manifest"):
        release_held_out(
            release_id="wrong-split",
            observations=held_out,
            split_manifest=replace(split, manifest_id="different-split"),
            model_lock=model_lock,
            released_at=T0 + timedelta(hours=4),
        )


def test_simulation_smoke_metrics_are_exact_but_never_empirical() -> None:
    program = _program()
    protocol = _protocol(program)
    observations = tuple(
        _observation(
            index,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            observed=value,
            predicted=value,
            baseline=value * 2.0,
            lower=value * 0.5,
            upper=value * 1.5,
        )
        for index, value in enumerate((1.0, 10.0, 100.0))
    )
    report = evaluate_simulation_smoke(observations, program=program, plan=_plan())
    assert report.authority is ReportAuthority.SIMULATION_ONLY
    assert report.decision is EvaluationDecision.NOT_ELIGIBLE
    assert report.promotion_allowed is False
    assert report.overall.bias == pytest.approx(0.0)
    assert report.overall.mae == pytest.approx(0.0)
    assert report.overall.rmse == pytest.approx(0.0)
    assert report.overall.median_absolute_fold_error == pytest.approx(1.0)
    assert report.overall.rank_agreement == pytest.approx(1.0)
    assert report.overall.calibration_slope == pytest.approx(1.0)
    assert report.overall.calibration_intercept == pytest.approx(0.0)
    assert report.overall.prediction_interval_coverage == pytest.approx(1.0)
    assert report.overall.baseline_rmse == pytest.approx(math.log10(2.0))
    assert report.overall.rmse_improvement_vs_baseline is not None
    assert report.overall.rmse_improvement_vs_baseline > 0.0
    assert {group.dimension for group in report.groups} == set(REQUIRED_GROUP_DIMENSIONS)


def test_metrics_record_catastrophic_outliers_abstentions_and_missing_domain() -> None:
    program = _program()
    protocol = _protocol(program)
    observations = (
        _observation(
            0,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            observed=1.0,
            predicted=100.0,
            baseline=2.0,
            lower=50.0,
            upper=150.0,
        ),
        _observation(
            1,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            observed=10.0,
            state=ObservationState.ABSTAINED,
        ),
        _observation(
            2,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            state=ObservationState.MISSING,
        ),
    )
    report = evaluate_simulation_smoke(observations, program=program, plan=_plan())
    assert report.overall.total_count == 3
    assert report.overall.scored_count == 1
    assert report.overall.catastrophic_outlier_count == 1
    assert report.overall.catastrophic_outlier_rate == pytest.approx(1.0)
    assert report.overall.abstention_count == 1
    assert report.overall.abstention_rate == pytest.approx(1.0 / 3.0)
    assert report.overall.missing_domain_count == 1
    assert report.overall.missing_domain_rate == pytest.approx(1.0 / 3.0)
    assert report.overall.prediction_interval_coverage == pytest.approx(0.0)


def test_linear_scale_metrics_use_declared_scale() -> None:
    program = _program()
    protocol = _protocol(program)
    observations = (
        _observation(
            0,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            observed=1.0,
            predicted=2.0,
            baseline=3.0,
            lower=1.5,
            upper=2.5,
        ),
        _observation(
            1,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
            observed=3.0,
            predicted=2.0,
            baseline=5.0,
            lower=1.5,
            upper=3.5,
        ),
    )
    report = evaluate_simulation_smoke(
        observations,
        program=program,
        plan=_plan(scale=MetricScale.LINEAR),
    )
    assert report.overall.bias == pytest.approx(0.0)
    assert report.overall.mae == pytest.approx(1.0)
    assert report.overall.rmse == pytest.approx(1.0)


def test_real_held_out_evaluation_applies_prespecified_pass_and_fail_criteria() -> None:
    passing_plan = _plan(criteria=(_criterion(threshold=0.01),))
    program, plan, model_lock, release = _released_real_set(plan=passing_plan)
    passing = evaluate_real_held_out(
        release,
        program=program,
        plan=plan,
        model_lock=model_lock,
    )
    assert passing.authority is ReportAuthority.REAL_INSTRUMENT_ONLY
    assert passing.decision is EvaluationDecision.PASS
    assert passing.promotion_allowed is True

    failing_plan = _plan(
        criteria=(
            _criterion(
                metric=MetricName.RANK_AGREEMENT,
                comparator=Comparator.GREATER_THAN_OR_EQUAL,
                threshold=1.1,
            ),
        )
    )
    program, plan, model_lock, release = _released_real_set(plan=failing_plan)
    failing = evaluate_real_held_out(
        release,
        program=program,
        plan=plan,
        model_lock=model_lock,
    )
    assert failing.decision is EvaluationDecision.FAIL
    assert failing.promotion_allowed is False
    assert failing.failed_criteria == ("criterion-rank_agreement",)


def test_real_evaluation_rejects_simulated_held_out_outcomes() -> None:
    program = _program()
    protocol = _protocol(program)
    split = _split(protocol)
    observations = tuple(_observation(index, protocol=protocol) for index in range(6))
    plan = _plan()
    model_lock = _model_lock(observations, split=split, plan=plan)
    simulated = tuple(
        _observation(
            index,
            protocol=protocol,
            origin=EvidenceOrigin.SIMULATED_SMOKE,
        )
        for index in (4, 5)
    )
    with pytest.raises(CalibrationProgramContractError, match="REAL_INSTRUMENT"):
        release_held_out(
            release_id="simulation-release",
            observations=simulated,
            split_manifest=split,
            model_lock=model_lock,
            released_at=T0 + timedelta(hours=4),
        )


def test_empirical_assessment_is_blocked_without_actual_data_and_has_no_metrics() -> None:
    assessment = assess_empirical_readiness(program=_program())
    assert assessment.status is EmpiricalStatus.BLOCKED_PENDING_DATA
    assert assessment.metrics is None
    assert assessment.promotion_allowed is False
    assert {
        "NO_B5_BOUND_PROTOCOL",
        "NO_REAL_INSTRUMENT_OBSERVATIONS",
        "NO_LOCKED_LEAK_RESISTANT_SPLIT",
        "NO_PRE_HELD_OUT_MODEL_LOCK",
    } <= set(assessment.reasons)
    assert not (ROOT / "data" / "calibration" / "wear_tests.jsonl").exists()


def test_c5_module_does_not_import_legacy_calibration_or_analytical_ledgers() -> None:
    source = (ROOT / "engine" / "physics" / "calibration_program.py").read_text(
        encoding="utf-8"
    )
    assert "engine.calibration import" not in source
    assert "engine.calibration.store" not in source
    assert "engine.analytical.ledger" not in source


def test_c5_contract_is_exported_and_in_canonical_verifier() -> None:
    from engine.physics import build_c5_program as exported_builder

    assert exported_builder().content_sha256 == _program().content_sha256
    verifier = (ROOT / "engine" / "project_verification.py").read_text(encoding="utf-8")
    assert '"tests/test_c5_calibration_program.py"' in verifier
    assert '"engine/physics/calibration_program.py"' in verifier
