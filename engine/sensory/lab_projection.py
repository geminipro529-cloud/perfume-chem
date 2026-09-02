"""Lossless, authority-false C0 projections into Laboratory Beta JSON fields.

The existing C0 dataclasses remain the scientific contract and Laboratory Beta
remains the persistence authority.  This module only validates a complete C0
graph and emits deterministic JSON-safe projections for the existing
``LabExperiment``, ``LabApplication``, ``LabObservation``, and ``LabOutcome``
records.  It creates no parallel experiment store and grants no execution,
study, calibration, or release authority.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from engine.calibration.hashing import canonical_json_bytes, stable_json_hash
from engine.sensory.panel_contract import (
    CONSTRUCTION_ATTRIBUTE_IDS,
    BindingState,
    C0ExitReport,
    ConstructionLexicon,
    ConstructionPanelProtocol,
    ExpertiseStratum,
    GateAuthority,
    GateKind,
    PanelObservation,
    PanelPerformanceResult,
    ParticipantQualificationReceipt,
    StudyPartition,
    evaluate_c0_exit,
    validate_panel_observation,
)
from engine.sensory.prepilot import C0PrepilotBundle, PrepilotDecision

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BLIND_CODE_RE = re.compile(r"^[A-Z0-9]{3,12}$")

C0_CLAIM_DOMAIN = "SEALED_STATIC_GLASS_HEADSPACE"
C0_FULL_ARTIFACT_IDS = (
    "C0_PREPILOT_PROTOCOL",
    "LEXICON",
    "ATTRIBUTE_ANCHOR_CANDIDATES",
    "SAMPLE_PREPARATION_MANIFEST",
    "APPARATUS_VALIDATION",
    "SAFETY_ETHICS_PRIVACY_HOLD",
    "PARTICIPANT_QUALIFICATION",
    "ENVIRONMENT_TIMING",
    "RANDOMIZATION_LEDGER",
    "BLIND_CODE_KEY",
    "OBSERVATION_SCHEMA",
    "ANALYSIS_PLAN",
    "STOP_GO_GATES",
    "DEVIATION_LOG",
    "RESULTS_RECEIPT",
    "SOURCE_MANIFEST",
    "DECISION_RECORD",
)
C0_OPAQUE_EXTERNAL_ARTIFACT_IDS = (
    "APPARATUS_VALIDATION",
    "OBSERVATION_SCHEMA",
    "DEVIATION_LOG",
)


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field_name} must be non-empty without surrounding whitespace")


class C0ArtifactState(str, Enum):
    UNBOUND = "UNBOUND"
    BOUND = "BOUND"


class C0EnvelopeKind(str, Enum):
    REAL_CANDIDATE_HOLD = "REAL_CANDIDATE_HOLD"
    SYNTHETIC_PERSISTENCE_FIT_ONLY = "SYNTHETIC_PERSISTENCE_FIT_ONLY"


@dataclass(frozen=True, slots=True)
class C0ArtifactReceipt:
    artifact_id: str
    state: C0ArtifactState
    artifact_sha256: str | None
    unbound_reason: str | None

    def __post_init__(self) -> None:
        if self.artifact_id not in C0_FULL_ARTIFACT_IDS:
            raise ValueError("artifact_id is outside the 17-artifact C0 denominator")
        if not isinstance(self.state, C0ArtifactState):
            raise ValueError("state must be a C0ArtifactState")
        if self.state is C0ArtifactState.BOUND:
            if self.artifact_sha256 is None:
                raise ValueError("bound C0 artifact requires artifact_sha256")
            _require_sha256(self.artifact_sha256, "artifact_sha256")
            if self.unbound_reason is not None:
                raise ValueError("bound C0 artifact cannot carry an unbound reason")
            return
        if self.artifact_sha256 is not None:
            raise ValueError("unbound C0 artifact cannot carry artifact_sha256")
        if self.unbound_reason is None:
            raise ValueError("unbound C0 artifact requires an explicit reason")
        _require_text(self.unbound_reason, "unbound_reason")

    @classmethod
    def bound(cls, artifact_id: str, artifact_sha256: str) -> C0ArtifactReceipt:
        return cls(artifact_id, C0ArtifactState.BOUND, artifact_sha256, None)

    @classmethod
    def unbound(cls, artifact_id: str, reason: str) -> C0ArtifactReceipt:
        return cls(artifact_id, C0ArtifactState.UNBOUND, None, reason)

    def as_dict(self) -> dict[str, str | None]:
        return {
            "artifact_id": self.artifact_id,
            "state": self.state.value,
            "artifact_sha256": self.artifact_sha256,
            "unbound_reason": self.unbound_reason,
        }


@dataclass(frozen=True, slots=True)
class C0PackageHoldEnvelope:
    """Exact recovered package candidate with all 17 artifacts still unbound."""

    source_payload_json: str
    source_payload_sha256: str
    artifact_registry: tuple[C0ArtifactReceipt, ...]
    claim_domain: str = C0_CLAIM_DOMAIN
    pleasantness_in_go_decision: bool = field(default=False, init=False)
    human_execution_authorized: bool = field(default=False, init=False)
    transfer_claims: tuple[str, ...] = field(default=(), init=False)
    decision_state: str = field(default="HOLD", init=False)
    scientific_authority: bool = field(default=False, init=False)
    study_authority: bool = field(default=False, init=False)
    calibration_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        try:
            payload = json.loads(self.source_payload_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("source_payload_json must contain valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("source C0 payload must be a JSON object")
        canonical = canonical_json_bytes(payload).decode("utf-8")
        object.__setattr__(self, "source_payload_json", canonical)
        if self.claim_domain != C0_CLAIM_DOMAIN:
            raise ValueError("package C0 claim domain must remain sealed static glass headspace")
        _validate_package_hold_payload(payload)
        _require_sha256(self.source_payload_sha256, "source_payload_sha256")
        if stable_json_hash(payload) != self.source_payload_sha256:
            raise ValueError("source payload hash does not match canonical bytes")
        _validate_artifact_registry(self.artifact_registry)
        if any(item.state is not C0ArtifactState.UNBOUND for item in self.artifact_registry):
            raise ValueError("real package candidate artifacts must remain unbound")

    @property
    def source_payload(self) -> dict[str, Any]:
        value = json.loads(self.source_payload_json)
        if not isinstance(value, dict):  # pragma: no cover - guarded in __post_init__
            raise TypeError("source payload is not an object")
        return value

    @property
    def artifact_registry_sha256(self) -> str:
        return stable_json_hash([item.as_dict() for item in self.artifact_registry])

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perfume-chem.c0-package-hold-envelope.v1",
            "envelope_kind": C0EnvelopeKind.REAL_CANDIDATE_HOLD.value,
            "source_payload": self.source_payload,
            "source_payload_sha256": self.source_payload_sha256,
            "claim_domain": self.claim_domain,
            "attributes": list(CONSTRUCTION_ATTRIBUTE_IDS),
            "artifact_registry": [item.as_dict() for item in self.artifact_registry],
            "artifact_registry_sha256": self.artifact_registry_sha256,
            "pleasantness_in_go_decision": self.pleasantness_in_go_decision,
            "human_execution_authorized": self.human_execution_authorized,
            "transfer_claims": list(self.transfer_claims),
            "decision_state": self.decision_state,
            "scientific_authority": self.scientific_authority,
            "study_authority": self.study_authority,
            "calibration_authority": self.calibration_authority,
            "release_authority": self.release_authority,
        }

    @property
    def envelope_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


def build_package_c0_hold_envelope(payload: Mapping[str, Any]) -> C0PackageHoldEnvelope:
    """Preserve the recovered package C0 fixture without promoting any claim."""

    copied = json.loads(canonical_json_bytes(payload).decode("utf-8"))
    _validate_package_hold_payload(copied)
    registry = tuple(
        C0ArtifactReceipt.unbound(
            artifact_id,
            "Recovered v3 package marks this artifact UNBOUND; exact reviewed bytes or receipts are unavailable.",
        )
        for artifact_id in C0_FULL_ARTIFACT_IDS
    )
    return C0PackageHoldEnvelope(
        source_payload_json=canonical_json_bytes(copied).decode("utf-8"),
        source_payload_sha256=stable_json_hash(copied),
        artifact_registry=registry,
    )


def _validate_package_hold_payload(payload: Mapping[str, Any]) -> None:
    if payload.get("claim_domain") != C0_CLAIM_DOMAIN:
        raise ValueError("package C0 claim domain must remain sealed static glass headspace")
    if payload.get("attributes") != list(CONSTRUCTION_ATTRIBUTE_IDS):
        raise ValueError("package C0 relational attribute order is incomplete or altered")
    artifacts = payload.get("artifacts")
    if (
        not isinstance(artifacts, dict)
        or len(artifacts) != len(C0_FULL_ARTIFACT_IDS)
        or set(artifacts) != set(C0_FULL_ARTIFACT_IDS)
    ):
        raise ValueError("package C0 payload must preserve all 17 artifacts")
    for artifact_id, record in artifacts.items():
        if not isinstance(record, dict) or record != {"state": "UNBOUND", "hash": None}:
            raise ValueError(f"package C0 artifact '{artifact_id}' must remain UNBOUND")
    if payload.get("pleasantness_in_go_decision") is not False:
        raise ValueError("pleasantness must remain outside the C0 GO decision")
    if payload.get("human_execution_authorized") is not False:
        raise ValueError("real package candidate cannot authorize human execution")
    if payload.get("transfer_claims") != []:
        raise ValueError("C0 transfer claims must remain empty")
    if payload.get("decision_state") != "HOLD":
        raise ValueError("real package candidate must remain HOLD")


@dataclass(frozen=True, slots=True)
class C0ExpectedObservationCell:
    blind_code: str
    participant_token_sha256: str
    qualification_receipt_sha256: str
    session_token_sha256: str
    repeat_index: int
    sniff_time_seconds: int

    def __post_init__(self) -> None:
        if not isinstance(self.blind_code, str) or not _BLIND_CODE_RE.fullmatch(self.blind_code):
            raise ValueError("blind_code must be 3-12 uppercase letters or digits")
        for value, name in (
            (self.participant_token_sha256, "participant_token_sha256"),
            (self.qualification_receipt_sha256, "qualification_receipt_sha256"),
            (self.session_token_sha256, "session_token_sha256"),
        ):
            _require_sha256(value, name)
        if (
            isinstance(self.repeat_index, bool)
            or not isinstance(self.repeat_index, int)
            or self.repeat_index <= 0
        ):
            raise ValueError("repeat_index must be a positive integer")
        if (
            isinstance(self.sniff_time_seconds, bool)
            or not isinstance(self.sniff_time_seconds, int)
            or self.sniff_time_seconds < 0
        ):
            raise ValueError("sniff_time_seconds must be a non-negative integer")

    @property
    def key(self) -> tuple[str, str, str, int, int]:
        return (
            self.blind_code,
            self.participant_token_sha256,
            self.session_token_sha256,
            self.repeat_index,
            self.sniff_time_seconds,
        )

    @property
    def application_key(self) -> tuple[str, str, str, int]:
        return self.key[:-1]

    def as_dict(self) -> dict[str, str | int]:
        return {
            "blind_code": self.blind_code,
            "participant_token_sha256": self.participant_token_sha256,
            "qualification_receipt_sha256": self.qualification_receipt_sha256,
            "session_token_sha256": self.session_token_sha256,
            "repeat_index": self.repeat_index,
            "sniff_time_seconds": self.sniff_time_seconds,
        }


@dataclass(frozen=True, slots=True)
class C0LabPersistenceProjection:
    """Canonical JSON records ready for the existing Laboratory Beta service."""

    experiment_protocol_json: str
    application_records_json: str
    observation_records_json: str
    outcome_json: str
    human_execution_authorized: bool = field(default=False, init=False)
    scientific_authority: bool = field(default=False, init=False)
    study_authority: bool = field(default=False, init=False)
    calibration_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "experiment_protocol_json",
            "application_records_json",
            "observation_records_json",
            "outcome_json",
        ):
            raw = getattr(self, field_name)
            try:
                value = json.loads(raw)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError(f"{field_name} must contain valid JSON") from exc
            object.__setattr__(self, field_name, canonical_json_bytes(value).decode("utf-8"))

    @staticmethod
    def _load_object(raw: str) -> dict[str, Any]:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise TypeError("projection JSON is not an object")
        return value

    @staticmethod
    def _load_list(raw: str) -> list[dict[str, Any]]:
        value = json.loads(raw)
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise TypeError("projection JSON is not a list of objects")
        return value

    @property
    def experiment_protocol(self) -> dict[str, Any]:
        return self._load_object(self.experiment_protocol_json)

    @property
    def application_records(self) -> list[dict[str, Any]]:
        return self._load_list(self.application_records_json)

    @property
    def observation_records(self) -> list[dict[str, Any]]:
        return self._load_list(self.observation_records_json)

    @property
    def outcome(self) -> dict[str, Any]:
        return self._load_object(self.outcome_json)

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_protocol": self.experiment_protocol,
            "application_records": self.application_records,
            "observation_records": self.observation_records,
            "outcome": self.outcome,
            "human_execution_authorized": self.human_execution_authorized,
            "scientific_authority": self.scientific_authority,
            "study_authority": self.study_authority,
            "calibration_authority": self.calibration_authority,
            "release_authority": self.release_authority,
        }

    @property
    def projection_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


def _validate_artifact_registry(registry: tuple[C0ArtifactReceipt, ...]) -> None:
    if tuple(item.artifact_id for item in registry) != C0_FULL_ARTIFACT_IDS:
        raise ValueError("artifact registry must preserve the full 17-artifact order")


def _observation_key(observation: PanelObservation) -> tuple[str, str, str, int, int]:
    return (
        observation.blind_code,
        observation.participant_token_sha256,
        observation.session_token_sha256,
        observation.repeat_index,
        observation.sniff_time_seconds,
    )


def _manifest_by_id(bundle: C0PrepilotBundle) -> dict[str, Any]:
    return {item.binding_id: item for item in bundle.manifests}


def project_complete_c0_to_lab(
    *,
    source_payload_sha256: str,
    artifact_registry: tuple[C0ArtifactReceipt, ...],
    lexicon: ConstructionLexicon,
    protocol: ConstructionPanelProtocol,
    prepilot_bundle: C0PrepilotBundle,
    qualification_receipts: tuple[ParticipantQualificationReceipt, ...],
    expected_observation_manifest: tuple[C0ExpectedObservationCell, ...],
    observations: tuple[PanelObservation, ...],
    panel_performance_results: tuple[PanelPerformanceResult, ...],
    exit_report: C0ExitReport,
) -> C0LabPersistenceProjection:
    """Validate and project one complete synthetic C0 persistence-fit graph."""

    _require_sha256(source_payload_sha256, "source_payload_sha256")
    _validate_artifact_registry(artifact_registry)
    if any(item.state is not C0ArtifactState.BOUND for item in artifact_registry):
        raise ValueError("synthetic persistence fit requires all 17 artifact hashes")
    if protocol.study_partition is not StudyPartition.PILOT:
        raise ValueError("C0 persistence fit must preserve the PILOT partition")
    if not protocol.protocol_locked:
        raise ValueError("complete C0 persistence fit requires a locked protocol")
    if protocol.lexicon_sha256 != lexicon.lexicon_sha256:
        raise ValueError("protocol lexicon hash does not match the supplied lexicon")
    if any(item.state is not BindingState.BOUND for item in protocol.bindings):
        raise ValueError("locked C0 persistence fit cannot contain unbound native bindings")
    if any(
        item.authority is not GateAuthority.PREREGISTERED_LOCKED
        for item in protocol.panel_gate_specs
    ):
        raise ValueError("locked C0 persistence fit requires preregistered gate specs")
    if prepilot_bundle.lexicon_sha256 != lexicon.lexicon_sha256:
        raise ValueError("prepilot bundle lexicon hash does not match")
    readiness = prepilot_bundle.readiness()
    if readiness.decision is not PrepilotDecision.BINDABLE:
        raise ValueError("prepilot bundle is not bindable")
    if protocol.bindings != prepilot_bundle.evidence_bindings():
        raise ValueError("protocol bindings do not match the applied prepilot bundle")

    manifests = _manifest_by_id(prepilot_bundle)
    timing = manifests["environment_timing_manifest"].payload["sniff_timepoints_seconds"]
    repeats = manifests["participant_plan"].payload["repeat_plan"]["repeats_per_sample"]
    if protocol.timepoints_seconds != tuple(timing) or protocol.repeat_count != repeats:
        raise ValueError("protocol timing/repeats do not match the prepilot bundle")

    if not qualification_receipts:
        raise ValueError("qualification receipts must not be empty")
    ordered_qualifications = tuple(
        sorted(
            qualification_receipts,
            key=lambda item: item.participant_token_sha256,
        )
    )
    receipt_by_participant: dict[str, ParticipantQualificationReceipt] = {}
    for receipt in ordered_qualifications:
        if receipt.participant_token_sha256 in receipt_by_participant:
            raise ValueError("participant qualification receipts contain duplicates")
        if receipt.protocol_sha256 != protocol.protocol_sha256:
            raise ValueError("qualification receipt protocol hash does not match")
        receipt_by_participant[receipt.participant_token_sha256] = receipt
    represented_strata = {item.expertise_stratum for item in ordered_qualifications}
    if not {ExpertiseStratum.TRAINED_DESCRIPTIVE, ExpertiseStratum.UNTRAINED}.issubset(
        represented_strata
    ):
        raise ValueError("synthetic fit must preserve trained and untrained participant strata")

    if not expected_observation_manifest:
        raise ValueError("expected observation manifest must not be empty")
    ordered_expected = tuple(sorted(expected_observation_manifest, key=lambda item: item.key))
    expected_by_key: dict[tuple[str, str, str, int, int], C0ExpectedObservationCell] = {}
    for cell in ordered_expected:
        if cell.key in expected_by_key:
            raise ValueError("expected observation manifest contains duplicate cells")
        receipt = receipt_by_participant.get(cell.participant_token_sha256)
        if receipt is None or receipt.receipt_sha256 != cell.qualification_receipt_sha256:
            raise ValueError("expected observation cell qualification binding does not match")
        if cell.repeat_index > protocol.repeat_count:
            raise ValueError("expected observation repeat is outside the protocol")
        if cell.sniff_time_seconds not in protocol.timepoints_seconds:
            raise ValueError("expected observation timepoint is outside the protocol")
        expected_by_key[cell.key] = cell

    observed_by_key: dict[tuple[str, str, str, int, int], PanelObservation] = {}
    ordered_observations = tuple(sorted(observations, key=_observation_key))
    for observation in ordered_observations:
        key = _observation_key(observation)
        if key in observed_by_key:
            raise ValueError("panel observations contain duplicate expected cells")
        receipt = receipt_by_participant.get(observation.participant_token_sha256)
        if receipt is None:
            raise ValueError("panel observation participant has no qualification receipt")
        validate_panel_observation(observation, protocol, lexicon, receipt)
        observed_by_key[key] = observation
    if set(observed_by_key) != set(expected_by_key):
        missing = len(set(expected_by_key) - set(observed_by_key))
        unexpected = len(set(observed_by_key) - set(expected_by_key))
        raise ValueError(
            f"panel observation coverage mismatch: missing={missing}, unexpected={unexpected}"
        )

    gate_rank = {kind: index for index, kind in enumerate(GateKind)}
    ordered_results = tuple(
        sorted(panel_performance_results, key=lambda item: gate_rank[item.gate_kind])
    )
    evaluated_exit = evaluate_c0_exit(protocol, lexicon, ordered_results)
    if evaluated_exit.as_dict() != exit_report.as_dict():
        raise ValueError("exit report does not match deterministic C0 evaluation")

    qualification_payload = [item.as_dict() for item in ordered_qualifications]
    expected_payload = [item.as_dict() for item in ordered_expected]
    result_payload = [item.as_dict() for item in ordered_results]
    expected_hashes = {
        "C0_PREPILOT_PROTOCOL": protocol.protocol_sha256,
        "LEXICON": lexicon.lexicon_sha256,
        "ATTRIBUTE_ANCHOR_CANDIDATES": manifests["anchor_reference_manifest"].manifest_sha256,
        "SAMPLE_PREPARATION_MANIFEST": manifests["preparation_dose_ppm_manifest"].manifest_sha256,
        "SAFETY_ETHICS_PRIVACY_HOLD": manifests["ethics_privacy_safety_review"].manifest_sha256,
        "PARTICIPANT_QUALIFICATION": stable_json_hash(qualification_payload),
        "ENVIRONMENT_TIMING": manifests["environment_timing_manifest"].manifest_sha256,
        "RANDOMIZATION_LEDGER": manifests["randomization_manifest"].manifest_sha256,
        "BLIND_CODE_KEY": manifests["sample_manifest"].manifest_sha256,
        "ANALYSIS_PLAN": manifests["analysis_plan"].manifest_sha256,
        "STOP_GO_GATES": stable_json_hash([item.as_dict() for item in protocol.panel_gate_specs]),
        "RESULTS_RECEIPT": stable_json_hash(result_payload),
        "SOURCE_MANIFEST": source_payload_sha256,
        "DECISION_RECORD": stable_json_hash(exit_report.as_dict()),
    }
    registry_by_id = {item.artifact_id: item for item in artifact_registry}
    for artifact_id, expected_hash in expected_hashes.items():
        if registry_by_id[artifact_id].artifact_sha256 != expected_hash:
            raise ValueError(f"artifact registry hash mismatch for {artifact_id}")

    registry_payload = [item.as_dict() for item in artifact_registry]
    experiment_protocol = {
        "schema_version": "perfume-chem.c0-lab-persistence-projection.v1",
        "envelope_kind": C0EnvelopeKind.SYNTHETIC_PERSISTENCE_FIT_ONLY.value,
        "persistence_fit_scope": "STORAGE_FIDELITY_ONLY",
        "semantic_revalidation_required_after_readback": True,
        "source_payload_sha256": source_payload_sha256,
        "claim_domain": C0_CLAIM_DOMAIN,
        "attributes": list(CONSTRUCTION_ATTRIBUTE_IDS),
        "artifact_registry": registry_payload,
        "artifact_registry_sha256": stable_json_hash(registry_payload),
        "opaque_external_artifact_ids": list(C0_OPAQUE_EXTERNAL_ARTIFACT_IDS),
        "lexicon": lexicon.as_dict(),
        "lexicon_sha256": lexicon.lexicon_sha256,
        "protocol": protocol.as_dict(),
        "protocol_sha256": protocol.protocol_sha256,
        "prepilot_bundle": prepilot_bundle.as_dict(),
        "prepilot_bundle_sha256": prepilot_bundle.bundle_sha256,
        "prepilot_readiness": readiness.as_dict(),
        "prepilot_readiness_sha256": stable_json_hash(readiness.as_dict()),
        "participant_qualification_receipts": qualification_payload,
        "participant_qualification_set_sha256": stable_json_hash(qualification_payload),
        "expected_observation_manifest": expected_payload,
        "expected_observation_manifest_sha256": stable_json_hash(expected_payload),
        "pleasantness_in_go_decision": False,
        "human_execution_authorized": False,
        "transfer_claims": [],
        "scientific_authority": False,
        "study_authority": False,
        "calibration_authority": False,
        "release_authority": False,
    }

    preparation_manifest = manifests["preparation_dose_ppm_manifest"]
    application_groups: dict[tuple[str, str, str, int], list[int]] = {}
    for cell in ordered_expected:
        application_groups.setdefault(cell.application_key, []).append(cell.sniff_time_seconds)
    application_records: list[dict[str, Any]] = []
    for application_key in sorted(application_groups):
        timepoints = application_groups[application_key]
        blind_code, participant_token, session_token, repeat_index = application_key
        receipt = receipt_by_participant[participant_token]
        key_payload = {
            "blind_code": blind_code,
            "participant_token_sha256": participant_token,
            "session_token_sha256": session_token,
            "repeat_index": repeat_index,
        }
        application_records.append(
            {
                "application_key_sha256": stable_json_hash(key_payload),
                "blind_code": blind_code,
                "dose_json": {
                    "preparation_manifest": preparation_manifest.payload,
                    "preparation_manifest_sha256": preparation_manifest.manifest_sha256,
                },
                "context_json": {
                    **key_payload,
                    "qualification_receipt_sha256": receipt.receipt_sha256,
                    "protocol_sha256": protocol.protocol_sha256,
                    "expected_timepoints_seconds": sorted(timepoints),
                    "human_execution_authorized": False,
                    "study_authority": False,
                    "release_authority": False,
                },
            }
        )

    observation_records: list[dict[str, Any]] = []
    for cell in ordered_expected:
        observation = observed_by_key[cell.key]
        application_key_payload = {
            "blind_code": cell.blind_code,
            "participant_token_sha256": cell.participant_token_sha256,
            "session_token_sha256": cell.session_token_sha256,
            "repeat_index": cell.repeat_index,
        }
        observation_records.append(
            {
                "application_key_sha256": stable_json_hash(application_key_payload),
                "elapsed_seconds": cell.sniff_time_seconds,
                "observations_json": {
                    "panel_observation": observation.as_dict(),
                    "panel_observation_sha256": observation.record_sha256,
                    "scientific_authority": False,
                    "study_authority": False,
                    "calibration_authority": False,
                    "release_authority": False,
                },
            }
        )

    outcome = {
        "schema_version": "perfume-chem.c0-lab-outcome-projection.v1",
        "envelope_kind": C0EnvelopeKind.SYNTHETIC_PERSISTENCE_FIT_ONLY.value,
        "persistence_fit_scope": "STORAGE_FIDELITY_ONLY",
        "semantic_revalidation_required_after_readback": True,
        "protocol_sha256": protocol.protocol_sha256,
        "panel_performance_results": result_payload,
        "panel_performance_results_sha256": stable_json_hash(result_payload),
        "c0_exit_report": exit_report.as_dict(),
        "c0_exit_report_sha256": stable_json_hash(exit_report.as_dict()),
        "human_execution_authorized": False,
        "scientific_authority": False,
        "study_authority": False,
        "calibration_authority": False,
        "release_authority": False,
    }
    return C0LabPersistenceProjection(
        experiment_protocol_json=canonical_json_bytes(experiment_protocol).decode("utf-8"),
        application_records_json=canonical_json_bytes(application_records).decode("utf-8"),
        observation_records_json=canonical_json_bytes(observation_records).decode("utf-8"),
        outcome_json=canonical_json_bytes(outcome).decode("utf-8"),
    )


__all__ = [
    "C0ArtifactReceipt",
    "C0ArtifactState",
    "C0EnvelopeKind",
    "C0ExpectedObservationCell",
    "C0LabPersistenceProjection",
    "C0PackageHoldEnvelope",
    "C0_CLAIM_DOMAIN",
    "C0_FULL_ARTIFACT_IDS",
    "C0_OPAQUE_EXTERNAL_ARTIFACT_IDS",
    "build_package_c0_hold_envelope",
    "project_complete_c0_to_lab",
]
