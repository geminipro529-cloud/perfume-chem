"""Closed module-specific scientific program contracts for SolForge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.conclusions import ConclusionLevel

PROGRAM_AUTHORITY_FLAGS = {
    "formula": False,
    "hedonic": False,
    "physical_execution": False,
    "release": False,
    "safety": False,
    "sensory": False,
}

FORBIDDEN_PROXIES = (
    "ingredient count",
    "formula frequency",
    "supplier prose",
    "price",
    "prestige",
    "oav sum",
    "modeled volatility",
    "darkness",
    "loudness",
    "complexity jargon",
)

_REQUIREMENTS = frozenset(
    {"APPARATUS", "BLINDING", "ORDER", "REPEATABILITY", "SAMPLE_UNIT", "STOPPING"}
)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonblank text")
    return " ".join(value.split())


def _texts(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{name} must be a nonempty sequence")
    return tuple(_text(item, name) for item in value)


@dataclass(frozen=True, slots=True)
class ProgramEndpointV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_program_endpoint_v1"
    endpoint_id: str
    criterion: str
    measure: str
    primary: bool
    physical_observation_required: bool

    def __post_init__(self) -> None:
        for name in ("endpoint_id", "criterion", "measure"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "criterion", self.criterion.upper())
        if not isinstance(self.primary, bool) or not isinstance(
            self.physical_observation_required, bool
        ):
            raise TypeError("endpoint flags must be boolean")

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "endpoint_id": self.endpoint_id,
            "criterion": self.criterion,
            "measure": self.measure,
            "primary": self.primary,
            "physical_observation_required": self.physical_observation_required,
        }

    @classmethod
    def from_dict(cls, payload: object) -> ProgramEndpointV1:
        if not isinstance(payload, dict) or set(payload) != {
            "schema_version",
            "endpoint_id",
            "criterion",
            "measure",
            "primary",
            "physical_observation_required",
        }:
            raise ValueError("endpoint fields do not match the closed schema")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("endpoint schema_version is invalid")
        return cls(**{key: value for key, value in payload.items() if key != "schema_version"})


@dataclass(frozen=True, slots=True)
class ProgramProtocolRequirementV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_program_protocol_requirement_v1"
    requirement_id: str
    requirement: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "requirement_id", _text(self.requirement_id, "requirement_id").upper())
        object.__setattr__(self, "requirement", _text(self.requirement, "requirement"))

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "requirement_id": self.requirement_id,
            "requirement": self.requirement,
        }

    @classmethod
    def from_dict(cls, payload: object) -> ProgramProtocolRequirementV1:
        if not isinstance(payload, dict) or set(payload) != {
            "schema_version",
            "requirement_id",
            "requirement",
        }:
            raise ValueError("protocol requirement fields do not match the closed schema")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("protocol requirement schema_version is invalid")
        return cls(
            requirement_id=payload["requirement_id"],
            requirement=payload["requirement"],
        )


@dataclass(frozen=True, slots=True)
class ScientificProgramV1:
    SCHEMA_VERSION: ClassVar[str] = "solforge_scientific_program_v1"
    program_id: str
    module_id: str
    claim: str
    exact_scope: str
    endpoints: tuple[ProgramEndpointV1, ...]
    primary_endpoint_id: str
    controls: tuple[str, ...]
    failure_criteria: tuple[str, ...]
    protocol_requirements: tuple[ProgramProtocolRequirementV1, ...]
    required_conclusion_level: ConclusionLevel
    result_disposition: str
    source_record_ids: tuple[str, ...]
    forbidden_proxies: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "program_id",
            "module_id",
            "claim",
            "exact_scope",
            "primary_endpoint_id",
            "result_disposition",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        endpoints = tuple(self.endpoints)
        requirements = tuple(self.protocol_requirements)
        if any(not isinstance(item, ProgramEndpointV1) for item in endpoints):
            raise TypeError("endpoints must contain ProgramEndpointV1 values")
        if any(not isinstance(item, ProgramProtocolRequirementV1) for item in requirements):
            raise TypeError(
                "protocol_requirements must contain ProgramProtocolRequirementV1 values"
            )
        object.__setattr__(self, "endpoints", endpoints)
        object.__setattr__(self, "protocol_requirements", requirements)
        for name in (
            "controls",
            "failure_criteria",
            "source_record_ids",
            "forbidden_proxies",
        ):
            object.__setattr__(self, name, _texts(getattr(self, name), name))
        object.__setattr__(
            self, "required_conclusion_level", ConclusionLevel(self.required_conclusion_level)
        )

    @property
    def primary_endpoint(self) -> ProgramEndpointV1:
        matches = [item for item in self.endpoints if item.endpoint_id == self.primary_endpoint_id]
        if len(matches) != 1:
            raise ValueError("primary_endpoint_id does not identify exactly one endpoint")
        return matches[0]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "program_id": self.program_id,
            "module_id": self.module_id,
            "claim": self.claim,
            "exact_scope": self.exact_scope,
            "endpoints": [item.as_dict() for item in self.endpoints],
            "primary_endpoint_id": self.primary_endpoint_id,
            "controls": list(self.controls),
            "failure_criteria": list(self.failure_criteria),
            "protocol_requirements": [
                item.as_dict() for item in self.protocol_requirements
            ],
            "required_conclusion_level": self.required_conclusion_level.value,
            "result_disposition": self.result_disposition,
            "source_record_ids": list(self.source_record_ids),
            "forbidden_proxies": list(self.forbidden_proxies),
            "authority_flags": dict(PROGRAM_AUTHORITY_FLAGS),
        }

    @property
    def record_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.as_dict()))

    @classmethod
    def from_dict(cls, payload: object) -> ScientificProgramV1:
        fields = {
            "program_id",
            "module_id",
            "claim",
            "exact_scope",
            "endpoints",
            "primary_endpoint_id",
            "controls",
            "failure_criteria",
            "protocol_requirements",
            "required_conclusion_level",
            "result_disposition",
            "source_record_ids",
            "forbidden_proxies",
        }
        if not isinstance(payload, dict) or set(payload) != fields | {
            "schema_version",
            "authority_flags",
        }:
            raise ValueError("program fields do not match the closed schema")
        if payload["schema_version"] != cls.SCHEMA_VERSION:
            raise ValueError("program schema_version is invalid")
        if payload["authority_flags"] != PROGRAM_AUTHORITY_FLAGS:
            raise ValueError("authority_flags must be the exact all-false mapping")
        values = {name: payload[name] for name in fields}
        values["endpoints"] = tuple(
            ProgramEndpointV1.from_dict(item) for item in values["endpoints"]
        )
        values["protocol_requirements"] = tuple(
            ProgramProtocolRequirementV1.from_dict(item)
            for item in values["protocol_requirements"]
        )
        for name in (
            "controls",
            "failure_criteria",
            "source_record_ids",
            "forbidden_proxies",
        ):
            values[name] = tuple(values[name])
        return cls(**values)


def evaluate_program_readiness(program: ScientificProgramV1) -> tuple[str, ...]:
    """Evaluate protocol completeness and reject proxy endpoints."""

    issues: list[str] = []
    endpoint_ids = [item.endpoint_id for item in program.endpoints]
    if len(endpoint_ids) != len(set(endpoint_ids)):
        issues.append("duplicate endpoint_id")
    primary = [item for item in program.endpoints if item.primary]
    if len(primary) != 1 or primary[0].endpoint_id != program.primary_endpoint_id:
        issues.append("exactly one declared primary endpoint is required")
    if primary and primary[0].criterion == "LIKING":
        issues.append("LIKING must remain separate from the primary nonhedonic endpoint")
    requirement_ids = {item.requirement_id for item in program.protocol_requirements}
    missing = _REQUIREMENTS.difference(requirement_ids)
    if missing:
        issues.append("missing protocol requirements: " + ", ".join(sorted(missing)))
    if set(program.forbidden_proxies) != set(FORBIDDEN_PROXIES):
        issues.append("forbidden proxy set is incomplete")
    endpoint_text = " ".join(item.measure.casefold() for item in program.endpoints)
    for proxy in FORBIDDEN_PROXIES:
        if proxy in endpoint_text:
            issues.append(f"endpoint uses forbidden proxy: {proxy}")
    return tuple(issues)


def load_scientific_programs(path: Path) -> tuple[ScientificProgramV1, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != (
        "solforge_scientific_programs_v1"
    ):
        raise ValueError("scientific program manifest schema is invalid")
    programs = tuple(ScientificProgramV1.from_dict(item) for item in payload["programs"])
    ids = [item.program_id for item in programs]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate program_id")
    for program in programs:
        issues = evaluate_program_readiness(program)
        if issues:
            raise ValueError(f"{program.program_id}: " + "; ".join(issues))
    return programs


__all__ = [
    "FORBIDDEN_PROXIES",
    "PROGRAM_AUTHORITY_FLAGS",
    "ProgramEndpointV1",
    "ProgramProtocolRequirementV1",
    "ScientificProgramV1",
    "evaluate_program_readiness",
    "load_scientific_programs",
]
