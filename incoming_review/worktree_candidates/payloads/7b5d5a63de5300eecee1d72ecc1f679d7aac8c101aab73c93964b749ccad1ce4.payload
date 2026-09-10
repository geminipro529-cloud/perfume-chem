"""Current-policy complexity dispatcher with an explicit V2 firewall.

The dispatcher consumes the Meaningful Complexity V3 rule surface. It never
falls back to the legacy V2 row-count or aggregate-quality-score policy.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping

from .canonical import sha256_payload


class ComplexityClass(str, Enum):
    COMPACT = "COMPACT"
    LAYERED = "LAYERED"
    HIGH_COMPLEXITY = "HIGH_COMPLEXITY"
    ORCHESTRAL = "ORCHESTRAL"
    UNCLASSIFIED_HOLD = "UNCLASSIFIED_HOLD"


class ClassificationState(str, Enum):
    PASS_FOR_DECLARED_SCOPE = "PASS_FOR_DECLARED_SCOPE"
    CONDITIONAL = "CONDITIONAL"
    HOLD = "HOLD"
    FAIL = "FAIL"
    REBUILD_REQUIRED = "REBUILD_REQUIRED"


class ClaimLevel(str, Enum):
    DESIGN_ONLY = "DESIGN_ONLY"
    SOURCE_SUPPORTED_DESIGN = "SOURCE_SUPPORTED_DESIGN"
    PHYSICALLY_OBSERVED = "PHYSICALLY_OBSERVED"
    TRAINED_SENSORY_CONFIRMED = "TRAINED_SENSORY_CONFIRMED"


class LegacyBandStatus(str, Enum):
    BELOW_LEGACY_BAND = "BELOW_LEGACY_BAND"
    WITHIN_LEGACY_BAND = "WITHIN_LEGACY_BAND"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class ComplexityProfile:
    formula_scope: str = "FULL_PERFUME"
    total_rows: int = 0
    distinct_canonical_odor_identities: int = 0
    effective_post_ablation_rows: int = 0
    technical_rows: int = 0
    duplicate_strength_rows: int = 0
    proposed_microtexture_rows: int = 0
    functional_row_ratio: float = 1.0
    recognizer_paths: int = 0
    single_point_dependencies: int = 0
    sensory_systems: int = 0
    time_windows: int = 0
    transitions: int = 0
    interaction_edges: int = 0
    interaction_effect_types: int = 0
    texture_axes: int = 0
    contrast_axes: int = 0
    resilience_control_paths: int = 0
    independent_motifs: int = 0
    independent_control_paths: int = 0
    source_supported: bool = True
    physical_data: bool = False
    trained_sensory_data: bool = False
    requested_claim: str = "COMPACT"
    explicit_v2_compatibility: bool = False
    target_identity_floor: int | None = None
    target_floor_authoritative: bool = False
    unsupported_note_to_molecule_mapping: bool = False
    inventory_first_target_distortion: bool = False
    unresolved_identity_merge: bool = False
    class_depends_on_duplicates_or_technical_rows: bool = False
    hedonic_claim_from_architecture: bool = False
    physical_claim_without_evidence: bool = False
    legacy_quality_score: float | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "ComplexityProfile":
        aliases = {
            "distinct_odor_materials": "distinct_canonical_odor_identities",
            "effective_rows": "effective_post_ablation_rows",
            "sensory_systems": "sensory_systems",
            "effect_types": "interaction_effect_types",
        }
        fields = cls.__dataclass_fields__
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            destination = aliases.get(key, key)
            if destination in fields:
                normalized[destination] = value
        if "formula_scope" not in normalized and "artifact_scope" in payload:
            normalized["formula_scope"] = str(payload["artifact_scope"])
        return cls(**normalized)


@dataclass(frozen=True)
class ComplexityDecision:
    assigned_class: ComplexityClass
    classification_state: ClassificationState
    claim_level: ClaimLevel
    legacy_row_band_status: LegacyBandStatus
    compression_review_required: bool
    padding_review_required: bool
    current_failed_gates: tuple[str, ...]
    current_gate_states: Mapping[str, str]
    reasons: tuple[str, ...]
    policy_version: str
    legacy_payload_preserved: Mapping[str, Any] | None
    legacy_quality_score_non_governing: float | None
    decision_hash: str = field(default="")

    def with_hash(self) -> "ComplexityDecision":
        payload = {
            "assigned_class": self.assigned_class.value,
            "classification_state": self.classification_state.value,
            "claim_level": self.claim_level.value,
            "legacy_row_band_status": self.legacy_row_band_status.value,
            "compression_review_required": self.compression_review_required,
            "padding_review_required": self.padding_review_required,
            "current_failed_gates": list(self.current_failed_gates),
            "current_gate_states": dict(self.current_gate_states),
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "legacy_payload_preserved": self.legacy_payload_preserved,
            "legacy_quality_score_non_governing": self.legacy_quality_score_non_governing,
        }
        return ComplexityDecision(
            **{name: getattr(self, name) for name in self.__dataclass_fields__ if name != "decision_hash"},
            decision_hash=sha256_payload(payload, domain="PERFUME_CHEM_V20_COMPLEXITY_DECISION"),
        )


class CurrentComplexityDispatcher:
    """Noncompensatory V3 dispatcher with no legacy-policy fallback."""

    def __init__(self, rules: Mapping[str, Any]) -> None:
        self._rules = deepcopy(dict(rules))
        if self._rules.get("model_version") != "3.0.0":
            raise ValueError("unsupported current complexity model version")
        if self._rules.get("no_overall_quality_score") is not True:
            raise ValueError("current policy must prohibit an overall quality score")
        legacy = self._rules.get("legacy_row_bands", {})
        self._accord_floor = int(legacy.get("v2_high_complexity_accord_minimum", 50))
        self._perfume_floor = int(legacy.get("v2_high_complexity_perfume_minimum", 65))
        shared = self._rules.get("shared_integrity_rules", {})
        self._functional_min = float(shared.get("functional_row_ratio_minimum", 0.90))
        self._microtexture_max = float(
            shared.get("proposed_microtexture_claim_ratio_maximum", 0.20)
        )

    @classmethod
    def from_rules_file(cls, path: str | Path) -> "CurrentComplexityDispatcher":
        with Path(path).open("r", encoding="utf-8") as handle:
            rules = json.load(handle)
        return cls(rules)

    @property
    def policy_version(self) -> str:
        return str(self._rules["model_version"])

    def classify(
        self,
        profile: ComplexityProfile,
        *,
        current_policy_available: bool = True,
        legacy_payload: Mapping[str, Any] | None = None,
    ) -> ComplexityDecision:
        preserved_legacy = deepcopy(dict(legacy_payload)) if legacy_payload is not None else None
        if not current_policy_available:
            return ComplexityDecision(
                assigned_class=ComplexityClass.UNCLASSIFIED_HOLD,
                classification_state=ClassificationState.HOLD,
                claim_level=ClaimLevel.DESIGN_ONLY,
                legacy_row_band_status=LegacyBandStatus.NOT_APPLICABLE,
                compression_review_required=False,
                padding_review_required=False,
                current_failed_gates=("CURRENT_POLICY_UNAVAILABLE",),
                current_gate_states={
                    "G3": "HOLD_CURRENT_POLICY_UNAVAILABLE",
                    "G14": "NON_GOVERNING",
                },
                reasons=(
                    "Current V3 policy is unavailable; silent fallback to V2 is prohibited.",
                ),
                policy_version=self.policy_version,
                legacy_payload_preserved=preserved_legacy,
                legacy_quality_score_non_governing=profile.legacy_quality_score,
            ).with_hash()

        self._validate_profile(profile)
        reasons: list[str] = []
        current_failures: set[str] = set()
        gate_states: dict[str, str] = {"G14": "NON_GOVERNING"}

        hard_failure_flags = {
            "unsupported note-to-molecule mapping": profile.unsupported_note_to_molecule_mapping,
            "inventory-first target distortion": profile.inventory_first_target_distortion,
            "unresolved identity merge": profile.unresolved_identity_merge,
            "class depends on duplicate strengths or technical rows": (
                profile.class_depends_on_duplicates_or_technical_rows
            ),
            "hedonic claim inferred from architecture": profile.hedonic_claim_from_architecture,
            "physical claim passed without physical evidence": profile.physical_claim_without_evidence,
        }
        for label, failed in hard_failure_flags.items():
            if failed:
                reasons.append(label)
                current_failures.add("EVIDENCE_OR_SCOPE_HARD_FAILURE")

        effective = profile.effective_post_ablation_rows
        distinct = profile.distinct_canonical_odor_identities
        microtexture_denominator = max(effective, 1)
        microtexture_ratio = profile.proposed_microtexture_rows / microtexture_denominator
        padding_review = (
            profile.functional_row_ratio < self._functional_min
            or microtexture_ratio > self._microtexture_max
            or profile.class_depends_on_duplicates_or_technical_rows
        )
        if padding_review:
            reasons.append("PADDING_REVIEW triggered by integrity ratios or row accounting.")

        threshold = (
            self._accord_floor
            if profile.formula_scope.upper() in {"ACCORD", "STANDALONE_ACCORD"}
            else self._perfume_floor
        )
        legacy_status = (
            LegacyBandStatus.WITHIN_LEGACY_BAND
            if distinct >= threshold
            else LegacyBandStatus.BELOW_LEGACY_BAND
        )
        requested = profile.requested_claim.upper()
        compression_review = (
            legacy_status is LegacyBandStatus.BELOW_LEGACY_BAND
            and requested in {"HIGH_COMPLEXITY", "ORCHESTRAL"}
        )

        if profile.explicit_v2_compatibility and distinct < threshold:
            current_failures.add("V2_COMPATIBILITY_FLOOR")
            reasons.append(
                f"Explicit V2 compatibility requires at least {threshold} distinct identities."
            )

        if profile.target_floor_authoritative:
            if profile.target_identity_floor is None:
                current_failures.add("TARGET_FLOOR_AUTHORITY_MALFORMED")
                reasons.append("Authoritative target floor is declared without a floor value.")
            elif distinct < profile.target_identity_floor:
                current_failures.add("TARGET_SPECIFIC_IDENTITY_FLOOR")
                reasons.append(
                    "Authoritative target-specific identity floor is not met."
                )

        assigned = self._highest_supported_class(profile)
        # The declared scope is a ceiling, not a trophy escalator. A compact or
        # layered artifact is not silently relabeled upward merely because some
        # dimensions exceed its bounded purpose.
        if requested == "COMPACT":
            assigned = ComplexityClass.COMPACT
        elif requested == "LAYERED" and self._class_rank(assigned.value) > 2:
            assigned = ComplexityClass.LAYERED

        if hard_failure_flags and any(hard_failure_flags.values()):
            assigned = ComplexityClass.UNCLASSIFIED_HOLD
        if padding_review and requested in {"HIGH_COMPLEXITY", "ORCHESTRAL"}:
            assigned = ComplexityClass.UNCLASSIFIED_HOLD
            current_failures.add("PADDING_INTEGRITY")

        requested_rank = self._class_rank(requested)
        assigned_rank = self._class_rank(assigned.value)

        if current_failures:
            if current_failures & {
                "EVIDENCE_OR_SCOPE_HARD_FAILURE",
                "PADDING_INTEGRITY",
                "V2_COMPATIBILITY_FLOOR",
                "TARGET_SPECIFIC_IDENTITY_FLOOR",
            }:
                state = ClassificationState.REBUILD_REQUIRED
            else:
                state = ClassificationState.HOLD
        elif requested_rank > assigned_rank:
            state = ClassificationState.CONDITIONAL
            reasons.append(
                f"Requested class {requested} exceeds the supported class {assigned.value}."
            )
        elif assigned in {ComplexityClass.HIGH_COMPLEXITY, ComplexityClass.ORCHESTRAL}:
            state = ClassificationState.CONDITIONAL
            if not profile.physical_data:
                reasons.append("Physical complexity constructs remain NOT_TESTED.")
        elif compression_review:
            state = ClassificationState.CONDITIONAL
            reasons.append("Compression review is required for a below-legacy-band high claim.")
        else:
            state = ClassificationState.PASS_FOR_DECLARED_SCOPE

        claim_level = self._claim_level(profile, state)
        gate_states.update(self._gate_projection(profile, assigned, state, padding_review))
        gate_states["G14"] = "NON_GOVERNING"
        current_failed_gates = tuple(sorted(current_failures))
        if profile.legacy_quality_score is not None:
            reasons.append(
                "Legacy quality_score is preserved as metadata and has no decision effect."
            )

        return ComplexityDecision(
            assigned_class=assigned,
            classification_state=state,
            claim_level=claim_level,
            legacy_row_band_status=legacy_status,
            compression_review_required=compression_review,
            padding_review_required=padding_review,
            current_failed_gates=current_failed_gates,
            current_gate_states=gate_states,
            reasons=tuple(reasons),
            policy_version=self.policy_version,
            legacy_payload_preserved=preserved_legacy,
            legacy_quality_score_non_governing=profile.legacy_quality_score,
        ).with_hash()

    def _validate_profile(self, profile: ComplexityProfile) -> None:
        integer_fields = (
            "total_rows",
            "distinct_canonical_odor_identities",
            "effective_post_ablation_rows",
            "technical_rows",
            "duplicate_strength_rows",
            "proposed_microtexture_rows",
            "recognizer_paths",
            "single_point_dependencies",
            "sensory_systems",
            "time_windows",
            "transitions",
            "interaction_edges",
            "interaction_effect_types",
            "texture_axes",
            "contrast_axes",
            "resilience_control_paths",
            "independent_motifs",
            "independent_control_paths",
        )
        for name in integer_fields:
            value = getattr(profile, name)
            if value < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0 <= profile.functional_row_ratio <= 1:
            raise ValueError("functional_row_ratio must be within [0, 1]")
        if profile.effective_post_ablation_rows > profile.distinct_canonical_odor_identities:
            raise ValueError("effective post-ablation rows cannot exceed distinct identities")

    def _highest_supported_class(self, p: ComplexityProfile) -> ComplexityClass:
        if self._meets_orchestral(p):
            return ComplexityClass.ORCHESTRAL
        if self._meets_high(p):
            return ComplexityClass.HIGH_COMPLEXITY
        if self._meets_layered(p):
            return ComplexityClass.LAYERED
        return ComplexityClass.COMPACT

    def _meets_layered(self, p: ComplexityProfile) -> bool:
        moderate_dimensions = sum(
            (
                p.recognizer_paths >= 1,
                p.sensory_systems >= 3,
                p.time_windows >= 2,
                p.transitions >= 1,
                p.interaction_edges >= 2,
                p.texture_axes >= 2,
                p.contrast_axes >= 1,
            )
        )
        return (
            moderate_dimensions >= 4
            and p.recognizer_paths >= 1
            and p.sensory_systems >= 3
            and p.time_windows >= 2
            and p.transitions >= 1
            and p.interaction_edges >= 2
            and p.functional_row_ratio >= self._functional_min
        )

    def _meets_high(self, p: ComplexityProfile) -> bool:
        interaction_high = p.interaction_edges >= 6 and p.interaction_effect_types >= 3
        required = (
            p.recognizer_paths >= 2
            and p.single_point_dependencies == 0
            and p.sensory_systems >= 5
            and p.time_windows >= 3
            and p.transitions >= 2
            and interaction_high
        )
        additional = sum(
            (
                interaction_high,
                p.texture_axes >= 3,
                p.contrast_axes >= 2,
                p.resilience_control_paths >= 2,
                p.effective_post_ablation_rows >= 30,
            )
        )
        return (
            required
            and additional >= 3
            and p.functional_row_ratio >= self._functional_min
            and p.proposed_microtexture_rows / max(p.effective_post_ablation_rows, 1)
            <= self._microtexture_max
        )

    def _meets_orchestral(self, p: ComplexityProfile) -> bool:
        return (
            self._meets_high(p)
            and p.independent_motifs >= 2
            and p.recognizer_paths >= 3
            and p.sensory_systems >= 6
            and p.time_windows >= 4
            and p.transitions >= 3
            and p.interaction_edges >= 10
            and p.interaction_effect_types >= 4
            and p.texture_axes >= 4
            and p.contrast_axes >= 3
            and max(p.independent_control_paths, p.resilience_control_paths) >= 2
        )

    @staticmethod
    def _class_rank(value: str) -> int:
        ranks = {
            "COMPACT": 1,
            "LAYERED": 2,
            "HIGH_COMPLEXITY": 3,
            "ORCHESTRAL": 4,
            "UNCLASSIFIED_HOLD": 0,
        }
        return ranks.get(value.upper(), 0)

    @staticmethod
    def _claim_level(
        profile: ComplexityProfile, state: ClassificationState
    ) -> ClaimLevel:
        if state in {ClassificationState.REBUILD_REQUIRED, ClassificationState.FAIL}:
            return ClaimLevel.DESIGN_ONLY
        if profile.trained_sensory_data and profile.physical_data:
            return ClaimLevel.TRAINED_SENSORY_CONFIRMED
        if profile.physical_data:
            return ClaimLevel.PHYSICALLY_OBSERVED
        if profile.source_supported:
            return ClaimLevel.SOURCE_SUPPORTED_DESIGN
        return ClaimLevel.DESIGN_ONLY

    def _gate_projection(
        self,
        p: ComplexityProfile,
        assigned: ComplexityClass,
        state: ClassificationState,
        padding_review: bool,
    ) -> dict[str, str]:
        g3 = "PASS"
        if padding_review:
            g3 = "REBUILD_REQUIRED"
        elif assigned in {ComplexityClass.HIGH_COMPLEXITY, ComplexityClass.ORCHESTRAL} and (
            p.distinct_canonical_odor_identities
            < (self._accord_floor if p.formula_scope.upper() == "ACCORD" else self._perfume_floor)
        ):
            g3 = "CONDITIONAL_COMPRESSION_REVIEW"
        g4 = "PASS" if p.sensory_systems >= 3 and p.time_windows >= 2 else "FAIL"
        g5 = "PASS" if p.interaction_edges >= 2 and p.interaction_effect_types >= 1 else "FAIL"
        g9 = "PASS" if p.effective_post_ablation_rows > 0 else "HOLD"
        return {
            "G3": g3,
            "G4": g4,
            "G5": g5,
            "G9": g9,
            "G14": "NON_GOVERNING",
            "FINAL": state.value,
        }
