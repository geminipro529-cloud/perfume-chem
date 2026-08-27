"""Strict, planning-only sensory contracts for construction-complexity studies.

This module deliberately lives beside the permissive legacy sensory ledger.
It does not migrate or reinterpret historical observations.  A C0 ``GO``
means only that the exact vocabulary, protocol, and panel-performance exit
contract are satisfied; it never authorizes a human study, a release, or model
calibration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from engine.calibration.hashing import stable_json_hash

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,95}$")
_BLIND_CODE_RE = re.compile(r"^[A-Z0-9]{3,12}$")

CONSTRUCTION_ATTRIBUTE_IDS = (
    "airiness",
    "separability",
    "density",
    "coherence",
    "target_fidelity",
    "contrast",
    "emergence",
    "recognition",
)
HEDONIC_ATTRIBUTE_IDS = ("pleasantness",)
REQUIRED_BINDING_IDS = (
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


def _require_unique(values: tuple[str, ...], field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must be unique")


def _require_finite_decimal(value: Decimal, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{field_name} must be a finite Decimal")


class ExpertiseStratum(str, Enum):
    """Participant strata that must remain distinct in storage and analysis."""

    TRAINED_DESCRIPTIVE = "trained_descriptive"
    PERFUMER_EXPERT = "perfumer_expert"
    UNTRAINED = "untrained"


class StudyPartition(str, Enum):
    PILOT = "pilot"
    CONFIRMATORY = "confirmatory"


class BindingState(str, Enum):
    BOUND = "bound"
    REQUIRED_UNBOUND = "required_unbound"


class GateKind(str, Enum):
    """Separate panel-performance dimensions; none substitutes for another."""

    DISCRIMINATION = "discrimination"
    AGREEMENT = "agreement"
    REPEATABILITY = "repeatability"


class GateAuthority(str, Enum):
    REQUIRED_UNBOUND = "required_unbound"
    PROVISIONAL_PREPILOT = "provisional_prepilot"
    PREREGISTERED_LOCKED = "preregistered_locked"


class GateDirection(str, Enum):
    AT_LEAST = "at_least"
    AT_MOST = "at_most"


class GateOutcome(str, Enum):
    UNMEASURED = "unmeasured"
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


class C0ExitDecision(str, Enum):
    """C0 contract decision, explicitly narrower than study authorization."""

    GO = "go"
    HOLD = "hold"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class ScaleAnchor:
    value: Decimal
    label: str
    operational_definition: str

    def __post_init__(self) -> None:
        _require_finite_decimal(self.value, "anchor value")
        if self.value < 0 or self.value > 10:
            raise ValueError("anchor value must be between 0 and 10")
        _require_text(self.label, "anchor label")
        _require_text(self.operational_definition, "anchor definition")

    def as_dict(self) -> dict[str, str]:
        return {
            "value": str(self.value),
            "label": self.label,
            "operational_definition": self.operational_definition,
        }


@dataclass(frozen=True, slots=True)
class SensoryAttributeDefinition:
    attribute_id: str
    display_name: str
    operational_definition: str
    assessor_prompt: str
    low_anchor: ScaleAnchor
    mid_anchor: ScaleAnchor
    high_anchor: ScaleAnchor
    is_hedonic: bool = False

    def __post_init__(self) -> None:
        _require_identifier(self.attribute_id, "attribute_id")
        _require_text(self.display_name, "display_name")
        _require_text(self.operational_definition, "operational_definition")
        _require_text(self.assessor_prompt, "assessor_prompt")
        if not isinstance(self.is_hedonic, bool):
            raise ValueError("is_hedonic must be boolean")
        if (
            self.low_anchor.value,
            self.mid_anchor.value,
            self.high_anchor.value,
        ) != (Decimal("0"), Decimal("5"), Decimal("10")):
            raise ValueError("C0 attributes require fixed 0, 5, and 10 anchors")

    def as_dict(self) -> dict[str, Any]:
        return {
            "attribute_id": self.attribute_id,
            "display_name": self.display_name,
            "operational_definition": self.operational_definition,
            "assessor_prompt": self.assessor_prompt,
            "low_anchor": self.low_anchor.as_dict(),
            "mid_anchor": self.mid_anchor.as_dict(),
            "high_anchor": self.high_anchor.as_dict(),
            "is_hedonic": self.is_hedonic,
        }


@dataclass(frozen=True, slots=True)
class ConstructionLexicon:
    schema_version: str
    version: int
    attributes: tuple[SensoryAttributeDefinition, ...]
    evidence_basis: tuple[str, ...]
    claims_iso_compliance: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise ValueError("version must be a positive integer")
        if self.version <= 0:
            raise ValueError("version must be a positive integer")
        attribute_ids = tuple(item.attribute_id for item in self.attributes)
        expected = (*CONSTRUCTION_ATTRIBUTE_IDS, *HEDONIC_ATTRIBUTE_IDS)
        if attribute_ids != expected:
            raise ValueError(
                "C0 lexicon attributes must preserve the frozen construction and "
                "hedonic order"
            )
        if any(item.is_hedonic for item in self.attributes[:-1]):
            raise ValueError("construction axes cannot be marked hedonic")
        if not self.attributes[-1].is_hedonic:
            raise ValueError("pleasantness must remain a separate hedonic endpoint")
        if not self.evidence_basis:
            raise ValueError("evidence_basis must not be empty")
        for item in self.evidence_basis:
            _require_text(item, "evidence_basis item")
        _require_unique(self.evidence_basis, "evidence_basis items")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "attributes": [item.as_dict() for item in self.attributes],
            "evidence_basis": list(self.evidence_basis),
            "claims_iso_compliance": self.claims_iso_compliance,
        }

    @property
    def lexicon_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


def _attribute(
    attribute_id: str,
    display_name: str,
    operational_definition: str,
    assessor_prompt: str,
    low_label: str,
    low_definition: str,
    mid_label: str,
    mid_definition: str,
    high_label: str,
    high_definition: str,
    *,
    is_hedonic: bool = False,
) -> SensoryAttributeDefinition:
    return SensoryAttributeDefinition(
        attribute_id=attribute_id,
        display_name=display_name,
        operational_definition=operational_definition,
        assessor_prompt=assessor_prompt,
        low_anchor=ScaleAnchor(Decimal("0"), low_label, low_definition),
        mid_anchor=ScaleAnchor(Decimal("5"), mid_label, mid_definition),
        high_anchor=ScaleAnchor(Decimal("10"), high_label, high_definition),
        is_hedonic=is_hedonic,
    )


def build_c0_construction_lexicon() -> ConstructionLexicon:
    """Return the immutable C0 vocabulary; it contains no empirical results."""

    attributes = (
        _attribute(
            "airiness",
            "Airiness",
            "Perceived spatial openness or room between concurrent odor "
            "impressions, rated separately from strength and diffusion.",
            "How much open sensory space is present between what you smell?",
            "Closed",
            "The impression is compact with no sensed space between elements.",
            "Partly open",
            "Some space is present, while portions remain compact or filled.",
            "Very open",
            "Clear sensory space remains around simultaneously perceived elements.",
        ),
        _attribute(
            "separability",
            "Separability",
            "Ease of perceiving concurrent odor impressions as distinct at the "
            "same time; this is not the number of descriptors named.",
            "How distinctly can concurrent odor impressions be perceived?",
            "Fused",
            "Concurrent impressions cannot be separated perceptually.",
            "Partly separable",
            "Some impressions are distinct and others remain fused.",
            "Clearly separable",
            "Multiple concurrent impressions remain clearly distinct.",
        ),
        _attribute(
            "density",
            "Density",
            "Perceived compactness or filled sensory mass. Density is measured "
            "independently and is not forced to be the inverse of airiness.",
            "How compact or filled does the overall odor impression feel?",
            "Sparse",
            "The odor impression is thin or lightly occupied.",
            "Moderately filled",
            "The odor impression has an intermediate degree of sensory mass.",
            "Very dense",
            "The odor impression is highly compact, continuous, or filled.",
        ),
        _attribute(
            "coherence",
            "Coherence",
            "Degree to which perceived parts seem integrated or intentionally "
            "related, independent of personal liking.",
            "How integrated and intentionally related do the parts seem?",
            "Disjoint",
            "The perceived parts conflict or appear unrelated.",
            "Partly coherent",
            "Some parts integrate while other transitions or relations remain weak.",
            "Highly coherent",
            "The perceived parts form a clear and integrated whole.",
        ),
        _attribute(
            "target_fidelity",
            "Target fidelity",
            "Match to the preregistered target description or physical reference; "
            "the response is not applicable when no target is presented.",
            "How closely does the sample match the declared target?",
            "No match",
            "The declared target is absent or contradicted.",
            "Partial match",
            "Several target features are present but important differences remain.",
            "Very close match",
            "The declared target is represented clearly across its defining features.",
        ),
        _attribute(
            "contrast",
            "Contrast",
            "Perceptual differentiation between preregistered foreground and "
            "background roles or adjacent construction regions.",
            "How clearly is the declared foreground distinguished from its support?",
            "No contrast",
            "Foreground and support cannot be distinguished.",
            "Moderate contrast",
            "Foreground is distinguishable but partially merges with its support.",
            "Strong contrast",
            "Foreground is clearly differentiated while the support remains present.",
        ),
        _attribute(
            "emergence",
            "Emergence",
            "Clarity of a whole-mixture quality not attributable to any separately "
            "presented single component; requires the preregistered comparison.",
            "How clearly does a new whole-mixture quality emerge?",
            "No emergence",
            "No additional whole-mixture quality is perceived.",
            "Possible emergence",
            "A weak or uncertain additional quality is perceived.",
            "Clear emergence",
            "A distinct additional whole-mixture quality is perceived reproducibly.",
        ),
        _attribute(
            "recognition",
            "Recognition confidence",
            "Confidence in selecting the preregistered target. Correctness is "
            "computed from the separate target-choice response, not this rating.",
            "How confident are you in your target choice?",
            "No confidence",
            "No target choice can be made with confidence.",
            "Uncertain",
            "A target choice is possible but remains uncertain.",
            "Very confident",
            "The target choice is clear and made with high confidence.",
        ),
        _attribute(
            "pleasantness",
            "Pleasantness",
            "Personal hedonic response, stored separately from every construction "
            "axis and never used as proof of complexity.",
            "How pleasant or unpleasant is the sample to you?",
            "Extremely unpleasant",
            "The sample is experienced as extremely unpleasant.",
            "Neutral",
            "The sample is neither pleasant nor unpleasant.",
            "Extremely pleasant",
            "The sample is experienced as extremely pleasant.",
            is_hedonic=True,
        ),
    )
    return ConstructionLexicon(
        schema_version="perfume-chem.c0-construction-lexicon.v1",
        version=1,
        attributes=attributes,
        evidence_basis=(
            "ISO 8586:2023 public metadata - assessor selection and training",
            "ISO 11132:2021 public metadata - discrimination, agreement, repeatability",
            "ISO 13299:2016 public metadata - common-attribute sensory profiles",
            "Barkat et al. 2012 - expertise affects configural odor perception",
            "Latreille et al. 2006 - separate sensory-panel performance dimensions",
            "Green et al. 1996 - labeled magnitude scaling evidence",
        ),
    )


@dataclass(frozen=True, slots=True)
class EvidenceBinding:
    binding_id: str
    state: BindingState
    sha256: str | None
    reason: str | None

    def __post_init__(self) -> None:
        _require_identifier(self.binding_id, "binding_id")
        if not isinstance(self.state, BindingState):
            raise ValueError("state must be a BindingState")
        if self.state is BindingState.BOUND:
            if self.sha256 is None:
                raise ValueError("bound evidence requires sha256")
            _require_sha256(self.sha256, "sha256")
            if self.reason is not None:
                raise ValueError("bound evidence cannot carry an unbound reason")
            return
        if self.sha256 is not None:
            raise ValueError("unbound evidence cannot carry sha256")
        if self.reason is None:
            raise ValueError("unbound evidence requires a reason")
        _require_text(self.reason, "unbound evidence reason")

    @classmethod
    def bound(cls, binding_id: str, sha256: str) -> EvidenceBinding:
        return cls(
            binding_id=binding_id,
            state=BindingState.BOUND,
            sha256=sha256,
            reason=None,
        )

    @classmethod
    def required_unbound(cls, binding_id: str, reason: str) -> EvidenceBinding:
        return cls(
            binding_id=binding_id,
            state=BindingState.REQUIRED_UNBOUND,
            sha256=None,
            reason=reason,
        )

    def as_dict(self) -> dict[str, str | None]:
        return {
            "binding_id": self.binding_id,
            "state": self.state.value,
            "sha256": self.sha256,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class PanelGateSpecification:
    gate_id: str
    kind: GateKind
    metric: str
    unit: str | None
    direction: GateDirection | None
    threshold: Decimal | None
    authority: GateAuthority
    success_rule: str
    failure_rule: str
    inconclusive_rule: str
    unbound_reason: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.gate_id, "gate_id")
        _require_text(self.metric, "metric")
        if not isinstance(self.kind, GateKind):
            raise ValueError("kind must be a GateKind")
        if not isinstance(self.authority, GateAuthority):
            raise ValueError("authority must be a GateAuthority")
        if self.direction is not None and not isinstance(
            self.direction, GateDirection
        ):
            raise ValueError("direction must be a GateDirection or None")
        for value, name in (
            (self.success_rule, "success_rule"),
            (self.failure_rule, "failure_rule"),
            (self.inconclusive_rule, "inconclusive_rule"),
        ):
            _require_text(value, name)
        if self.authority is GateAuthority.REQUIRED_UNBOUND:
            if self.unit is not None or self.direction is not None:
                raise ValueError("unbound gate cannot carry a unit or direction")
            if self.threshold is not None:
                raise ValueError("unbound gate cannot carry a threshold")
            if self.unbound_reason is None:
                raise ValueError("unbound gate requires a reason")
            _require_text(self.unbound_reason, "unbound_reason")
            return
        if self.unit is None or self.direction is None or self.threshold is None:
            raise ValueError("bound gate requires unit, direction, and threshold")
        _require_text(self.unit, "unit")
        _require_finite_decimal(self.threshold, "threshold")
        if self.unbound_reason is not None:
            raise ValueError("bound gate cannot carry an unbound reason")

    @classmethod
    def required_unbound(
        cls,
        *,
        gate_id: str,
        kind: GateKind,
        metric: str,
        reason: str,
    ) -> PanelGateSpecification:
        return cls(
            gate_id=gate_id,
            kind=kind,
            metric=metric,
            unit=None,
            direction=None,
            threshold=None,
            authority=GateAuthority.REQUIRED_UNBOUND,
            success_rule="Apply the preregistered success rule after it is locked.",
            failure_rule="Apply the preregistered failure rule after it is locked.",
            inconclusive_rule=(
                "Hold when the preregistered evidence is incomplete or unstable."
            ),
            unbound_reason=reason,
        )

    @classmethod
    def locked(
        cls,
        *,
        gate_id: str,
        kind: GateKind,
        metric: str,
        unit: str,
        direction: GateDirection,
        threshold: Decimal,
        success_rule: str,
        failure_rule: str,
        inconclusive_rule: str,
    ) -> PanelGateSpecification:
        return cls(
            gate_id=gate_id,
            kind=kind,
            metric=metric,
            unit=unit,
            direction=direction,
            threshold=threshold,
            authority=GateAuthority.PREREGISTERED_LOCKED,
            success_rule=success_rule,
            failure_rule=failure_rule,
            inconclusive_rule=inconclusive_rule,
            unbound_reason=None,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "kind": self.kind.value,
            "metric": self.metric,
            "unit": self.unit,
            "direction": self.direction.value if self.direction else None,
            "threshold": str(self.threshold) if self.threshold is not None else None,
            "authority": self.authority.value,
            "success_rule": self.success_rule,
            "failure_rule": self.failure_rule,
            "inconclusive_rule": self.inconclusive_rule,
            "unbound_reason": self.unbound_reason,
        }

    @property
    def spec_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class ConstructionPanelProtocol:
    protocol_id: str
    version: int
    study_partition: StudyPartition
    lexicon_sha256: str
    bindings: tuple[EvidenceBinding, ...]
    panel_gate_specs: tuple[PanelGateSpecification, ...]
    expertise_strata: tuple[ExpertiseStratum, ...]
    timepoints_seconds: tuple[int, ...]
    repeat_count: int
    blinded: bool
    randomized: bool
    individual_scores_preserved: bool
    strata_analyzed_separately: bool
    pilot_confirmatory_separated: bool
    protocol_locked: bool
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    model_calibration_authority: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _require_identifier(self.protocol_id, "protocol_id")
        if isinstance(self.version, bool) or not isinstance(self.version, int):
            raise ValueError("version must be a positive integer")
        if self.version <= 0:
            raise ValueError("version must be a positive integer")
        if not isinstance(self.study_partition, StudyPartition):
            raise ValueError("study_partition must be a StudyPartition")
        _require_sha256(self.lexicon_sha256, "lexicon_sha256")
        binding_ids = tuple(item.binding_id for item in self.bindings)
        if binding_ids != REQUIRED_BINDING_IDS:
            raise ValueError("protocol must contain every required evidence binding")
        gate_kinds = tuple(item.kind for item in self.panel_gate_specs)
        if gate_kinds != tuple(GateKind):
            raise ValueError(
                "protocol must keep discrimination, agreement, and repeatability "
                "as separate gates"
            )
        _require_unique(
            tuple(item.gate_id for item in self.panel_gate_specs),
            "panel gate IDs",
        )
        if len(self.expertise_strata) != len(set(self.expertise_strata)):
            raise ValueError("expertise_strata must be unique")
        if any(
            not isinstance(item, ExpertiseStratum)
            for item in self.expertise_strata
        ):
            raise ValueError("expertise_strata must contain ExpertiseStratum values")
        if (
            ExpertiseStratum.TRAINED_DESCRIPTIVE not in self.expertise_strata
            or ExpertiseStratum.UNTRAINED not in self.expertise_strata
        ):
            raise ValueError("trained and untrained strata must remain distinct")
        if any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in self.timepoints_seconds
        ):
            raise ValueError("timepoints_seconds must contain non-negative integers")
        if tuple(sorted(set(self.timepoints_seconds))) != self.timepoints_seconds:
            raise ValueError("timepoints_seconds must be unique and increasing")
        if isinstance(self.repeat_count, bool) or not isinstance(
            self.repeat_count, int
        ):
            raise ValueError("repeat_count must be a non-negative integer")
        if self.repeat_count < 0:
            raise ValueError("repeat_count must be a non-negative integer")
        for value, name in (
            (self.blinded, "blinded"),
            (self.randomized, "randomized"),
            (self.individual_scores_preserved, "individual_scores_preserved"),
            (self.strata_analyzed_separately, "strata_analyzed_separately"),
            (self.pilot_confirmatory_separated, "pilot_confirmatory_separated"),
            (self.protocol_locked, "protocol_locked"),
        ):
            if not isinstance(value, bool):
                raise ValueError(f"{name} must be boolean")
        if self.protocol_locked:
            lock_errors = self._lock_errors()
            if lock_errors:
                raise ValueError(
                    "protocol cannot be locked: " + "; ".join(lock_errors)
                )

    def _lock_errors(self) -> tuple[str, ...]:
        errors: list[str] = []
        if any(item.state is not BindingState.BOUND for item in self.bindings):
            errors.append("required evidence remains unbound")
        if any(
            item.authority is not GateAuthority.PREREGISTERED_LOCKED
            for item in self.panel_gate_specs
        ):
            errors.append("panel gate threshold is not preregistered and locked")
        if not self.timepoints_seconds:
            errors.append("sniff timepoints are empty")
        if self.repeat_count < 2:
            errors.append("repeat_count must permit repeatability assessment")
        requirements = {
            "blinded": self.blinded,
            "randomized": self.randomized,
            "individual_scores_preserved": self.individual_scores_preserved,
            "strata_analyzed_separately": self.strata_analyzed_separately,
            "pilot_confirmatory_separated": self.pilot_confirmatory_separated,
        }
        errors.extend(name for name, enabled in requirements.items() if not enabled)
        if self.study_partition is not StudyPartition.PILOT:
            errors.append("C0 exit protocol must use the pilot partition")
        return tuple(errors)

    def as_dict(self) -> dict[str, Any]:
        return {
            "protocol_id": self.protocol_id,
            "version": self.version,
            "study_partition": self.study_partition.value,
            "lexicon_sha256": self.lexicon_sha256,
            "bindings": [item.as_dict() for item in self.bindings],
            "panel_gate_specs": [
                item.as_dict() for item in self.panel_gate_specs
            ],
            "expertise_strata": [item.value for item in self.expertise_strata],
            "timepoints_seconds": list(self.timepoints_seconds),
            "repeat_count": self.repeat_count,
            "blinded": self.blinded,
            "randomized": self.randomized,
            "individual_scores_preserved": self.individual_scores_preserved,
            "strata_analyzed_separately": self.strata_analyzed_separately,
            "pilot_confirmatory_separated": self.pilot_confirmatory_separated,
            "protocol_locked": self.protocol_locked,
            "study_authorized": self.study_authorized,
            "release_authority": self.release_authority,
            "model_calibration_authority": self.model_calibration_authority,
        }

    @property
    def protocol_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


def build_c0_protocol_draft(
    lexicon: ConstructionLexicon,
) -> ConstructionPanelProtocol:
    """Build a fail-closed draft with no invented thresholds or study authority."""

    binding_reasons = {
        "sample_manifest": (
            "Bind opaque blind codes to the custodian-only sample manifest."
        ),
        "preparation_dose_ppm_manifest": (
            "Bind matrix, concentrate ppm, active application dose, substrate, "
            "and preparation procedure."
        ),
        "formula_oav_manifest": (
            "Bind the formula-level ODT/OAV screening receipt for every dosed sample."
        ),
        "randomization_manifest": (
            "Bind sequence generation, allocation concealment, and carryover rules."
        ),
        "anchor_reference_manifest": (
            "Bind physical references and training anchors for every attribute."
        ),
        "participant_plan": (
            "Bind eligibility, expertise strata, screening, training, and repeats."
        ),
        "environment_timing_manifest": (
            "Bind room conditions, sniff timing, ventilation, and session limits."
        ),
        "analysis_plan": (
            "Bind estimands, missing-data handling, multiplicity, and stop/go rules."
        ),
        "ethics_privacy_safety_review": (
            "Bind applicable consent, privacy, exposure-safety, and review receipts."
        ),
    }
    gate_metrics = {
        GateKind.DISCRIMINATION: (
            "panel discrimination metric selected by the locked analysis plan"
        ),
        GateKind.AGREEMENT: (
            "panel agreement metric selected by the locked analysis plan"
        ),
        GateKind.REPEATABILITY: (
            "panel repeatability metric selected by the locked analysis plan"
        ),
    }
    return ConstructionPanelProtocol(
        protocol_id="perfume-chem-c0-construction-panel",
        version=1,
        study_partition=StudyPartition.PILOT,
        lexicon_sha256=lexicon.lexicon_sha256,
        bindings=tuple(
            EvidenceBinding.required_unbound(item, binding_reasons[item])
            for item in REQUIRED_BINDING_IDS
        ),
        panel_gate_specs=tuple(
            PanelGateSpecification.required_unbound(
                gate_id=f"c0-{kind.value}-required",
                kind=kind,
                metric=gate_metrics[kind],
                reason=(
                    "Select and preregister the threshold from prepilot evidence; "
                    "no universal value is encoded."
                ),
            )
            for kind in GateKind
        ),
        expertise_strata=(
            ExpertiseStratum.TRAINED_DESCRIPTIVE,
            ExpertiseStratum.PERFUMER_EXPERT,
            ExpertiseStratum.UNTRAINED,
        ),
        timepoints_seconds=(),
        repeat_count=0,
        blinded=True,
        randomized=True,
        individual_scores_preserved=True,
        strata_analyzed_separately=True,
        pilot_confirmatory_separated=True,
        protocol_locked=False,
    )


@dataclass(frozen=True, slots=True)
class ParticipantQualificationReceipt:
    """Pseudonymous receipts only; raw identity and health data stay elsewhere."""

    participant_token_sha256: str
    expertise_stratum: ExpertiseStratum
    protocol_sha256: str
    consent_receipt_sha256: str
    privacy_notice_sha256: str
    eligibility_receipt_sha256: str
    olfactory_screening_receipt_sha256: str
    specific_anosmia_screen_receipt_sha256: str | None
    training_receipt_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.expertise_stratum, ExpertiseStratum):
            raise ValueError("expertise_stratum must be an ExpertiseStratum")
        for value, name in (
            (self.participant_token_sha256, "participant_token_sha256"),
            (self.protocol_sha256, "protocol_sha256"),
            (self.consent_receipt_sha256, "consent_receipt_sha256"),
            (self.privacy_notice_sha256, "privacy_notice_sha256"),
            (self.eligibility_receipt_sha256, "eligibility_receipt_sha256"),
            (
                self.olfactory_screening_receipt_sha256,
                "olfactory_screening_receipt_sha256",
            ),
        ):
            _require_sha256(value, name)
        if self.specific_anosmia_screen_receipt_sha256 is not None:
            _require_sha256(
                self.specific_anosmia_screen_receipt_sha256,
                "specific_anosmia_screen_receipt_sha256",
            )
        if self.training_receipt_sha256 is not None:
            _require_sha256(
                self.training_receipt_sha256, "training_receipt_sha256"
            )
        if (
            self.expertise_stratum
            in {
                ExpertiseStratum.TRAINED_DESCRIPTIVE,
                ExpertiseStratum.PERFUMER_EXPERT,
            }
            and self.training_receipt_sha256 is None
        ):
            raise ValueError("trained or expert strata require a training receipt")

    def as_dict(self) -> dict[str, str | None]:
        return {
            "participant_token_sha256": self.participant_token_sha256,
            "expertise_stratum": self.expertise_stratum.value,
            "protocol_sha256": self.protocol_sha256,
            "consent_receipt_sha256": self.consent_receipt_sha256,
            "privacy_notice_sha256": self.privacy_notice_sha256,
            "eligibility_receipt_sha256": self.eligibility_receipt_sha256,
            "olfactory_screening_receipt_sha256": (
                self.olfactory_screening_receipt_sha256
            ),
            "specific_anosmia_screen_receipt_sha256": (
                self.specific_anosmia_screen_receipt_sha256
            ),
            "training_receipt_sha256": self.training_receipt_sha256,
        }

    @property
    def receipt_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class PanelAttributeRating:
    attribute_id: str
    value: Decimal | None
    not_applicable_reason: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.attribute_id, "attribute_id")
        if self.value is None:
            if self.not_applicable_reason is None:
                raise ValueError(
                    "not_applicable_reason is required when value is missing"
                )
            _require_text(self.not_applicable_reason, "not_applicable_reason")
            return
        _require_finite_decimal(self.value, "rating value")
        if self.value < 0 or self.value > 10:
            raise ValueError("rating value must be between 0 and 10")
        if self.not_applicable_reason is not None:
            raise ValueError("rated attributes cannot carry not_applicable_reason")

    def as_dict(self) -> dict[str, str | None]:
        return {
            "attribute_id": self.attribute_id,
            "value": str(self.value) if self.value is not None else None,
            "not_applicable_reason": self.not_applicable_reason,
        }


@dataclass(frozen=True, slots=True)
class PanelObservation:
    """One strict response row containing no formula, batch, or raw identity."""

    observation_token_sha256: str
    blind_code: str
    participant_token_sha256: str
    qualification_receipt_sha256: str
    protocol_sha256: str
    lexicon_sha256: str
    session_token_sha256: str
    repeat_index: int
    sniff_time_seconds: int
    ratings: tuple[PanelAttributeRating, ...]
    target_choice_id: str | None = None

    def __post_init__(self) -> None:
        for value, name in (
            (self.observation_token_sha256, "observation_token_sha256"),
            (self.participant_token_sha256, "participant_token_sha256"),
            (self.qualification_receipt_sha256, "qualification_receipt_sha256"),
            (self.protocol_sha256, "protocol_sha256"),
            (self.lexicon_sha256, "lexicon_sha256"),
            (self.session_token_sha256, "session_token_sha256"),
        ):
            _require_sha256(value, name)
        if not isinstance(self.blind_code, str) or not _BLIND_CODE_RE.fullmatch(
            self.blind_code
        ):
            raise ValueError("blind_code must be 3-12 uppercase letters or digits")
        if isinstance(self.repeat_index, bool) or not isinstance(
            self.repeat_index, int
        ):
            raise ValueError("repeat_index must be a positive integer")
        if self.repeat_index <= 0:
            raise ValueError("repeat_index must be a positive integer")
        if isinstance(self.sniff_time_seconds, bool) or not isinstance(
            self.sniff_time_seconds, int
        ):
            raise ValueError("sniff_time_seconds must be a non-negative integer")
        if self.sniff_time_seconds < 0:
            raise ValueError("sniff_time_seconds must be a non-negative integer")
        if not self.ratings:
            raise ValueError("ratings must not be empty")
        _require_unique(
            tuple(item.attribute_id for item in self.ratings),
            "rating attribute IDs",
        )
        if self.target_choice_id is not None:
            _require_identifier(self.target_choice_id, "target_choice_id")

    def as_dict(self) -> dict[str, Any]:
        return {
            "observation_token_sha256": self.observation_token_sha256,
            "blind_code": self.blind_code,
            "participant_token_sha256": self.participant_token_sha256,
            "qualification_receipt_sha256": self.qualification_receipt_sha256,
            "protocol_sha256": self.protocol_sha256,
            "lexicon_sha256": self.lexicon_sha256,
            "session_token_sha256": self.session_token_sha256,
            "repeat_index": self.repeat_index,
            "sniff_time_seconds": self.sniff_time_seconds,
            "ratings": [item.as_dict() for item in self.ratings],
            "target_choice_id": self.target_choice_id,
        }

    @property
    def record_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


def validate_panel_observation(
    observation: PanelObservation,
    protocol: ConstructionPanelProtocol,
    lexicon: ConstructionLexicon,
    receipt: ParticipantQualificationReceipt,
) -> None:
    """Validate one response against exact locked contracts and hashed receipts."""

    if not protocol.protocol_locked:
        raise ValueError("panel observations require a locked protocol")
    if protocol.lexicon_sha256 != lexicon.lexicon_sha256:
        raise ValueError("protocol lexicon hash does not match the supplied lexicon")
    if observation.protocol_sha256 != protocol.protocol_sha256:
        raise ValueError("observation protocol hash does not match")
    if observation.lexicon_sha256 != lexicon.lexicon_sha256:
        raise ValueError("observation lexicon hash does not match")
    if receipt.protocol_sha256 != protocol.protocol_sha256:
        raise ValueError("qualification receipt protocol hash does not match")
    if observation.participant_token_sha256 != receipt.participant_token_sha256:
        raise ValueError("observation participant token does not match receipt")
    if observation.qualification_receipt_sha256 != receipt.receipt_sha256:
        raise ValueError("observation qualification receipt hash does not match")
    if receipt.expertise_stratum not in protocol.expertise_strata:
        raise ValueError("participant expertise stratum is outside the protocol")
    expected_attributes = tuple(item.attribute_id for item in lexicon.attributes)
    observed_attributes = tuple(item.attribute_id for item in observation.ratings)
    if observed_attributes != expected_attributes:
        raise ValueError(
            "observation must contain exactly one rating for every lexicon attribute"
        )
    if observation.sniff_time_seconds not in protocol.timepoints_seconds:
        raise ValueError("observation sniff time is outside the locked protocol")
    if observation.repeat_index > protocol.repeat_count:
        raise ValueError("observation repeat index is outside the locked protocol")


@dataclass(frozen=True, slots=True)
class PanelPerformanceResult:
    gate_kind: GateKind
    gate_spec_sha256: str
    outcome: GateOutcome
    observed_value: Decimal | None
    result_receipt_sha256: str
    participant_set_sha256: str
    analysis_plan_sha256: str
    study_partition: StudyPartition

    def __post_init__(self) -> None:
        if not isinstance(self.gate_kind, GateKind):
            raise ValueError("gate_kind must be a GateKind")
        if not isinstance(self.outcome, GateOutcome):
            raise ValueError("outcome must be a GateOutcome")
        if not isinstance(self.study_partition, StudyPartition):
            raise ValueError("study_partition must be a StudyPartition")
        for value, name in (
            (self.gate_spec_sha256, "gate_spec_sha256"),
            (self.result_receipt_sha256, "result_receipt_sha256"),
            (self.participant_set_sha256, "participant_set_sha256"),
            (self.analysis_plan_sha256, "analysis_plan_sha256"),
        ):
            _require_sha256(value, name)
        if self.outcome is GateOutcome.UNMEASURED:
            if self.observed_value is not None:
                raise ValueError("unmeasured gate cannot carry an observed value")
            return
        if self.observed_value is None:
            raise ValueError("measured gate outcome requires an observed value")
        _require_finite_decimal(self.observed_value, "observed_value")

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_kind": self.gate_kind.value,
            "gate_spec_sha256": self.gate_spec_sha256,
            "outcome": self.outcome.value,
            "observed_value": (
                str(self.observed_value)
                if self.observed_value is not None
                else None
            ),
            "result_receipt_sha256": self.result_receipt_sha256,
            "participant_set_sha256": self.participant_set_sha256,
            "analysis_plan_sha256": self.analysis_plan_sha256,
            "study_partition": self.study_partition.value,
        }


@dataclass(frozen=True, slots=True)
class C0ExitReport:
    decision: C0ExitDecision
    protocol_sha256: str
    lexicon_sha256: str
    passed_gates: tuple[GateKind, ...]
    failed_gates: tuple[GateKind, ...]
    inconclusive_gates: tuple[GateKind, ...]
    blockers: tuple[str, ...]
    c0_exit_satisfied: bool
    study_authorized: bool = field(default=False, init=False)
    release_authority: bool = field(default=False, init=False)
    model_calibration_authority: bool = field(default=False, init=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "protocol_sha256": self.protocol_sha256,
            "lexicon_sha256": self.lexicon_sha256,
            "passed_gates": [item.value for item in self.passed_gates],
            "failed_gates": [item.value for item in self.failed_gates],
            "inconclusive_gates": [
                item.value for item in self.inconclusive_gates
            ],
            "blockers": list(self.blockers),
            "c0_exit_satisfied": self.c0_exit_satisfied,
            "study_authorized": self.study_authorized,
            "release_authority": self.release_authority,
            "model_calibration_authority": self.model_calibration_authority,
        }


def evaluate_c0_exit(
    protocol: ConstructionPanelProtocol,
    lexicon: ConstructionLexicon,
    results: tuple[PanelPerformanceResult, ...],
) -> C0ExitReport:
    """Evaluate exact C0 exit evidence without granting downstream authority."""

    blockers: list[str] = []
    passed: list[GateKind] = []
    failed: list[GateKind] = []
    inconclusive: list[GateKind] = []

    if protocol.lexicon_sha256 != lexicon.lexicon_sha256:
        blockers.append("protocol lexicon hash does not match the supplied lexicon")
    if not protocol.protocol_locked:
        blockers.append("protocol is not locked")
        blockers.extend(
            f"required evidence binding '{item.binding_id}' is unbound"
            for item in protocol.bindings
            if item.state is not BindingState.BOUND
        )
        blockers.extend(
            f"gate threshold '{item.kind.value}' is not preregistered and locked"
            for item in protocol.panel_gate_specs
            if item.authority is not GateAuthority.PREREGISTERED_LOCKED
        )
        if not protocol.timepoints_seconds:
            blockers.append("sniff timepoints are not bound")
        if protocol.repeat_count < 2:
            blockers.append("repeat plan cannot estimate repeatability")

    result_kinds = tuple(item.gate_kind for item in results)
    if len(result_kinds) != len(set(result_kinds)):
        blockers.append("panel performance results contain duplicate gate kinds")

    analysis_plan = next(
        (
            item.sha256
            for item in protocol.bindings
            if item.binding_id == "analysis_plan"
        ),
        None,
    )
    results_are_authoritative_for_exit = (
        protocol.protocol_locked
        and protocol.lexicon_sha256 == lexicon.lexicon_sha256
    )
    result_by_kind = {item.gate_kind: item for item in results}
    for spec in protocol.panel_gate_specs:
        result = result_by_kind.get(spec.kind)
        if result is None:
            blockers.append(f"panel gate '{spec.kind.value}' has no result")
            continue
        if not results_are_authoritative_for_exit:
            continue
        result_errors: list[str] = []
        if result.gate_spec_sha256 != spec.spec_sha256:
            result_errors.append("gate specification hash mismatch")
        if result.study_partition is not protocol.study_partition:
            result_errors.append("study partition mismatch")
        if analysis_plan is None or result.analysis_plan_sha256 != analysis_plan:
            result_errors.append("analysis plan hash mismatch")
        if result_errors:
            blockers.extend(
                f"panel gate '{spec.kind.value}' {item}" for item in result_errors
            )
            continue
        if result.outcome is GateOutcome.PASS:
            passed.append(spec.kind)
        elif result.outcome is GateOutcome.FAIL:
            failed.append(spec.kind)
        else:
            inconclusive.append(spec.kind)
            blockers.append(
                f"panel gate '{spec.kind.value}' is {result.outcome.value}"
            )

    if failed:
        decision = C0ExitDecision.STOP
    elif blockers or inconclusive:
        decision = C0ExitDecision.HOLD
    elif tuple(passed) == tuple(GateKind):
        decision = C0ExitDecision.GO
    else:
        decision = C0ExitDecision.HOLD
        blockers.append("not every independent panel-performance gate passed")

    return C0ExitReport(
        decision=decision,
        protocol_sha256=protocol.protocol_sha256,
        lexicon_sha256=lexicon.lexicon_sha256,
        passed_gates=tuple(passed),
        failed_gates=tuple(failed),
        inconclusive_gates=tuple(inconclusive),
        blockers=tuple(blockers),
        c0_exit_satisfied=decision is C0ExitDecision.GO,
    )


__all__ = [
    "BindingState",
    "C0ExitDecision",
    "C0ExitReport",
    "CONSTRUCTION_ATTRIBUTE_IDS",
    "ConstructionLexicon",
    "ConstructionPanelProtocol",
    "EvidenceBinding",
    "ExpertiseStratum",
    "GateAuthority",
    "GateDirection",
    "GateKind",
    "GateOutcome",
    "HEDONIC_ATTRIBUTE_IDS",
    "PanelAttributeRating",
    "PanelGateSpecification",
    "PanelObservation",
    "PanelPerformanceResult",
    "ParticipantQualificationReceipt",
    "ScaleAnchor",
    "SensoryAttributeDefinition",
    "StudyPartition",
    "build_c0_construction_lexicon",
    "build_c0_protocol_draft",
    "evaluate_c0_exit",
    "validate_panel_observation",
]
