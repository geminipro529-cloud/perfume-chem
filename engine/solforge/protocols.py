"""Deterministic preregistration and physical-evidence intake firewall."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import ClassVar, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.sensory.order_balance import generate_williams_schedule

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

PROTOCOL_AUTHORITY_FLAGS = {
    "compounding": False,
    "hedonic": False,
    "physical_execution": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class PhysicalEvidenceIntakeError(ValueError):
    """Physical evidence failed exact preregistration binding."""


class ProtocolDesignClass(str, Enum):
    OMISSION_ALTERNATIVE = "OMISSION_ALTERNATIVE"
    RATIO_WINDOW = "RATIO_WINDOW"
    TWO_FACTOR_FOUR_ARM_MIXTURE = "TWO_FACTOR_FOUR_ARM_MIXTURE"
    TEMPORAL_REPEATED_MEASURES = "TEMPORAL_REPEATED_MEASURES"
    CRITERION_PAIRWISE_LIKING = "CRITERION_PAIRWISE_LIKING"
    SOFTWARE_DECISION_YIELD = "SOFTWARE_DECISION_YIELD"


class ParticipantScopeV2(str, Enum):
    OWNER = "OWNER"
    TRAINED_PANEL = "TRAINED_PANEL"
    CONSUMER = "CONSUMER"


class ProtocolEndpointV2(str, Enum):
    TARGET_FIDELITY = "TARGET_FIDELITY"
    DEPTH = "DEPTH"
    RICHNESS = "RICHNESS"
    LIKING = "LIKING"
    INTENSITY = "INTENSITY"
    FAMILIARITY = "FAMILIARITY"
    DETECTABILITY = "DETECTABILITY"


class ProtocolAnalysisUnitV2(str, Enum):
    ASSESSOR = "ASSESSOR"
    SESSION = "SESSION"


V2_COUNTERBALANCING_METHOD = "WILLIAMS_FIRST_ORDER_BALANCED"
V2_TIE_SEMANTICS = (
    "ALLOW_INDIFFERENCE_EXCLUDE_FROM_DIRECTIONAL_FIT_RETAIN_AS_EVIDENCE"
)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _sha(value: object, name: str) -> str:
    if not isinstance(value, str) or _SHA_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lower-case SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ProtocolTemplateV1:
    template_id: str
    design_class: ProtocolDesignClass
    arm_ids: tuple[str, ...]
    primary_endpoint: str
    secondary_endpoints: tuple[str, ...]
    washout_seconds: float
    repeat_count: int
    assessor_scope: str
    stopping_rule: str
    safety_stop: str

    def __post_init__(self) -> None:
        for name in (
            "template_id",
            "primary_endpoint",
            "assessor_scope",
            "stopping_rule",
            "safety_stop",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "design_class", ProtocolDesignClass(self.design_class))
        arms = tuple(_text(item, "arm_id") for item in self.arm_ids)
        if len(arms) < 2 or len(arms) != len(set(arms)):
            raise ValueError("arm_ids must contain unique control and treatment arms")
        object.__setattr__(self, "arm_ids", arms)
        object.__setattr__(
            self,
            "secondary_endpoints",
            tuple(_text(item, "secondary_endpoint") for item in self.secondary_endpoints),
        )
        if self.washout_seconds <= 0 or self.repeat_count < 2:
            raise ValueError("washout and repeat requirements must be positive")


@dataclass(frozen=True, slots=True)
class ProtocolTemplateV2:
    template_id: str
    design_class: ProtocolDesignClass
    arm_ids: tuple[str, ...]
    primary_endpoint: ProtocolEndpointV2
    secondary_endpoints: tuple[ProtocolEndpointV2, ...]
    washout_seconds: float
    repeat_count: int
    maximum_exposures_per_session: int
    minimum_comparisons: int
    minimum_heldout_comparisons: int
    declared_baseline_accuracy: float
    bootstrap_replicates: int
    bootstrap_seed: int
    stopping_rule: str
    safety_stop: str
    counterbalancing_method: str = V2_COUNTERBALANCING_METHOD
    tie_semantics: str = V2_TIE_SEMANTICS

    def __post_init__(self) -> None:
        for name in ("template_id", "stopping_rule", "safety_stop"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "design_class", ProtocolDesignClass(self.design_class))
        arms = tuple(_text(item, "arm_id") for item in self.arm_ids)
        if len(arms) < 2 or len(arms) != len(set(arms)):
            raise ValueError("arm_ids must contain unique control and treatment arms")
        object.__setattr__(self, "arm_ids", arms)
        object.__setattr__(
            self,
            "primary_endpoint",
            ProtocolEndpointV2(self.primary_endpoint),
        )
        secondary = tuple(
            ProtocolEndpointV2(item) for item in self.secondary_endpoints
        )
        if len(secondary) != len(set(secondary)):
            raise ValueError("secondary endpoints must be unique")
        if self.primary_endpoint in secondary:
            raise ValueError("primary and secondary endpoints must remain separate")
        object.__setattr__(self, "secondary_endpoints", secondary)
        object.__setattr__(
            self,
            "counterbalancing_method",
            _text(self.counterbalancing_method, "counterbalancing_method"),
        )
        object.__setattr__(
            self,
            "tie_semantics",
            _text(self.tie_semantics, "tie_semantics"),
        )
        if self.counterbalancing_method != V2_COUNTERBALANCING_METHOD:
            raise ValueError("V2 protocols require Williams counterbalancing")
        if self.tie_semantics != V2_TIE_SEMANTICS:
            raise ValueError("V2 tie semantics must retain indifference evidence")
        if not isfinite(self.washout_seconds) or self.washout_seconds <= 0:
            raise ValueError("washout_seconds must be finite and positive")
        for name in (
            "repeat_count",
            "maximum_exposures_per_session",
            "minimum_comparisons",
            "minimum_heldout_comparisons",
            "bootstrap_replicates",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.repeat_count < 2:
            raise ValueError("V2 protocols require at least two repeats")
        if not 0 <= self.declared_baseline_accuracy < 1:
            raise ValueError("declared baseline accuracy must be in [0, 1)")
        if isinstance(self.bootstrap_seed, bool) or not isinstance(
            self.bootstrap_seed, int
        ):
            raise ValueError("bootstrap_seed must be an integer")


@dataclass(frozen=True, slots=True)
class ProtocolArmV1:
    arm_id: str
    sample_sha256: str
    total_active_mass_g: float
    blind_code: str

    def as_dict(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "sample_sha256": self.sample_sha256,
            "total_active_mass_g": self.total_active_mass_g,
            "blind_code": self.blind_code,
        }


@dataclass(frozen=True, slots=True)
class PreregisteredProtocolV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_preregistered_protocol_v1"
    protocol_id: str
    design_class: ProtocolDesignClass
    program_sha256: str
    formula_build_sha256: str
    dose_receipt_sha256: str
    inventory_sha256: str
    arms: tuple[ProtocolArmV1, ...]
    sample_sha256: tuple[tuple[str, str], ...]
    schedule_sha256: str
    primary_endpoint: str
    secondary_endpoints: tuple[str, ...]
    washout_seconds: float
    repeat_count: int
    assessor_scope: str
    stopping_rule: str
    safety_stop: str
    status: str = "PREREGISTERED_NOT_EXECUTED"

    def __post_init__(self) -> None:
        for name in (
            "protocol_id",
            "primary_endpoint",
            "assessor_scope",
            "stopping_rule",
            "safety_stop",
            "status",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "design_class", ProtocolDesignClass(self.design_class))
        for name in (
            "program_sha256",
            "formula_build_sha256",
            "dose_receipt_sha256",
            "inventory_sha256",
            "schedule_sha256",
        ):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        object.__setattr__(self, "arms", tuple(self.arms))
        object.__setattr__(self, "sample_sha256", tuple(self.sample_sha256))
        object.__setattr__(self, "secondary_endpoints", tuple(self.secondary_endpoints))
        if self.status != "PREREGISTERED_NOT_EXECUTED":
            raise ValueError("new protocols must remain PREREGISTERED_NOT_EXECUTED")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "protocol_id": self.protocol_id,
            "design_class": self.design_class.value,
            "program_sha256": self.program_sha256,
            "formula_build_sha256": self.formula_build_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "inventory_sha256": self.inventory_sha256,
            "arms": [arm.as_dict() for arm in self.arms],
            "sample_sha256": [list(item) for item in self.sample_sha256],
            "schedule_sha256": self.schedule_sha256,
            "primary_endpoint": self.primary_endpoint,
            "secondary_endpoints": list(self.secondary_endpoints),
            "washout_seconds": self.washout_seconds,
            "repeat_count": self.repeat_count,
            "assessor_scope": self.assessor_scope,
            "stopping_rule": self.stopping_rule,
            "safety_stop": self.safety_stop,
            "status": self.status,
            "authority_flags": dict(PROTOCOL_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> PreregisteredProtocolV1:
        if not isinstance(payload, dict) or payload.get("authority_flags") != (
            PROTOCOL_AUTHORITY_FLAGS
        ):
            raise ValueError("protocol authority_flags must be exact and all false")
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("protocol schema_version is invalid")
        expected = {
            "schema_version",
            "protocol_id",
            "design_class",
            "program_sha256",
            "formula_build_sha256",
            "dose_receipt_sha256",
            "inventory_sha256",
            "arms",
            "sample_sha256",
            "schedule_sha256",
            "primary_endpoint",
            "secondary_endpoints",
            "washout_seconds",
            "repeat_count",
            "assessor_scope",
            "stopping_rule",
            "safety_stop",
            "status",
            "authority_flags",
        }
        if set(payload) != expected:
            raise ValueError("protocol fields do not match the closed schema")
        arms = tuple(ProtocolArmV1(**item) for item in payload["arms"])
        return cls(
            protocol_id=payload["protocol_id"],
            design_class=payload["design_class"],
            program_sha256=payload["program_sha256"],
            formula_build_sha256=payload["formula_build_sha256"],
            dose_receipt_sha256=payload["dose_receipt_sha256"],
            inventory_sha256=payload["inventory_sha256"],
            arms=arms,
            sample_sha256=tuple(tuple(item) for item in payload["sample_sha256"]),
            schedule_sha256=payload["schedule_sha256"],
            primary_endpoint=payload["primary_endpoint"],
            secondary_endpoints=tuple(payload["secondary_endpoints"]),
            washout_seconds=payload["washout_seconds"],
            repeat_count=payload["repeat_count"],
            assessor_scope=payload["assessor_scope"],
            stopping_rule=payload["stopping_rule"],
            safety_stop=payload["safety_stop"],
            status=payload["status"],
        )


@dataclass(frozen=True, slots=True)
class PreregisteredProtocolV2:
    SCHEMA_VERSION: ClassVar[str] = "solforge_preregistered_protocol_v2"
    protocol_id: str
    design_class: ProtocolDesignClass
    participant_scope: ParticipantScopeV2
    program_sha256: str
    formula_build_sha256: str
    dose_receipt_sha256: str
    inventory_sha256: str
    execution_plan_sha256: str
    deviation_policy_sha256: str
    arms: tuple[ProtocolArmV1, ...]
    sample_sha256: tuple[tuple[str, str], ...]
    assessor_ids: tuple[str, ...]
    repeat_ids: tuple[str, ...]
    session_ids: tuple[str, ...]
    session_sequence_ids: tuple[tuple[str, str], ...]
    timepoints_seconds: tuple[float, ...]
    schedule_sequences: tuple[tuple[str, ...], ...]
    schedule_sha256: str
    counterbalancing_method: str
    primary_endpoint: ProtocolEndpointV2
    secondary_endpoints: tuple[ProtocolEndpointV2, ...]
    washout_seconds: float
    repeat_count: int
    maximum_exposures_per_session: int
    tie_semantics: str
    cluster_unit: ProtocolAnalysisUnitV2
    heldout_unit: ProtocolAnalysisUnitV2
    minimum_comparisons: int
    minimum_heldout_comparisons: int
    declared_baseline_accuracy: float
    bootstrap_replicates: int
    bootstrap_seed: int
    apparatus_id: str
    apparatus_qualification_sha256: str
    within_sniff: bool
    within_sniff_apparatus_qualified: bool
    within_sniff_timing_protocol_qualified: bool
    timing_protocol_sha256: str | None
    timing_clock_source: str | None
    timing_tolerance_ms: float | None
    stopping_rule: str
    safety_stop: str
    status: str = "PREREGISTERED_NOT_EXECUTED"

    def __post_init__(self) -> None:
        for name in (
            "protocol_id",
            "counterbalancing_method",
            "tie_semantics",
            "apparatus_id",
            "stopping_rule",
            "safety_stop",
            "status",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "design_class", ProtocolDesignClass(self.design_class))
        object.__setattr__(
            self,
            "participant_scope",
            ParticipantScopeV2(self.participant_scope),
        )
        object.__setattr__(
            self,
            "primary_endpoint",
            ProtocolEndpointV2(self.primary_endpoint),
        )
        object.__setattr__(
            self,
            "secondary_endpoints",
            tuple(ProtocolEndpointV2(item) for item in self.secondary_endpoints),
        )
        object.__setattr__(
            self,
            "cluster_unit",
            ProtocolAnalysisUnitV2(self.cluster_unit),
        )
        object.__setattr__(
            self,
            "heldout_unit",
            ProtocolAnalysisUnitV2(self.heldout_unit),
        )
        for name in (
            "program_sha256",
            "formula_build_sha256",
            "dose_receipt_sha256",
            "inventory_sha256",
            "execution_plan_sha256",
            "deviation_policy_sha256",
            "schedule_sha256",
            "apparatus_qualification_sha256",
        ):
            object.__setattr__(self, name, _sha(getattr(self, name), name))
        if self.timing_protocol_sha256 is not None:
            object.__setattr__(
                self,
                "timing_protocol_sha256",
                _sha(self.timing_protocol_sha256, "timing_protocol_sha256"),
            )
        if self.timing_clock_source is not None:
            object.__setattr__(
                self,
                "timing_clock_source",
                _text(self.timing_clock_source, "timing_clock_source"),
            )
        object.__setattr__(self, "arms", tuple(self.arms))
        object.__setattr__(
            self,
            "sample_sha256",
            tuple(
                (
                    _text(sample_id, "sample_sha256 sample"),
                    _sha(digest, "sample_sha256 digest"),
                )
                for sample_id, digest in self.sample_sha256
            ),
        )
        for name in ("assessor_ids", "repeat_ids", "session_ids"):
            values = tuple(_text(item, name) for item in getattr(self, name))
            object.__setattr__(self, name, values)
        object.__setattr__(
            self,
            "session_sequence_ids",
            tuple(
                (
                    _text(session_id, "session_sequence_ids session"),
                    _text(sequence_id, "session_sequence_ids sequence"),
                )
                for session_id, sequence_id in self.session_sequence_ids
            ),
        )
        object.__setattr__(
            self,
            "timepoints_seconds",
            tuple(float(item) for item in self.timepoints_seconds),
        )
        if self.timing_tolerance_ms is not None:
            object.__setattr__(
                self,
                "timing_tolerance_ms",
                float(self.timing_tolerance_ms),
            )
        object.__setattr__(
            self,
            "schedule_sequences",
            tuple(tuple(_text(item, "schedule item") for item in row) for row in self.schedule_sequences),
        )
        for name in (
            "within_sniff",
            "within_sniff_apparatus_qualified",
            "within_sniff_timing_protocol_qualified",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be boolean")
        for name in (
            "repeat_count",
            "maximum_exposures_per_session",
            "minimum_comparisons",
            "minimum_heldout_comparisons",
            "bootstrap_replicates",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if isinstance(self.bootstrap_seed, bool) or not isinstance(
            self.bootstrap_seed, int
        ):
            raise TypeError("bootstrap_seed must be an integer")
        if self.status != "PREREGISTERED_NOT_EXECUTED":
            raise ValueError("new protocols must remain PREREGISTERED_NOT_EXECUTED")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "protocol_id": self.protocol_id,
            "design_class": self.design_class.value,
            "participant_scope": self.participant_scope.value,
            "program_sha256": self.program_sha256,
            "formula_build_sha256": self.formula_build_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "inventory_sha256": self.inventory_sha256,
            "execution_plan_sha256": self.execution_plan_sha256,
            "deviation_policy_sha256": self.deviation_policy_sha256,
            "arms": [arm.as_dict() for arm in self.arms],
            "sample_sha256": [list(item) for item in self.sample_sha256],
            "assessor_ids": list(self.assessor_ids),
            "repeat_ids": list(self.repeat_ids),
            "session_ids": list(self.session_ids),
            "session_sequence_ids": [
                list(item) for item in self.session_sequence_ids
            ],
            "timepoints_seconds": list(self.timepoints_seconds),
            "schedule_sequences": [list(item) for item in self.schedule_sequences],
            "schedule_sha256": self.schedule_sha256,
            "counterbalancing_method": self.counterbalancing_method,
            "primary_endpoint": self.primary_endpoint.value,
            "secondary_endpoints": [item.value for item in self.secondary_endpoints],
            "washout_seconds": self.washout_seconds,
            "repeat_count": self.repeat_count,
            "maximum_exposures_per_session": self.maximum_exposures_per_session,
            "tie_semantics": self.tie_semantics,
            "cluster_unit": self.cluster_unit.value,
            "heldout_unit": self.heldout_unit.value,
            "minimum_comparisons": self.minimum_comparisons,
            "minimum_heldout_comparisons": self.minimum_heldout_comparisons,
            "declared_baseline_accuracy": self.declared_baseline_accuracy,
            "bootstrap_replicates": self.bootstrap_replicates,
            "bootstrap_seed": self.bootstrap_seed,
            "apparatus_id": self.apparatus_id,
            "apparatus_qualification_sha256": self.apparatus_qualification_sha256,
            "within_sniff": self.within_sniff,
            "within_sniff_apparatus_qualified": self.within_sniff_apparatus_qualified,
            "within_sniff_timing_protocol_qualified": self.within_sniff_timing_protocol_qualified,
            "timing_protocol_sha256": self.timing_protocol_sha256,
            "timing_clock_source": self.timing_clock_source,
            "timing_tolerance_ms": self.timing_tolerance_ms,
            "stopping_rule": self.stopping_rule,
            "safety_stop": self.safety_stop,
            "status": self.status,
            "authority_flags": dict(PROTOCOL_AUTHORITY_FLAGS),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.as_dict())

    @property
    def record_sha256(self) -> str:
        return sha256_hex(self.canonical_bytes())

    @classmethod
    def from_dict(cls, payload: object) -> PreregisteredProtocolV2:
        if not isinstance(payload, dict):
            raise ValueError("V2 protocol payload must be an object")
        if payload.get("authority_flags") != PROTOCOL_AUTHORITY_FLAGS:
            raise ValueError("protocol authority_flags must be exact and all false")
        if payload.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("protocol schema_version is invalid")
        expected = set(cls.__dataclass_fields__) - {"SCHEMA_VERSION"}
        expected.update({"schema_version", "authority_flags"})
        if set(payload) != expected:
            raise ValueError("V2 protocol fields do not match the closed schema")
        values = dict(payload)
        values.pop("schema_version")
        values.pop("authority_flags")
        values["arms"] = tuple(ProtocolArmV1(**item) for item in values["arms"])
        values["sample_sha256"] = tuple(tuple(item) for item in values["sample_sha256"])
        values["assessor_ids"] = tuple(values["assessor_ids"])
        values["repeat_ids"] = tuple(values["repeat_ids"])
        values["session_ids"] = tuple(values["session_ids"])
        values["session_sequence_ids"] = tuple(
            tuple(item) for item in values["session_sequence_ids"]
        )
        values["timepoints_seconds"] = tuple(values["timepoints_seconds"])
        values["schedule_sequences"] = tuple(
            tuple(item) for item in values["schedule_sequences"]
        )
        values["secondary_endpoints"] = tuple(values["secondary_endpoints"])
        return cls(**values)


def load_protocol_templates(path: Path) -> tuple[ProtocolTemplateV1, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "solforge_protocol_templates_v1" or payload.get(
        "authority_flags"
    ) != PROTOCOL_AUTHORITY_FLAGS:
        raise ValueError("protocol template manifest is invalid or grants authority")
    templates = tuple(
        ProtocolTemplateV1(
            template_id=item["template_id"],
            design_class=item["design_class"],
            arm_ids=tuple(item["arm_ids"]),
            primary_endpoint=item["primary_endpoint"],
            secondary_endpoints=tuple(item["secondary_endpoints"]),
            washout_seconds=float(item["washout_seconds"]),
            repeat_count=int(item["repeat_count"]),
            assessor_scope=item["assessor_scope"],
            stopping_rule=item["stopping_rule"],
            safety_stop=item["safety_stop"],
        )
        for item in payload["templates"]
    )
    if len(templates) != len(ProtocolDesignClass):
        raise ValueError("one template per protocol design class is required")
    return templates


def load_protocol_templates_v2(path: Path) -> tuple[ProtocolTemplateV2, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "solforge_protocol_templates_v2" or payload.get(
        "authority_flags"
    ) != PROTOCOL_AUTHORITY_FLAGS:
        raise ValueError("V2 protocol template manifest is invalid or grants authority")
    raw_templates = payload.get("templates")
    if not isinstance(raw_templates, list) or not raw_templates:
        raise ValueError("V2 protocol templates must be a nonempty list")
    templates = tuple(
        ProtocolTemplateV2(
            template_id=item["template_id"],
            design_class=item["design_class"],
            arm_ids=tuple(item["arm_ids"]),
            primary_endpoint=item["primary_endpoint"],
            secondary_endpoints=tuple(item["secondary_endpoints"]),
            washout_seconds=float(item["washout_seconds"]),
            repeat_count=int(item["repeat_count"]),
            maximum_exposures_per_session=int(item["maximum_exposures_per_session"]),
            minimum_comparisons=int(item["minimum_comparisons"]),
            minimum_heldout_comparisons=int(item["minimum_heldout_comparisons"]),
            declared_baseline_accuracy=float(item["declared_baseline_accuracy"]),
            bootstrap_replicates=int(item["bootstrap_replicates"]),
            bootstrap_seed=int(item["bootstrap_seed"]),
            stopping_rule=item["stopping_rule"],
            safety_stop=item["safety_stop"],
            counterbalancing_method=item["counterbalancing_method"],
            tie_semantics=item["tie_semantics"],
        )
        for item in raw_templates
    )
    template_ids = tuple(item.template_id for item in templates)
    if len(template_ids) != len(set(template_ids)):
        raise ValueError("V2 template ids must be unique")
    endpoints = {
        endpoint
        for template in templates
        for endpoint in (template.primary_endpoint, *template.secondary_endpoints)
    }
    if endpoints != set(ProtocolEndpointV2):
        raise ValueError("V2 templates must cover every separate endpoint")
    return templates


def build_protocol(
    template: ProtocolTemplateV1,
    bindings: Mapping[str, object],
) -> PreregisteredProtocolV1:
    sample_map = bindings.get("sample_sha256")
    if not isinstance(sample_map, Mapping):
        raise ValueError("sample_sha256 binding must be a mapping")
    arms: list[ProtocolArmV1] = []
    for arm_id in template.arm_ids:
        sample_hash = _sha(sample_map.get(arm_id), f"sample_sha256[{arm_id}]")
        blind_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "template_id": template.template_id,
                    "program_sha256": bindings["program_sha256"],
                    "arm_id": arm_id,
                    "sample_sha256": sample_hash,
                }
            )
        )
        arms.append(
            ProtocolArmV1(
                arm_id=arm_id,
                sample_sha256=sample_hash,
                total_active_mass_g=1.0,
                blind_code=f"SF-{blind_hash[:10].upper()}",
            )
        )
    schedule = generate_williams_schedule(template.arm_ids)
    protocol_id = "SF-PROTOCOL-" + sha256_hex(
        canonical_json_bytes(
            {
                "template": template.template_id,
                "program": bindings["program_sha256"],
                "samples": sample_map,
            }
        )
    )[:16].upper()
    return PreregisteredProtocolV1(
        protocol_id=protocol_id,
        design_class=template.design_class,
        program_sha256=_sha(bindings.get("program_sha256"), "program_sha256"),
        formula_build_sha256=_sha(
            bindings.get("formula_build_sha256"), "formula_build_sha256"
        ),
        dose_receipt_sha256=_sha(
            bindings.get("dose_receipt_sha256"), "dose_receipt_sha256"
        ),
        inventory_sha256=_sha(bindings.get("inventory_sha256"), "inventory_sha256"),
        arms=tuple(arms),
        sample_sha256=tuple((arm.arm_id, arm.sample_sha256) for arm in arms),
        schedule_sha256=schedule.schedule_sha256,
        primary_endpoint=template.primary_endpoint,
        secondary_endpoints=template.secondary_endpoints,
        washout_seconds=template.washout_seconds,
        repeat_count=template.repeat_count,
        assessor_scope=template.assessor_scope,
        stopping_rule=template.stopping_rule,
        safety_stop=template.safety_stop,
    )


def build_protocol_v2(
    template: ProtocolTemplateV2,
    bindings: Mapping[str, object],
) -> PreregisteredProtocolV2:
    if not isinstance(template, ProtocolTemplateV2):
        raise TypeError("template must be ProtocolTemplateV2")
    sample_map = bindings.get("sample_sha256")
    if not isinstance(sample_map, Mapping):
        raise ValueError("sample_sha256 binding must be a mapping")
    arms: list[ProtocolArmV1] = []
    for arm_id in template.arm_ids:
        sample_hash = _sha(sample_map.get(arm_id), f"sample_sha256[{arm_id}]")
        blind_hash = sha256_hex(
            canonical_json_bytes(
                {
                    "schema_version": PreregisteredProtocolV2.SCHEMA_VERSION,
                    "template_id": template.template_id,
                    "program_sha256": bindings.get("program_sha256"),
                    "arm_id": arm_id,
                    "sample_sha256": sample_hash,
                }
            )
        )
        arms.append(
            ProtocolArmV1(
                arm_id=arm_id,
                sample_sha256=sample_hash,
                total_active_mass_g=1.0,
                blind_code=f"SF2-{blind_hash[:10].upper()}",
            )
        )
    schedule = generate_williams_schedule(template.arm_ids)
    session_ids = tuple(bindings.get("session_ids", ()))
    sequence_ids = tuple(
        f"SEQUENCE-{index + 1}" for index in range(len(schedule.sequences))
    )
    session_sequence_ids = tuple(
        (session_id, sequence_ids[index % len(sequence_ids)])
        for index, session_id in enumerate(session_ids)
    )
    participant_scope = ParticipantScopeV2(bindings.get("participant_scope"))
    analysis_unit = (
        ProtocolAnalysisUnitV2.SESSION
        if participant_scope is ParticipantScopeV2.OWNER
        else ProtocolAnalysisUnitV2.ASSESSOR
    )
    protocol_id = "SF-PROTOCOL-V2-" + sha256_hex(
        canonical_json_bytes(
            {
                "template": template.template_id,
                "program": bindings.get("program_sha256"),
                "samples": sample_map,
                "participant_scope": participant_scope.value,
                "assessors": bindings.get("assessor_ids"),
                "repeats": bindings.get("repeat_ids"),
                "sessions": bindings.get("session_ids"),
                "timepoints": bindings.get("timepoints_seconds"),
                "execution_plan": bindings.get("execution_plan_sha256"),
            }
        )
    )[:16].upper()
    timing_protocol = bindings.get("timing_protocol_sha256")
    protocol = PreregisteredProtocolV2(
        protocol_id=protocol_id,
        design_class=template.design_class,
        participant_scope=participant_scope,
        program_sha256=_sha(bindings.get("program_sha256"), "program_sha256"),
        formula_build_sha256=_sha(
            bindings.get("formula_build_sha256"), "formula_build_sha256"
        ),
        dose_receipt_sha256=_sha(
            bindings.get("dose_receipt_sha256"), "dose_receipt_sha256"
        ),
        inventory_sha256=_sha(bindings.get("inventory_sha256"), "inventory_sha256"),
        execution_plan_sha256=_sha(
            bindings.get("execution_plan_sha256"), "execution_plan_sha256"
        ),
        deviation_policy_sha256=_sha(
            bindings.get("deviation_policy_sha256"), "deviation_policy_sha256"
        ),
        arms=tuple(arms),
        sample_sha256=tuple((arm.arm_id, arm.sample_sha256) for arm in arms),
        assessor_ids=tuple(bindings.get("assessor_ids", ())),
        repeat_ids=tuple(bindings.get("repeat_ids", ())),
        session_ids=session_ids,
        session_sequence_ids=session_sequence_ids,
        timepoints_seconds=tuple(bindings.get("timepoints_seconds", ())),
        schedule_sequences=schedule.sequences,
        schedule_sha256=schedule.schedule_sha256,
        counterbalancing_method=template.counterbalancing_method,
        primary_endpoint=template.primary_endpoint,
        secondary_endpoints=template.secondary_endpoints,
        washout_seconds=template.washout_seconds,
        repeat_count=template.repeat_count,
        maximum_exposures_per_session=template.maximum_exposures_per_session,
        tie_semantics=template.tie_semantics,
        cluster_unit=analysis_unit,
        heldout_unit=analysis_unit,
        minimum_comparisons=template.minimum_comparisons,
        minimum_heldout_comparisons=template.minimum_heldout_comparisons,
        declared_baseline_accuracy=template.declared_baseline_accuracy,
        bootstrap_replicates=template.bootstrap_replicates,
        bootstrap_seed=template.bootstrap_seed,
        apparatus_id=bindings.get("apparatus_id"),
        apparatus_qualification_sha256=_sha(
            bindings.get("apparatus_qualification_sha256"),
            "apparatus_qualification_sha256",
        ),
        within_sniff=bool(bindings.get("within_sniff", False)),
        within_sniff_apparatus_qualified=bool(
            bindings.get("within_sniff_apparatus_qualified", False)
        ),
        within_sniff_timing_protocol_qualified=bool(
            bindings.get("within_sniff_timing_protocol_qualified", False)
        ),
        timing_protocol_sha256=(
            _sha(timing_protocol, "timing_protocol_sha256")
            if timing_protocol is not None
            else None
        ),
        timing_clock_source=bindings.get("timing_clock_source"),
        timing_tolerance_ms=bindings.get("timing_tolerance_ms"),
        stopping_rule=template.stopping_rule,
        safety_stop=template.safety_stop,
    )
    issues = validate_protocol_v2(protocol)
    if issues:
        raise ValueError("; ".join(issues))
    return protocol


def validate_protocol_v2(protocol: PreregisteredProtocolV2) -> tuple[str, ...]:
    if not isinstance(protocol, PreregisteredProtocolV2):
        raise TypeError("protocol must be PreregisteredProtocolV2")
    issues: list[str] = []
    arm_ids = tuple(arm.arm_id for arm in protocol.arms)
    if "CONTROL" not in arm_ids:
        issues.append("CONTROL arm is required")
    if len(arm_ids) < 2 or len(arm_ids) != len(set(arm_ids)):
        issues.append("arm IDs must contain unique control and treatment arms")
    if tuple(name for name, _ in protocol.sample_sha256) != arm_ids:
        issues.append("sample SHA-256 mapping must exactly match protocol arms")
    if protocol.sample_sha256 != tuple(
        (arm.arm_id, arm.sample_sha256) for arm in protocol.arms
    ):
        issues.append("sample SHA-256 values must exactly match protocol arms")
    if any(
        not isfinite(arm.total_active_mass_g) or arm.total_active_mass_g <= 0
        for arm in protocol.arms
    ):
        issues.append("arm active masses must be finite and positive")
    if len({arm.blind_code for arm in protocol.arms}) != len(protocol.arms):
        issues.append("blind codes must be unique")
    if len({arm.total_active_mass_g for arm in protocol.arms}) != 1:
        issues.append("all arms require matched total active mass")
    expected_schedule = generate_williams_schedule(arm_ids)
    if (
        protocol.counterbalancing_method != V2_COUNTERBALANCING_METHOD
        or protocol.schedule_sequences != expected_schedule.sequences
        or protocol.schedule_sha256 != expected_schedule.schedule_sha256
    ):
        issues.append("schedule must match the Williams first-order balanced design")
    endpoints = (protocol.primary_endpoint, *protocol.secondary_endpoints)
    if len(endpoints) != len(set(endpoints)):
        issues.append("primary and secondary endpoints must remain separate")
    for name in ("assessor_ids", "repeat_ids", "session_ids"):
        values = getattr(protocol, name)
        if not values or len(values) != len(set(values)):
            issues.append(f"{name} must contain unique declared identifiers")
    if protocol.participant_scope is ParticipantScopeV2.OWNER:
        if len(protocol.assessor_ids) != 1:
            issues.append("OWNER scope requires exactly one assessor")
        if protocol.heldout_unit is not ProtocolAnalysisUnitV2.SESSION:
            issues.append("OWNER heldout unit must be SESSION")
        if protocol.cluster_unit is not ProtocolAnalysisUnitV2.SESSION:
            issues.append("OWNER cluster unit must be SESSION")
    elif len(protocol.assessor_ids) < 2:
        issues.append("panel and consumer scopes require at least two assessors")
    elif (
        protocol.heldout_unit is not ProtocolAnalysisUnitV2.ASSESSOR
        or protocol.cluster_unit is not ProtocolAnalysisUnitV2.ASSESSOR
    ):
        issues.append("panel and consumer analysis units must be ASSESSOR")
    if protocol.repeat_count < 2 or len(protocol.repeat_ids) != protocol.repeat_count:
        issues.append("V2 protocols require at least two repeats with exact repeat IDs")
    if len(protocol.session_ids) < protocol.repeat_count:
        issues.append("session IDs must support every declared repeat")
    expected_sequence_ids = {
        f"SEQUENCE-{index + 1}" for index in range(len(protocol.schedule_sequences))
    }
    if (
        tuple(session for session, _ in protocol.session_sequence_ids)
        != protocol.session_ids
        or any(
            sequence not in expected_sequence_ids
            for _, sequence in protocol.session_sequence_ids
        )
    ):
        issues.append("every session must bind one declared presentation sequence")
    if protocol.schedule_sequences and tuple(protocol.session_sequence_ids) != tuple(
        (
            session_id,
            f"SEQUENCE-{index % len(protocol.schedule_sequences) + 1}",
        )
        for index, session_id in enumerate(protocol.session_ids)
    ):
        issues.append("session sequence assignment must be deterministic and balanced")
    if (
        not protocol.timepoints_seconds
        or any(
            not isfinite(item) or item < 0 for item in protocol.timepoints_seconds
        )
        or tuple(sorted(set(protocol.timepoints_seconds)))
        != protocol.timepoints_seconds
    ):
        issues.append("timepoints must be unique, increasing, finite, and nonnegative")
    if (
        not isfinite(protocol.washout_seconds)
        or protocol.washout_seconds <= 0
    ):
        issues.append("washout must be finite and positive")
    if (
        protocol.maximum_exposures_per_session < len(arm_ids)
        or protocol.maximum_exposures_per_session < 1
    ):
        issues.append("maximum exposure count is unsafe for the declared arm set")
    if protocol.tie_semantics != V2_TIE_SEMANTICS:
        issues.append("tie semantics must retain indifference evidence")
    if protocol.minimum_comparisons < 1 or protocol.minimum_heldout_comparisons < 1:
        issues.append("comparison and heldout gates must be positive")
    if protocol.bootstrap_replicates < 1:
        issues.append("bootstrap_replicates must be positive")
    if (
        not isfinite(protocol.declared_baseline_accuracy)
        or not 0 <= protocol.declared_baseline_accuracy < 1
    ):
        issues.append("declared baseline must be in [0, 1)")
    if not protocol.apparatus_id or not protocol.apparatus_qualification_sha256:
        issues.append("qualified apparatus identity and hash are required")
    if protocol.within_sniff and not (
        protocol.within_sniff_apparatus_qualified
        and protocol.within_sniff_timing_protocol_qualified
        and protocol.timing_protocol_sha256 is not None
        and protocol.timing_clock_source is not None
        and protocol.timing_tolerance_ms is not None
        and isfinite(protocol.timing_tolerance_ms)
        and protocol.timing_tolerance_ms > 0
    ):
        issues.append("within-sniff timing requires qualified apparatus and timing")
    return tuple(issues)


@dataclass(frozen=True, slots=True)
class ProtocolExecutionBindingV2:
    SCHEMA_VERSION: ClassVar[str] = "solforge_protocol_execution_binding_v2"
    protocol_sha256: str
    execution_receipt_sha256: str
    execution_plan_sha256: str
    formula_build_sha256: str
    sample_sha256: tuple[tuple[str, str], ...]
    schedule_sha256: str
    deviation_policy_sha256: str
    deviations_sha256: str
    state: str
    test_only: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "protocol_sha256": self.protocol_sha256,
            "execution_receipt_sha256": self.execution_receipt_sha256,
            "execution_plan_sha256": self.execution_plan_sha256,
            "formula_build_sha256": self.formula_build_sha256,
            "sample_sha256": [list(item) for item in self.sample_sha256],
            "schedule_sha256": self.schedule_sha256,
            "deviation_policy_sha256": self.deviation_policy_sha256,
            "deviations_sha256": self.deviations_sha256,
            "state": self.state,
            "test_only": self.test_only,
            "authority_flags": dict(PROTOCOL_AUTHORITY_FLAGS),
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))


def bind_protocol_execution_v2(
    protocol: PreregisteredProtocolV2,
    execution: object,
    *,
    allow_test_only: bool = False,
) -> ProtocolExecutionBindingV2:
    from engine.solforge.contracts import ExecutionReceiptV1

    if not isinstance(protocol, PreregisteredProtocolV2):
        raise TypeError("protocol must be PreregisteredProtocolV2")
    if not isinstance(execution, ExecutionReceiptV1):
        raise TypeError("execution must be ExecutionReceiptV1")
    issues = validate_protocol_v2(protocol)
    if issues:
        raise ValueError("invalid V2 protocol: " + "; ".join(issues))
    if execution.test_only and not allow_test_only:
        raise ValueError("test-only or synthetic execution cannot enter promotion")
    if execution.compiled_experiment_sha256 != protocol.execution_plan_sha256:
        raise ValueError("execution plan SHA-256 mismatch")
    if execution.sample_sha256 != protocol.sample_sha256:
        raise ValueError("execution sample SHA-256 mapping mismatch")
    context = execution.as_dict().get("execution_context")
    if not isinstance(context, dict):
        raise ValueError("execution_context must be an object")
    expected_context: dict[str, object] = {
        "protocol_v2_sha256": protocol.record_sha256,
        "formula_build_sha256": protocol.formula_build_sha256,
        "schedule_sha256": protocol.schedule_sha256,
        "participant_scope": protocol.participant_scope.value,
        "assessor_ids": list(protocol.assessor_ids),
        "repeat_ids": list(protocol.repeat_ids),
        "session_ids": list(protocol.session_ids),
        "session_sequence_ids": [list(item) for item in protocol.session_sequence_ids],
        "timepoints_seconds": list(protocol.timepoints_seconds),
        "endpoint_ids": [
            protocol.primary_endpoint.value,
            *(item.value for item in protocol.secondary_endpoints),
        ],
        "deviation_policy_sha256": protocol.deviation_policy_sha256,
        "washout_seconds": protocol.washout_seconds,
        "maximum_exposures_per_session": protocol.maximum_exposures_per_session,
        "apparatus_id": protocol.apparatus_id,
        "apparatus_qualification_sha256": protocol.apparatus_qualification_sha256,
        "timing_protocol_sha256": protocol.timing_protocol_sha256,
        "stopping_rule": protocol.stopping_rule,
        "safety_stop": protocol.safety_stop,
    }
    for name, expected in expected_context.items():
        if context.get(name) != expected:
            raise ValueError(f"execution {name} does not match V2 protocol")
    deviations_sha256 = sha256_hex(canonical_json_bytes(list(execution.deviations)))
    return ProtocolExecutionBindingV2(
        protocol_sha256=protocol.record_sha256,
        execution_receipt_sha256=execution.record_sha256,
        execution_plan_sha256=protocol.execution_plan_sha256,
        formula_build_sha256=protocol.formula_build_sha256,
        sample_sha256=protocol.sample_sha256,
        schedule_sha256=protocol.schedule_sha256,
        deviation_policy_sha256=protocol.deviation_policy_sha256,
        deviations_sha256=deviations_sha256,
        state="HOLD_DEVIATION" if execution.deviations else "BOUND_NO_AUTHORITY",
        test_only=execution.test_only,
    )


def validate_protocol(protocol: PreregisteredProtocolV1) -> tuple[str, ...]:
    issues: list[str] = []
    arm_ids = tuple(arm.arm_id for arm in protocol.arms)
    if "CONTROL" not in arm_ids:
        issues.append("CONTROL arm is required")
    if len(arm_ids) != len(set(arm_ids)):
        issues.append("arm IDs must be unique")
    if len({arm.blind_code for arm in protocol.arms}) != len(protocol.arms):
        issues.append("blind codes must be unique")
    if len({arm.total_active_mass_g for arm in protocol.arms}) != 1:
        issues.append("all arms require matched total active mass")
    if protocol.design_class is ProtocolDesignClass.TWO_FACTOR_FOUR_ARM_MIXTURE and arm_ids != (
        "CONTROL",
        "A",
        "B",
        "A_X_B",
    ):
        issues.append("two-factor mixture requires complete CONTROL/A/B/A_X_B arms")
    expected_schedule = generate_williams_schedule(arm_ids).schedule_sha256
    if protocol.schedule_sha256 != expected_schedule:
        issues.append("schedule hash does not match Williams-balanced arms")
    if protocol.primary_endpoint in protocol.secondary_endpoints:
        issues.append("primary and secondary endpoints must be separate")
    return tuple(issues)


def ingest_physical_results(
    protocol: PreregisteredProtocolV1,
    result: Mapping[str, object],
) -> dict[str, object]:
    """Bind prospective results without interpolation or claim promotion."""

    if result.get("synthetic") is True or result.get("test_only") is True:
        raise PhysicalEvidenceIntakeError(
            "synthetic or test-only results cannot enter physical evidence"
        )
    exact = {
        "protocol_sha256": protocol.record_sha256,
        "formula_build_sha256": protocol.formula_build_sha256,
        "dose_receipt_sha256": protocol.dose_receipt_sha256,
        "inventory_sha256": protocol.inventory_sha256,
        "schedule_sha256": protocol.schedule_sha256,
    }
    for name, expected in exact.items():
        if result.get(name) != expected:
            label = "protocol hash" if name == "protocol_sha256" else name
            raise PhysicalEvidenceIntakeError(f"{label} mismatch")
    samples = result.get("sample_sha256")
    if not isinstance(samples, Mapping) or dict(protocol.sample_sha256) != dict(samples):
        raise PhysicalEvidenceIntakeError("sample SHA-256 mapping mismatch")
    assessors = result.get("assessor_ids")
    if not isinstance(assessors, list) or not assessors:
        raise PhysicalEvidenceIntakeError("assessor_ids are required")
    observations = result.get("observations")
    if not isinstance(observations, list):
        raise PhysicalEvidenceIntakeError("observations must be a list")
    observed_ids = {
        str(item.get("observation_id"))
        for item in observations
        if isinstance(item, Mapping) and item.get("observation_id") is not None
    }
    expected_ids = result.get("expected_observation_ids", [])
    if not isinstance(expected_ids, list):
        raise PhysicalEvidenceIntakeError("expected_observation_ids must be a list")
    return {
        "schema_version": "solforge_physical_evidence_intake_v1",
        "protocol_sha256": protocol.record_sha256,
        "observations": observations,
        "missing_observation_ids": sorted(set(map(str, expected_ids)) - observed_ids),
        "interpolated_observation_count": 0,
        "physical_claim_authorized": False,
        "sensory_claim_authorized": False,
        "hedonic_claim_authorized": False,
        "release_authorized": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--templates", type=Path, required=True)
    build.add_argument("--template-id", required=True)
    build.add_argument("--bindings", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--protocol", type=Path, required=True)
    build_v2 = subparsers.add_parser("build-v2")
    build_v2.add_argument("--templates", type=Path, required=True)
    build_v2.add_argument("--template-id", required=True)
    build_v2.add_argument("--bindings", type=Path, required=True)
    build_v2.add_argument("--output", type=Path, required=True)
    validate_v2 = subparsers.add_parser("validate-v2")
    validate_v2.add_argument("--protocol", type=Path, required=True)
    ingest = subparsers.add_parser("ingest-results")
    ingest.add_argument("--protocol", type=Path, required=True)
    ingest.add_argument("--results", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.action in {"build", "build-v2"}:
        loader = (
            load_protocol_templates_v2
            if args.action == "build-v2"
            else load_protocol_templates
        )
        template = next(
            item
            for item in loader(args.templates)
            if item.template_id == args.template_id
        )
        bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        if args.action == "build-v2":
            if not isinstance(template, ProtocolTemplateV2):
                raise TypeError("V2 loader returned an invalid template")
            payload = build_protocol_v2(template, bindings).as_dict()
        else:
            if not isinstance(template, ProtocolTemplateV1):
                raise TypeError("V1 loader returned an invalid template")
            payload = build_protocol(template, bindings).as_dict()
    else:
        raw_protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
        if args.action == "validate-v2":
            protocol_v2 = PreregisteredProtocolV2.from_dict(raw_protocol)
            issues = validate_protocol_v2(protocol_v2)
            if issues:
                raise PhysicalEvidenceIntakeError("; ".join(issues))
            return 0
        protocol = PreregisteredProtocolV1.from_dict(raw_protocol)
        if args.action == "validate":
            issues = validate_protocol(protocol)
            if issues:
                raise PhysicalEvidenceIntakeError("; ".join(issues))
            return 0
        results = json.loads(args.results.read_text(encoding="utf-8"))
        payload = ingest_physical_results(protocol, results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "PROTOCOL_AUTHORITY_FLAGS",
    "V2_COUNTERBALANCING_METHOD",
    "V2_TIE_SEMANTICS",
    "ParticipantScopeV2",
    "PhysicalEvidenceIntakeError",
    "PreregisteredProtocolV1",
    "PreregisteredProtocolV2",
    "ProtocolAnalysisUnitV2",
    "ProtocolArmV1",
    "ProtocolDesignClass",
    "ProtocolEndpointV2",
    "ProtocolExecutionBindingV2",
    "ProtocolTemplateV1",
    "ProtocolTemplateV2",
    "build_protocol",
    "build_protocol_v2",
    "bind_protocol_execution_v2",
    "ingest_physical_results",
    "load_protocol_templates",
    "load_protocol_templates_v2",
    "validate_protocol",
    "validate_protocol_v2",
]
