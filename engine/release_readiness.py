"""Axis-separated release readiness without optimistic score blending."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.scientific_contract import EvidenceDescriptor, ScientificClass


class ReadinessStatus(str, Enum):
    READY = "ready"
    READY_WITH_LIMITATIONS = "ready_with_limitations"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class ReadinessInput:
    code_checks_passed: bool
    data_contracts_passed: bool
    local_validation_passed: bool
    migration_verified: bool
    backup_restore_verified: bool
    heldout_sensory_validation_passed: bool
    external_limitations: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReadinessAxis:
    status: ReadinessStatus
    evidence: tuple[str, ...]
    blockers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "evidence": list(self.evidence),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True, slots=True)
class ReleaseReadinessReport:
    laboratory_beta_status: ReadinessStatus
    scientific_release_status: ReadinessStatus
    axes: dict[str, ReadinessAxis]
    external_blockers: tuple[str, ...]
    evidence: EvidenceDescriptor

    def as_dict(self) -> dict[str, object]:
        return {
            "laboratory_beta_status": self.laboratory_beta_status.value,
            "scientific_release_status": self.scientific_release_status.value,
            "axes": {name: axis.as_dict() for name, axis in self.axes.items()},
            "external_blockers": list(self.external_blockers),
            "evidence": self.evidence.as_dict(),
        }


def build_release_readiness(inputs: ReadinessInput) -> ReleaseReadinessReport:
    code = _binary_axis(
        inputs.code_checks_passed,
        "Required code checks passed.",
        "Required code checks have failures or were not fully evaluated.",
    )
    data = _binary_axis(
        inputs.data_contracts_passed,
        "Typed units, provenance, schema, and conservative missing-data contracts passed.",
        "Required data contracts are incomplete or failing.",
    )

    validation_blockers: list[str] = []
    validation_evidence: list[str] = []
    if inputs.local_validation_passed:
        validation_evidence.append("Local deterministic and integration validation passed.")
    else:
        validation_blockers.append("Local validation has failures or was not fully evaluated.")
    if inputs.heldout_sensory_validation_passed:
        validation_evidence.append("Held-out sensory validation beat the declared baseline.")
    else:
        validation_blockers.append("Held-out sensory validation has not passed.")
    validation = ReadinessAxis(
        status=(
            ReadinessStatus.READY
            if not validation_blockers
            else ReadinessStatus.BLOCKED
        ),
        evidence=tuple(validation_evidence),
        blockers=tuple(validation_blockers),
    )

    infrastructure_blockers: list[str] = []
    infrastructure_evidence: list[str] = []
    if inputs.migration_verified:
        infrastructure_evidence.append("Migration drift and upgrade path were verified.")
    else:
        infrastructure_blockers.append("Migration verification has not passed.")
    if inputs.backup_restore_verified:
        infrastructure_evidence.append("Backup, validation, staging, and restore tests passed.")
    else:
        infrastructure_blockers.append("Backup and restore verification has not passed.")
    local_infrastructure_ready = (
        inputs.migration_verified and inputs.backup_restore_verified
    )
    if local_infrastructure_ready:
        infrastructure_evidence.append("Repository-owned full verification passed.")
        infrastructure_status = ReadinessStatus.READY
    else:
        infrastructure_status = ReadinessStatus.BLOCKED
    infrastructure = ReadinessAxis(
        status=infrastructure_status,
        evidence=tuple(infrastructure_evidence),
        blockers=tuple(infrastructure_blockers),
    )

    beta_ready = all(
        (
            inputs.code_checks_passed,
            inputs.data_contracts_passed,
            inputs.local_validation_passed,
            inputs.migration_verified,
            inputs.backup_restore_verified,
        )
    )
    scientific_ready = (
        beta_ready
        and inputs.heldout_sensory_validation_passed
    )
    external_blockers: list[str] = []
    if not inputs.heldout_sensory_validation_passed:
        external_blockers.append("held-out sensory validation is still required")
    external_blockers.extend(inputs.external_limitations)

    return ReleaseReadinessReport(
        laboratory_beta_status=(
            ReadinessStatus.READY if beta_ready else ReadinessStatus.BLOCKED
        ),
        scientific_release_status=(
            ReadinessStatus.READY if scientific_ready else ReadinessStatus.BLOCKED
        ),
        axes={
            "code": code,
            "data": data,
            "validation": validation,
            "infrastructure": infrastructure,
        },
        external_blockers=tuple(dict.fromkeys(external_blockers)),
        evidence=EvidenceDescriptor(
            classification=ScientificClass.EXACT,
            basis="Boolean release gates reported independently by axis without score blending.",
            sources=("engine.release_readiness",),
            limitations=(
                "A ready gate means its declared checks passed; it does not expand their scientific scope.",
            ),
        ),
    )


def _binary_axis(passed: bool, success: str, failure: str) -> ReadinessAxis:
    return ReadinessAxis(
        status=ReadinessStatus.READY if passed else ReadinessStatus.BLOCKED,
        evidence=(success,) if passed else (),
        blockers=() if passed else (failure,),
    )


__all__ = [
    "ReadinessAxis",
    "ReadinessInput",
    "ReadinessStatus",
    "ReleaseReadinessReport",
    "build_release_readiness",
]
