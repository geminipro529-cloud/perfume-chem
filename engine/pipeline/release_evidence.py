"""Noncompensatory release evidence conjunction for Perfume-Chem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.hedonic_evidence import HedonicEvidenceResult, HedonicEvidenceState
from engine.pipeline.oav_evidence import OAVEvidenceResult, OAVEvidenceState

_REQUIRED_AXIS_IDS = (
    "source_rights",
    "target_formula_identity",
    "inventory_lineage",
    "active_dose_rebase",
    "oav_evidence",
    "safety_ifra",
    "laboratory_execution",
    "sensory_evidence",
    "hedonic_evidence",
)

_GATE_ALIASES = {
    "source_rights": ("source_rights", "reference_claim_contract"),
    "target_formula_identity": (
        "target_formula_identity",
        "formula_identity",
        "exact_subtotal",
    ),
    "inventory_lineage": ("inventory_lineage", "inventory_stock_contract"),
    "active_dose_rebase": (
        "active_dose_rebase",
        "formula_state_contract",
        "g15_oav_firewall",
    ),
    "safety_ifra": ("safety_ifra", "safety_ifra_allergen"),
    "laboratory_execution": ("laboratory_execution",),
    "sensory_evidence": ("sensory_evidence",),
}


class EvidenceAxisState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    NOT_TESTED = "NOT_TESTED"
    INVALID = "INVALID"


class ReleaseEvidenceStatus(str, Enum):
    HOLD = "HOLD"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    INVALID = "INVALID"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _sha256(value: object, field_name: str) -> str:
    normalized = _required_text(value, field_name).lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{field_name} must be a SHA-256 hex digest")
    return normalized


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceAxis:
    """One independently evaluated hard release axis."""

    axis_id: str
    state: EvidenceAxisState
    source_sha256: str
    scope: Mapping[str, object]
    blockers: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "axis_id", _required_text(self.axis_id, "axis_id"))
        object.__setattr__(self, "state", EvidenceAxisState(self.state))
        object.__setattr__(
            self,
            "source_sha256",
            _sha256(self.source_sha256, "source_sha256"),
        )
        if not isinstance(self.scope, Mapping):
            raise TypeError("scope must be a mapping")
        object.__setattr__(self, "scope", dict(self.scope))
        object.__setattr__(
            self,
            "blockers",
            tuple(_required_text(value, "blockers") for value in self.blockers),
        )
        object.__setattr__(
            self,
            "limitations",
            tuple(
                _required_text(value, "limitations") for value in self.limitations
            ),
        )
        canonical_json_bytes(self.scope)

    @staticmethod
    def required_axis_ids() -> tuple[str, ...]:
        return _REQUIRED_AXIS_IDS

    def as_dict(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "state": self.state.value,
            "source_sha256": self.source_sha256,
            "scope": dict(self.scope),
            "blockers": self.blockers,
            "limitations": self.limitations,
        }


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceRequest:
    formula_sha256: str
    axes: tuple[ReleaseEvidenceAxis, ...]
    diagnostics: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "formula_sha256",
            _sha256(self.formula_sha256, "formula_sha256"),
        )
        object.__setattr__(self, "axes", tuple(self.axes))
        if not isinstance(self.diagnostics, Mapping):
            raise TypeError("diagnostics must be a mapping")
        object.__setattr__(self, "diagnostics", dict(self.diagnostics))
        canonical_json_bytes(self.diagnostics)


@dataclass(frozen=True, slots=True)
class ReleaseEvidenceResult:
    status: ReleaseEvidenceStatus
    formula_sha256: str
    axes: tuple[ReleaseEvidenceAxis, ...]
    diagnostics: Mapping[str, object]
    blockers: tuple[str, ...]
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "release_evidence_v2",
            "status": self.status.value,
            "formula_sha256": self.formula_sha256,
            "axes": [axis.as_dict() for axis in self.axes],
            "diagnostics": dict(self.diagnostics),
            "blockers": self.blockers,
            "release_authority": self.release_authority,
        }


def evaluate_release_evidence(
    request: ReleaseEvidenceRequest,
) -> ReleaseEvidenceResult:
    """Conjoin hard evidence axes without averaging diagnostic indices."""

    blockers: list[str] = []
    axis_ids = tuple(axis.axis_id for axis in request.axes)
    duplicates = sorted(
        axis_id for axis_id in set(axis_ids) if axis_ids.count(axis_id) > 1
    )
    missing = sorted(set(_REQUIRED_AXIS_IDS).difference(axis_ids))
    unknown = sorted(set(axis_ids).difference(_REQUIRED_AXIS_IDS))
    if duplicates:
        blockers.append("duplicate axes: " + ", ".join(duplicates))
    if missing:
        blockers.append("missing required axes: " + ", ".join(missing))
    if unknown:
        blockers.append("unknown axes: " + ", ".join(unknown))
    for axis in request.axes:
        formula_scope = axis.scope.get("formula_sha256")
        if formula_scope is None:
            blockers.append(f"{axis.axis_id}: formula_sha256 scope is missing")
        elif formula_scope != request.formula_sha256:
            blockers.append(f"{axis.axis_id}: formula_sha256 scope mismatch")

    structurally_invalid = bool(blockers)
    invalid_axes = tuple(
        axis for axis in request.axes if axis.state is EvidenceAxisState.INVALID
    )
    if invalid_axes:
        blockers.extend(
            f"{axis.axis_id}: INVALID" for axis in invalid_axes
        )
    if structurally_invalid or invalid_axes:
        status = ReleaseEvidenceStatus.INVALID
    elif all(axis.state is EvidenceAxisState.PASS for axis in request.axes):
        status = ReleaseEvidenceStatus.READY_FOR_HUMAN_REVIEW
    else:
        status = ReleaseEvidenceStatus.HOLD
        blockers.extend(
            f"{axis.axis_id}: {axis.state.value}"
            for axis in request.axes
            if axis.state is not EvidenceAxisState.PASS
        )
    return ReleaseEvidenceResult(
        status=status,
        formula_sha256=request.formula_sha256,
        axes=tuple(request.axes),
        diagnostics=dict(request.diagnostics),
        blockers=tuple(blockers),
    )


def release_axis_from_oav(result: OAVEvidenceResult) -> ReleaseEvidenceAxis:
    state = {
        OAVEvidenceState.STRICT_MEASURED: EvidenceAxisState.PASS,
        OAVEvidenceState.MODELED_SCREEN: EvidenceAxisState.HOLD,
        OAVEvidenceState.PARTIAL: EvidenceAxisState.HOLD,
        OAVEvidenceState.ABSTAINED: EvidenceAxisState.NOT_TESTED,
        OAVEvidenceState.INVALID: EvidenceAxisState.INVALID,
    }[result.state]
    payload = result.as_dict()
    return ReleaseEvidenceAxis(
        axis_id="oav_evidence",
        state=state,
        source_sha256=sha256_hex(canonical_json_bytes(payload)),
        scope={
            "formula_sha256": result.formula_sha256,
            "dose_receipt_sha256": result.dose_receipt_sha256,
        },
        blockers=result.blockers,
        limitations=result.limitations,
    )


def release_axis_from_hedonic(
    result: HedonicEvidenceResult,
) -> ReleaseEvidenceAxis:
    state = {
        HedonicEvidenceState.VALIDATED_EXACT_SCOPE: EvidenceAxisState.PASS,
        HedonicEvidenceState.NOT_TESTED: EvidenceAxisState.NOT_TESTED,
        HedonicEvidenceState.INSUFFICIENT_EVIDENCE: EvidenceAxisState.HOLD,
        HedonicEvidenceState.DIAGNOSTIC: EvidenceAxisState.HOLD,
        HedonicEvidenceState.FAILED_HELDOUT_BASELINE: EvidenceAxisState.HOLD,
        HedonicEvidenceState.INVALID_OR_CONFOUNDED: EvidenceAxisState.INVALID,
    }[result.state]
    blockers = result.blockers
    if (
        result.state is HedonicEvidenceState.VALIDATED_EXACT_SCOPE
        and result.fit_receipt_sha256 is None
    ):
        state = EvidenceAxisState.INVALID
        blockers = (*blockers, "validated liking is missing its fit receipt hash")
    payload = result.as_dict()
    scope: dict[str, object] = {
        "formula_sha256": result.formula_build_sha256,
        "criterion_id": result.criterion_id,
        "population_scope": result.scope.value,
    }
    if result.fit_receipt_sha256 is not None:
        scope["fit_receipt_sha256"] = result.fit_receipt_sha256
    return ReleaseEvidenceAxis(
        axis_id="hedonic_evidence",
        state=state,
        source_sha256=sha256_hex(canonical_json_bytes(payload)),
        scope=scope,
        blockers=blockers,
        limitations=result.limitations,
    )


def release_axes_from_gate_report(
    gate_report: Mapping[str, object],
    *,
    formula_sha256: str,
) -> tuple[ReleaseEvidenceAxis, ...]:
    """Adapt deterministic gate rows while preserving absent and malformed states."""

    formula_hash = _sha256(formula_sha256, "formula_sha256")
    raw_gates = gate_report.get("gates", ())
    gates = tuple(raw_gates) if isinstance(raw_gates, (tuple, list)) else ()
    by_name = {
        str(gate.get("gate")): gate
        for gate in gates
        if isinstance(gate, Mapping) and gate.get("gate") is not None
    }
    axes: list[ReleaseEvidenceAxis] = []
    for axis_id, aliases in _GATE_ALIASES.items():
        gate = next((by_name[alias] for alias in aliases if alias in by_name), None)
        if gate is None:
            state = EvidenceAxisState.NOT_TESTED
            blockers = ("source gate is absent",)
            source_payload: object = {"axis_id": axis_id, "source": "absent"}
        else:
            raw_status = gate.get("status")
            normalized = (
                str(raw_status).strip().upper().replace(" ", "_")
                if raw_status is not None
                else ""
            )
            state = {
                "PASS": EvidenceAxisState.PASS,
                "FAIL": EvidenceAxisState.HOLD,
                "HOLD": EvidenceAxisState.HOLD,
                "WARN": EvidenceAxisState.HOLD,
                "NOT_TESTED": EvidenceAxisState.NOT_TESTED,
                "NOT_RUN": EvidenceAxisState.NOT_TESTED,
            }.get(normalized, EvidenceAxisState.INVALID)
            blockers = (
                ()
                if state is EvidenceAxisState.PASS
                else (f"source gate status: {normalized or 'MISSING'}",)
            )
            source_payload = dict(gate)
        axes.append(
            ReleaseEvidenceAxis(
                axis_id=axis_id,
                state=state,
                source_sha256=sha256_hex(canonical_json_bytes(source_payload)),
                scope={"formula_sha256": formula_hash},
                blockers=blockers,
            )
        )
    return tuple(axes)


__all__ = [
    "EvidenceAxisState",
    "ReleaseEvidenceAxis",
    "ReleaseEvidenceRequest",
    "ReleaseEvidenceResult",
    "ReleaseEvidenceStatus",
    "evaluate_release_evidence",
    "release_axes_from_gate_report",
    "release_axis_from_hedonic",
    "release_axis_from_oav",
]
