"""Planning-only C0 prepilot manifest validation.

The sensory panel contract binds nine hashes.  This module validates the
minimum content and review receipts behind those hashes before they may become
``EvidenceBinding`` objects.  It does not select physical materials, calculate
doses, choose statistical thresholds, authorize a study, or lock a protocol.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Mapping

from engine.calibration.hashing import canonical_json_bytes, stable_json_hash
from engine.sensory.panel_contract import (
    CONSTRUCTION_ATTRIBUTE_IDS,
    HEDONIC_ATTRIBUTE_IDS,
    REQUIRED_BINDING_IDS,
    ConstructionLexicon,
    ConstructionPanelProtocol,
    EvidenceBinding,
    GateKind,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,95}$")
_FORBIDDEN_PARTICIPANT_KEY_TOKENS = {
    "address",
    "assessorname",
    "assessors",
    "birthdate",
    "consentdocument",
    "dateofbirth",
    "deviceid",
    "dob",
    "email",
    "emailaddress",
    "familyname",
    "firstname",
    "fullname",
    "givenname",
    "healthrecord",
    "homeaddress",
    "ipaddress",
    "lastname",
    "medicalrecord",
    "mobile",
    "mobilenumber",
    "panelistname",
    "panelists",
    "participantname",
    "participants",
    "phone",
    "phonenumber",
    "postaladdress",
    "rawscreeningresponse",
    "screeningresponses",
}

_CONSTRUCTION_ANCHOR_MODES = {
    "airiness": "graded_sample_set",
    "separability": "graded_sample_set",
    "density": "graded_sample_set",
    "coherence": "graded_sample_set",
    "target_fidelity": "target_reference_task",
    "contrast": "graded_sample_set",
    "emergence": "component_mixture_comparison",
    "recognition": "blind_target_choice",
}

REQUIRED_MANIFEST_FIELDS: dict[str, tuple[str, ...]] = {
    "sample_manifest": (
        "blind_code_scheme.format",
        "blind_code_scheme.length",
        "custodian_role",
        "sample_identity_map_receipt_sha256",
        "allocation_concealment",
        "code_collision_check",
    ),
    "preparation_dose_ppm_manifest": (
        "matrix_id",
        "concentrate_ppm",
        "active_application_mass_mg",
        "substrate",
        "carrier_id",
        "preparation_sop_sha256",
        "dose_tolerance_fraction",
    ),
    "formula_oav_manifest": (
        "formula_manifest_sha256",
        "odt_dataset_sha256",
        "oav_report_sha256",
        "natural_mixture_oav_policy",
        "time_windows_seconds",
        "data_quality_review_receipt_sha256",
    ),
    "randomization_manifest": (
        "sequence_method",
        "seed_commitment_sha256",
        "allocation_receipt_sha256",
        "carryover_rule",
        "blinding_roles",
    ),
    "anchor_reference_manifest": (
        "lexicon_sha256",
        "attribute_anchors",
        "reference_preparation_sop_sha256",
    ),
    "participant_plan": (
        "expertise_strata",
        "eligibility_rules_sha256",
        "olfactory_screening_plan_sha256",
        "specific_anosmia_policy",
        "training_plan_sha256",
        "repeat_plan.repeats_per_sample",
        "attrition_rule",
        "privacy_separation_receipt_sha256",
        "qualification_receipt_schema_sha256",
    ),
    "environment_timing_manifest": (
        "room_sop_sha256",
        "temperature_c_range",
        "relative_humidity_pct_range",
        "ventilation_rule",
        "session_duration_limit_minutes",
        "sniff_timepoints_seconds",
        "rest_interval_seconds",
        "confounder_rules_sha256",
    ),
    "analysis_plan": (
        "estimands",
        "missing_data_rule",
        "multiplicity_rule",
        "uncertainty_method",
        "gate_specification_receipts",
        "pilot_confirmatory_separation",
        "analysis_implementation_receipt_sha256",
    ),
    "ethics_privacy_safety_review": (
        "applicability_determination_receipt_sha256",
        "consent_plan_sha256",
        "privacy_plan_sha256",
        "exposure_safety_review_sha256",
        "withdrawal_process",
        "adverse_event_process",
        "review_jurisdiction",
    ),
}


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    if value != value.strip():
        raise ValueError(f"{field_name} must not contain surrounding whitespace")


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase stable identifier")


def _require_sha256(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")


def _value_at_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return True


def _walk_mapping(value: Any, prefix: str = "") -> tuple[tuple[str, Any], ...]:
    found: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.append((path, child))
            found.extend(_walk_mapping(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_mapping(child, f"{prefix}[{index}]"))
    return tuple(found)


def _range_errors(
    value: Any,
    field_name: str,
    *,
    minimum: float,
    maximum: float,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        return (f"{field_name} must contain two numeric bounds",)
    low, high = (float(value[0]), float(value[1]))
    if low < minimum or high > maximum or low > high:
        return (
            f"{field_name} must be increasing within {minimum:g}-{maximum:g}",
        )
    return ()


class ManifestReviewState(str, Enum):
    DRAFT = "draft"
    TECHNICAL_REVIEWED = "technical_reviewed"
    LOCK_CANDIDATE = "lock_candidate"


class PrepilotDecision(str, Enum):
    HOLD = "hold"
    BINDABLE = "bindable"


@dataclass(frozen=True, slots=True)
class PrepilotManifest:
    """Immutable canonical payload plus non-authorizing review receipts."""

    binding_id: str
    schema_version: str
    payload_json: str
    unresolved_items: tuple[str, ...]
    review_state: ManifestReviewState
    review_receipt_sha256: str | None
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    model_calibration_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_identifier(self.binding_id, "binding_id")
        if self.binding_id not in REQUIRED_BINDING_IDS:
            raise ValueError("binding_id is not part of the C0 panel contract")
        _require_text(self.schema_version, "schema_version")
        if not isinstance(self.review_state, ManifestReviewState):
            raise ValueError("review_state must be a ManifestReviewState")
        try:
            parsed = json.loads(self.payload_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("payload_json must contain valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValueError("prepilot manifest payload must be a JSON object")
        canonical = canonical_json_bytes(parsed).decode("utf-8")
        object.__setattr__(self, "payload_json", canonical)
        if len(self.unresolved_items) != len(set(self.unresolved_items)):
            raise ValueError("unresolved_items must be unique")
        for item in self.unresolved_items:
            _require_text(item, "unresolved item")
        if self.review_state is ManifestReviewState.DRAFT:
            if self.review_receipt_sha256 is not None:
                raise ValueError("draft manifest cannot carry a review receipt")
        else:
            if self.review_receipt_sha256 is None:
                raise ValueError("reviewed manifest requires a review receipt")
            _require_sha256(
                self.review_receipt_sha256, "review_receipt_sha256"
            )
        forbidden_paths = tuple(
            path
            for path, _ in _walk_mapping(parsed)
            if re.sub(
                r"[^a-z0-9]",
                "",
                path.rsplit(".", 1)[-1].casefold(),
            )
            in _FORBIDDEN_PARTICIPANT_KEY_TOKENS
        )
        if forbidden_paths:
            raise ValueError(
                "raw participant data is prohibited in prepilot manifests: "
                + ", ".join(forbidden_paths)
            )

    @classmethod
    def from_payload(
        cls,
        *,
        binding_id: str,
        schema_version: str,
        payload: Mapping[str, Any],
        unresolved_items: tuple[str, ...],
        review_state: ManifestReviewState,
        review_receipt_sha256: str | None,
    ) -> PrepilotManifest:
        return cls(
            binding_id=binding_id,
            schema_version=schema_version,
            payload_json=canonical_json_bytes(payload).decode("utf-8"),
            unresolved_items=unresolved_items,
            review_state=review_state,
            review_receipt_sha256=review_receipt_sha256,
        )

    @property
    def payload(self) -> dict[str, Any]:
        parsed = json.loads(self.payload_json)
        if not isinstance(parsed, dict):  # pragma: no cover - protected by __post_init__
            raise TypeError("canonical manifest payload is not an object")
        return parsed

    @property
    def payload_sha256(self) -> str:
        return stable_json_hash(self.payload)

    @property
    def missing_required_fields(self) -> tuple[str, ...]:
        payload = self.payload
        return tuple(
            path
            for path in REQUIRED_MANIFEST_FIELDS[self.binding_id]
            if not _has_value(_value_at_path(payload, path))
        )

    @property
    def validation_errors(self) -> tuple[str, ...]:
        errors = [
            f"missing required field '{path}'"
            for path in self.missing_required_fields
        ]
        errors.extend(f"unresolved item: {item}" for item in self.unresolved_items)
        if self.review_state is not ManifestReviewState.LOCK_CANDIDATE:
            errors.append("review state is not lock_candidate")
        errors.extend(_invalid_sha_paths(self.payload))
        errors.extend(_semantic_errors(self.binding_id, self.payload))
        return tuple(errors)

    @property
    def is_bindable(self) -> bool:
        return not self.validation_errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "schema_version": self.schema_version,
            "payload": self.payload,
            "payload_sha256": self.payload_sha256,
            "unresolved_items": list(self.unresolved_items),
            "review_state": self.review_state.value,
            "review_receipt_sha256": self.review_receipt_sha256,
            "study_authorized": self.study_authorized,
            "release_authority": self.release_authority,
            "model_calibration_authority": self.model_calibration_authority,
        }

    @property
    def manifest_sha256(self) -> str:
        return stable_json_hash(self.as_dict())

    def to_evidence_binding(self) -> EvidenceBinding:
        if not self.is_bindable:
            raise ValueError(
                f"manifest '{self.binding_id}' is not bindable: "
                + "; ".join(self.validation_errors)
            )
        return EvidenceBinding.bound(self.binding_id, self.manifest_sha256)


def _invalid_sha_paths(payload: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        f"'{path}' must be a lowercase SHA-256 digest"
        for path, value in _walk_mapping(payload)
        if path.rsplit(".", 1)[-1].endswith("_sha256")
        and value is not None
        and (not isinstance(value, str) or not _SHA256_RE.fullmatch(value))
    )


def _semantic_errors(binding_id: str, payload: Mapping[str, Any]) -> tuple[str, ...]:
    validators = {
        "sample_manifest": _sample_errors,
        "preparation_dose_ppm_manifest": _preparation_errors,
        "formula_oav_manifest": _formula_oav_errors,
        "randomization_manifest": _randomization_errors,
        "anchor_reference_manifest": _anchor_errors,
        "participant_plan": _participant_errors,
        "environment_timing_manifest": _environment_errors,
        "analysis_plan": _analysis_errors,
        "ethics_privacy_safety_review": lambda _: (),
    }
    return validators[binding_id](payload)


def _sample_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    length = _value_at_path(payload, "blind_code_scheme.length")
    if length is None:
        return ()
    if isinstance(length, bool) or not isinstance(length, int) or not 3 <= length <= 12:
        return ("blind-code length must be an integer from 3 through 12",)
    return ()


def _preparation_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    for path, maximum in (
        ("concentrate_ppm", 1_000_000.0),
        ("active_application_mass_mg", float("inf")),
    ):
        value = _value_at_path(payload, path)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or float(value) <= 0
            or float(value) > maximum
        ):
            errors.append(f"{path} must be positive and physically bounded")
    tolerance = _value_at_path(payload, "dose_tolerance_fraction")
    if tolerance is not None and (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not 0 < float(tolerance) <= 1
    ):
        errors.append("dose_tolerance_fraction must be greater than 0 and at most 1")
    return tuple(errors)


def _formula_oav_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    policy = payload.get("natural_mixture_oav_policy")
    if policy is not None and policy not in {
        "applied_composite_oav",
        "not_applicable_no_natural_mixtures",
    }:
        errors.append(
            "natural-mixture policy must apply composite OAV or document that "
            "no natural mixtures are present"
        )
    windows = payload.get("time_windows_seconds")
    if windows is not None and not _valid_timepoints(windows):
        errors.append("OAV time windows must be unique increasing non-negative integers")
    return tuple(errors)


def _randomization_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    roles = payload.get("blinding_roles")
    if roles is None:
        return ()
    if (
        not isinstance(roles, list)
        or not roles
        or any(not isinstance(item, str) or not item.strip() for item in roles)
    ):
        return ("blinding_roles must be a non-empty list of role identifiers",)
    return ()


def _anchor_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    anchors = payload.get("attribute_anchors")
    if anchors is None:
        return ()
    if not isinstance(anchors, Mapping):
        return ("attribute_anchors must be an object",)
    expected = (*CONSTRUCTION_ATTRIBUTE_IDS, *HEDONIC_ATTRIBUTE_IDS)
    if set(anchors) != set(expected) or len(anchors) != len(expected):
        return ("anchor manifest must cover every lexicon attribute exactly once",)
    errors: list[str] = []
    for attribute_id in CONSTRUCTION_ATTRIBUTE_IDS:
        entry = anchors.get(attribute_id)
        if not isinstance(entry, Mapping):
            errors.append(f"{attribute_id} anchor entry must be an object")
            continue
        expected_mode = _CONSTRUCTION_ANCHOR_MODES[attribute_id]
        if entry.get("anchor_mode") != expected_mode:
            errors.append(
                f"{attribute_id} must use frozen reference mode '{expected_mode}'"
            )
        if entry.get("training_reference_permitted") is not True:
            errors.append(f"{attribute_id} must permit its construction reference")
        for level in ("low", "mid", "high"):
            value = entry.get(f"{level}_reference_receipt_sha256")
            if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
                errors.append(f"{attribute_id} {level} reference receipt is invalid")
    pleasantness = anchors.get("pleasantness")
    if not isinstance(pleasantness, Mapping):
        errors.append("pleasantness anchor entry must be an object")
    else:
        if pleasantness.get("anchor_mode") != "verbal_scale_only":
            errors.append("pleasantness must use verbal_scale_only anchors")
        if pleasantness.get("training_reference_permitted") is not False:
            errors.append("pleasantness cannot use training reference samples")
        if any(
            pleasantness.get(f"{level}_reference_receipt_sha256") is not None
            for level in ("low", "mid", "high")
        ):
            errors.append("pleasantness cannot bind physical reference receipts")
    return tuple(errors)


def _participant_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    strata = payload.get("expertise_strata")
    if strata is not None:
        if (
            not isinstance(strata, list)
            or not strata
            or any(not isinstance(item, str) or not item.strip() for item in strata)
        ):
            errors.append("expertise_strata must be a non-empty unique string list")
        elif len(strata) != len(set(strata)):
            errors.append("expertise_strata must be a non-empty unique string list")
        elif not {"trained_descriptive", "untrained"}.issubset(set(strata)):
            errors.append("trained_descriptive and untrained strata must remain distinct")
    repeats = _value_at_path(payload, "repeat_plan.repeats_per_sample")
    if repeats is not None and (
        isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 2
    ):
        errors.append("repeats_per_sample must be an integer of at least 2")
    return tuple(errors)


def _valid_timepoints(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(
            not isinstance(item, bool) and isinstance(item, int) and item >= 0
            for item in value
        )
        and value == sorted(set(value))
    )


def _environment_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors = list(
        _range_errors(
            payload.get("temperature_c_range"),
            "temperature_c_range",
            minimum=0,
            maximum=50,
        )
        if payload.get("temperature_c_range") is not None
        else ()
    )
    if payload.get("relative_humidity_pct_range") is not None:
        errors.extend(
            _range_errors(
                payload.get("relative_humidity_pct_range"),
                "relative_humidity_pct_range",
                minimum=0,
                maximum=100,
            )
        )
    timepoints = payload.get("sniff_timepoints_seconds")
    if timepoints is not None and not _valid_timepoints(timepoints):
        errors.append("sniff timepoints must be unique increasing non-negative integers")
    for field_name in ("session_duration_limit_minutes", "rest_interval_seconds"):
        value = payload.get(field_name)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or float(value) < 0
            or (field_name == "session_duration_limit_minutes" and float(value) == 0)
        ):
            errors.append(f"{field_name} must be non-negative and meaningful")
    return tuple(errors)


def _analysis_errors(payload: Mapping[str, Any]) -> tuple[str, ...]:
    errors: list[str] = []
    receipts = payload.get("gate_specification_receipts")
    if receipts is not None:
        expected = tuple(kind.value for kind in GateKind)
        if (
            not isinstance(receipts, Mapping)
            or set(receipts) != set(expected)
            or len(receipts) != len(expected)
        ):
            errors.append(
                "gate specification receipts must cover discrimination, agreement, "
                "and repeatability exactly once"
            )
        else:
            for gate_id in expected:
                receipt = receipts.get(gate_id)
                if not isinstance(receipt, str) or not _SHA256_RE.fullmatch(receipt):
                    errors.append(
                        f"{gate_id} gate specification receipt must be a "
                        "lowercase SHA-256 digest"
                    )
    separation = payload.get("pilot_confirmatory_separation")
    if separation is not None and separation is not True:
        errors.append("pilot and confirmatory evidence must remain separate")
    return tuple(errors)


@dataclass(frozen=True, slots=True)
class PrepilotReadinessReport:
    decision: PrepilotDecision
    bundle_sha256: str
    bindable_manifests: tuple[str, ...]
    held_manifests: tuple[str, ...]
    blockers: tuple[str, ...]
    bindable_for_protocol: bool
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    model_calibration_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "bundle_sha256": self.bundle_sha256,
            "bindable_manifests": list(self.bindable_manifests),
            "held_manifests": list(self.held_manifests),
            "blockers": list(self.blockers),
            "bindable_for_protocol": self.bindable_for_protocol,
            "study_authorized": self.study_authorized,
            "release_authority": self.release_authority,
            "model_calibration_authority": self.model_calibration_authority,
        }


@dataclass(frozen=True, slots=True)
class C0PrepilotBundle:
    schema_version: str
    version: int
    lexicon_sha256: str
    base_protocol_sha256: str
    manifests: tuple[PrepilotManifest, ...]
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    model_calibration_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise ValueError("version must be a positive integer")
        if self.version <= 0:
            raise ValueError("version must be a positive integer")
        _require_sha256(self.lexicon_sha256, "lexicon_sha256")
        _require_sha256(self.base_protocol_sha256, "base_protocol_sha256")
        binding_ids = tuple(item.binding_id for item in self.manifests)
        if binding_ids != REQUIRED_BINDING_IDS:
            raise ValueError("prepilot bundle must contain all nine manifests in order")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "lexicon_sha256": self.lexicon_sha256,
            "base_protocol_sha256": self.base_protocol_sha256,
            "manifests": [item.as_dict() for item in self.manifests],
            "study_authorized": self.study_authorized,
            "release_authority": self.release_authority,
            "model_calibration_authority": self.model_calibration_authority,
        }

    @property
    def bundle_sha256(self) -> str:
        return stable_json_hash(self.as_dict())

    def readiness(self) -> PrepilotReadinessReport:
        blockers: list[str] = []
        bindable: list[str] = []
        held: list[str] = []
        payload_by_id = {
            manifest.binding_id: manifest.payload for manifest in self.manifests
        }
        for manifest in self.manifests:
            manifest_errors = list(manifest.validation_errors)
            if manifest.binding_id == "anchor_reference_manifest":
                anchor_lexicon = manifest.payload.get("lexicon_sha256")
                if anchor_lexicon != self.lexicon_sha256:
                    manifest_errors.append(
                        "anchor lexicon hash does not match the bundle"
                    )
            if manifest.binding_id == "formula_oav_manifest":
                oav_windows = manifest.payload.get("time_windows_seconds")
                sniff_timepoints = payload_by_id["environment_timing_manifest"].get(
                    "sniff_timepoints_seconds"
                )
                if (
                    _valid_timepoints(oav_windows)
                    and _valid_timepoints(sniff_timepoints)
                    and not set(sniff_timepoints).issubset(set(oav_windows))
                ):
                    manifest_errors.append(
                        "OAV time windows must cover every sensory sniff timepoint"
                    )
            if manifest_errors:
                held.append(manifest.binding_id)
                blockers.extend(
                    f"{manifest.binding_id}: {error}" for error in manifest_errors
                )
            else:
                bindable.append(manifest.binding_id)
        bindable_for_protocol = not blockers and tuple(bindable) == REQUIRED_BINDING_IDS
        return PrepilotReadinessReport(
            decision=(
                PrepilotDecision.BINDABLE
                if bindable_for_protocol
                else PrepilotDecision.HOLD
            ),
            bundle_sha256=self.bundle_sha256,
            bindable_manifests=tuple(bindable),
            held_manifests=tuple(held),
            blockers=tuple(blockers),
            bindable_for_protocol=bindable_for_protocol,
        )

    def evidence_bindings(self) -> tuple[EvidenceBinding, ...]:
        report = self.readiness()
        if not report.bindable_for_protocol:
            raise ValueError(
                "prepilot bundle is not bindable: " + "; ".join(report.blockers)
            )
        return tuple(item.to_evidence_binding() for item in self.manifests)


def _draft_manifest(
    binding_id: str,
    payload: Mapping[str, Any],
) -> PrepilotManifest:
    return PrepilotManifest.from_payload(
        binding_id=binding_id,
        schema_version=f"perfume-chem.c0-prepilot.{binding_id}.v1",
        payload=payload,
        unresolved_items=(
            "Complete and technically review this exact manifest before binding.",
        ),
        review_state=ManifestReviewState.DRAFT,
        review_receipt_sha256=None,
    )


def build_c0_prepilot_bundle_draft(
    lexicon: ConstructionLexicon,
    protocol: ConstructionPanelProtocol,
) -> C0PrepilotBundle:
    """Create the deterministic incomplete template; no study is authorized."""

    if protocol.lexicon_sha256 != lexicon.lexicon_sha256:
        raise ValueError("protocol and lexicon identities do not match")
    anchor_entries: dict[str, dict[str, Any]] = {
        attribute_id: {
            "anchor_mode": mode,
            "training_reference_permitted": True,
            "low_reference_receipt_sha256": None,
            "mid_reference_receipt_sha256": None,
            "high_reference_receipt_sha256": None,
        }
        for attribute_id, mode in _CONSTRUCTION_ANCHOR_MODES.items()
    }
    anchor_entries["pleasantness"] = {
        "anchor_mode": "verbal_scale_only",
        "training_reference_permitted": False,
        "low_reference_receipt_sha256": None,
        "mid_reference_receipt_sha256": None,
        "high_reference_receipt_sha256": None,
    }
    payloads: dict[str, dict[str, Any]] = {
        "sample_manifest": {
            "blind_code_scheme": {
                "format": "uppercase_alphanumeric",
                "length": None,
            },
            "custodian_role": None,
            "sample_identity_map_receipt_sha256": None,
            "allocation_concealment": None,
            "code_collision_check": None,
        },
        "preparation_dose_ppm_manifest": {
            "matrix_id": None,
            "concentrate_ppm": None,
            "active_application_mass_mg": None,
            "substrate": None,
            "carrier_id": None,
            "preparation_sop_sha256": None,
            "dose_tolerance_fraction": None,
        },
        "formula_oav_manifest": {
            "formula_manifest_sha256": None,
            "odt_dataset_sha256": None,
            "oav_report_sha256": None,
            "natural_mixture_oav_policy": None,
            "time_windows_seconds": None,
            "data_quality_review_receipt_sha256": None,
        },
        "randomization_manifest": {
            "sequence_method": None,
            "seed_commitment_sha256": None,
            "allocation_receipt_sha256": None,
            "carryover_rule": None,
            "blinding_roles": None,
        },
        "anchor_reference_manifest": {
            "lexicon_sha256": lexicon.lexicon_sha256,
            "attribute_anchors": anchor_entries,
            "reference_preparation_sop_sha256": None,
        },
        "participant_plan": {
            "expertise_strata": [
                "trained_descriptive",
                "perfumer_expert",
                "untrained",
            ],
            "eligibility_rules_sha256": None,
            "olfactory_screening_plan_sha256": None,
            "specific_anosmia_policy": None,
            "training_plan_sha256": None,
            "repeat_plan": {"repeats_per_sample": None},
            "attrition_rule": None,
            "privacy_separation_receipt_sha256": None,
            "qualification_receipt_schema_sha256": None,
        },
        "environment_timing_manifest": {
            "room_sop_sha256": None,
            "temperature_c_range": None,
            "relative_humidity_pct_range": None,
            "ventilation_rule": None,
            "session_duration_limit_minutes": None,
            "sniff_timepoints_seconds": None,
            "rest_interval_seconds": None,
            "confounder_rules_sha256": None,
        },
        "analysis_plan": {
            "estimands": None,
            "missing_data_rule": None,
            "multiplicity_rule": None,
            "uncertainty_method": None,
            "gate_specification_receipts": {
                kind.value: None for kind in GateKind
            },
            "pilot_confirmatory_separation": True,
            "analysis_implementation_receipt_sha256": None,
        },
        "ethics_privacy_safety_review": {
            "applicability_determination_receipt_sha256": None,
            "consent_plan_sha256": None,
            "privacy_plan_sha256": None,
            "exposure_safety_review_sha256": None,
            "withdrawal_process": None,
            "adverse_event_process": None,
            "review_jurisdiction": None,
        },
    }
    return C0PrepilotBundle(
        schema_version="perfume-chem.c0-prepilot-bundle.v1",
        version=1,
        lexicon_sha256=lexicon.lexicon_sha256,
        base_protocol_sha256=protocol.protocol_sha256,
        manifests=tuple(
            _draft_manifest(binding_id, payloads[binding_id])
            for binding_id in REQUIRED_BINDING_IDS
        ),
    )


def apply_prepilot_bundle(
    protocol: ConstructionPanelProtocol,
    bundle: C0PrepilotBundle,
) -> ConstructionPanelProtocol:
    """Bind reviewed manifests while deliberately leaving protocol lock false."""

    if protocol.protocol_sha256 != bundle.base_protocol_sha256:
        raise ValueError("bundle base protocol hash does not match the protocol")
    if protocol.lexicon_sha256 != bundle.lexicon_sha256:
        raise ValueError("bundle lexicon hash does not match the protocol")
    if protocol.protocol_locked:
        raise ValueError("a locked protocol cannot accept new prepilot bindings")
    bindings = bundle.evidence_bindings()
    payload_by_id = {item.binding_id: item.payload for item in bundle.manifests}
    timepoints = payload_by_id["environment_timing_manifest"][
        "sniff_timepoints_seconds"
    ]
    repeats = payload_by_id["participant_plan"]["repeat_plan"][
        "repeats_per_sample"
    ]
    if not isinstance(timepoints, list) or not isinstance(repeats, int):
        raise ValueError("reviewed timing and repeat payloads are malformed")
    return replace(
        protocol,
        bindings=bindings,
        timepoints_seconds=tuple(int(item) for item in timepoints),
        repeat_count=repeats,
        protocol_locked=False,
    )


__all__ = [
    "C0PrepilotBundle",
    "ManifestReviewState",
    "PrepilotDecision",
    "PrepilotManifest",
    "PrepilotReadinessReport",
    "REQUIRED_MANIFEST_FIELDS",
    "apply_prepilot_bundle",
    "build_c0_prepilot_bundle_draft",
]
