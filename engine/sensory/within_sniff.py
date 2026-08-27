"""Design-only within-sniff sequence contracts with an explicit OAV firewall."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash
from engine.scientific_validation.complexity_model_admission import OAVGateBinding

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class WithinSniffClaimCeiling(str, Enum):
    DESIGN_ONLY = "DESIGN_ONLY"
    OBSERVED_WITHIN_APPARATUS_SCOPE = "OBSERVED_WITHIN_APPARATUS_SCOPE"


class DeliveryApparatusKind(str, Enum):
    PULSE_OLFACTOMETER = "PULSE_OLFACTOMETER"
    DYNAMIC_MULTICHANNEL = "DYNAMIC_MULTICHANNEL"
    STATIC_BLOTTER = "STATIC_BLOTTER"


class WithinSniffState(str, Enum):
    REBUILD = "REBUILD"
    PASS_FOR_DESIGN = "PASS_FOR_DESIGN"
    CONDITIONAL_EMPIRICAL = "CONDITIONAL_EMPIRICAL"


def _text(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{field_name} must not be blank")
    return text


def _sha256(value: object, field_name: str) -> str:
    text = _text(value, field_name).lower()
    if _SHA256_RE.fullmatch(text) is None:
        raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
    return text


def _decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return result


@dataclass(frozen=True, slots=True)
class WithinSniffPulse:
    channel: str
    onset_ms: Decimal
    duration_ms: Decimal
    delivered_mass: Decimal
    delivered_mass_unit: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel", _text(self.channel, "channel"))
        onset = _decimal(self.onset_ms, "onset_ms")
        duration = _decimal(self.duration_ms, "duration_ms")
        mass = _decimal(self.delivered_mass, "delivered_mass")
        if onset < 0:
            raise ValueError("onset_ms must be non-negative")
        if duration <= 0:
            raise ValueError("duration_ms must be positive")
        if mass <= 0:
            raise ValueError("delivered_mass must be positive")
        object.__setattr__(self, "onset_ms", onset)
        object.__setattr__(self, "duration_ms", duration)
        object.__setattr__(self, "delivered_mass", mass)
        object.__setattr__(
            self,
            "delivered_mass_unit",
            _text(self.delivered_mass_unit, "delivered_mass_unit"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "channel": self.channel,
            "onset_ms": str(self.onset_ms),
            "duration_ms": str(self.duration_ms),
            "delivered_mass": str(self.delivered_mass),
            "delivered_mass_unit": self.delivered_mass_unit,
        }


@dataclass(frozen=True, slots=True)
class WithinSniffSequence:
    sequence_id: str
    formula_sha256: str
    apparatus_kind: DeliveryApparatusKind
    apparatus_receipt_sha256: str
    pulses: tuple[WithinSniffPulse, ...]
    counterbalanced_orders: tuple[tuple[str, ...], ...]
    claim_ceiling: WithinSniffClaimCeiling
    matched_total_delivered_mass: bool
    oav_binding: OAVGateBinding
    apparatus_qualified: bool = False
    delivered_mass_receipt_sha256: str | None = None
    evidence_links: tuple[str, ...] = ()
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sequence_id", _text(self.sequence_id, "sequence_id"))
        object.__setattr__(
            self,
            "formula_sha256",
            _sha256(self.formula_sha256, "formula_sha256"),
        )
        if not isinstance(self.apparatus_kind, DeliveryApparatusKind):
            raise TypeError("apparatus_kind must be a DeliveryApparatusKind")
        if not isinstance(self.claim_ceiling, WithinSniffClaimCeiling):
            raise TypeError("claim_ceiling must be a WithinSniffClaimCeiling")
        object.__setattr__(
            self,
            "apparatus_receipt_sha256",
            _sha256(self.apparatus_receipt_sha256, "apparatus_receipt_sha256"),
        )
        if len(self.pulses) < 2:
            raise ValueError("at least two pulses are required")
        if any(not isinstance(item, WithinSniffPulse) for item in self.pulses):
            raise TypeError("pulses must contain WithinSniffPulse values")
        channels = tuple(item.channel for item in self.pulses)
        if len(channels) != len(set(channels)):
            raise ValueError("pulse channels must be unique")
        if len(self.counterbalanced_orders) < 2:
            raise ValueError("at least two counterbalanced orders are required")
        expected = set(channels)
        for order in self.counterbalanced_orders:
            if len(order) != len(channels) or set(order) != expected:
                raise ValueError(
                    "every counterbalanced order must contain each channel exactly once"
                )
        if not isinstance(self.matched_total_delivered_mass, bool):
            raise TypeError("matched_total_delivered_mass must be bool")
        if not isinstance(self.apparatus_qualified, bool):
            raise TypeError("apparatus_qualified must be bool")
        if not isinstance(self.oav_binding, OAVGateBinding):
            raise TypeError("oav_binding must be an OAVGateBinding")
        if self.oav_binding.formula_sha256 != self.formula_sha256:
            raise ValueError("OAV binding formula hash does not match the sequence")
        if self.delivered_mass_receipt_sha256 is not None:
            object.__setattr__(
                self,
                "delivered_mass_receipt_sha256",
                _sha256(
                    self.delivered_mass_receipt_sha256,
                    "delivered_mass_receipt_sha256",
                ),
            )
        links = tuple(_text(item, "evidence_links") for item in self.evidence_links)
        if len(links) != len(set(links)):
            raise ValueError("evidence_links must be unique")
        object.__setattr__(self, "evidence_links", links)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "formula_sha256": self.formula_sha256,
            "apparatus_kind": self.apparatus_kind.value,
            "apparatus_receipt_sha256": self.apparatus_receipt_sha256,
            "pulses": [item.as_dict() for item in self.pulses],
            "counterbalanced_orders": [list(item) for item in self.counterbalanced_orders],
            "claim_ceiling": self.claim_ceiling.value,
            "matched_total_delivered_mass": self.matched_total_delivered_mass,
            "oav_binding": self.oav_binding.as_dict(),
            "apparatus_qualified": self.apparatus_qualified,
            "delivered_mass_receipt_sha256": self.delivered_mass_receipt_sha256,
            "evidence_links": list(self.evidence_links),
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }


@dataclass(frozen=True, slots=True)
class WithinSniffAssessment:
    state: WithinSniffState
    sequence_id: str
    pulse_count: int
    onset_span_ms: Decimal
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    input_sha256: str
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    sensory_authority: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "sequence_id": self.sequence_id,
            "pulse_count": self.pulse_count,
            "onset_span_ms": str(self.onset_span_ms),
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "input_sha256": self.input_sha256,
            "boundary": (
                "A passing design is not a perfume effect. Observed scope still requires "
                "qualified pulse delivery, delivered-mass receipts, receipt-bound strict OAV, "
                "locked evidence, and independent scientific acceptance."
            ),
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "sensory_authority": self.sensory_authority,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def evaluate_within_sniff_sequence(
    sequence: WithinSniffSequence,
) -> WithinSniffAssessment:
    if not isinstance(sequence, WithinSniffSequence):
        raise TypeError("sequence must be a WithinSniffSequence")
    failures: list[str] = []
    warnings: list[str] = []
    if sequence.apparatus_kind is DeliveryApparatusKind.STATIC_BLOTTER:
        failures.append("static blotter is not a within-sniff delivery apparatus")
    if not sequence.matched_total_delivered_mass:
        failures.append("matched_total_delivered_mass must be true")
    failures.extend(
        f"OAV gate: {blocker}" for blocker in sequence.oav_binding.screening_blockers
    )
    first_order = sequence.counterbalanced_orders[0]
    if tuple(reversed(first_order)) not in sequence.counterbalanced_orders[1:]:
        warnings.append("no exact reversed order is present; justify counterbalancing")
    onsets = tuple(item.onset_ms for item in sequence.pulses)
    if onsets != tuple(sorted(onsets)):
        warnings.append("pulse rows are not ordered by onset_ms")

    if sequence.claim_ceiling is WithinSniffClaimCeiling.OBSERVED_WITHIN_APPARATUS_SCOPE:
        if not sequence.apparatus_qualified:
            failures.append("observed scope requires apparatus_qualified=true")
        if sequence.delivered_mass_receipt_sha256 is None:
            failures.append("observed scope requires a delivered-mass receipt")
        if not sequence.evidence_links:
            failures.append("observed scope requires evidence links")
        if sequence.oav_binding.strict_oav_status != "COMPUTED":
            failures.append("observed scope requires receipt-bound strict OAV=COMPUTED")

    if failures:
        state = WithinSniffState.REBUILD
    elif sequence.claim_ceiling is WithinSniffClaimCeiling.DESIGN_ONLY:
        state = WithinSniffState.PASS_FOR_DESIGN
    else:
        state = WithinSniffState.CONDITIONAL_EMPIRICAL
    return WithinSniffAssessment(
        state=state,
        sequence_id=sequence.sequence_id,
        pulse_count=len(sequence.pulses),
        onset_span_ms=max(onsets) - min(onsets),
        failures=tuple(failures),
        warnings=tuple(warnings),
        input_sha256=stable_json_hash(sequence.as_dict()),
    )


__all__ = [
    "DeliveryApparatusKind",
    "WithinSniffAssessment",
    "WithinSniffClaimCeiling",
    "WithinSniffPulse",
    "WithinSniffSequence",
    "WithinSniffState",
    "evaluate_within_sniff_sequence",
]
