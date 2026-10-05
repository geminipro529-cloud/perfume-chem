"""Authority-safe research contracts and scientific challengers.

This package is deliberately separate from the legacy scoring pipeline.  Its
objects describe evidence, applicability, uncertainty, and physical state; no
object in this package grants safety, release, purchase, or compounding
authority.
"""

from .accounting import AccountedFormulaRowV1, account_formula_snapshot
from .capabilities import adjudicate_wakayama_identities, load_local_identity_index
from .commercial_references import (
    CommercialProductIdentityV1,
    CommercialReferenceEvidenceV1,
    CommercialReferencePanelV1,
    CommercialReferenceSampleV1,
    build_commercial_reference_panel,
    evaluate_reference_panel,
    load_commercial_reference_registry,
)
from .comparison import (
    ComparatorEvidenceV1,
    compare_design_evidence,
    project_completion_states,
)
from .contracts import (
    FALSE_ACTION_AUTHORITY,
    CandidateEvaluationV1,
    CapabilityManifestV1,
    EndpointEstimateV1,
    FormulaComponentV1,
    FormulaSnapshotV1,
    MaterialIdentityV1,
    ProductIdentityV1,
    ReleaseScenarioV1,
    SensoryObservationV1,
    StockLotV1,
    ValidationEnvelopeV2,
)
from .goal_analysis import (
    GoalAnalysisRequestV1,
    GoalFormulaRowV1,
    analyze_formula_for_goal,
)
from .perception import (
    CharacterComponentV1,
    compute_detection_diagnostic,
    linear_intensity_weighted_character,
    unavailable_hedonic_endpoints,
)
from .preference import DavidsonFitConfigV1, fit_davidson_personal_preference
from .protocols import (
    BlindingManifestV1,
    InstrumentalObservationContractV1,
    build_personal_sensory_protocol,
    build_reference_anchored_protocol,
)
from .release import (
    FiniteReleaseParametersV1,
    ReleaseComponentV1,
    simulate_finite_release,
)
from .request_interpretation import (
    RequestInterpretationInputV1,
    interpret_request,
)
from .selection import (
    OfflineCandidateV1,
    compare_search_arms,
    lavender_ambrox_search_contract,
)
from .snapshots import (
    FormulaSnapshotLoadV1,
    SnapshotSourceError,
    load_markdown_design_snapshot,
    load_parallel_a_design_snapshot,
    load_r5_design_snapshot,
    load_r6_design_snapshot,
)

__all__ = [
    "FALSE_ACTION_AUTHORITY",
    "CandidateEvaluationV1",
    "CapabilityManifestV1",
    "EndpointEstimateV1",
    "FormulaComponentV1",
    "FormulaSnapshotV1",
    "MaterialIdentityV1",
    "ProductIdentityV1",
    "ReleaseScenarioV1",
    "SensoryObservationV1",
    "StockLotV1",
    "ValidationEnvelopeV2",
    "AccountedFormulaRowV1",
    "account_formula_snapshot",
    "FiniteReleaseParametersV1",
    "ReleaseComponentV1",
    "simulate_finite_release",
    "CharacterComponentV1",
    "compute_detection_diagnostic",
    "linear_intensity_weighted_character",
    "unavailable_hedonic_endpoints",
    "DavidsonFitConfigV1",
    "fit_davidson_personal_preference",
    "adjudicate_wakayama_identities",
    "load_local_identity_index",
    "BlindingManifestV1",
    "InstrumentalObservationContractV1",
    "build_personal_sensory_protocol",
    "build_reference_anchored_protocol",
    "OfflineCandidateV1",
    "compare_search_arms",
    "lavender_ambrox_search_contract",
    "ComparatorEvidenceV1",
    "compare_design_evidence",
    "project_completion_states",
    "CommercialProductIdentityV1",
    "CommercialReferenceEvidenceV1",
    "CommercialReferencePanelV1",
    "CommercialReferenceSampleV1",
    "build_commercial_reference_panel",
    "evaluate_reference_panel",
    "load_commercial_reference_registry",
    "FormulaSnapshotLoadV1",
    "SnapshotSourceError",
    "load_markdown_design_snapshot",
    "load_parallel_a_design_snapshot",
    "load_r5_design_snapshot",
    "load_r6_design_snapshot",
    "GoalAnalysisRequestV1",
    "GoalFormulaRowV1",
    "analyze_formula_for_goal",
    "RequestInterpretationInputV1",
    "interpret_request",
]
