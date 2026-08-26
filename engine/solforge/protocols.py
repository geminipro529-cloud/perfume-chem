"""Deterministic preregistration and physical-evidence intake firewall."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from enum import Enum
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
    ingest = subparsers.add_parser("ingest-results")
    ingest.add_argument("--protocol", type=Path, required=True)
    ingest.add_argument("--results", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.action == "build":
        template = next(
            item
            for item in load_protocol_templates(args.templates)
            if item.template_id == args.template_id
        )
        bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        payload = build_protocol(template, bindings).as_dict()
    else:
        protocol = PreregisteredProtocolV1.from_dict(
            json.loads(args.protocol.read_text(encoding="utf-8"))
        )
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
    "PhysicalEvidenceIntakeError",
    "PreregisteredProtocolV1",
    "ProtocolArmV1",
    "ProtocolDesignClass",
    "ProtocolTemplateV1",
    "build_protocol",
    "ingest_physical_results",
    "load_protocol_templates",
    "validate_protocol",
]
