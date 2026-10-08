"""Claim-scoped admission firewall for Complex Perfumery model candidates.

The M0-M16 map is noncompensatory.  Formula-bearing packets additionally bind
to the native ppm/ODT/OAV and pre-mix guards.  Passing this diagnostic contract
never authorizes formula mutation, physical execution, safety, or release.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_formula_hash, stable_json_hash

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class ComplexityClaimScope(str, Enum):
    DESIGN = "DESIGN"
    EMPIRICAL_MECHANISM = "EMPIRICAL_MECHANISM"
    TEMPORAL = "TEMPORAL"
    SPATIAL_MATRIX = "SPATIAL_MATRIX"
    ANALYTICAL = "ANALYTICAL"
    PHYSICAL_RELEASE = "PHYSICAL_RELEASE"
    PRODUCTION = "PRODUCTION"
    CANONICAL = "CANONICAL"


class ComplexityGateState(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    CONFLICT_HOLD = "CONFLICT_HOLD"
    FAIL = "FAIL"
    REBUILD = "REBUILD"
    NOT_RUN = "NOT_RUN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ComplexityAdmissionState(str, Enum):
    INVALID_PACKET = "INVALID_PACKET"
    HOLD = "HOLD"
    DESIGN_REGISTRY_ADMITTED = "DESIGN_REGISTRY_ADMITTED"
    EMPIRICAL_SCOPE_CANDIDATE = "EMPIRICAL_SCOPE_CANDIDATE"
    ANALYTICAL_SCOPE_CANDIDATE = "ANALYTICAL_SCOPE_CANDIDATE"
    PHYSICAL_RELEASE_CANDIDATE = "PHYSICAL_RELEASE_CANDIDATE"
    PRODUCTION_CANDIDATE = "PRODUCTION_CANDIDATE"
    CANONICAL_MODEL_CANDIDATE = "CANONICAL_MODEL_CANDIDATE"


_REQUIRED_GATES: Mapping[ComplexityClaimScope, frozenset[str]] = {
    ComplexityClaimScope.DESIGN: frozenset({"M0", "M1", "M5", "M16"}),
    ComplexityClaimScope.EMPIRICAL_MECHANISM: frozenset(
        {f"M{index}" for index in range(13)} | {"M16"}
    ),
    ComplexityClaimScope.TEMPORAL: frozenset(
        {f"M{index}" for index in range(13)} | {"M16"}
    ),
    ComplexityClaimScope.SPATIAL_MATRIX: frozenset(
        {f"M{index}" for index in range(13)} | {"M16"}
    ),
    ComplexityClaimScope.ANALYTICAL: frozenset(
        {"M0", "M1", "M2", "M3", "M4", "M5", "M7", "M12", "M13", "M14", "M16"}
    ),
    ComplexityClaimScope.PHYSICAL_RELEASE: frozenset(
        {f"M{index}" for index in range(14)} | {"M16"}
    ),
    ComplexityClaimScope.PRODUCTION: frozenset(
        {f"M{index}" for index in range(16)} | {"M16"}
    ),
    ComplexityClaimScope.CANONICAL: frozenset({f"M{index}" for index in range(17)}),
}

_EVIDENCE_SCOPES = frozenset(set(ComplexityClaimScope) - {ComplexityClaimScope.DESIGN})
_STRICT_OAV_SCOPES = frozenset(
    {
        ComplexityClaimScope.ANALYTICAL,
        ComplexityClaimScope.PHYSICAL_RELEASE,
        ComplexityClaimScope.PRODUCTION,
        ComplexityClaimScope.CANONICAL,
    }
)
_HARD_GATE_STATES = frozenset(
    {
        ComplexityGateState.HOLD,
        ComplexityGateState.CONFLICT_HOLD,
        ComplexityGateState.FAIL,
        ComplexityGateState.REBUILD,
    }
)


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


def _unique_text(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    normalized = tuple(_text(value, field_name) for value in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must contain unique values")
    return normalized


def required_complexity_gates(scope: ComplexityClaimScope) -> frozenset[str]:
    if not isinstance(scope, ComplexityClaimScope):
        raise TypeError("scope must be a ComplexityClaimScope")
    return _REQUIRED_GATES[scope]


@dataclass(frozen=True, slots=True)
class ComplexityGateEvidence:
    gate_id: str
    state: ComplexityGateState
    evidence_links: tuple[str, ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        gate_id = _text(self.gate_id, "gate_id")
        if re.fullmatch(r"M(?:[0-9]|1[0-6])", gate_id) is None:
            raise ValueError("gate_id must be M0 through M16")
        if not isinstance(self.state, ComplexityGateState):
            raise TypeError("state must be a ComplexityGateState")
        object.__setattr__(self, "gate_id", gate_id)
        object.__setattr__(
            self,
            "evidence_links",
            _unique_text(self.evidence_links, "evidence_links"),
        )
        if self.reason is not None:
            object.__setattr__(self, "reason", _text(self.reason, "reason"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "state": self.state.value,
            "evidence_links": list(self.evidence_links),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class OAVGateBinding:
    """Receipt-bound OAV screen for one exact formula state."""

    formula_sha256: str
    dose_receipt_sha256: str
    oav_result_sha256: str
    quantitative_ppm_status: str
    odt_authority_status: str
    odt_coverage_status: str
    natural_composite_coverage_status: str
    headspace_scope_status: str
    receipt_binding_status: str
    strict_oav_status: str
    pre_mix_gate_status: str
    planned_active_equivalence_status: str
    formula_is_revision: bool
    parent_formula_sha256: str | None = None
    oav_per_time_role: str = "SCREENING_ONLY"
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for field_name in (
            "formula_sha256",
            "dose_receipt_sha256",
            "oav_result_sha256",
        ):
            object.__setattr__(self, field_name, _sha256(getattr(self, field_name), field_name))
        if not isinstance(self.formula_is_revision, bool):
            raise TypeError("formula_is_revision must be bool")
        if self.parent_formula_sha256 is not None:
            object.__setattr__(
                self,
                "parent_formula_sha256",
                _sha256(self.parent_formula_sha256, "parent_formula_sha256"),
            )
        if self.formula_is_revision and self.parent_formula_sha256 is None:
            raise ValueError("a revised formula requires its immediate parent hash")
        for field_name in (
            "quantitative_ppm_status",
            "odt_authority_status",
            "odt_coverage_status",
            "natural_composite_coverage_status",
            "headspace_scope_status",
            "receipt_binding_status",
            "strict_oav_status",
            "pre_mix_gate_status",
            "planned_active_equivalence_status",
            "oav_per_time_role",
        ):
            object.__setattr__(
                self,
                field_name,
                _text(getattr(self, field_name), field_name).upper(),
            )
        if self.oav_per_time_role != "SCREENING_ONLY":
            raise ValueError("oav_per_time_role must remain SCREENING_ONLY")

    @property
    def screening_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        required_pass = {
            "quantitative_ppm_status": self.quantitative_ppm_status,
            "odt_authority_status": self.odt_authority_status,
            "odt_coverage_status": self.odt_coverage_status,
            "natural_composite_coverage_status": self.natural_composite_coverage_status,
            "headspace_scope_status": self.headspace_scope_status,
            "pre_mix_gate_status": self.pre_mix_gate_status,
        }
        for field_name, state in required_pass.items():
            if state != "PASS":
                blockers.append(f"{field_name} must be PASS, got {state}")
        if self.receipt_binding_status != "BOUND_GATE_RECEIPT":
            blockers.append("receipt_binding_status must be BOUND_GATE_RECEIPT")
        if self.formula_is_revision:
            if self.planned_active_equivalence_status != "PASS":
                blockers.append(
                    "revised formula planned_active_equivalence_status must be PASS"
                )
        elif self.planned_active_equivalence_status not in {
            "PASS",
            "NOT_APPLICABLE_NEW_FORMULA",
        }:
            blockers.append(
                "new formula planned_active_equivalence_status must be PASS or NOT_APPLICABLE_NEW_FORMULA"
            )
        return tuple(blockers)

    @property
    def strict_blockers(self) -> tuple[str, ...]:
        blockers = list(self.screening_blockers)
        if self.strict_oav_status != "COMPUTED":
            blockers.append(
                "strict_oav_status must be COMPUTED from compatible measured air and ODT evidence"
            )
        return tuple(blockers)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "formula_sha256": self.formula_sha256,
            "dose_receipt_sha256": self.dose_receipt_sha256,
            "oav_result_sha256": self.oav_result_sha256,
            "quantitative_ppm_status": self.quantitative_ppm_status,
            "odt_authority_status": self.odt_authority_status,
            "odt_coverage_status": self.odt_coverage_status,
            "natural_composite_coverage_status": self.natural_composite_coverage_status,
            "headspace_scope_status": self.headspace_scope_status,
            "receipt_binding_status": self.receipt_binding_status,
            "strict_oav_status": self.strict_oav_status,
            "pre_mix_gate_status": self.pre_mix_gate_status,
            "planned_active_equivalence_status": self.planned_active_equivalence_status,
            "formula_is_revision": self.formula_is_revision,
            "parent_formula_sha256": self.parent_formula_sha256,
            "oav_per_time_role": self.oav_per_time_role,
            "release_authority": self.release_authority,
        }
        payload["binding_sha256"] = stable_json_hash(payload)
        return payload

    @classmethod
    def from_native_results(
        cls,
        *,
        formula_sha256: str,
        oav_result: object,
        preflight_report: object,
        pre_mix_report: object,
        planned_active_equivalence_status: str,
        formula_is_revision: bool,
        parent_formula_sha256: str | None = None,
    ) -> "OAVGateBinding":
        """Bind the firewall to actual native gate result objects."""

        from engine.fuckups.pre_mix_guard import PreMixGuardReport
        from engine.pipeline.oav_authority import OAVAuthorityResult
        from engine.pipeline.preflight import PreflightReport

        if not isinstance(oav_result, OAVAuthorityResult):
            raise TypeError("oav_result must be an OAVAuthorityResult")
        if not isinstance(preflight_report, PreflightReport):
            raise TypeError("preflight_report must be a PreflightReport")
        if not isinstance(pre_mix_report, PreMixGuardReport):
            raise TypeError("pre_mix_report must be a PreMixGuardReport")
        dose_receipt_sha256 = oav_result.state.dose_receipt_sha256
        if dose_receipt_sha256 is None:
            raise ValueError("native OAV result lacks a bound dose receipt")
        native_formula_sha256 = stable_formula_hash(
            oav_result.request.formula_name,
            oav_result.request.ingredients_ul,
            oav_result.request.dilutions,
        )
        if _sha256(formula_sha256, "formula_sha256") != native_formula_sha256:
            raise ValueError(
                "formula_sha256 does not match the exact formula analyzed by native OAV"
            )
        checks = {item.name: item.status for item in preflight_report.checks}
        required_checks = {
            "formula_dose_receipt",
            "quantitative_authority",
            "odt_authority",
            "natural_composite_coverage",
            "headspace_scope",
        }
        missing = sorted(required_checks - set(checks))
        if missing:
            raise ValueError("preflight report lacks checks: " + ", ".join(missing))
        receipt_check = next(item for item in preflight_report.checks
                             if item.name == "formula_dose_receipt")
        receipt_is_bound = (
            receipt_check.status == "PASS"
            and receipt_check.data.get("receipt_sha256") == dose_receipt_sha256
            and oav_result.state.dose_receipt_status == "BOUND"
        )
        return cls(
            formula_sha256=formula_sha256,
            dose_receipt_sha256=dose_receipt_sha256,
            oav_result_sha256=stable_json_hash(oav_result.as_dict()),
            quantitative_ppm_status=checks["quantitative_authority"],
            odt_authority_status=checks["odt_authority"],
            odt_coverage_status=str(oav_result.odt_coverage.get("status") or "MISSING"),
            natural_composite_coverage_status=checks["natural_composite_coverage"],
            headspace_scope_status=checks["headspace_scope"],
            receipt_binding_status=("BOUND_GATE_RECEIPT" if receipt_is_bound else "UNBOUND_OR_ABSTAINED"),
            # The current native OAV request contains formula inputs, not an
            # admitted measured delivered-air/threshold pair. Never promote a
            # simulated screening result to the strict measurement endpoint.
            strict_oav_status="ABSTAINED",
            pre_mix_gate_status=pre_mix_report.status,
            planned_active_equivalence_status=planned_active_equivalence_status,
            formula_is_revision=formula_is_revision,
            parent_formula_sha256=parent_formula_sha256,
        )


@dataclass(frozen=True, slots=True)
class ComplexityModelAdmissionPacket:
    model_id: str
    version: str
    claim_scope: ComplexityClaimScope
    parent_model_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    supersession_state: str
    gate_evidence: tuple[ComplexityGateEvidence, ...]
    formula_sha256: str | None = None
    oav_binding: OAVGateBinding | None = None
    repository_canary_pass: bool = False
    no_scalar_compensation: bool = True
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _text(self.model_id, "model_id"))
        object.__setattr__(self, "version", _text(self.version, "version"))
        if not isinstance(self.claim_scope, ComplexityClaimScope):
            raise TypeError("claim_scope must be a ComplexityClaimScope")
        object.__setattr__(
            self,
            "parent_model_ids",
            _unique_text(self.parent_model_ids, "parent_model_ids"),
        )
        object.__setattr__(
            self,
            "source_hashes",
            tuple(_sha256(value, "source_hashes") for value in self.source_hashes),
        )
        if not self.source_hashes:
            raise ValueError("source_hashes must not be empty")
        object.__setattr__(
            self,
            "supersession_state",
            _text(self.supersession_state, "supersession_state"),
        )
        if not self.gate_evidence:
            raise ValueError("gate_evidence must not be empty")
        gate_ids = tuple(item.gate_id for item in self.gate_evidence)
        if len(gate_ids) != len(set(gate_ids)):
            raise ValueError("gate_evidence contains duplicate gate IDs")
        if self.formula_sha256 is not None:
            object.__setattr__(
                self,
                "formula_sha256",
                _sha256(self.formula_sha256, "formula_sha256"),
            )
        if self.oav_binding is not None and not isinstance(
            self.oav_binding, OAVGateBinding
        ):
            raise TypeError("oav_binding must be an OAVGateBinding")
        if not isinstance(self.repository_canary_pass, bool):
            raise TypeError("repository_canary_pass must be bool")
        if self.no_scalar_compensation is not True:
            raise ValueError("no_scalar_compensation must be true")

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "claim_scope": self.claim_scope.value,
            "parent_model_ids": list(self.parent_model_ids),
            "source_hashes": list(self.source_hashes),
            "supersession_state": self.supersession_state,
            "gate_evidence": [item.as_dict() for item in self.gate_evidence],
            "formula_sha256": self.formula_sha256,
            "oav_binding": self.oav_binding.as_dict() if self.oav_binding else None,
            "repository_canary_pass": self.repository_canary_pass,
            "no_scalar_compensation": self.no_scalar_compensation,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "release_authority": self.release_authority,
        }


@dataclass(frozen=True, slots=True)
class ComplexityModelAdmissionResult:
    state: ComplexityAdmissionState
    model_id: str
    claim_scope: ComplexityClaimScope
    required_gates: tuple[str, ...]
    gate_failures: tuple[str, ...]
    packet_failures: tuple[str, ...]
    oav_gate_state: str
    oav_blockers: tuple[str, ...]
    input_sha256: str
    formula_mutation_authorized: bool = field(default=False, init=False)
    physical_execution_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "state": self.state.value,
            "model_id": self.model_id,
            "claim_scope": self.claim_scope.value,
            "required_gates": list(self.required_gates),
            "gate_failures": list(self.gate_failures),
            "packet_failures": list(self.packet_failures),
            "oav_gate_state": self.oav_gate_state,
            "oav_blockers": list(self.oav_blockers),
            "input_sha256": self.input_sha256,
            "formula_mutation_authorized": self.formula_mutation_authorized,
            "physical_execution_authorized": self.physical_execution_authorized,
            "release_authority": self.release_authority,
        }
        payload["result_sha256"] = stable_json_hash(payload)
        return payload


def evaluate_complexity_model_admission(
    packet: ComplexityModelAdmissionPacket,
) -> ComplexityModelAdmissionResult:
    """Evaluate one model packet with no scalar gate compensation."""

    if not isinstance(packet, ComplexityModelAdmissionPacket):
        raise TypeError("packet must be a ComplexityModelAdmissionPacket")
    required = required_complexity_gates(packet.claim_scope)
    evidence = {item.gate_id: item for item in packet.gate_evidence}
    packet_failures: list[str] = []
    gate_failures: list[str] = []
    missing = sorted(required - set(evidence), key=lambda value: int(value[1:]))
    if missing:
        packet_failures.append("missing required gates: " + ", ".join(missing))
    for gate_id in sorted(required & set(evidence), key=lambda value: int(value[1:])):
        item = evidence[gate_id]
        if item.state in _HARD_GATE_STATES:
            gate_failures.append(
                f"{gate_id}={item.state.value}: {item.reason or 'no reason supplied'}"
            )
        elif item.state is ComplexityGateState.NOT_RUN:
            gate_failures.append(f"{gate_id}=NOT_RUN")
        elif item.state is ComplexityGateState.NOT_APPLICABLE:
            gate_failures.append(f"{gate_id}=HOLD: a required gate cannot be waived")
        elif (
            item.state is ComplexityGateState.PASS
            and packet.claim_scope in _EVIDENCE_SCOPES
            and not item.evidence_links
        ):
            gate_failures.append(f"{gate_id}=HOLD: PASS requires evidence links")

    oav_blockers: tuple[str, ...] = ()
    if packet.formula_sha256 is None:
        if packet.claim_scope is ComplexityClaimScope.DESIGN:
            oav_state = "NOT_APPLICABLE_NO_FORMULA"
        else:
            oav_state = "HOLD"
            oav_blockers = ("non-design claim scopes require an exact formula hash",)
    elif packet.oav_binding is None:
        oav_state = "HOLD"
        oav_blockers = ("formula-bearing packets require an OAVGateBinding",)
    elif packet.oav_binding.formula_sha256 != packet.formula_sha256:
        oav_state = "HOLD"
        oav_blockers = ("OAV binding formula hash does not match the packet",)
    else:
        oav_blockers = (
            packet.oav_binding.strict_blockers
            if packet.claim_scope in _STRICT_OAV_SCOPES
            else packet.oav_binding.screening_blockers
        )
        oav_state = "PASS" if not oav_blockers else "HOLD"

    if (
        packet.claim_scope is ComplexityClaimScope.CANONICAL
        and not packet.repository_canary_pass
    ):
        gate_failures.append("REPOSITORY=BRIDGE_BLOCKED: canonical scope needs a live canary")

    if packet_failures:
        state = ComplexityAdmissionState.INVALID_PACKET
    elif gate_failures or oav_blockers:
        state = ComplexityAdmissionState.HOLD
    elif packet.claim_scope is ComplexityClaimScope.DESIGN:
        state = ComplexityAdmissionState.DESIGN_REGISTRY_ADMITTED
    elif packet.claim_scope in {
        ComplexityClaimScope.EMPIRICAL_MECHANISM,
        ComplexityClaimScope.TEMPORAL,
        ComplexityClaimScope.SPATIAL_MATRIX,
    }:
        state = ComplexityAdmissionState.EMPIRICAL_SCOPE_CANDIDATE
    elif packet.claim_scope is ComplexityClaimScope.ANALYTICAL:
        state = ComplexityAdmissionState.ANALYTICAL_SCOPE_CANDIDATE
    elif packet.claim_scope is ComplexityClaimScope.PHYSICAL_RELEASE:
        state = ComplexityAdmissionState.PHYSICAL_RELEASE_CANDIDATE
    elif packet.claim_scope is ComplexityClaimScope.PRODUCTION:
        state = ComplexityAdmissionState.PRODUCTION_CANDIDATE
    else:
        state = ComplexityAdmissionState.CANONICAL_MODEL_CANDIDATE

    return ComplexityModelAdmissionResult(
        state=state,
        model_id=packet.model_id,
        claim_scope=packet.claim_scope,
        required_gates=tuple(sorted(required, key=lambda value: int(value[1:]))),
        gate_failures=tuple(gate_failures),
        packet_failures=tuple(packet_failures),
        oav_gate_state=oav_state,
        oav_blockers=oav_blockers,
        input_sha256=stable_json_hash(packet.as_dict()),
    )


__all__ = [
    "ComplexityAdmissionState",
    "ComplexityClaimScope",
    "ComplexityGateEvidence",
    "ComplexityGateState",
    "ComplexityModelAdmissionPacket",
    "ComplexityModelAdmissionResult",
    "OAVGateBinding",
    "evaluate_complexity_model_admission",
    "required_complexity_gates",
]
