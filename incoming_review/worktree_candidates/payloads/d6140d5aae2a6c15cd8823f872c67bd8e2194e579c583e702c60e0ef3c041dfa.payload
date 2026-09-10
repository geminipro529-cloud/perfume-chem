"""Closed transport models for the local SolForge Workbench shell."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^sf-[0-9a-f]{32}$")

AUTHORITY_FLAGS_FALSE = {
    "compounding": False,
    "hedonic": False,
    "physical_execution": False,
    "purchase": False,
    "release": False,
    "safety": False,
    "sensory": False,
}


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _AuthorityModel(_ClosedModel):
    authority_flags: dict[str, bool]

    @field_validator("authority_flags")
    @classmethod
    def _all_authority_false(cls, value: dict[str, bool]) -> dict[str, bool]:
        if value != AUTHORITY_FLAGS_FALSE:
            raise ValueError("authority_flags must be the exact all-false mapping")
        return dict(value)


class SolForgeWorkbenchDesignRequestV1(_ClosedModel):
    schema_version: Literal["solforge_workbench_design_request_v1"]
    case: dict[str, Any]
    hypotheses: dict[str, Any]

    @model_validator(mode="after")
    def _validate_packets(self):
        if self.case.get("schema_version") != "solforge_case_v1":
            raise ValueError("case must be solforge_case_v1")
        if self.hypotheses.get("schema_version") != "sol_hypothesis_set_v1":
            raise ValueError("hypotheses must be sol_hypothesis_set_v1")
        for packet in (self.case, self.hypotheses):
            if packet.get("authority_flags") != AUTHORITY_FLAGS_FALSE:
                raise ValueError(
                    "packet authority_flags must be the exact all-false mapping"
                )
        return self


class ArtifactRecordSummaryV1(_ClosedModel):
    filename: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    record_sha256: str
    file_sha256: str

    @field_validator("record_sha256", "file_sha256")
    @classmethod
    def _valid_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("digest must be a lower-case SHA-256")
        return value

    @field_validator("filename")
    @classmethod
    def _basename_only(cls, value: str) -> str:
        if "/" in value or "\\" in value or value in {".", ".."}:
            raise ValueError("filename must be a basename")
        return value


class ArmSummaryV1(_ClosedModel):
    arm_id: str = Field(min_length=1)
    blind_code: str = Field(min_length=1)
    sample_sha256: str
    total_active_mass_g: float = Field(ge=0)
    factor_presence: dict[str, bool]

    @field_validator("sample_sha256")
    @classmethod
    def _valid_sample_sha256(cls, value: str) -> str:
        if not _SHA256_RE.fullmatch(value):
            raise ValueError("sample_sha256 must be a lower-case SHA-256")
        return value


class SolForgeWorkbenchDesignResponseV1(_AuthorityModel):
    schema_version: Literal["solforge_workbench_design_response_v1"]
    run_id: str
    stage: Literal["HELD", "DECIDED", "EXPORTED"]
    history: tuple[str, ...]
    decision: str = Field(min_length=1)
    blockers: tuple[str, ...]
    evidence_limitations: tuple[str, ...]
    next_action: str | None
    registry_sha256: str
    admitted_module_ids: tuple[str, ...]
    compiled_experiment_sha256: str | None
    selected_hypothesis_id: str | None
    delta_kind: str | None
    arms: tuple[ArmSummaryV1, ...]
    inventory_statuses: tuple[tuple[str, str], ...]
    manifest_sha256: str
    records: tuple[ArtifactRecordSummaryV1, ...]
    artifact_download_available: Literal[False]

    @field_validator("run_id")
    @classmethod
    def _valid_run_id(cls, value: str) -> str:
        if not _RUN_ID_RE.fullmatch(value):
            raise ValueError("run_id must be a server-generated SolForge id")
        return value

    @field_validator(
        "registry_sha256", "compiled_experiment_sha256", "manifest_sha256"
    )
    @classmethod
    def _valid_optional_sha256(cls, value: str | None) -> str | None:
        if value is not None and not _SHA256_RE.fullmatch(value):
            raise ValueError("digest must be a lower-case SHA-256")
        return value


class SolForgeWorkbenchStatusV1(_AuthorityModel):
    schema_version: Literal["solforge_workbench_status_v1"]
    ready: bool
    blockers: tuple[str, ...]
    completed_run_count: int = Field(ge=0)
    artifact_bytes: int = Field(ge=0)
    max_runs: int = Field(ge=1)
    max_artifact_bytes: int = Field(ge=1)
    max_concurrent_runs: int = Field(ge=1)
    artifact_download_available: Literal[False]


__all__ = [
    "AUTHORITY_FLAGS_FALSE",
    "ArmSummaryV1",
    "ArtifactRecordSummaryV1",
    "SolForgeWorkbenchDesignRequestV1",
    "SolForgeWorkbenchDesignResponseV1",
    "SolForgeWorkbenchStatusV1",
]
