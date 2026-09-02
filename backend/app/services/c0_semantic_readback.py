"""Pure, read-only semantic revalidation for persisted C0 projection graphs.

Laboratory Beta owns storage while the engine C0 contracts own scientific
semantics.  This module validates the closed serialized boundary without
importing the engine package, mutating rows, or granting any authority.  Every
failure becomes a deterministic HOLD receipt.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ATTRIBUTES = (
    "airiness",
    "separability",
    "density",
    "coherence",
    "target_fidelity",
    "contrast",
    "emergence",
    "recognition",
    "pleasantness",
)
_CONSTRUCTION_ATTRIBUTES = _ATTRIBUTES[:-1]
_ARTIFACT_IDS = (
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
_OPAQUE_ARTIFACT_IDS = (
    "APPARATUS_VALIDATION",
    "OBSERVATION_SCHEMA",
    "DEVIATION_LOG",
)
_MANIFEST_IDS = (
    "sample_manifest",
    "preparation_dose_ppm_manifest",
    "formula_oav_manifest",
    "randomization_manifest",
    "anchor_reference_manifest",
    "participant_plan",
    "environment_timing_manifest",
    "analysis_plan",
    "ethics_privacy_safety_review",
)
_GATE_KINDS = ("discrimination", "agreement", "repeatability")
_AUTHORITY_KEYS = {
    "human_execution_authorized",
    "scientific_authority",
    "study_authority",
    "study_authorized",
    "calibration_authority",
    "model_calibration_authority",
    "release_authority",
}


class C0SemanticReadbackState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _stable_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _as_mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_sequence(value: object) -> Sequence[Any] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return None


def _decimal(value: object) -> Decimal | None:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return result if result.is_finite() else None


def _walk_authority_bits(value: object, path: str = "$") -> tuple[str, ...]:
    failures: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}.{key}"
            if key in _AUTHORITY_KEYS and item is not False:
                failures.append(f"AUTHORITY_BIT_NOT_FALSE:{child}")
            failures.extend(_walk_authority_bits(item, child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            failures.extend(_walk_authority_bits(item, f"{path}[{index}]"))
    return tuple(failures)


@dataclass(frozen=True, slots=True)
class C0SemanticReadbackReceipt:
    state: C0SemanticReadbackState
    graph_sha256: str
    protocol_sha256: str | None
    application_set_sha256: str | None
    observation_set_sha256: str | None
    outcome_sha256: str | None
    expected_cell_count: int
    observed_cell_count: int
    blockers: tuple[str, ...]
    semantic_revalidation_passed: bool
    human_execution_authorized: bool = field(default=False, init=False)
    scientific_authority: bool = field(default=False, init=False)
    study_authority: bool = field(default=False, init=False)
    calibration_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "perfume-chem.c0-semantic-readback-receipt.v1",
            "state": self.state.value,
            "graph_sha256": self.graph_sha256,
            "protocol_sha256": self.protocol_sha256,
            "application_set_sha256": self.application_set_sha256,
            "observation_set_sha256": self.observation_set_sha256,
            "outcome_sha256": self.outcome_sha256,
            "expected_cell_count": self.expected_cell_count,
            "observed_cell_count": self.observed_cell_count,
            "blockers": list(self.blockers),
            "semantic_revalidation_passed": self.semantic_revalidation_passed,
            "human_execution_authorized": self.human_execution_authorized,
            "scientific_authority": self.scientific_authority,
            "study_authority": self.study_authority,
            "calibration_authority": self.calibration_authority,
            "release_authority": self.release_authority,
        }

    @property
    def receipt_sha256(self) -> str:
        return _stable_hash(self.as_dict())


class _Validator:
    def __init__(self, graph: Mapping[str, Any]) -> None:
        self.graph = graph
        self.errors: list[str] = []
        self.expected_cells: set[tuple[object, ...]] = set()
        self.observed_cells: set[tuple[object, ...]] = set()

    def require(self, condition: bool, code: str) -> None:
        if not condition and code not in self.errors:
            self.errors.append(code)

    def validate(self) -> None:
        protocol = _as_mapping(self.graph.get("experiment_protocol"))
        applications = _as_sequence(self.graph.get("application_records"))
        observations = _as_sequence(self.graph.get("observation_records"))
        outcome = _as_mapping(self.graph.get("outcome"))
        self.require(protocol is not None, "EXPERIMENT_PROTOCOL_MISSING")
        self.require(applications is not None, "APPLICATION_RECORDS_MISSING")
        self.require(observations is not None, "OBSERVATION_RECORDS_MISSING")
        self.require(outcome is not None, "OUTCOME_RECORD_MISSING")
        if protocol is None or applications is None or observations is None or outcome is None:
            return
        self.errors.extend(_walk_authority_bits(self.graph))
        self._validate_protocol(protocol)
        self._validate_applications(protocol, applications)
        self._validate_observations(protocol, observations)
        self._validate_outcome(protocol, outcome)

    def _validate_protocol(self, envelope: Mapping[str, Any]) -> None:
        self.require(
            envelope.get("schema_version")
            == "perfume-chem.c0-lab-persistence-projection.v1",
            "PROTOCOL_SCHEMA_MISMATCH",
        )
        self.require(
            envelope.get("envelope_kind") == "SYNTHETIC_PERSISTENCE_FIT_ONLY",
            "ENVELOPE_KIND_MISMATCH",
        )
        self.require(
            envelope.get("persistence_fit_scope") == "STORAGE_FIDELITY_ONLY",
            "PERSISTENCE_SCOPE_MISMATCH",
        )
        self.require(
            envelope.get("semantic_revalidation_required_after_readback") is True,
            "READBACK_REVALIDATION_FLAG_MISSING",
        )
        self.require(
            envelope.get("claim_domain") == "SEALED_STATIC_GLASS_HEADSPACE",
            "CLAIM_DOMAIN_MISMATCH",
        )
        self.require(envelope.get("transfer_claims") == [], "TRANSFER_CLAIMS_NOT_EMPTY")
        self.require(
            envelope.get("pleasantness_in_go_decision") is False,
            "PLEASANTNESS_PROMOTED_TO_GO",
        )
        self.require(
            tuple(envelope.get("attributes", ())) == _CONSTRUCTION_ATTRIBUTES,
            "CONSTRUCTION_ATTRIBUTE_SET_MISMATCH",
        )
        self.require(
            tuple(envelope.get("opaque_external_artifact_ids", ()))
            == _OPAQUE_ARTIFACT_IDS,
            "OPAQUE_ARTIFACT_SET_MISMATCH",
        )

        lexicon = _as_mapping(envelope.get("lexicon"))
        protocol = _as_mapping(envelope.get("protocol"))
        bundle = _as_mapping(envelope.get("prepilot_bundle"))
        readiness = _as_mapping(envelope.get("prepilot_readiness"))
        qualifications = _as_sequence(envelope.get("participant_qualification_receipts"))
        manifest = _as_sequence(envelope.get("expected_observation_manifest"))
        registry = _as_sequence(envelope.get("artifact_registry"))
        for value, code in (
            (lexicon, "LEXICON_MISSING"),
            (protocol, "NATIVE_PROTOCOL_MISSING"),
            (bundle, "PREPILOT_BUNDLE_MISSING"),
            (readiness, "PREPILOT_READINESS_MISSING"),
            (qualifications, "QUALIFICATION_SET_MISSING"),
            (manifest, "EXPECTED_MANIFEST_MISSING"),
            (registry, "ARTIFACT_REGISTRY_MISSING"),
        ):
            self.require(value is not None, code)
        if any(
            value is None
            for value in (lexicon, protocol, bundle, readiness, qualifications, manifest, registry)
        ):
            return
        assert lexicon is not None
        assert protocol is not None
        assert bundle is not None
        assert readiness is not None
        assert qualifications is not None
        assert manifest is not None
        assert registry is not None

        lexicon_hash = _stable_hash(lexicon)
        protocol_hash = _stable_hash(protocol)
        bundle_hash = _stable_hash(bundle)
        self.require(envelope.get("lexicon_sha256") == lexicon_hash, "LEXICON_HASH_MISMATCH")
        self.require(envelope.get("protocol_sha256") == protocol_hash, "PROTOCOL_HASH_MISMATCH")
        self.require(
            envelope.get("prepilot_bundle_sha256") == bundle_hash,
            "PREPILOT_BUNDLE_HASH_MISMATCH",
        )
        self.require(
            envelope.get("prepilot_readiness_sha256") == _stable_hash(readiness),
            "PREPILOT_READINESS_HASH_MISMATCH",
        )
        self.require(
            envelope.get("participant_qualification_set_sha256")
            == _stable_hash(qualifications),
            "QUALIFICATION_SET_HASH_MISMATCH",
        )
        self.require(
            envelope.get("expected_observation_manifest_sha256") == _stable_hash(manifest),
            "EXPECTED_MANIFEST_HASH_MISMATCH",
        )
        self.require(
            envelope.get("artifact_registry_sha256") == _stable_hash(registry),
            "ARTIFACT_REGISTRY_HASH_MISMATCH",
        )
        self._validate_lexicon(lexicon)
        manifest_hashes = self._validate_bundle(bundle, lexicon_hash, protocol)
        gate_specs = self._validate_native_protocol(protocol, lexicon_hash, manifest_hashes)
        qualification_hashes = self._validate_qualifications(qualifications, protocol_hash)
        self._validate_expected_manifest(manifest, protocol, qualification_hashes)
        self._validate_readiness(readiness, bundle_hash)
        self._validate_artifact_registry(
            registry,
            envelope,
            protocol_hash,
            lexicon_hash,
            qualifications,
            gate_specs,
            manifest_hashes,
        )

    def _validate_lexicon(self, lexicon: Mapping[str, Any]) -> None:
        attributes = _as_sequence(lexicon.get("attributes"))
        self.require(attributes is not None, "LEXICON_ATTRIBUTES_MISSING")
        if attributes is None:
            return
        ids: list[object] = []
        for index, item in enumerate(attributes):
            row = _as_mapping(item)
            if row is None:
                self.require(False, "LEXICON_ATTRIBUTE_MALFORMED")
                continue
            ids.append(row.get("attribute_id"))
            self.require(
                row.get("is_hedonic") is (index == len(_ATTRIBUTES) - 1),
                "LEXICON_HEDONIC_BOUNDARY_MISMATCH",
            )
            for key, expected in (
                ("low_anchor", "0"),
                ("mid_anchor", "5"),
                ("high_anchor", "10"),
            ):
                anchor = _as_mapping(row.get(key))
                self.require(
                    anchor is not None and anchor.get("value") == expected,
                    "LEXICON_ANCHOR_MISMATCH",
                )
        self.require(tuple(ids) == _ATTRIBUTES, "LEXICON_ATTRIBUTE_ORDER_MISMATCH")
        self.require(lexicon.get("claims_iso_compliance") is False, "ISO_COMPLIANCE_CLAIMED")

    def _validate_bundle(
        self,
        bundle: Mapping[str, Any],
        lexicon_hash: str,
        protocol: Mapping[str, Any],
    ) -> dict[str, str]:
        self.require(bundle.get("lexicon_sha256") == lexicon_hash, "BUNDLE_LEXICON_MISMATCH")
        manifests = _as_sequence(bundle.get("manifests"))
        self.require(manifests is not None, "PREPILOT_MANIFESTS_MISSING")
        hashes: dict[str, str] = {}
        if manifests is None:
            return hashes
        ids: list[object] = []
        for item in manifests:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "PREPILOT_MANIFEST_MALFORMED")
                continue
            binding_id = row.get("binding_id")
            ids.append(binding_id)
            payload = _as_mapping(row.get("payload"))
            self.require(payload is not None, "PREPILOT_PAYLOAD_MISSING")
            if payload is not None:
                self.require(row.get("payload_sha256") == _stable_hash(payload), "PREPILOT_PAYLOAD_HASH_MISMATCH")
            self.require(row.get("unresolved_items") == [], "PREPILOT_UNRESOLVED_ITEMS")
            self.require(row.get("review_state") == "lock_candidate", "PREPILOT_NOT_LOCK_CANDIDATE")
            self.require(_is_sha256(row.get("review_receipt_sha256")), "PREPILOT_REVIEW_HASH_INVALID")
            if isinstance(binding_id, str):
                hashes[binding_id] = _stable_hash(row)
        self.require(tuple(ids) == _MANIFEST_IDS, "PREPILOT_MANIFEST_ORDER_MISMATCH")
        bindings = _as_sequence(protocol.get("bindings"))
        if bindings is not None:
            binding_map = {
                row.get("binding_id"): row
                for item in bindings
                if (row := _as_mapping(item)) is not None
            }
            for binding_id, digest in hashes.items():
                row = _as_mapping(binding_map.get(binding_id))
                self.require(
                    row is not None
                    and row.get("state") == "bound"
                    and row.get("sha256") == digest
                    and row.get("reason") is None,
                    "PROTOCOL_BINDING_MISMATCH",
                )
        return hashes

    def _validate_native_protocol(
        self,
        protocol: Mapping[str, Any],
        lexicon_hash: str,
        manifest_hashes: Mapping[str, str],
    ) -> dict[str, str]:
        self.require(protocol.get("study_partition") == "pilot", "PROTOCOL_NOT_PILOT")
        self.require(protocol.get("protocol_locked") is True, "PROTOCOL_NOT_LOCKED")
        self.require(protocol.get("lexicon_sha256") == lexicon_hash, "PROTOCOL_LEXICON_MISMATCH")
        for key in (
            "blinded",
            "randomized",
            "individual_scores_preserved",
            "strata_analyzed_separately",
            "pilot_confirmatory_separated",
        ):
            self.require(protocol.get(key) is True, f"PROTOCOL_{key.upper()}_REQUIRED")
        self.require(
            tuple(protocol.get("expertise_strata", ()))
            == ("trained_descriptive", "untrained"),
            "PROTOCOL_STRATA_MISMATCH",
        )
        timepoints = protocol.get("timepoints_seconds")
        repeats = protocol.get("repeat_count")
        self.require(
            isinstance(timepoints, list)
            and bool(timepoints)
            and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in timepoints)
            and timepoints == sorted(set(timepoints)),
            "PROTOCOL_TIMEPOINTS_INVALID",
        )
        self.require(isinstance(repeats, int) and not isinstance(repeats, bool) and repeats >= 2, "PROTOCOL_REPEATS_INVALID")
        gates = _as_sequence(protocol.get("panel_gate_specs"))
        self.require(gates is not None, "PANEL_GATE_SPECS_MISSING")
        gate_hashes: dict[str, str] = {}
        if gates is not None:
            kinds: list[object] = []
            for item in gates:
                row = _as_mapping(item)
                if row is None:
                    self.require(False, "PANEL_GATE_SPEC_MALFORMED")
                    continue
                kind = row.get("kind")
                kinds.append(kind)
                self.require(row.get("authority") == "preregistered_locked", "GATE_NOT_PREREGISTERED")
                self.require(row.get("direction") in {"at_least", "at_most"}, "GATE_DIRECTION_INVALID")
                self.require(_decimal(row.get("threshold")) is not None, "GATE_THRESHOLD_INVALID")
                if isinstance(kind, str):
                    gate_hashes[kind] = _stable_hash(row)
            self.require(tuple(kinds) == _GATE_KINDS, "PANEL_GATE_ORDER_MISMATCH")
        bindings = _as_sequence(protocol.get("bindings"))
        self.require(bindings is not None and len(bindings) == len(_MANIFEST_IDS), "PROTOCOL_BINDING_SET_MISMATCH")
        if bindings is not None:
            ids_list: list[object] = []
            for item in bindings:
                row = _as_mapping(item)
                if row is not None:
                    ids_list.append(row.get("binding_id"))
            ids = tuple(ids_list)
            self.require(ids == _MANIFEST_IDS, "PROTOCOL_BINDING_ORDER_MISMATCH")
        return gate_hashes

    def _validate_qualifications(
        self,
        rows: Sequence[Any],
        protocol_hash: str,
    ) -> dict[str, str]:
        receipt_by_participant: dict[str, str] = {}
        strata: set[object] = set()
        for item in rows:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "QUALIFICATION_RECEIPT_MALFORMED")
                continue
            participant = row.get("participant_token_sha256")
            self.require(_is_sha256(participant), "QUALIFICATION_PARTICIPANT_HASH_INVALID")
            self.require(row.get("protocol_sha256") == protocol_hash, "QUALIFICATION_PROTOCOL_MISMATCH")
            self.require(participant not in receipt_by_participant, "QUALIFICATION_DUPLICATE_PARTICIPANT")
            if isinstance(participant, str):
                receipt_by_participant[participant] = _stable_hash(row)
            strata.add(row.get("expertise_stratum"))
        self.require(
            {"trained_descriptive", "untrained"}.issubset(strata),
            "QUALIFICATION_STRATA_INCOMPLETE",
        )
        return receipt_by_participant

    def _validate_expected_manifest(
        self,
        rows: Sequence[Any],
        protocol: Mapping[str, Any],
        qualifications: Mapping[str, str],
    ) -> None:
        timepoints = set(protocol.get("timepoints_seconds", ()))
        repeat_count = protocol.get("repeat_count")
        for item in rows:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "EXPECTED_CELL_MALFORMED")
                continue
            key = self._cell_key(row)
            self.require(key not in self.expected_cells, "EXPECTED_CELL_DUPLICATE")
            self.expected_cells.add(key)
            participant = row.get("participant_token_sha256")
            self.require(
                qualifications.get(str(participant)) == row.get("qualification_receipt_sha256"),
                "EXPECTED_CELL_QUALIFICATION_MISMATCH",
            )
            self.require(row.get("sniff_time_seconds") in timepoints, "EXPECTED_CELL_TIMEPOINT_MISMATCH")
            repeat = row.get("repeat_index")
            self.require(
                isinstance(repeat, int)
                and not isinstance(repeat, bool)
                and isinstance(repeat_count, int)
                and 1 <= repeat <= repeat_count,
                "EXPECTED_CELL_REPEAT_MISMATCH",
            )

    def _validate_readiness(self, readiness: Mapping[str, Any], bundle_hash: str) -> None:
        expected = {
            "decision": "bindable",
            "bundle_sha256": bundle_hash,
            "bindable_manifests": list(_MANIFEST_IDS),
            "held_manifests": [],
            "blockers": [],
            "bindable_for_protocol": True,
            "study_authorized": False,
            "release_authority": False,
            "model_calibration_authority": False,
        }
        self.require(dict(readiness) == expected, "PREPILOT_READINESS_SEMANTICS_MISMATCH")

    def _validate_artifact_registry(
        self,
        rows: Sequence[Any],
        envelope: Mapping[str, Any],
        protocol_hash: str,
        lexicon_hash: str,
        qualifications: Sequence[Any],
        gate_hashes: Mapping[str, str],
        manifest_hashes: Mapping[str, str],
    ) -> None:
        registry: dict[str, Mapping[str, Any]] = {}
        ids: list[object] = []
        for item in rows:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "ARTIFACT_RECEIPT_MALFORMED")
                continue
            artifact_id = row.get("artifact_id")
            ids.append(artifact_id)
            self.require(
                row.get("state") == "BOUND"
                and _is_sha256(row.get("artifact_sha256"))
                and row.get("unbound_reason") is None,
                "ARTIFACT_RECEIPT_NOT_BOUND",
            )
            if isinstance(artifact_id, str):
                registry[artifact_id] = row
        self.require(tuple(ids) == _ARTIFACT_IDS, "ARTIFACT_REGISTRY_ORDER_MISMATCH")
        native_protocol = _as_mapping(envelope.get("protocol"))
        expected = {
            "C0_PREPILOT_PROTOCOL": protocol_hash,
            "LEXICON": lexicon_hash,
            "ATTRIBUTE_ANCHOR_CANDIDATES": manifest_hashes.get("anchor_reference_manifest"),
            "SAMPLE_PREPARATION_MANIFEST": manifest_hashes.get("preparation_dose_ppm_manifest"),
            "SAFETY_ETHICS_PRIVACY_HOLD": manifest_hashes.get("ethics_privacy_safety_review"),
            "PARTICIPANT_QUALIFICATION": _stable_hash(qualifications),
            "ENVIRONMENT_TIMING": manifest_hashes.get("environment_timing_manifest"),
            "RANDOMIZATION_LEDGER": manifest_hashes.get("randomization_manifest"),
            "BLIND_CODE_KEY": manifest_hashes.get("sample_manifest"),
            "ANALYSIS_PLAN": manifest_hashes.get("analysis_plan"),
            "STOP_GO_GATES": _stable_hash(
                native_protocol.get("panel_gate_specs")
                if native_protocol is not None
                else []
            ),
            "SOURCE_MANIFEST": envelope.get("source_payload_sha256"),
        }
        for artifact_id, expected_hash in expected.items():
            row = registry.get(artifact_id)
            self.require(
                row is not None and row.get("artifact_sha256") == expected_hash,
                f"ARTIFACT_HASH_MISMATCH:{artifact_id}",
            )
        for artifact_id in _OPAQUE_ARTIFACT_IDS:
            row = registry.get(artifact_id)
            self.require(row is not None and _is_sha256(row.get("artifact_sha256")), f"OPAQUE_ARTIFACT_HASH_INVALID:{artifact_id}")
        self.require(set(gate_hashes) == set(_GATE_KINDS), "GATE_HASH_SET_INCOMPLETE")

    @staticmethod
    def _cell_key(row: Mapping[str, Any]) -> tuple[object, ...]:
        return (
            row.get("blind_code"),
            row.get("participant_token_sha256"),
            row.get("session_token_sha256"),
            row.get("repeat_index"),
            row.get("sniff_time_seconds"),
        )

    @staticmethod
    def _application_key(row: Mapping[str, Any]) -> tuple[object, ...]:
        return (
            row.get("blind_code"),
            row.get("participant_token_sha256"),
            row.get("session_token_sha256"),
            row.get("repeat_index"),
        )

    def _validate_applications(
        self,
        envelope: Mapping[str, Any],
        rows: Sequence[Any],
    ) -> None:
        protocol_hash = envelope.get("protocol_sha256")
        expected_rows = _as_sequence(envelope.get("expected_observation_manifest")) or ()
        expected_groups: dict[tuple[object, ...], list[int]] = {}
        qualification_by_group: dict[tuple[object, ...], object] = {}
        for item in expected_rows:
            cell = _as_mapping(item)
            if cell is None:
                continue
            key = self._application_key(cell)
            timepoint = cell.get("sniff_time_seconds")
            if isinstance(timepoint, int) and not isinstance(timepoint, bool):
                expected_groups.setdefault(key, []).append(timepoint)
            else:
                self.require(False, "EXPECTED_CELL_TIMEPOINT_MISMATCH")
            qualification_by_group[key] = cell.get("qualification_receipt_sha256")
        bundle = _as_mapping(envelope.get("prepilot_bundle"))
        manifests = _as_sequence(bundle.get("manifests")) if bundle is not None else None
        manifest_by_id = {
            row.get("binding_id"): row
            for item in (manifests or ())
            if (row := _as_mapping(item)) is not None
        }
        preparation = _as_mapping(manifest_by_id.get("preparation_dose_ppm_manifest"))
        seen: set[tuple[object, ...]] = set()
        for item in rows:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "APPLICATION_RECORD_MALFORMED")
                continue
            context = _as_mapping(row.get("context_json"))
            dose = _as_mapping(row.get("dose_json"))
            self.require(context is not None and dose is not None, "APPLICATION_PAYLOAD_MISSING")
            if context is None or dose is None:
                continue
            key = self._application_key(context)
            self.require(key not in seen, "APPLICATION_DUPLICATE")
            seen.add(key)
            key_payload = {
                "blind_code": key[0],
                "participant_token_sha256": key[1],
                "session_token_sha256": key[2],
                "repeat_index": key[3],
            }
            self.require(row.get("application_key_sha256") == _stable_hash(key_payload), "APPLICATION_KEY_HASH_MISMATCH")
            self.require(row.get("blind_code") == key[0], "APPLICATION_BLIND_CODE_MISMATCH")
            self.require(context.get("protocol_sha256") == protocol_hash, "APPLICATION_PROTOCOL_MISMATCH")
            self.require(context.get("qualification_receipt_sha256") == qualification_by_group.get(key), "APPLICATION_QUALIFICATION_MISMATCH")
            self.require(context.get("expected_timepoints_seconds") == sorted(expected_groups.get(key, [])), "APPLICATION_TIMEPOINT_SET_MISMATCH")
            if preparation is not None:
                self.require(dose.get("preparation_manifest") == preparation.get("payload"), "APPLICATION_DOSE_PAYLOAD_MISMATCH")
                self.require(dose.get("preparation_manifest_sha256") == _stable_hash(preparation), "APPLICATION_DOSE_HASH_MISMATCH")
        self.require(seen == set(expected_groups), "APPLICATION_COVERAGE_MISMATCH")

    def _validate_observations(
        self,
        envelope: Mapping[str, Any],
        rows: Sequence[Any],
    ) -> None:
        protocol = _as_mapping(envelope.get("protocol"))
        allowed_timepoints = set(protocol.get("timepoints_seconds", ())) if protocol else set()
        repeat_count = protocol.get("repeat_count") if protocol else None
        qualifications = _as_sequence(envelope.get("participant_qualification_receipts")) or ()
        qualification_hashes = {
            row.get("participant_token_sha256"): _stable_hash(row)
            for item in qualifications
            if (row := _as_mapping(item)) is not None
        }
        valid_application_hashes = {
            item.get("application_key_sha256")
            for raw in (_as_sequence(self.graph.get("application_records")) or ())
            if (item := _as_mapping(raw)) is not None
        }
        for item in rows:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "OBSERVATION_RECORD_MALFORMED")
                continue
            payload = _as_mapping(row.get("observations_json"))
            observation = _as_mapping(payload.get("panel_observation")) if payload is not None else None
            self.require(payload is not None and observation is not None, "PANEL_OBSERVATION_MISSING")
            if payload is None or observation is None:
                continue
            key = self._cell_key(observation)
            self.require(key not in self.observed_cells, "OBSERVATION_CELL_DUPLICATE")
            self.observed_cells.add(key)
            self.require(row.get("application_key_sha256") in valid_application_hashes, "OBSERVATION_APPLICATION_MISMATCH")
            self.require(row.get("elapsed_seconds") == observation.get("sniff_time_seconds"), "OBSERVATION_TIMEPOINT_MISMATCH")
            self.require(payload.get("panel_observation_sha256") == _stable_hash(observation), "OBSERVATION_NESTED_HASH_MISMATCH")
            self.require(observation.get("protocol_sha256") == envelope.get("protocol_sha256"), "OBSERVATION_PROTOCOL_MISMATCH")
            self.require(observation.get("lexicon_sha256") == envelope.get("lexicon_sha256"), "OBSERVATION_LEXICON_MISMATCH")
            self.require(
                observation.get("sniff_time_seconds") in allowed_timepoints,
                "OBSERVATION_TIMEPOINT_OUTSIDE_PROTOCOL",
            )
            repeat = observation.get("repeat_index")
            self.require(
                isinstance(repeat, int)
                and not isinstance(repeat, bool)
                and isinstance(repeat_count, int)
                and 1 <= repeat <= repeat_count,
                "OBSERVATION_REPEAT_OUTSIDE_PROTOCOL",
            )
            participant = observation.get("participant_token_sha256")
            self.require(observation.get("qualification_receipt_sha256") == qualification_hashes.get(participant), "OBSERVATION_QUALIFICATION_MISMATCH")
            ratings = _as_sequence(observation.get("ratings"))
            self.require(ratings is not None, "OBSERVATION_RATINGS_MISSING")
            if ratings is not None:
                ids: list[object] = []
                for rating_item in ratings:
                    rating = _as_mapping(rating_item)
                    if rating is None:
                        self.require(False, "OBSERVATION_RATING_MALFORMED")
                        continue
                    ids.append(rating.get("attribute_id"))
                    value = rating.get("value")
                    if value is None:
                        self.require(bool(str(rating.get("not_applicable_reason", "")).strip()), "OBSERVATION_MISSING_REASON")
                    else:
                        parsed = _decimal(value)
                        self.require(parsed is not None and Decimal("0") <= parsed <= Decimal("10"), "OBSERVATION_RATING_OUT_OF_RANGE")
                        self.require(rating.get("not_applicable_reason") is None, "OBSERVATION_RATED_WITH_MISSING_REASON")
                self.require(tuple(ids) == _ATTRIBUTES, "OBSERVATION_ATTRIBUTE_ORDER_MISMATCH")
        missing = self.expected_cells - self.observed_cells
        unexpected = self.observed_cells - self.expected_cells
        self.require(not missing, f"OBSERVATION_CELLS_MISSING:{len(missing)}")
        self.require(not unexpected, f"OBSERVATION_CELLS_UNEXPECTED:{len(unexpected)}")

    def _validate_outcome(
        self,
        envelope: Mapping[str, Any],
        outcome: Mapping[str, Any],
    ) -> None:
        self.require(outcome.get("schema_version") == "perfume-chem.c0-lab-outcome-projection.v1", "OUTCOME_SCHEMA_MISMATCH")
        self.require(outcome.get("protocol_sha256") == envelope.get("protocol_sha256"), "OUTCOME_PROTOCOL_MISMATCH")
        results = _as_sequence(outcome.get("panel_performance_results"))
        exit_report = _as_mapping(outcome.get("c0_exit_report"))
        self.require(results is not None, "PERFORMANCE_RESULTS_MISSING")
        self.require(exit_report is not None, "EXIT_REPORT_MISSING")
        if results is None or exit_report is None:
            return
        self.require(outcome.get("panel_performance_results_sha256") == _stable_hash(results), "PERFORMANCE_RESULTS_HASH_MISMATCH")
        self.require(outcome.get("c0_exit_report_sha256") == _stable_hash(exit_report), "EXIT_REPORT_HASH_MISMATCH")
        registry_rows = _as_sequence(envelope.get("artifact_registry")) or ()
        registry = {
            row.get("artifact_id"): row
            for item in registry_rows
            if (row := _as_mapping(item)) is not None
        }
        results_receipt = _as_mapping(registry.get("RESULTS_RECEIPT"))
        decision_receipt = _as_mapping(registry.get("DECISION_RECORD"))
        self.require(
            results_receipt is not None
            and results_receipt.get("artifact_sha256") == _stable_hash(results),
            "ARTIFACT_HASH_MISMATCH:RESULTS_RECEIPT",
        )
        self.require(
            decision_receipt is not None
            and decision_receipt.get("artifact_sha256") == _stable_hash(exit_report),
            "ARTIFACT_HASH_MISMATCH:DECISION_RECORD",
        )
        protocol = _as_mapping(envelope.get("protocol"))
        gates = _as_sequence(protocol.get("panel_gate_specs")) if protocol is not None else None
        gate_by_kind = {
            row.get("kind"): row
            for item in (gates or ())
            if (row := _as_mapping(item)) is not None
        }
        outcomes: dict[str, str] = {}
        participant_set_hashes: set[object] = set()
        analysis_hash = None
        if protocol is not None:
            bindings = _as_sequence(protocol.get("bindings")) or ()
            for item in bindings:
                row = _as_mapping(item)
                if row is not None and row.get("binding_id") == "analysis_plan":
                    analysis_hash = row.get("sha256")
        kinds: list[object] = []
        for item in results:
            row = _as_mapping(item)
            if row is None:
                self.require(False, "PERFORMANCE_RESULT_MALFORMED")
                continue
            kind = row.get("gate_kind")
            kinds.append(kind)
            gate = _as_mapping(gate_by_kind.get(kind))
            self.require(gate is not None and row.get("gate_spec_sha256") == _stable_hash(gate), "PERFORMANCE_GATE_BINDING_MISMATCH")
            self.require(row.get("analysis_plan_sha256") == analysis_hash, "PERFORMANCE_ANALYSIS_PLAN_MISMATCH")
            self.require(row.get("study_partition") == "pilot", "PERFORMANCE_PARTITION_MISMATCH")
            self.require(_is_sha256(row.get("result_receipt_sha256")), "PERFORMANCE_RECEIPT_HASH_INVALID")
            self.require(_is_sha256(row.get("participant_set_sha256")), "PERFORMANCE_PARTICIPANT_SET_HASH_INVALID")
            participant_set_hashes.add(row.get("participant_set_sha256"))
            result = row.get("outcome")
            if isinstance(kind, str) and isinstance(result, str):
                outcomes[kind] = result
            if gate is not None:
                observed = _decimal(row.get("observed_value"))
                threshold = _decimal(gate.get("threshold"))
                direction = gate.get("direction")
                if result == "unmeasured":
                    self.require(row.get("observed_value") is None, "UNMEASURED_RESULT_HAS_VALUE")
                elif observed is None or threshold is None:
                    self.require(False, "MEASURED_RESULT_VALUE_INVALID")
                else:
                    met = observed >= threshold if direction == "at_least" else observed <= threshold
                    self.require(result == ("pass" if met else "fail"), "PERFORMANCE_OUTCOME_MISMATCH")
        self.require(tuple(kinds) == _GATE_KINDS, "PERFORMANCE_GATE_ORDER_MISMATCH")
        self.require(len(participant_set_hashes) == 1, "PERFORMANCE_PARTICIPANT_SET_MISMATCH")
        passed = [kind for kind in _GATE_KINDS if outcomes.get(kind) == "pass"]
        failed = [kind for kind in _GATE_KINDS if outcomes.get(kind) == "fail"]
        inconclusive = [kind for kind in _GATE_KINDS if outcomes.get(kind) not in {"pass", "fail"}]
        expected_exit = {
            "decision": "go" if len(passed) == len(_GATE_KINDS) else ("stop" if failed else "hold"),
            "protocol_sha256": envelope.get("protocol_sha256"),
            "lexicon_sha256": envelope.get("lexicon_sha256"),
            "passed_gates": passed,
            "failed_gates": failed,
            "inconclusive_gates": inconclusive,
            "blockers": [],
            "c0_exit_satisfied": len(passed) == len(_GATE_KINDS),
            "study_authorized": False,
            "release_authority": False,
            "model_calibration_authority": False,
        }
        self.require(dict(exit_report) == expected_exit, "EXIT_REPORT_SEMANTICS_MISMATCH")


def revalidate_c0_lab_persistence_graph(
    graph: Mapping[str, Any],
) -> C0SemanticReadbackReceipt:
    """Return PASS only for an exact, authority-false semantic replay."""

    try:
        canonical_graph = json.loads(_canonical_json(graph))
    except (TypeError, ValueError, OverflowError) as error:
        fallback_hash = hashlib.sha256(repr(graph).encode("utf-8")).hexdigest()
        return C0SemanticReadbackReceipt(
            state=C0SemanticReadbackState.HOLD,
            graph_sha256=fallback_hash,
            protocol_sha256=None,
            application_set_sha256=None,
            observation_set_sha256=None,
            outcome_sha256=None,
            expected_cell_count=0,
            observed_cell_count=0,
            blockers=(f"GRAPH_NOT_CANONICAL_JSON:{type(error).__name__}",),
            semantic_revalidation_passed=False,
        )
    if not isinstance(canonical_graph, dict):
        canonical_graph = {"invalid_graph": canonical_graph}
    validator = _Validator(canonical_graph)
    validator.validate()
    protocol = _as_mapping(canonical_graph.get("experiment_protocol"))
    applications = _as_sequence(canonical_graph.get("application_records"))
    observations = _as_sequence(canonical_graph.get("observation_records"))
    outcome = _as_mapping(canonical_graph.get("outcome"))
    blockers = tuple(sorted(set(validator.errors)))
    return C0SemanticReadbackReceipt(
        state=(C0SemanticReadbackState.HOLD if blockers else C0SemanticReadbackState.PASS),
        graph_sha256=_stable_hash(canonical_graph),
        protocol_sha256=(
            str(protocol.get("protocol_sha256")) if protocol is not None else None
        ),
        application_set_sha256=_stable_hash(applications) if applications is not None else None,
        observation_set_sha256=_stable_hash(observations) if observations is not None else None,
        outcome_sha256=_stable_hash(outcome) if outcome is not None else None,
        expected_cell_count=len(validator.expected_cells),
        observed_cell_count=len(validator.observed_cells),
        blockers=blockers,
        semantic_revalidation_passed=not blockers,
    )


__all__ = [
    "C0SemanticReadbackReceipt",
    "C0SemanticReadbackState",
    "revalidate_c0_lab_persistence_graph",
]
