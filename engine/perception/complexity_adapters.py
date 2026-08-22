"""Closed JSON adapters for the admitted native complexity families."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from engine.calibration.hashing import stable_json_hash
from engine.perception.complexity_ensemble import Adapter
from engine.perception.complexity_expansion import (
    ExpansionDirection,
    ExpansionDiscoveryRound,
    assess_bounded_saturation,
    audit_expansion_registry,
    pareto_experiment_frontier,
)
from engine.perception.construction_complexity import (
    ConstructionComplexityInputs,
    NegativeSpaceProbe,
    analyze_construction_complexity,
)
from engine.perception.musk_design import (
    ClaimStatus,
    InventoryState,
    MuskCandidate,
    MuskDesignRequest,
    MuskExceptionCall,
    MuskFingerprint,
    MuskRole,
    MuskTargetBrief,
    PairwiseNonredundancy,
    evaluate_musk_design,
)
from engine.physics.model_lifecycle import (
    ModelDriftObservation,
    ModelLifecycleCard,
    ModelLifecycleState,
    assess_model_drift,
)
from engine.scientific_validation.complexity_design_contracts import (
    CausalArmRole,
    CausalInvariant,
    CausalIsolateArm,
    CausalIsolateDesign,
    FormulaSignature,
    FormulaSignatureComponent,
    NaryEvidenceState,
    NaryInteractionCandidate,
    NaryParticipant,
    compare_formula_signatures,
    evaluate_causal_isolate,
    evaluate_nary_interaction,
)
from engine.scientific_validation.complexity_model_admission import (
    ComplexityClaimScope,
    ComplexityGateEvidence,
    ComplexityGateState,
    ComplexityModelAdmissionPacket,
    OAVGateBinding,
    evaluate_complexity_model_admission,
)
from engine.sensory.order_balance import PresentationSchedule, assess_order_balance
from engine.sensory.panel_contract import (
    GateKind,
    GateOutcome,
    PanelPerformanceResult,
    StudyPartition,
    build_c0_construction_lexicon,
    build_c0_protocol_draft,
    evaluate_c0_exit,
)
from engine.sensory.temporal_observations import (
    TemporalObservation,
    TemporalObservationSeries,
    summarize_temporal_observations,
)
from engine.sensory.within_sniff import (
    DeliveryApparatusKind,
    WithinSniffClaimCeiling,
    WithinSniffPulse,
    WithinSniffSequence,
    evaluate_within_sniff_sequence,
)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field_name} must be a string-keyed mapping")
    return value


def _closed(
    value: Any,
    allowed: set[str],
    field_name: str,
    *,
    required: set[str] | None = None,
) -> Mapping[str, Any]:
    mapping = _mapping(value, field_name)
    unknown = set(mapping).difference(allowed)
    if unknown:
        raise ValueError(f"{field_name} has unknown keys: {sorted(unknown)}")
    required_keys = allowed if required is None else required
    missing = required_keys.difference(mapping)
    if missing:
        raise ValueError(f"{field_name} is missing keys: {sorted(missing)}")
    return mapping


def _tuple_strings(value: Any, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a sequence")
    return tuple(str(item) for item in value)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _seal(
    payload: Mapping[str, Any],
    *,
    claim_ceiling: str = "COMPUTATIONAL_DESIGN_ONLY",
) -> dict[str, Any]:
    result = dict(payload)
    result.pop("result_sha256", None)
    result.setdefault("claim_ceiling", claim_ceiling)
    result["source_admission_authority"] = False
    result["formula_authority"] = False
    result["inventory_authority"] = False
    result["physical_execution_authorized"] = False
    result["sensory_authority"] = False
    result["safety_authority"] = False
    result["release_authority"] = False
    result["result_sha256"] = stable_json_hash(result)
    return result


@dataclass(frozen=True, slots=True)
class _MaterialView:
    name: str
    oav: float | None
    intensity: float | None
    is_known: bool = True
    is_opaque_preblend: bool = False
    functional_groups: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _StateView:
    materials: tuple[_MaterialView, ...]


@dataclass(frozen=True, slots=True)
class _FrameView:
    label: str
    t_seconds: float
    state: _StateView


def _material_view(value: Any) -> _MaterialView:
    row = _closed(
        value,
        {
            "name",
            "oav",
            "intensity",
            "is_known",
            "is_opaque_preblend",
            "functional_groups",
        },
        "construction material",
        required={"name", "oav", "intensity"},
    )
    return _MaterialView(
        name=str(row["name"]),
        oav=None if row["oav"] is None else float(row["oav"]),
        intensity=None if row["intensity"] is None else float(row["intensity"]),
        is_known=bool(row.get("is_known", True)),
        is_opaque_preblend=bool(row.get("is_opaque_preblend", False)),
        functional_groups=_tuple_strings(row.get("functional_groups", []), "functional_groups"),
    )


def _construction_inputs(value: Any) -> ConstructionComplexityInputs:
    row = _closed(
        value,
        {
            "foreground_materials",
            "background_materials",
            "heavy_materials",
            "descriptor_vectors",
            "descriptor_vectors_standardized",
            "gradient_material_order",
            "negative_space_probes",
            "hedonic_values",
            "hedonic_material_order",
        },
        "construction inputs",
        required=set(),
    )
    probes = tuple(
        NegativeSpaceProbe(
            label=str(item["label"]),
            axis=str(item["axis"]),
            minimum=float(item["minimum"]),
            maximum=float(item["maximum"]),
        )
        for raw in row.get("negative_space_probes", [])
        for item in [
            _closed(
                raw,
                {"label", "axis", "minimum", "maximum"},
                "negative-space probe",
            )
        ]
    )
    return ConstructionComplexityInputs(
        foreground_materials=_tuple_strings(
            row.get("foreground_materials", []), "foreground_materials"
        ),
        background_materials=_tuple_strings(
            row.get("background_materials", []), "background_materials"
        ),
        heavy_materials=_tuple_strings(row.get("heavy_materials", []), "heavy_materials"),
        descriptor_vectors={
            str(material): {str(axis): float(value) for axis, value in axes.items()}
            for material, axes in _mapping(
                row.get("descriptor_vectors", {}), "descriptor_vectors"
            ).items()
        },
        descriptor_vectors_standardized=bool(
            row.get("descriptor_vectors_standardized", False)
        ),
        gradient_material_order=_tuple_strings(
            row.get("gradient_material_order", []), "gradient_material_order"
        ),
        negative_space_probes=probes,
        hedonic_values={
            str(material): float(number)
            for material, number in _mapping(
                row.get("hedonic_values", {}), "hedonic_values"
            ).items()
        },
        hedonic_material_order=_tuple_strings(
            row.get("hedonic_material_order", []), "hedonic_material_order"
        ),
    )


def adapt_construction_profile(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    row = _closed(
        payload,
        {"materials", "frames", "inputs"},
        "construction payload",
    )
    materials = tuple(_material_view(item) for item in row["materials"])
    frames: list[_FrameView] = []
    for raw_frame in row["frames"]:
        frame = _closed(
            raw_frame,
            {"label", "t_seconds", "materials"},
            "construction frame",
        )
        frames.append(
            _FrameView(
                label=str(frame["label"]),
                t_seconds=float(frame["t_seconds"]),
                state=_StateView(
                    tuple(_material_view(item) for item in frame["materials"])
                ),
            )
        )
    result = analyze_construction_complexity(
        _StateView(materials),
        tuple(frames),
        inputs=_construction_inputs(row["inputs"]),
    )
    return _seal(result.as_dict())


def adapt_expansion_frontier(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    row = _closed(
        payload,
        {
            "registry",
            "source_package_sha256",
            "frontier_values",
            "discovery_rounds",
            "declared_scope",
        },
        "expansion payload",
    )
    registry = _mapping(row["registry"], "registry")
    audit = audit_expansion_registry(
        registry,
        source_package_sha256=str(row["source_package_sha256"]),
    )
    invalid = set(audit.invalid_records)
    directions: dict[str, ExpansionDirection] = {}
    for raw in registry.get("directions", []):
        direction_id = str(_mapping(raw, "direction").get("direction_id", ""))
        if direction_id in invalid:
            continue
        try:
            direction = ExpansionDirection.from_mapping(raw)
        except (TypeError, ValueError):
            continue
        directions[direction.direction_id] = direction
    frontier_rows = []
    for raw in row["frontier_values"]:
        item = _closed(
            raw,
            {"direction_id", "impact", "information_gain"},
            "frontier value",
        )
        direction_id = str(item["direction_id"])
        if direction_id not in directions:
            raise ValueError(f"frontier direction is not valid: {direction_id}")
        frontier_rows.append(
            (
                directions[direction_id],
                float(item["impact"]),
                float(item["information_gain"]),
            )
        )
    frontier = pareto_experiment_frontier(tuple(frontier_rows))
    rounds = tuple(
        ExpansionDiscoveryRound(
            round_id=str(item["round_id"]),
            new_p0_p1_count=int(item["new_p0_p1_count"]),
            source_classes=_tuple_strings(item["source_classes"], "source_classes"),
            evidence_sha256=str(item["evidence_sha256"]),
        )
        for raw in row["discovery_rounds"]
        for item in [
            _closed(
                raw,
                {"round_id", "new_p0_p1_count", "source_classes", "evidence_sha256"},
                "discovery round",
            )
        ]
    )
    saturation = (
        assess_bounded_saturation(rounds, declared_scope=str(row["declared_scope"]))
        if rounds
        else None
    )
    return _seal(
        {
            "schema_version": "complexity_expansion_adapter_v1",
            "registry_audit": audit.as_dict(),
            "pareto_frontier": [item.as_dict() for item in frontier],
            "saturation": saturation.as_dict() if saturation is not None else None,
        }
    )


_OAV_FIELDS = {
    "formula_sha256",
    "dose_receipt_sha256",
    "oav_result_sha256",
    "quantitative_ppm_status",
    "odt_authority_status",
    "odt_coverage_status",
    "natural_composite_coverage_status",
    "headspace_scope_status",
    "receipt_binding_status",
    "strict_oav_status",
    "pre_mix_gate_status",
    "planned_active_equivalence_status",
    "formula_is_revision",
    "parent_formula_sha256",
    "oav_per_time_role",
}


def _oav_binding(value: Any) -> OAVGateBinding:
    row = _closed(
        value,
        _OAV_FIELDS,
        "OAV binding",
        required=_OAV_FIELDS.difference({"parent_formula_sha256", "oav_per_time_role"}),
    )
    return OAVGateBinding(**dict(row))


def _causal_arm(value: Any) -> CausalIsolateArm:
    row = _closed(
        value,
        {
            "arm_id",
            "role",
            "axis_level",
            "formula_sha256",
            "dose_receipt_sha256",
            "supplied_stock_total_ul",
            "active_equivalent_total_ul",
            "carrier_total_ul",
            "invariants",
        },
        "causal arm",
    )
    invariants = tuple(
        CausalInvariant(
            invariant_id=str(item["invariant_id"]),
            value_sha256=str(item["value_sha256"]),
        )
        for raw in row["invariants"]
        for item in [
            _closed(raw, {"invariant_id", "value_sha256"}, "causal invariant")
        ]
    )
    return CausalIsolateArm(
        arm_id=str(row["arm_id"]),
        role=CausalArmRole(str(row["role"])),
        axis_level=_decimal(row["axis_level"]),
        formula_sha256=str(row["formula_sha256"]),
        dose_receipt_sha256=str(row["dose_receipt_sha256"]),
        supplied_stock_total_ul=_decimal(row["supplied_stock_total_ul"]),
        active_equivalent_total_ul=_decimal(row["active_equivalent_total_ul"]),
        carrier_total_ul=_decimal(row["carrier_total_ul"]),
        invariants=invariants,
    )


def _signature(value: Any) -> FormulaSignature:
    row = _closed(
        value,
        {"formula_sha256", "dose_receipt_sha256", "quantity_basis", "components"},
        "formula signature",
    )
    components = tuple(
        FormulaSignatureComponent(
            component_id=str(item["component_id"]),
            supplied_stock_amount=_decimal(item["supplied_stock_amount"]),
            active_equivalent_amount=(
                None
                if item["active_equivalent_amount"] is None
                else _decimal(item["active_equivalent_amount"])
            ),
            sensory_system_ids=_tuple_strings(
                item.get("sensory_system_ids", []), "sensory_system_ids"
            ),
            recognizer_ids=_tuple_strings(item.get("recognizer_ids", []), "recognizer_ids"),
            phase_ids=_tuple_strings(item.get("phase_ids", []), "phase_ids"),
        )
        for raw in row["components"]
        for item in [
            _closed(
                raw,
                {
                    "component_id",
                    "supplied_stock_amount",
                    "active_equivalent_amount",
                    "sensory_system_ids",
                    "recognizer_ids",
                    "phase_ids",
                },
                "signature component",
                required={
                    "component_id",
                    "supplied_stock_amount",
                    "active_equivalent_amount",
                },
            )
        ]
    )
    return FormulaSignature(
        formula_sha256=str(row["formula_sha256"]),
        dose_receipt_sha256=str(row["dose_receipt_sha256"]),
        quantity_basis=str(row["quantity_basis"]),
        components=components,
    )


def _nary_candidate(value: Any) -> NaryInteractionCandidate:
    allowed = {
        "interaction_id",
        "evidence_state",
        "participants",
        "formula_sha256",
        "formula_signature_sha256",
        "matrix_sha256",
        "pairwise_evidence_refs",
        "causal_isolate_sha256",
        "experiment_design_sha256",
        "experiment_execution_sha256",
        "observation_receipt_sha256s",
        "oav_binding",
    }
    required = {
        "interaction_id",
        "evidence_state",
        "participants",
        "formula_sha256",
        "formula_signature_sha256",
        "matrix_sha256",
    }
    row = _closed(value, allowed, "nary candidate", required=required)
    participants = tuple(
        NaryParticipant(
            material_id=str(item["material_id"]),
            role=str(item["role"]),
            ratio=_decimal(item["ratio"]),
        )
        for raw in row["participants"]
        for item in [
            _closed(raw, {"material_id", "role", "ratio"}, "nary participant")
        ]
    )
    return NaryInteractionCandidate(
        interaction_id=str(row["interaction_id"]),
        evidence_state=NaryEvidenceState(str(row["evidence_state"])),
        participants=participants,
        formula_sha256=str(row["formula_sha256"]),
        formula_signature_sha256=str(row["formula_signature_sha256"]),
        matrix_sha256=str(row["matrix_sha256"]),
        pairwise_evidence_refs=_tuple_strings(
            row.get("pairwise_evidence_refs", []), "pairwise_evidence_refs"
        ),
        causal_isolate_sha256=row.get("causal_isolate_sha256"),
        experiment_design_sha256=row.get("experiment_design_sha256"),
        experiment_execution_sha256=row.get("experiment_execution_sha256"),
        observation_receipt_sha256s=_tuple_strings(
            row.get("observation_receipt_sha256s", []),
            "observation_receipt_sha256s",
        ),
        oav_binding=(
            None if row.get("oav_binding") is None else _oav_binding(row["oav_binding"])
        ),
    )


def adapt_experimental_design(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = str(payload.get("operation", ""))
    if operation == "causal_isolate":
        row = _closed(
            payload,
            {"operation", "model_id", "manipulated_axis_id", "arms", "required_invariant_ids"},
            "experimental payload",
        )
        result = evaluate_causal_isolate(
            CausalIsolateDesign(
                model_id=str(row["model_id"]),
                manipulated_axis_id=str(row["manipulated_axis_id"]),
                arms=tuple(_causal_arm(item) for item in row["arms"]),
                required_invariant_ids=_tuple_strings(
                    row["required_invariant_ids"], "required_invariant_ids"
                ),
            )
        )
    elif operation == "formula_signature":
        row = _closed(
            payload,
            {"operation", "left", "right"},
            "experimental payload",
        )
        result = compare_formula_signatures(_signature(row["left"]), _signature(row["right"]))
    elif operation == "nary_interaction":
        row = _closed(
            payload,
            {"operation", "candidate"},
            "experimental payload",
        )
        result = evaluate_nary_interaction(_nary_candidate(row["candidate"]))
    else:
        raise ValueError(f"unsupported operation: {operation or '<missing>'}")
    return _seal(result.as_dict())


def _model_admission_packet(value: Mapping[str, Any]) -> ComplexityModelAdmissionPacket:
    allowed = {
        "operation",
        "model_id",
        "version",
        "claim_scope",
        "parent_model_ids",
        "source_hashes",
        "supersession_state",
        "gate_evidence",
        "formula_sha256",
        "oav_binding",
        "repository_canary_pass",
        "no_scalar_compensation",
    }
    row = _closed(value, allowed, "admission payload")
    gates = tuple(
        ComplexityGateEvidence(
            gate_id=str(item["gate_id"]),
            state=ComplexityGateState(str(item["state"])),
            evidence_links=_tuple_strings(item.get("evidence_links", []), "evidence_links"),
            reason=item.get("reason"),
        )
        for raw in row["gate_evidence"]
        for item in [
            _closed(
                raw,
                {"gate_id", "state", "evidence_links", "reason"},
                "gate evidence",
                required={"gate_id", "state"},
            )
        ]
    )
    return ComplexityModelAdmissionPacket(
        model_id=str(row["model_id"]),
        version=str(row["version"]),
        claim_scope=ComplexityClaimScope(str(row["claim_scope"])),
        parent_model_ids=_tuple_strings(row["parent_model_ids"], "parent_model_ids"),
        source_hashes=_tuple_strings(row["source_hashes"], "source_hashes"),
        supersession_state=str(row["supersession_state"]),
        gate_evidence=gates,
        formula_sha256=row["formula_sha256"],
        oav_binding=(
            None if row["oav_binding"] is None else _oav_binding(row["oav_binding"])
        ),
        repository_canary_pass=bool(row["repository_canary_pass"]),
        no_scalar_compensation=bool(row["no_scalar_compensation"]),
    )


def _model_lifecycle_card(value: Any) -> ModelLifecycleCard:
    allowed = {
        "model_id",
        "version",
        "release_sha256",
        "calibration_scope",
        "calibration_data_ids",
        "held_out_data_ids",
        "endpoint_ids",
        "abstention_rule",
        "drift_tolerance",
        "minimum_n",
        "drift_action",
        "supersession_rule",
        "retirement_rule",
        "evidence_ceiling",
        "claim_scopes",
        "known_failure_modes",
        "lifecycle_state",
        "superseded_by_release_sha256",
        "retirement_reason",
    }
    required = allowed.difference(
        {"lifecycle_state", "superseded_by_release_sha256", "retirement_reason"}
    )
    row = _closed(value, allowed, "lifecycle card", required=required)
    return ModelLifecycleCard(
        model_id=str(row["model_id"]),
        version=str(row["version"]),
        release_sha256=str(row["release_sha256"]),
        calibration_scope=str(row["calibration_scope"]),
        calibration_data_ids=_tuple_strings(row["calibration_data_ids"], "calibration_data_ids"),
        held_out_data_ids=_tuple_strings(row["held_out_data_ids"], "held_out_data_ids"),
        endpoint_ids=_tuple_strings(row["endpoint_ids"], "endpoint_ids"),
        abstention_rule=str(row["abstention_rule"]),
        drift_tolerance=_decimal(row["drift_tolerance"]),
        minimum_n=int(row["minimum_n"]),
        drift_action=str(row["drift_action"]),
        supersession_rule=str(row["supersession_rule"]),
        retirement_rule=str(row["retirement_rule"]),
        evidence_ceiling=str(row["evidence_ceiling"]),
        claim_scopes=_tuple_strings(row["claim_scopes"], "claim_scopes"),
        known_failure_modes=_tuple_strings(
            row["known_failure_modes"], "known_failure_modes"
        ),
        lifecycle_state=ModelLifecycleState(str(row.get("lifecycle_state", "CANDIDATE"))),
        superseded_by_release_sha256=row.get("superseded_by_release_sha256"),
        retirement_reason=row.get("retirement_reason"),
    )


def adapt_admission_lifecycle(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = str(payload.get("operation", ""))
    if operation == "model_admission":
        result = evaluate_complexity_model_admission(_model_admission_packet(payload))
    elif operation == "model_drift":
        row = _closed(
            payload,
            {"operation", "card", "observations", "calibration_scope"},
            "admission payload",
        )
        observations = tuple(
            ModelDriftObservation(
                observation_id=str(item["observation_id"]),
                observed=_decimal(item["observed"]),
                predicted=_decimal(item["predicted"]),
                evidence_sha256=str(item["evidence_sha256"]),
            )
            for raw in row["observations"]
            for item in [
                _closed(
                    raw,
                    {"observation_id", "observed", "predicted", "evidence_sha256"},
                    "drift observation",
                )
            ]
        )
        result = assess_model_drift(
            _model_lifecycle_card(row["card"]),
            observations,
            calibration_scope=str(row["calibration_scope"]),
        )
    else:
        raise ValueError(f"unsupported operation: {operation or '<missing>'}")
    return _seal(result.as_dict())


def _within_sniff(value: Mapping[str, Any]) -> WithinSniffSequence:
    allowed = {
        "operation",
        "sequence_id",
        "formula_sha256",
        "apparatus_kind",
        "apparatus_receipt_sha256",
        "pulses",
        "counterbalanced_orders",
        "claim_ceiling",
        "matched_total_delivered_mass",
        "oav_binding",
        "apparatus_qualified",
        "delivered_mass_receipt_sha256",
        "evidence_links",
    }
    row = _closed(value, allowed, "within-sniff payload")
    pulses = tuple(
        WithinSniffPulse(
            channel=str(item["channel"]),
            onset_ms=_decimal(item["onset_ms"]),
            duration_ms=_decimal(item["duration_ms"]),
            delivered_mass=_decimal(item["delivered_mass"]),
            delivered_mass_unit=str(item["delivered_mass_unit"]),
        )
        for raw in row["pulses"]
        for item in [
            _closed(
                raw,
                {"channel", "onset_ms", "duration_ms", "delivered_mass", "delivered_mass_unit"},
                "within-sniff pulse",
            )
        ]
    )
    return WithinSniffSequence(
        sequence_id=str(row["sequence_id"]),
        formula_sha256=str(row["formula_sha256"]),
        apparatus_kind=DeliveryApparatusKind(str(row["apparatus_kind"])),
        apparatus_receipt_sha256=str(row["apparatus_receipt_sha256"]),
        pulses=pulses,
        counterbalanced_orders=tuple(
            _tuple_strings(item, "counterbalanced order")
            for item in row["counterbalanced_orders"]
        ),
        claim_ceiling=WithinSniffClaimCeiling(str(row["claim_ceiling"])),
        matched_total_delivered_mass=bool(row["matched_total_delivered_mass"]),
        oav_binding=_oav_binding(row["oav_binding"]),
        apparatus_qualified=bool(row["apparatus_qualified"]),
        delivered_mass_receipt_sha256=row["delivered_mass_receipt_sha256"],
        evidence_links=_tuple_strings(row["evidence_links"], "evidence_links"),
    )


def _temporal_series(value: Mapping[str, Any]) -> TemporalObservationSeries:
    row = _closed(
        value,
        {"operation", "series_id", "formula_sha256", "time_unit", "observations", "oav_binding"},
        "temporal payload",
    )
    observations = tuple(
        TemporalObservation(
            observation_id=str(item["observation_id"]),
            dimension=str(item["dimension"]),
            timepoint=str(item["timepoint"]),
            time_numeric=_decimal(item["time_numeric"]),
            value=_decimal(item["value"]),
            dominant_system=item["dominant_system"],
            evidence_sha256=str(item["evidence_sha256"]),
        )
        for raw in row["observations"]
        for item in [
            _closed(
                raw,
                {
                    "observation_id",
                    "dimension",
                    "timepoint",
                    "time_numeric",
                    "value",
                    "dominant_system",
                    "evidence_sha256",
                },
                "temporal observation",
            )
        ]
    )
    return TemporalObservationSeries(
        series_id=str(row["series_id"]),
        formula_sha256=str(row["formula_sha256"]),
        time_unit=str(row["time_unit"]),
        observations=observations,
        oav_binding=_oav_binding(row["oav_binding"]),
    )


def adapt_temporal_sensory(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = str(payload.get("operation", ""))
    if operation == "within_sniff":
        result = evaluate_within_sniff_sequence(_within_sniff(payload))
    elif operation == "temporal_observations":
        result = summarize_temporal_observations(_temporal_series(payload))
    elif operation == "order_balance":
        row = _closed(
            payload,
            {"operation", "labels", "sequences", "method"},
            "order-balance payload",
        )
        result = assess_order_balance(
            PresentationSchedule(
                labels=_tuple_strings(row["labels"], "labels"),
                sequences=tuple(
                    _tuple_strings(item, "presentation sequence")
                    for item in row["sequences"]
                ),
                method=str(row["method"]),
            )
        )
    elif operation == "panel_exit":
        row = _closed(
            payload,
            {"operation", "results"},
            "panel-exit payload",
        )
        results = tuple(
            PanelPerformanceResult(
                gate_kind=GateKind(str(item["gate_kind"])),
                gate_spec_sha256=str(item["gate_spec_sha256"]),
                outcome=GateOutcome(str(item["outcome"])),
                observed_value=(
                    None if item["observed_value"] is None else _decimal(item["observed_value"])
                ),
                result_receipt_sha256=str(item["result_receipt_sha256"]),
                participant_set_sha256=str(item["participant_set_sha256"]),
                analysis_plan_sha256=str(item["analysis_plan_sha256"]),
                study_partition=StudyPartition(str(item["study_partition"])),
            )
            for raw in row["results"]
            for item in [
                _closed(
                    raw,
                    {
                        "gate_kind",
                        "gate_spec_sha256",
                        "outcome",
                        "observed_value",
                        "result_receipt_sha256",
                        "participant_set_sha256",
                        "analysis_plan_sha256",
                        "study_partition",
                    },
                    "panel result",
                )
            ]
        )
        lexicon = build_c0_construction_lexicon()
        result = evaluate_c0_exit(build_c0_protocol_draft(lexicon), lexicon, results)
    else:
        raise ValueError(f"unsupported operation: {operation or '<missing>'}")
    return _seal(result.as_dict())


def _exception(value: Any) -> MuskExceptionCall | None:
    if value is None:
        return None
    row = _closed(
        value,
        {
            "material",
            "target_tonal_role",
            "why_alternatives_fail",
            "loss_if_omitted",
            "failure_mode",
            "omission_control",
            "alternative_control",
        },
        "musk exception",
    )
    return MuskExceptionCall(**dict(row))


def _fingerprint(value: Any) -> MuskFingerprint | None:
    if value is None:
        return None
    row = _closed(
        value,
        {
            "material",
            "exact_target_effect",
            "temporal_window",
            "texture_axis",
            "projection_axis",
            "character_axis",
            "interaction_risks",
            "evidence_refs",
            "claim_status",
        },
        "musk fingerprint",
    )
    return MuskFingerprint(
        material=str(row["material"]),
        exact_target_effect=str(row["exact_target_effect"]),
        temporal_window=str(row["temporal_window"]),
        texture_axis=str(row["texture_axis"]),
        projection_axis=str(row["projection_axis"]),
        character_axis=str(row["character_axis"]),
        interaction_risks=_tuple_strings(row["interaction_risks"], "interaction_risks"),
        evidence_refs=_tuple_strings(row["evidence_refs"], "evidence_refs"),
        claim_status=ClaimStatus(str(row["claim_status"])),
    )


def adapt_musk_design(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    row = _closed(
        payload,
        {"target_identity", "target_brief", "candidates", "pairwise_nonredundancy"},
        "musk payload",
    )
    brief_value = row["target_brief"]
    target_brief = None
    if brief_value is not None:
        brief = _closed(
            brief_value,
            {
                "required_character",
                "unwanted_character",
                "temporal_behavior",
                "projection_intimacy",
                "texture",
                "system_connections",
            },
            "musk target brief",
        )
        target_brief = MuskTargetBrief(
            required_character=str(brief["required_character"]),
            unwanted_character=str(brief["unwanted_character"]),
            temporal_behavior=str(brief["temporal_behavior"]),
            projection_intimacy=str(brief["projection_intimacy"]),
            texture=str(brief["texture"]),
            system_connections=_tuple_strings(
                brief["system_connections"], "system_connections"
            ),
        )
    candidates = tuple(
        MuskCandidate(
            material=str(item["material"]),
            role=MuskRole(str(item["role"])),
            target_function=str(item["target_function"]),
            why_nonredundant=str(item["why_nonredundant"]),
            inventory_state=InventoryState(str(item["inventory_state"])),
            exact_stock_ref=item["exact_stock_ref"],
            exception=_exception(item["exception"]),
            fingerprint=_fingerprint(item["fingerprint"]),
        )
        for raw in row["candidates"]
        for item in [
            _closed(
                raw,
                {
                    "material",
                    "role",
                    "target_function",
                    "why_nonredundant",
                    "inventory_state",
                    "exact_stock_ref",
                    "exception",
                    "fingerprint",
                },
                "musk candidate",
            )
        ]
    )
    pairwise = tuple(
        PairwiseNonredundancy(**dict(item))
        for raw in row["pairwise_nonredundancy"]
        for item in [
            _closed(
                raw,
                {
                    "material_a",
                    "material_b",
                    "distinct_function_a",
                    "distinct_function_b",
                    "loss_if_a_omitted",
                    "loss_if_b_omitted",
                    "collision_risk",
                    "controlled_comparison",
                },
                "pairwise musk record",
            )
        ]
    )
    result = evaluate_musk_design(
        MuskDesignRequest(
            target_identity=str(row["target_identity"]),
            candidates=candidates,
            target_brief=target_brief,
            pairwise_nonredundancy=pairwise,
        )
    )
    return _seal(result.as_dict())


DEFAULT_COMPLEXITY_ADAPTERS: Mapping[str, Adapter] = MappingProxyType(
    {
        "construction_profile": adapt_construction_profile,
        "complexity_expansion": adapt_expansion_frontier,
        "experimental_design": adapt_experimental_design,
        "admission_lifecycle": adapt_admission_lifecycle,
        "temporal_sensory_integrity": adapt_temporal_sensory,
        "musk_design_restraint": adapt_musk_design,
    }
)
