"""Exact-scope integration of floral morphology with family architecture.

This adapter is deliberately stock-free.  It preserves the complete family and
floral source assessments inside one non-flattening synthesis receipt; it does
not choose materials, generate a formula, infer a generic family, or create
sensory, hedonic, safety, stability, compounding, or release authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from engine.formulation_intelligence.contracts import AssessmentScope
from engine.formulation_intelligence.family_architecture import (
    FamilyArchitectureAdapter,
    FamilyResolution,
)
from engine.formulation_intelligence.floral_lattice import (
    FloralCandidateSignals,
    FloralMorphologyIntent,
    FloralMorphologyPlaneAdapter,
    MorphologyEvidence,
)
from engine.formulation_intelligence.plane_synthesis import (
    PlaneSynthesisResult,
    synthesize_plane_assessments,
)


@dataclass(frozen=True, slots=True)
class FloralFamilyIntegrationAdapter:
    """Bind one exact family resolution to one exact floral morphology intent."""

    resolution: FamilyResolution
    intent: FloralMorphologyIntent
    scope: AssessmentScope
    evidence: tuple[MorphologyEvidence, ...] = ()
    candidate_signals: FloralCandidateSignals = FloralCandidateSignals()

    def __post_init__(self) -> None:
        if not isinstance(self.resolution, FamilyResolution):
            raise TypeError("resolution must be a FamilyResolution")
        if not isinstance(self.intent, FloralMorphologyIntent):
            raise TypeError("intent must be a FloralMorphologyIntent")
        if not isinstance(self.scope, AssessmentScope):
            raise TypeError("scope must be an AssessmentScope")
        request = self.resolution.request
        mismatches = tuple(
            field_name
            for field_name, actual, expected in (
                ("target_scope", self.scope.target_scope, request.target_scope),
                ("temporal_scope", self.scope.temporal_scope, request.temporal_scope),
                ("matrix_scope", self.scope.matrix_scope, request.matrix_scope),
            )
            if actual != expected
        )
        if mismatches:
            raise ValueError(
                "floral/family integration requires exact shared scope; mismatched "
                + ", ".join(mismatches)
            )
        # Reuse the source adapter's canonicalization and type validation rather
        # than maintaining a second evidence contract here.
        morphology = FloralMorphologyPlaneAdapter(
            intent=self.intent,
            scope=self.scope,
            evidence=self.evidence,
            candidate_signals=self.candidate_signals,
        )
        object.__setattr__(self, "evidence", morphology.evidence)
        object.__setattr__(self, "candidate_signals", morphology.candidate_signals)

    def to_synthesis(self) -> PlaneSynthesisResult:
        """Return a deterministic receipt retaining both complete source planes."""

        family = FamilyArchitectureAdapter(self.resolution).to_plane_assessment()
        morphology = FloralMorphologyPlaneAdapter(
            intent=self.intent,
            scope=self.scope,
            evidence=self.evidence,
            candidate_signals=self.candidate_signals,
        ).to_plane_assessment()
        return synthesize_plane_assessments((family, morphology))


def build_floral_family_synthesis(
    resolution: FamilyResolution,
    intent: FloralMorphologyIntent,
    *,
    scope: AssessmentScope,
    evidence: Iterable[MorphologyEvidence] = (),
    candidate_signals: FloralCandidateSignals | None = None,
) -> PlaneSynthesisResult:
    """Build the exact-scope family/morphology synthesis without runtime writes."""

    return FloralFamilyIntegrationAdapter(
        resolution=resolution,
        intent=intent,
        scope=scope,
        evidence=tuple(evidence),
        candidate_signals=candidate_signals or FloralCandidateSignals(),
    ).to_synthesis()


__all__ = [
    "FloralFamilyIntegrationAdapter",
    "build_floral_family_synthesis",
]
