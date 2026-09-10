"""Evidence-bounded architecture model for Dior Homme Intense 2011.

The exact target is the 2011--2014 lineage commonly associated with package
formula code 05443/A.  The module models identity, anatomy, relations, phase
transitions, failure modes, and controlled falsification probes.  It does not
claim access to Dior's concentrate formula or an authenticated quantitative
GC-MS report.

Selection is Pareto-based over non-interchangeable target criteria.  Ingredient
count, OAV, ownership, prestige, and a scalar composition score cannot earn
similarity, depth, or liking authority.  All physical, sensory, safety, and
release authorities remain false until their own evidence exists.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum, IntEnum
from typing import Any, Iterable, Mapping

from engine.calibration.hashing import stable_json_hash


class DHI2011ProgramState(str, Enum):
    """Decision state for this exact architecture scope."""

    THEORY_SELECTED = "THEORY_SELECTED"
    FRONTIER = "FRONTIER"
    HOLD = "HOLD"


class DHI2011EvidenceTier(str, Enum):
    """Claim provenance; tiers do not silently convert into formula truth."""

    CONFIRMED_MARKETING_ARCHITECTURE = "CONFIRMED_MARKETING_ARCHITECTURE"
    PERSISTENT_HOUSE_DESCRIPTION = "PERSISTENT_HOUSE_DESCRIPTION"
    CONTEMPORANEOUS_LAUNCH_REPORT = "CONTEMPORANEOUS_LAUNCH_REPORT"
    PACKAGE_DISCLOSURE_TRANSCRIPTION = "PACKAGE_DISCLOSURE_TRANSCRIPTION"
    COLLECTOR_VERSION_EVIDENCE = "COLLECTOR_VERSION_EVIDENCE"
    PERFUMER_INFERENCE = "PERFUMER_INFERENCE"
    COMMERCIAL_ANALYSIS_CLAIM_UNVERIFIED = "COMMERCIAL_ANALYSIS_CLAIM_UNVERIFIED"
    REFERENCE_SAMPLE_TEST_REQUIRED = "REFERENCE_SAMPLE_TEST_REQUIRED"


class DHI2011Criterion(str, Enum):
    """Non-collapsible criteria used for target-first candidate selection."""

    VERSION_SCOPE_LOCK = "VERSION_SCOPE_LOCK"
    IRIS_ORRIS_IDENTITY = "IRIS_ORRIS_IDENTITY"
    AMBRETTE_PEAR_TALC_RELATION = "AMBRETTE_PEAR_TALC_RELATION"
    LAVENDER_OPENING = "LAVENDER_OPENING"
    CEDAR_VETIVER_RETURN = "CEDAR_VETIVER_RETURN"
    AMBER_VANILLIC_WARMTH = "AMBER_VANILLIC_WARMTH"
    TEMPORAL_HANDOFF = "TEMPORAL_HANDOFF"
    DISTINCTIVE_IDENTITY = "DISTINCTIVE_IDENTITY"
    CURRENT_INVENTORY_FEASIBILITY = "CURRENT_INVENTORY_FEASIBILITY"
    CONTROLLED_TESTABILITY = "CONTROLLED_TESTABILITY"


class DHI2011DepthDimension(str, Enum):
    """Cypress-parity depth dimensions; count is diagnostic only."""

    OBJECT_IDENTITY = "OBJECT_IDENTITY"
    INTERNAL_ANATOMY = "INTERNAL_ANATOMY"
    RELATIONAL_TOPOLOGY = "RELATIONAL_TOPOLOGY"
    CONTRAST_AND_NEGATIVE_SPACE = "CONTRAST_AND_NEGATIVE_SPACE"
    TEXTURE_AND_MATERIALITY = "TEXTURE_AND_MATERIALITY"
    TEMPORAL_ARCHITECTURE = "TEMPORAL_ARCHITECTURE"
    SPATIAL_PERFORMANCE = "SPATIAL_PERFORMANCE"
    HEDONIC_ARCHITECTURE = "HEDONIC_ARCHITECTURE"
    NONLINEAR_INTERACTION = "NONLINEAR_INTERACTION"
    PHYSICAL_CHEMISTRY = "PHYSICAL_CHEMISTRY"
    COGNITIVE_CONTEXT = "COGNITIVE_CONTEXT"
    ROBUSTNESS_ANTI_COLLAPSE = "ROBUSTNESS_ANTI_COLLAPSE"
    EVIDENCE_QUALITY = "EVIDENCE_QUALITY"
    CONSTRUCTION_COMPLEXITY_DIAGNOSTIC = "CONSTRUCTION_COMPLEXITY_DIAGNOSTIC"


class DHI2011SupportLevel(IntEnum):
    CONTRAINDICATED = 0
    UNRESOLVED = 1
    PLAUSIBLE = 2
    STRONGLY_TARGET_LINKED = 3


TIME_WINDOWS = (
    "opening_0s",
    "top_5min",
    "heart_30min",
    "late_heart_2h",
    "drydown_4h",
)


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be nonblank text")
    return " ".join(value.split())


def _text_tuple(
    values: Iterable[str], field_name: str, *, allow_empty: bool = False
) -> tuple[str, ...]:
    result = tuple(_text(value, field_name) for value in values)
    if not allow_empty and not result:
        raise ValueError(f"{field_name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{field_name} must contain unique values")
    return result


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if is_dataclass(value) and hasattr(value, "as_dict"):
        return value.as_dict()  # type: ignore[no-any-return, union-attr]
    return value


class _CanonicalRecord:
    SCHEMA_VERSION: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            **{item.name: _json_value(getattr(self, item.name)) for item in fields(self)},
        }

    @property
    def record_sha256(self) -> str:
        return stable_json_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class DHI2011AuthorityVectorV1(_CanonicalRecord):
    """This theory artifact is deliberately incapable of granting authority."""

    SCHEMA_VERSION = "dhi_2011_authority_vector_v1"

    sensory_similarity: bool = False
    observed_target_fidelity: bool = False
    observed_depth: bool = False
    observed_liking: bool = False
    physical_performance: bool = False
    exact_quantitative_formula: bool = False
    safety_ifra: bool = False
    stability: bool = False
    compounding: bool = False
    purchase: bool = False
    release: bool = False

    def __post_init__(self) -> None:
        for item in fields(self):
            if getattr(self, item.name) is not False:
                raise ValueError(f"{item.name} authority must remain false")


@dataclass(frozen=True, slots=True)
class DHI2011EvidenceClaimV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_evidence_claim_v1"

    claim_id: str
    statement: str
    tier: DHI2011EvidenceTier
    support: str
    uncertainty: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("claim_id", "statement", "support", "uncertainty"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "tier", DHI2011EvidenceTier(self.tier))
        object.__setattr__(self, "source_refs", _text_tuple(self.source_refs, "source_refs"))


@dataclass(frozen=True, slots=True)
class DHI2011TargetContractV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_target_contract_v1"

    target_id: str
    target_identity: str
    edition_window: str
    formula_code_scope: str
    perfumer_attribution: str
    olfactory_family: str
    target_ideal_ref: str
    current_inventory_build_ref: str
    positive_invariants: tuple[str, ...]
    forbidden_drift: tuple[str, ...]
    exact_formula_status: str
    reference_sample_requirement: str
    claim_ceiling: str
    authorities: DHI2011AuthorityVectorV1

    def __post_init__(self) -> None:
        for name in (
            "target_id",
            "target_identity",
            "edition_window",
            "formula_code_scope",
            "perfumer_attribution",
            "olfactory_family",
            "target_ideal_ref",
            "current_inventory_build_ref",
            "exact_formula_status",
            "reference_sample_requirement",
            "claim_ceiling",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.formula_code_scope != "05443/A":
            raise ValueError("DHI 2011 target must remain locked to formula-code scope 05443/A")
        object.__setattr__(
            self, "positive_invariants", _text_tuple(self.positive_invariants, "positive_invariants")
        )
        object.__setattr__(
            self, "forbidden_drift", _text_tuple(self.forbidden_drift, "forbidden_drift")
        )
        if not isinstance(self.authorities, DHI2011AuthorityVectorV1):
            raise TypeError("authorities must be DHI2011AuthorityVectorV1")


@dataclass(frozen=True, slots=True)
class DHI2011AssessmentV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_assessment_v1"

    criterion: DHI2011Criterion
    support_level: DHI2011SupportLevel
    rationale: str
    uncertainty: str
    falsifiable_failure: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "criterion", DHI2011Criterion(self.criterion))
        object.__setattr__(self, "support_level", DHI2011SupportLevel(self.support_level))
        for name in ("rationale", "uncertainty", "falsifiable_failure"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True, slots=True)
class DHI2011MaterialIntentV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_material_intent_v1"

    intent_id: str
    target_function_id: str
    ideal_material_or_effect: str
    current_material: str
    current_stock: str
    time_windows: tuple[str, ...]
    evidence_tier: DHI2011EvidenceTier
    omission_loss: str
    overdose_or_drift: str
    uncertainty: str
    exact_reference_formula_claim: bool = False

    def __post_init__(self) -> None:
        for name in (
            "intent_id",
            "target_function_id",
            "ideal_material_or_effect",
            "current_material",
            "current_stock",
            "omission_loss",
            "overdose_or_drift",
            "uncertainty",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "time_windows", _text_tuple(self.time_windows, "time_windows"))
        if not set(self.time_windows).issubset(TIME_WINDOWS):
            raise ValueError("material intent uses an unknown time window")
        object.__setattr__(self, "evidence_tier", DHI2011EvidenceTier(self.evidence_tier))
        if self.exact_reference_formula_claim is not False:
            raise ValueError("material intents cannot claim exact DHI formula membership")


@dataclass(frozen=True, slots=True)
class DHI2011FunctionV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_function_v1"

    function_id: str
    description: str
    target_link: str
    omission_loss: str
    success_observable: str
    failure_observable: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "function_id",
            "description",
            "target_link",
            "omission_loss",
            "success_observable",
            "failure_observable",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True, slots=True)
class DHI2011LayerV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_layer_v1"

    layer_id: str
    identity: str
    temporal_position: tuple[str, ...]
    spatial_position: str
    texture: str
    owned_function_ids: tuple[str, ...]
    takeover_condition: str

    def __post_init__(self) -> None:
        for name in ("layer_id", "identity", "spatial_position", "texture", "takeover_condition"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(
            self, "temporal_position", _text_tuple(self.temporal_position, "temporal_position")
        )
        if not set(self.temporal_position).issubset(TIME_WINDOWS):
            raise ValueError("layer uses an unknown time window")
        object.__setattr__(
            self, "owned_function_ids", _text_tuple(self.owned_function_ids, "owned_function_ids")
        )


@dataclass(frozen=True, slots=True)
class DHI2011TransitionV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_transition_v1"

    transition_id: str
    source_layer_id: str
    target_layer_id: str
    relational_mechanism: str
    intended_effect: str
    omission_failure: str
    overdose_failure: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "transition_id",
            "source_layer_id",
            "target_layer_id",
            "relational_mechanism",
            "intended_effect",
            "omission_failure",
            "overdose_failure",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.source_layer_id == self.target_layer_id:
            raise ValueError("a transition must connect two distinct layers")
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs"))


@dataclass(frozen=True, slots=True)
class DHI2011ControlledProbeV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_controlled_probe_v1"

    probe_id: str
    question: str
    arms: tuple[str, ...]
    constants: tuple[str, ...]
    endpoints: tuple[str, ...]
    time_windows: tuple[str, ...]
    blinding: str
    presentation_order: str
    acceptance_rule: str
    rejection_rule: str

    def __post_init__(self) -> None:
        for name in (
            "probe_id",
            "question",
            "blinding",
            "presentation_order",
            "acceptance_rule",
            "rejection_rule",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "arms", _text_tuple(self.arms, "arms"))
        if len(self.arms) < 2:
            raise ValueError("controlled probes require at least two arms")
        object.__setattr__(self, "constants", _text_tuple(self.constants, "constants"))
        object.__setattr__(self, "endpoints", _text_tuple(self.endpoints, "endpoints"))
        object.__setattr__(self, "time_windows", _text_tuple(self.time_windows, "time_windows"))
        if not set(self.time_windows).issubset(TIME_WINDOWS):
            raise ValueError("controlled probe uses an unknown time window")


@dataclass(frozen=True, slots=True)
class DHI2011MechanismV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_mechanism_v1"

    mechanism_id: str
    dimensions: tuple[DHI2011DepthDimension, ...]
    participant_intent_ids: tuple[str, ...]
    function_ids: tuple[str, ...]
    causal_hypothesis: str
    omission_loss: str
    failure_mode: str
    time_windows: tuple[str, ...]
    falsification_probe_id: str
    evidence_tier: DHI2011EvidenceTier

    def __post_init__(self) -> None:
        object.__setattr__(self, "mechanism_id", _text(self.mechanism_id, "mechanism_id"))
        dimensions = tuple(DHI2011DepthDimension(item) for item in self.dimensions)
        if not dimensions or len(dimensions) != len(set(dimensions)):
            raise ValueError("dimensions must be nonempty and unique")
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(
            self, "participant_intent_ids", _text_tuple(self.participant_intent_ids, "participant_intent_ids")
        )
        object.__setattr__(self, "function_ids", _text_tuple(self.function_ids, "function_ids"))
        for name in ("causal_hypothesis", "omission_loss", "failure_mode", "falsification_probe_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "time_windows", _text_tuple(self.time_windows, "time_windows"))
        if not set(self.time_windows).issubset(TIME_WINDOWS):
            raise ValueError("mechanism uses an unknown time window")
        object.__setattr__(self, "evidence_tier", DHI2011EvidenceTier(self.evidence_tier))


@dataclass(frozen=True, slots=True)
class DHI2011CandidateV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_candidate_v1"

    candidate_id: str
    architecture_identity: str
    smell_hypothesis: str
    primary_relation: str
    assessments: tuple[DHI2011AssessmentV1, ...]
    required_function_ids: tuple[str, ...]
    controlled_comparison_ref: str

    def __post_init__(self) -> None:
        for name in (
            "candidate_id",
            "architecture_identity",
            "smell_hypothesis",
            "primary_relation",
            "controlled_comparison_ref",
        ):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        assessments = tuple(self.assessments)
        if any(not isinstance(item, DHI2011AssessmentV1) for item in assessments):
            raise TypeError("assessments must contain DHI2011AssessmentV1")
        criteria = tuple(item.criterion for item in assessments)
        if len(criteria) != len(set(criteria)):
            raise ValueError("candidate criteria must be unique")
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(
            self, "required_function_ids", _text_tuple(self.required_function_ids, "required_function_ids")
        )


@dataclass(frozen=True, slots=True)
class DHI2011DominanceRecordV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_dominance_record_v1"

    dominant_candidate_id: str
    dominated_candidate_id: str
    equal_criteria: tuple[DHI2011Criterion, ...]
    stronger_criteria: tuple[DHI2011Criterion, ...]

    def __post_init__(self) -> None:
        for name in ("dominant_candidate_id", "dominated_candidate_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.dominant_candidate_id == self.dominated_candidate_id:
            raise ValueError("dominance requires distinct candidates")
        equal = tuple(DHI2011Criterion(item) for item in self.equal_criteria)
        stronger = tuple(DHI2011Criterion(item) for item in self.stronger_criteria)
        if not stronger or set(equal) & set(stronger):
            raise ValueError("dominance needs disjoint criteria and at least one stronger criterion")
        object.__setattr__(self, "equal_criteria", equal)
        object.__setattr__(self, "stronger_criteria", stronger)


@dataclass(frozen=True, slots=True)
class DHI2011ArchitectureRequestV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_architecture_request_v1"

    target: DHI2011TargetContractV1
    evidence_claims: tuple[DHI2011EvidenceClaimV1, ...]
    criteria_priority: tuple[DHI2011Criterion, ...]
    candidates: tuple[DHI2011CandidateV1, ...]
    functions: tuple[DHI2011FunctionV1, ...]
    layers: tuple[DHI2011LayerV1, ...]
    transitions: tuple[DHI2011TransitionV1, ...]
    material_intents: tuple[DHI2011MaterialIntentV1, ...]
    controlled_probes: tuple[DHI2011ControlledProbeV1, ...]
    mechanisms: tuple[DHI2011MechanismV1, ...]
    time_windows: tuple[str, ...]
    formula_binding_ref: str
    inventory_execution_state: str
    component_count_used_as_complexity: bool = False
    predicted_oav_used_as_perception: bool = False
    composition_score_used_as_hedonic: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.target, DHI2011TargetContractV1):
            raise TypeError("target must be DHI2011TargetContractV1")
        for name, item_type in (
            ("evidence_claims", DHI2011EvidenceClaimV1),
            ("candidates", DHI2011CandidateV1),
            ("functions", DHI2011FunctionV1),
            ("layers", DHI2011LayerV1),
            ("transitions", DHI2011TransitionV1),
            ("material_intents", DHI2011MaterialIntentV1),
            ("controlled_probes", DHI2011ControlledProbeV1),
            ("mechanisms", DHI2011MechanismV1),
        ):
            values = tuple(getattr(self, name))
            if not values or any(not isinstance(value, item_type) for value in values):
                raise TypeError(f"{name} must be a nonempty tuple of {item_type.__name__}")
            object.__setattr__(self, name, values)
        criteria = tuple(DHI2011Criterion(item) for item in self.criteria_priority)
        if set(criteria) != set(DHI2011Criterion):
            raise ValueError("criteria_priority must contain every DHI criterion exactly once")
        object.__setattr__(self, "criteria_priority", criteria)
        object.__setattr__(self, "time_windows", _text_tuple(self.time_windows, "time_windows"))
        if self.time_windows != TIME_WINDOWS:
            raise ValueError("DHI architecture requires the frozen five-window time sequence")
        for name in ("formula_binding_ref", "inventory_execution_state"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in (
            "component_count_used_as_complexity",
            "predicted_oav_used_as_perception",
            "composition_score_used_as_hedonic",
        ):
            if getattr(self, name) is not False:
                raise ValueError(f"{name} must remain false")


@dataclass(frozen=True, slots=True)
class DHI2011ArchitectureResultV1(_CanonicalRecord):
    SCHEMA_VERSION = "dhi_2011_architecture_result_v1"

    state: DHI2011ProgramState
    request_sha256: str
    selected_candidate_id: str | None
    frontier_candidate_ids: tuple[str, ...]
    dominance_records: tuple[DHI2011DominanceRecordV1, ...]
    required_dimensions: tuple[DHI2011DepthDimension, ...]
    covered_dimensions: tuple[DHI2011DepthDimension, ...]
    uncovered_dimensions: tuple[DHI2011DepthDimension, ...]
    reason_codes: tuple[str, ...]
    claim_ceiling: str
    authorities: DHI2011AuthorityVectorV1

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", DHI2011ProgramState(self.state))
        object.__setattr__(self, "request_sha256", _text(self.request_sha256, "request_sha256"))
        if self.selected_candidate_id is not None:
            object.__setattr__(
                self, "selected_candidate_id", _text(self.selected_candidate_id, "selected_candidate_id")
            )
        object.__setattr__(
            self, "frontier_candidate_ids", _text_tuple(self.frontier_candidate_ids, "frontier_candidate_ids")
        )
        for name in ("required_dimensions", "covered_dimensions", "uncovered_dimensions"):
            values = tuple(DHI2011DepthDimension(item) for item in getattr(self, name))
            object.__setattr__(self, name, values)
        object.__setattr__(self, "reason_codes", _text_tuple(self.reason_codes, "reason_codes"))
        object.__setattr__(self, "claim_ceiling", _text(self.claim_ceiling, "claim_ceiling"))
        if not isinstance(self.authorities, DHI2011AuthorityVectorV1):
            raise TypeError("authorities must be DHI2011AuthorityVectorV1")


def _assessment_set(
    candidate_id: str,
    levels: Mapping[DHI2011Criterion, DHI2011SupportLevel],
    notes: Mapping[DHI2011Criterion, str],
    shared_risk: str,
    evidence_refs: tuple[str, ...],
) -> tuple[DHI2011AssessmentV1, ...]:
    return tuple(
        DHI2011AssessmentV1(
            criterion=criterion,
            support_level=levels[criterion],
            rationale=f"{candidate_id}: {notes[criterion]}",
            uncertainty="No candidate has been compounded or compared with an authenticated 05443/A sample.",
            falsifiable_failure=f"Reject this assessment if blinded evaluation shows {shared_risk}",
            evidence_refs=evidence_refs,
        )
        for criterion in DHI2011Criterion
    )


def _candidate(
    candidate_id: str,
    architecture_identity: str,
    smell_hypothesis: str,
    primary_relation: str,
    level_values: tuple[int, ...],
    notes: Mapping[DHI2011Criterion, str],
    shared_risk: str,
    required_function_ids: tuple[str, ...],
    comparison_ref: str,
) -> DHI2011CandidateV1:
    levels = {
        criterion: DHI2011SupportLevel(level)
        for criterion, level in zip(DHI2011Criterion, level_values, strict=True)
    }
    return DHI2011CandidateV1(
        candidate_id=candidate_id,
        architecture_identity=architecture_identity,
        smell_hypothesis=smell_hypothesis,
        primary_relation=primary_relation,
        assessments=_assessment_set(
            candidate_id,
            levels,
            notes,
            shared_risk,
            ("evidence:dhi2011:house", "evidence:dhi2011:launch", "protocol:dhi2011:blind"),
        ),
        required_function_ids=required_function_ids,
        controlled_comparison_ref=comparison_ref,
    )


def _candidate_notes(direction: str, central_risk: str) -> dict[DHI2011Criterion, str]:
    return {
        DHI2011Criterion.VERSION_SCOPE_LOCK: f"{direction} is explicitly evaluated against 05443/A rather than a blended Dior Homme lineage.",
        DHI2011Criterion.IRIS_ORRIS_IDENTITY: f"The iris object is judged for powder, violet mobility, root coolness, and woody anatomy; risk: {central_risk}.",
        DHI2011Criterion.AMBRETTE_PEAR_TALC_RELATION: f"Pear liqueur and silk talc are treated as an ambrette-mediated relation, not a literal fruit syrup; risk: {central_risk}.",
        DHI2011Criterion.LAVENDER_OPENING: f"Lavender must be legible at entry and fold into iris without establishing a fougere subject; risk: {central_risk}.",
        DHI2011Criterion.CEDAR_VETIVER_RETURN: f"Virginia cedar and vetiver must return as a dry masculine counterform after the iris heart; risk: {central_risk}.",
        DHI2011Criterion.AMBER_VANILLIC_WARMTH: f"Warmth must sit inside the iris fabric rather than read as dessert vanilla; risk: {central_risk}.",
        DHI2011Criterion.TEMPORAL_HANDOFF: f"The design is scored across five windows, with no instantaneous note pyramid standing in for evolution; risk: {central_risk}.",
        DHI2011Criterion.DISTINCTIVE_IDENTITY: f"The direction must preserve the dressed, dense, powdery-woody DHI tension; risk: {central_risk}.",
        DHI2011Criterion.CURRENT_INVENTORY_FEASIBILITY: f"A separate current-stock projection exists but cannot rewrite the ideal target; risk: {central_risk}.",
        DHI2011Criterion.CONTROLLED_TESTABILITY: f"Omission and dose-frontier arms can falsify the claimed relation; risk: {central_risk}.",
    }


def build_default_dhi_2011_architecture_request() -> DHI2011ArchitectureRequestV1:
    """Build the frozen 05443/A target and a current-stock design hypothesis."""

    authorities = DHI2011AuthorityVectorV1()
    target = DHI2011TargetContractV1(
        target_id="dhi-2011-05443a-v1",
        target_identity="Dior Homme Intense 2011 re-edition architecture, formula-code scope 05443/A",
        edition_window="2011-2014 collector-associated package lineage",
        formula_code_scope="05443/A",
        perfumer_attribution="Francois Demachy",
        olfactory_family="powdery iris, ambrette, ambery wood",
        target_ideal_ref="formula:dhi-2011-05443a:target-ideal:v1",
        current_inventory_build_ref="formula:dhi-11-velours-d-iris:smooth-successor:v3",
        positive_invariants=(
            "lavender is a short aromatic veil, never a fougere subject",
            "iris or orris is the dominant recognizable object through the heart",
            "ambrette mediates musk, pear-liqueur nuance, and silk-talc texture",
            "amber and vanilla warm the iris without creating a dessert accord",
            "Virginia cedar and vetiver return as a dry masculine counterform",
            "the composition moves from tailored brightness to cosmetic density to dry wood and skin",
        ),
        forbidden_drift=(
            "generic lipstick or undifferentiated ionone wall",
            "cocoa, praline, caramel, or pastry gourmand caricature",
            "leather, oud, or sandalwood-heavy Dior Homme Parfum drift",
            "cold blue ambrox or sharp modern amberwood pressure",
            "detergent white-musk volume",
            "syrupy literal pear candy",
            "pencil-shaving cedar wall",
            "lavender-coumarin fougere takeover",
        ),
        exact_formula_status="UNKNOWN; no authenticated public quantitative 05443/A formula or traceable GC-MS report located",
        reference_sample_requirement="lot-documented 05443/A bottle plus storage history and repeated coded comparison",
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
        authorities=authorities,
    )

    evidence_claims = (
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:house",
            "Dior persistently describes a powdery Tuscan-iris signature, Ecuadorian ambrette with pear-liqueur and silk-talc facets, Virginia cedar, amber, and precious woods.",
            DHI2011EvidenceTier.PERSISTENT_HOUSE_DESCRIPTION,
            "Strong architecture support; the currently published ingredient list belongs to a later formula code and is not back-projected.",
            "House copy does not disclose 05443/A constituent identities or ratios.",
            ("https://www.dior.com/en_ch/beauty/products/dior-homme-intense-Y0479201.html",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:training",
            "Dior training material links DHI with Tuscan iris butter, Ecuadorian ambrette seed absolute, Virginia cedar essence, and a woody fragrance warmed by iris and vanilla.",
            DHI2011EvidenceTier.CONFIRMED_MARKETING_ARCHITECTURE,
            "House-authored architecture corroboration.",
            "The 2020 document describes the continuing product identity, not authenticated 05443/A percentages.",
            ("https://www.diortraining.com/uploads/1/2/9/1/12917753/fragrance_memo_2020_english.pdf#page=82",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:launch",
            "A contemporaneous launch report gives lavender; iris, ambrette, pear liqueur and powder; then Virginia cedar and vetiver.",
            DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT,
            "Moderate 2011 architecture evidence consistent with persistent house identity.",
            "Secondary reporting relays launch material and is not an analytical formula.",
            ("https://www.fragrantica.com/news/Dior-Homme-2011-by-Francois-Demachy-Dior-Homme-Intense-2011-Francois-Demachy-Dior-J-adore-Eau-de-Toilette-2011-2383.html",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:version",
            "Collector photo chronology associates 05443/A with the 2011-2014 DHI lineage.",
            DHI2011EvidenceTier.COLLECTOR_VERSION_EVIDENCE,
            "Moderate version-lock evidence and stronger than an unqualified bottle year.",
            "Not a Dior archival formula register; reference bottles must still be documented individually.",
            ("https://www.raidersofthelostscent.blog/2016/04/dior-homme-dior-homme-intense-and-other.html?m=0",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:package",
            "A community transcription of a 05443/A box lists alpha-isomethyl ionone, coumarin, and benzyl benzoate among declarable ingredients.",
            DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION,
            "Supports presence hypotheses only; it cannot establish concentrate percentages.",
            "The package and transcription are not independently authenticated in this model.",
            ("https://basenotes.com/threads/dior-homme-intense-reformulated-review.285329/page-11",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:cocoa",
            "A cocoa-like shadow is modeled as a possible emergent effect of ionone, coumarinic, vanillic, and roasted traces, not as a confirmed note or ingredient.",
            DHI2011EvidenceTier.PERFUMER_INFERENCE,
            "Permits a trace cocoa ablation experiment without elevating cocoa to target truth.",
            "Literal Cocoa Absolute is unconfirmed, and the reference may need none at all.",
            ("probe:dhi2011:cocoa-shadow",),
        ),
        DHI2011EvidenceClaimV1(
            "evidence:dhi2011:quantitative-gap",
            "No public analysis located for an authenticated 05443/A sample exposes provenance, chromatogram, method, calibration, response factors, and uncertainty.",
            DHI2011EvidenceTier.REFERENCE_SAMPLE_TEST_REQUIRED,
            "Hard ceiling against exact-formula or quantitative-similarity claims.",
            "A future qualified report could supersede this negative evidence audit.",
            ("protocol:dhi2011:analytical-admission",),
        ),
    )

    function_ids = (
        "fn:version-lock",
        "fn:iris-object",
        "fn:iris-mobility",
        "fn:orris-root",
        "fn:iris-tail",
        "fn:ambrette-mediator",
        "fn:pear-glint",
        "fn:talc-cushion",
        "fn:lavender-entry",
        "fn:warm-shadow",
        "fn:coumarinic-shadow",
        "fn:vanillic-shadow",
        "fn:wood-return",
        "fn:wood-softening",
        "fn:negative-space",
        "fn:skin-closure",
        "fn:musk-velvet",
        "fn:musk-diffusion",
    )
    functions = (
        DHI2011FunctionV1("fn:version-lock", "Prevent cross-version note and formula contamination.", "Exact 05443/A scope.", "The model silently blends 2007, 2015, 2020, 2025, or DHP architecture.", "Every claim carries source tier and version applicability.", "A current Dior ingredient list is back-projected into 2011.", ("evidence:dhi2011:version",)),
        DHI2011FunctionV1("fn:iris-object", "Construct a dense iris object with powder, violet mobility, root coolness, and woody anatomy.", "DHI's dominant recognizer.", "A generic sweet woody perfume remains.", "Iris remains named at 5 min, 30 min, and 2 h without one-dimensional lipstick.", "Ionone mass becomes chalky, cosmetic, flat, or violet-candy.", ("evidence:dhi2011:house", "evidence:dhi2011:training")),
        DHI2011FunctionV1("fn:iris-mobility", "Move the powder body from fruit-violet ingress toward dry wood rather than leaving it static.", "A dimensional iris needs a mobile edge as well as mass.", "The center reads as one beige AIMI slab.", "Violet curvature is legible inside iris without becoming violet candy.", "Bright ionone becomes a separate floral subject.", ("protocol:dhi2011:whole-formula",)),
        DHI2011FunctionV1("fn:orris-root", "Add cool rhizome, fatty root, and botanical irregularity to the cosmetic iris body.", "Root specificity distinguishes orris from generic violet powder.", "The heart is smooth but synthetic and rootless.", "A cool root texture appears beneath lipstick powder.", "Carrot, butter, wax, or earth is named independently.", ("evidence:dhi2011:training",)),
        DHI2011FunctionV1("fn:iris-tail", "Carry a dry woody-violet afterimage through the late heart and into cedar.", "The target retains iris while the wood counterform returns.", "Iris disappears at the base transition.", "A residual iris trace remains woven through dry wood.", "Extra ionones add count but no repeatable late-phase loss when omitted.", ("protocol:dhi2011:whole-formula",)),
        DHI2011FunctionV1("fn:ambrette-mediator", "Join musk, pear-liqueur nuance, silk talc, and iris fabric as one relation.", "Dior's own ambrette description.", "Pear becomes absent or literal fruit; talc becomes dry chalk; musk detaches.", "A soft fermented-fruit glint and skin-talc texture appear inside iris.", "Wine musk, pear candy, or laundry musk becomes an independent object.", ("evidence:dhi2011:house", "evidence:dhi2011:launch")),
        DHI2011FunctionV1("fn:pear-glint", "Construct an independently doseable pear-liqueur glint with flash, green flesh, floral skin, and a suede-apricot trace.", "Pear is named in the 2011 launch architecture and cannot be delegated to Ambrettolide alone.", "The target's fruit relation is absent.", "Fruit appears briefly inside the ambrette-orris membrane.", "Candy apple, pineapple, peach, banana, or obvious apricot becomes a note.", ("evidence:dhi2011:launch",)),
        DHI2011FunctionV1("fn:talc-cushion", "Place waxy cosmetic powder and creamy textile volume between ionone mass and musk.", "Silk-talc texture requires an adjustable layer distinct from ambrette and iris.", "Powder falls directly onto musk and feels chalky.", "The heart has a soft compact-to-fabric transition.", "Sunscreen, yellow floral, marzipan, or anonymous musk blanket takes over.", ("evidence:dhi2011:house",)),
        DHI2011FunctionV1("fn:lavender-entry", "Provide a tailored aromatic first light that folds into powder.", "2011 launch architecture.", "The perfume begins as an already-formed cosmetic block.", "Lavender is legible early and ceases to be a subject by 30 min.", "Barbershop, herbal oil, or fougere takeover.", ("evidence:dhi2011:launch",)),
        DHI2011FunctionV1("fn:warm-shadow", "Warm the underside of iris with coumarinic, vanillic, and optional roasted shadow.", "House vanilla and amber language.", "The iris feels cold, thin, or merely violet-woody.", "Warmth deepens texture without being named before iris.", "Cocoa dessert, tonka hay, pastry cream, or syrup.", ("evidence:dhi2011:training", "evidence:dhi2011:cocoa")),
        DHI2011FunctionV1("fn:coumarinic-shadow", "Supply hay-tonka depth independently of vanilla color.", "Coumarinic warmth is target-linked but must remain below iris.", "The lower heart lacks dry warmth.", "A restrained dry tonka register thickens the orris underside.", "Lavender-tonka fougere or almond-hay becomes the subject.", ("evidence:dhi2011:package",)),
        DHI2011FunctionV1("fn:vanillic-shadow", "Add a narrow buttery-vanillic seam independently of the tonka register.", "Separate control prevents one material from impersonating the whole warm layer.", "Warmth is hay-like but not amber-soft.", "Vanillic color is sensed without vanilla naming.", "Pastry cream, frosting, or cloying sweetness appears.", ("evidence:dhi2011:training",)),
        DHI2011FunctionV1("fn:wood-return", "Return Virginia cedar and vetiver after the iris maximum.", "2011 base architecture and persistent cedar story.", "The drydown is cosmetic musk without masculine counterform.", "Dry cedar-vetiver becomes clearer from 2 h while iris remains traceable.", "Pencil shavings, rooty vetiver subject, or amberwood wall.", ("evidence:dhi2011:house", "evidence:dhi2011:launch")),
        DHI2011FunctionV1("fn:wood-softening", "Grade the change from orris fabric to cedar-vetiver using polished vetiver, sandalwood seam, and textile wood.", "The late return should emerge, not snap into place.", "A hard powder-to-pencil cut remains.", "Wood grain arrives through suede and soft sandal texture.", "Creamy sandalwood or generic woody amber replaces the cedar-vetiver counterform.", ("protocol:dhi2011:whole-formula",)),
        DHI2011FunctionV1("fn:negative-space", "Ventilate a dense iris core and preserve foreground/background separation.", "Target-linked readability rather than an official ingredient claim.", "All layers fuse into an opaque block.", "The iris feels dimensional with air around its edges.", "Generic Hedione/Iso E diffusion becomes the perfume's identity.", ("protocol:dhi2011:whole-formula",)),
        DHI2011FunctionV1("fn:skin-closure", "Close wood, talc, and warm iris into an intimate musky textile.", "Ambrette and silk-talc identity.", "The drydown ends technically or abruptly.", "The final trace reads as warm fabric and dry wood, not detergent.", "Musk anosmia, wine-musk takeover, or laundry volume.", ("evidence:dhi2011:house",)),
        DHI2011FunctionV1("fn:musk-velvet", "Give the powder a creamy low-frequency textile bed without assigning it the ambrette role.", "A separate velvet axis lets talc mass be tuned independently.", "The iris becomes dry and mechanically woody.", "Powder rests on soft fabric while remaining legible.", "A thick anonymous musk blanket erases the iris anatomy.", ("protocol:dhi2011:whole-formula",)),
        DHI2011FunctionV1("fn:musk-diffusion", "Project a restrained woody-musk shell outside the inward ambrette and velvet axes.", "Outward trail and intimate skin are different controls.", "The drydown is dense but has no exterior wake.", "A small woody textile echo leaves the skin plane.", "Laundry-clean or synthetic woody musk is named.", ("protocol:dhi2011:whole-formula",)),
    )

    layers = (
        DHI2011LayerV1("layer:lavender-veil", "Lavender Veil", ("opening_0s", "top_5min"), "front and upper edge", "dry aromatic light with soft ester polish", ("fn:lavender-entry", "fn:version-lock"), "lavender persists as a fougere subject at 30 minutes"),
        DHI2011LayerV1("layer:ambrette-pear-talc-membrane", "Ambrette-Pear-Talc Membrane", ("top_5min", "heart_30min", "late_heart_2h"), "close halo around the iris object", "soft fermented-fruit glint over silky powder", ("fn:ambrette-mediator", "fn:pear-glint", "fn:talc-cushion"), "pear, wine, yellow flower, or musk separates into a named object"),
        DHI2011LayerV1("layer:orris-body", "Orris Body", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "central foreground with violet movement through depth", "lipstick powder, cool rhizome, warm bread, and polished wood", ("fn:iris-object", "fn:iris-mobility", "fn:orris-root", "fn:iris-tail"), "the body becomes a flat ionone slab or loses recognition"),
        DHI2011LayerV1("layer:amber-vanillic-shadow", "Amber-Vanillic Shadow", ("heart_30min", "late_heart_2h", "drydown_4h"), "beneath and behind iris", "restrained amber warmth, never edible glaze", ("fn:warm-shadow", "fn:coumarinic-shadow", "fn:vanillic-shadow"), "cocoa, vanilla, or tonka is named before iris"),
        DHI2011LayerV1("layer:cedar-vetiver-counterform", "Cedar-Vetiver Counterform", ("late_heart_2h", "drydown_4h"), "rear frame moving toward foreground late", "dry pencil-free cedar fiber and earthy vetiver tension", ("fn:wood-return", "fn:wood-softening", "fn:negative-space"), "wood becomes a blunt wall or disappears under powder"),
        DHI2011LayerV1("layer:musky-skin-echo", "Musky Skin Echo", ("late_heart_2h", "drydown_4h"), "intimate skin plane with a restrained outward shell", "soft musky cloth carrying residual iris and wood", ("fn:skin-closure", "fn:musk-velvet", "fn:musk-diffusion"), "clean laundry musk erases the dry iris trace"),
    )

    transitions = (
        DHI2011TransitionV1("transition:aromatic-fold", "layer:lavender-veil", "layer:ambrette-pear-talc-membrane", "shared linalyl softness and powder-bound aromatic decay form the first membrane", "lavender loses herbal edges as ambrette-like fruit/talc appears", "abrupt aromatic-to-cosmetic cut", "sweet lavender-tonka fougere seam", ("evidence:dhi2011:launch",)),
        DHI2011TransitionV1("transition:membrane-wrap", "layer:ambrette-pear-talc-membrane", "layer:orris-body", "musk-fruit-talc wraps rather than sits above the iris body", "pear is perceived as an inner gleam and talc as texture", "pear disappears and iris becomes chalky", "syrupy pear or wine musk obscures iris", ("evidence:dhi2011:house",)),
        DHI2011TransitionV1("transition:warmth-underlay", "layer:orris-body", "layer:amber-vanillic-shadow", "coumarinic and vanillic color develops below the powder object", "iris gains density and amber warmth without dessert naming", "cold violet wood", "cocoa-tonka gourmand caricature", ("evidence:dhi2011:training", "evidence:dhi2011:cocoa")),
        DHI2011TransitionV1("transition:dry-wood-reveal", "layer:orris-body", "layer:cedar-vetiver-counterform", "cedar, vetiver, Iso E, and violet-woody ionones share a dry grain", "the masculine wood frame becomes clearer as powder recedes", "cosmetic musk drydown with no return", "pencil cedar, earthy vetiver, or generic Iso E cloud", ("evidence:dhi2011:launch",)),
        DHI2011TransitionV1("transition:talc-musk-recurrence", "layer:ambrette-pear-talc-membrane", "layer:musky-skin-echo", "the ambrette relation carries a small talc and pear memory into the late skin phase", "the opening membrane recurs as texture rather than a fruit note", "the drydown loses the target's ambrette memory", "wine musk, fruit musk, or detergent becomes a late subject", ("evidence:dhi2011:house",)),
        DHI2011TransitionV1("transition:wood-fibre-settling", "layer:cedar-vetiver-counterform", "layer:musky-skin-echo", "dry wood settles into intimate musk while retaining an iris trace", "residual iris remains woven into warm dry wood", "technical abrupt ending", "detergent or anonymous woody-musk finish", ("evidence:dhi2011:house",)),
    )

    material_intents = (
        DHI2011MaterialIntentV1("intent:aimi", "fn:iris-object", "methyl-ionone powder and violet-wood body", "Alpha Isomethyl Ionone (Methyl Ionone Pure)", "neat", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION, "The iris object loses opaque cosmetic body.", "A flat lipstick and chalk wall.", "Package transcription supports presence, never the proposed dose."),
        DHI2011MaterialIntentV1("intent:alpha-ionone", "fn:iris-mobility", "mobile violet-iris curvature", "Alpha Ionone", "neat", ("top_5min", "heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The iris body becomes static and beige.", "Violet candy and excessive floral brightness.", "Not disclosed as a specific 05443/A constituent."),
        DHI2011MaterialIntentV1("intent:alpha-irone", "fn:orris-root", "cool buttery rhizome character or iris-butter facet", "Alpha Irone", "10% w/w in DEP", ("heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Less root-cool specificity.", "The accent becomes a separate violet object.", "Proxy for an ideal orris/irone effect, not proof of Dior material."),
        DHI2011MaterialIntentV1("intent:orivone", "fn:orris-root", "warm fatty orris transition", "Orivone", "neat", ("heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The rhizome joins less naturally to amber.", "Butter, cosmetic wax, or potency spike.", "High modeled OAV demands a zero arm."),
        DHI2011MaterialIntentV1("intent:dihydro-beta-ionone", "fn:iris-tail", "low-volatility woody-violet egress", "Dihydro Beta Ionone", "neat", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The iris-to-wood handoff loses its dark underside.", "Dull woody powder or redundancy.", "Retention depends on a constant-total tail omission."),
        DHI2011MaterialIntentV1("intent:irotyl", "fn:iris-tail", "dry persistent iris grain", "Irotyl", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Late powder loses dry grain.", "Silent decorative complexity.", "Unverified threshold data requires sensory omission."),
        DHI2011MaterialIntentV1("intent:ultralia", "fn:iris-tail", "transparent ghost-iris afterimage", "Ultralia", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The final wood carries less iris memory.", "Transparent material adds no detectable loss when omitted.", "Unverified threshold data requires sensory omission."),
        DHI2011MaterialIntentV1("intent:carrot-seed", "fn:orris-root", "botanical root irregularity", "Carrot Seed EO", "neat", ("heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The root object becomes wholly synthetic.", "Carrot or vegetal earth is named.", "Natural composite is a literature proxy, not a lot assay."),
        DHI2011MaterialIntentV1("intent:ambrettolide", "fn:ambrette-mediator", "Ecuadorian ambrette seed absolute with pear-liqueur and silk-talc facets", "Ambrettolide", "10% w/w in DPG; stock-solution density unmeasured", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The fruit/talc/musk membrane and skin continuity weaken.", "Wine-musk or fruity musk becomes a separate subject.", "Ambrettolide is a current-stock proxy, not ambrette seed absolute or sensory equivalence."),
        DHI2011MaterialIntentV1("intent:e2mb", "fn:pear-glint", "volatile juicy pear-liqueur spark", "Ethyl 2-Methylbutyrate", "0.1% in DPG", ("opening_0s", "top_5min"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The fruit signal loses its first flash.", "Candy apple appears.", "ODT and vapor-pressure authority are uncertain; use as a screening microdose."),
        DHI2011MaterialIntentV1("intent:verdox", "fn:pear-glint", "green pear flesh and woody continuity", "Verdox", "neat", ("top_5min", "heart_30min"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Pear has sparkle but no body.", "Green apple shampoo or woody fruit takes over.", "Current-stock pear-body hypothesis."),
        DHI2011MaterialIntentV1("intent:benzyl-acetate", "fn:pear-glint", "soft floral-fruit skin", "Benzyl Acetate", "neat", ("top_5min", "heart_30min"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The fruit-to-floral fold becomes angular.", "Jasmine, banana, or solventy fruit is named.", "Bridge hypothesis rather than reference constituent claim."),
        DHI2011MaterialIntentV1("intent:osmanthus", "fn:pear-glint", "trace apricot-suede skin inside the liqueur membrane", "Osmanthus Absolute", "10% in DPG", ("heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The fruit skin lacks a soft suede irregularity.", "Apricot, tea, or leather becomes recognizable.", "Composite OAV is literature-derived and batch-unspecific."),
        DHI2011MaterialIntentV1("intent:lavender", "fn:lavender-entry", "lot-qualified fine French lavender opening", "Lavender EO High Altitude", "neat", ("opening_0s", "top_5min"), DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT, "The first phase lacks tailored aromatic lift.", "Herbal oil, camphor, or fougere takeover.", "Owned lot lacks independent CoA and sensory authentication."),
        DHI2011MaterialIntentV1("intent:linalyl-acetate", "fn:lavender-entry", "soft ester bridge inside lavender", "Linalyl Acetate", "neat", ("opening_0s", "top_5min", "heart_30min"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Lavender falls into fruit and powder too abruptly.", "Shampoo-like polished floral top.", "Bridge hypothesis rather than exact reference constituent claim."),
        DHI2011MaterialIntentV1("intent:linalool", "fn:lavender-entry", "small floral-air continuation from the natural oil", "Linalool", "neat", ("opening_0s", "top_5min", "heart_30min"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The aromatic fold has less air.", "Clean floral or detergent lift becomes visible.", "Independent adjustment of a lavender constituent is a formulation hypothesis."),
        DHI2011MaterialIntentV1("intent:mimosa", "fn:talc-cushion", "honeyed-green natural powder irregularity", "Mimosa Absolute", "10% in DPG", ("heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The talc layer becomes synthetic and uniform.", "Yellow flower, pollen, or honey is named.", "Composite OAV is literature-derived and batch-unspecific."),
        DHI2011MaterialIntentV1("intent:benzyl-salicylate", "fn:talc-cushion", "slow waxy cosmetic film", "Benzyl Salicylate", "neat", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Powder meets musk without a waxy cushion.", "Sunscreen or generic white floral appears.", "Modeled OAV may be below one; this is a falsifiable structural role."),
        DHI2011MaterialIntentV1("intent:tonkarome", "fn:coumarinic-shadow", "restrained coumarinic tonka warmth", "Tonkarome", "20% w/w in TEC", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Less hay-tonka warmth and amber continuity.", "Fougere, almond-hay, or sweet tonka subject.", "Coumarin package evidence does not prove Tonkarome use."),
        DHI2011MaterialIntentV1("intent:isobutavan", "fn:vanillic-shadow", "narrow buttery-vanillic seam", "Isobutavan", "neat", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The tonka shadow stays dry and unrounded.", "Pastry cream or frosting is named.", "Current-stock proxy for an independently adjustable vanilla color."),
        DHI2011MaterialIntentV1("intent:cedar", "fn:wood-return", "Virginia cedar essence", "Cedarwood oil Virginia", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.CONFIRMED_MARKETING_ARCHITECTURE, "The late masculine wood frame loses dry grain.", "Pencil shavings or cedar subject takeover.", "House note identity supports architecture, not proposed dose."),
        DHI2011MaterialIntentV1("intent:vetiver", "fn:wood-return", "dry vetiver counterline", "Vetiver EO (India)", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.CONTEMPORANEOUS_LAUNCH_REPORT, "Cedar lacks earthy tension and the drydown feels cosmetic.", "Rooty, smoky, green, or earthy vetiver subject.", "Indian stock is a proxy; the reference source is unknown."),
        DHI2011MaterialIntentV1("intent:vetival", "fn:wood-softening", "polished suede-vetiver grain", "Vetival", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "Natural vetiver meets powder too roughly.", "Dry suede becomes a subject.", "Distinctness from the natural vetiver must survive omission."),
        DHI2011MaterialIntentV1("intent:sandalore", "fn:wood-softening", "small creamy sandal seam", "Sandalore", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The cedar-to-musk landing becomes angular.", "Fresh sandalwood shifts the target toward creamy wood.", "One sandal bridge only; no sandalwood-complexity claim."),
        DHI2011MaterialIntentV1("intent:iso-e", "fn:negative-space", "transparent cedar-like rear volume", "Iso E Super", "neat", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The dense iris meets cedar as a hard seam.", "Generic woody aura masks the target's internal anatomy.", "Not an exact-reference material claim."),
        DHI2011MaterialIntentV1("intent:hedione", "fn:negative-space", "transparent floral air and edge ventilation", "Hedione", "neat", ("top_5min", "heart_30min", "late_heart_2h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The powder body becomes opaque and airless.", "Radiant jasmine cleanliness dilutes the dressed iris identity.", "Not an official DHI note or exact-reference claim."),
        DHI2011MaterialIntentV1("intent:cashmeran", "fn:skin-closure", "warm textile flex between powder and dry wood", "Cashmeran", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The lower transition feels brittle.", "Plush spicy wood or modern amber texture becomes too visible.", "Current-stock texture hypothesis only."),
        DHI2011MaterialIntentV1("intent:benzyl-benzoate", "fn:negative-space", "slow structural mass and constant-total reservoir", "Benzyl Benzoate", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PACKAGE_DISCLOSURE_TRANSCRIPTION, "The formula loses slow neutral mass and controlled replacement volume.", "Excess inert-feeling weight can suppress lift.", "Modeled OAV is below one; no perceptible facet is claimed."),
        DHI2011MaterialIntentV1("intent:ethylene-brassylate", "fn:musk-velvet", "creamy powder-textile mass", "Ethylene Brassylate", "neat", ("heart_30min", "late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The iris becomes drier and more mechanically woody.", "Anonymous musk blanket blurs the iris.", "Nonredundancy from Ambrettolide and Romandolide requires omission testing."),
        DHI2011MaterialIntentV1("intent:romandolide", "fn:musk-diffusion", "outward woody-musk shell", "Romandolide", "neat", ("late_heart_2h", "drydown_4h"), DHI2011EvidenceTier.PERFUMER_INFERENCE, "The late textile remains inward and heavy.", "Laundry-clean synthetic musk is named.", "First musk support to remove if projection gain is not repeatable."),
    )

    probes = (
        DHI2011ControlledProbeV1("probe:dhi2011:whole-formula", "Does the complete build preserve recognizers and trajectory against a documented 05443/A reference?", ("coded current build", "coded documented 05443/A reference", "repeated coded current-build control"), ("same ethanol lot and final raw-stock concentration", "same application mass and substrate", "same maturation and evaluation room"), ("identity naming", "target fidelity", "depth", "richness", "liking", "projection", "defects"), TIME_WINDOWS, "opaque three-digit codes held by another person", "balanced Latin-square order with the repeated control in a hidden position", "Promote architecture only if iris is dominant, pear/talc remains relational, lavender hands off, wood returns, and repeated-control reliability is acceptable.", "Reject similarity promotion after version ambiguity, failed repeated control, or any major forbidden drift."),
        DHI2011ControlledProbeV1("probe:dhi2011:ambrette-omission", "Does the Ambrettolide proxy bind pear, talc, and skin rather than merely add musk?", ("selected 1,600 uL of 10% w/w Ambrettolide", "0 uL Ambrettolide with carrier-matched replacement", "800 uL Ambrettolide with carrier-matched replacement"), ("6,000 uL total", "all fruit and support-musk rows fixed", "stock density measured before claiming exact carrier displacement"), ("pear-liqueur nuance", "silk-talc texture", "iris continuity", "musk naming", "liking"), ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "coded blind", "counterbalanced", "Retain the lowest dose that improves the relation without wine-musk or laundry naming.", "Remove or reduce if no causal change or musk becomes an object."),
        DHI2011ControlledProbeV1("probe:dhi2011:cocoa-shadow", "Is literal Cocoa Absolute needed for the dark shadow?", ("selected zero: 0 uL Cocoa plus 80 uL Benzyl Benzoate replacement space", "40 uL Cocoa plus 40 uL Benzyl Benzoate replacement space", "80 uL Cocoa plus 0 uL Benzyl Benzoate replacement space"), ("6,000 uL total", "the other 120 uL Benzyl Benzoate fixed", "all other rows fixed", "same natural lot", "constituent-composite OAV used"), ("iris dominance", "dark warmth", "chocolate naming", "target fidelity", "liking"), ("heart_30min", "late_heart_2h", "drydown_4h"), "coded blind", "Williams-balanced order", "Use a nonzero dose only if zero is repeatably inferior on dark warmth and the addition is not worse on target fidelity.", "Reject literal cocoa if chocolate is named or the zero arm is not inferior."),
        DHI2011ControlledProbeV1("probe:dhi2011:orivone-frontier", "Does Orivone improve orris continuity without a potency spike?", ("0 uL Orivone plus 20 uL Benzyl Benzoate", "selected 20 uL Orivone", "40 uL Orivone minus 20 uL Benzyl Benzoate"), ("6,000 uL total", "all other iris rows fixed"), ("orris continuity", "butter or wax defect", "iris dimensionality", "target fidelity"), ("top_5min", "heart_30min", "late_heart_2h"), "coded blind", "balanced order", "Select the lowest dose that improves the iris-to-warmth seam.", "Reject if wax/butter becomes named or no improvement is repeatable."),
        DHI2011ControlledProbeV1("probe:dhi2011:lavender-frontier", "Where is the lavender dose that is legible but not fougere?", ("95 uL Lavender plus 40 uL Benzyl Benzoate", "selected 135 uL Lavender", "175 uL Lavender minus 40 uL Benzyl Benzoate"), ("6,000 uL total", "Linalyl Acetate and Linalool fixed", "all non-lavender rows fixed"), ("opening recognition", "handoff by 30 minutes", "fougere drift", "target fidelity"), ("opening_0s", "top_5min", "heart_30min"), "coded blind", "balanced order", "Select the lowest arm with reliable opening recognition and complete handoff by 30 minutes.", "Reject an arm if lavender remains the subject at 30 minutes."),
        DHI2011ControlledProbeV1("probe:dhi2011:wood-frontier", "Which cedar-vetiver relation gives a dry return without pencil or root takeover?", ("290 uL cedar plus 100 uL vetiver", "selected 250 uL cedar plus 140 uL vetiver", "210 uL cedar plus 180 uL vetiver"), ("390 uL cedar-plus-vetiver total", "6,000 uL formula total", "Vetival and Sandalore fixed", "all other rows fixed"), ("cedar grain", "vetiver earth", "iris persistence", "late masculine return", "defects"), ("late_heart_2h", "drydown_4h"), "coded blind", "balanced order", "Retain the arm with a recognizable dry return and neither wood named as a new subject.", "Reject pencil, smoke, root, green, or abrupt base takeover."),
        DHI2011ControlledProbeV1("probe:dhi2011:iris-anatomy", "Does multi-part iris anatomy outperform an equal-total AIMI wall?", ("selected eight-row iris/root/tail geometry", "same nominal active total collapsed toward AIMI", "selected geometry with the late-tail quartet omitted and constant-total replacement"), ("nominal iris active total held where chemically meaningful", "DEP and total raw volume carrier matched", "all non-iris rows fixed"), ("iris recognition", "root coolness", "violet mobility", "late iris trace", "lipstick flatness", "target fidelity"), ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "coded blind", "balanced order", "Retain each submodule only if it adds repeatable target-linked anatomy without extra defects.", "Reject count-based complexity if the collapsed or reduced arm is not inferior."),
        DHI2011ControlledProbeV1("probe:dhi2011:pear-continuum", "Does the four-route fruit system create a pear-liqueur glint inside ambrette rather than a freestanding fruit accord?", ("selected E2MB/Verdox/Benzyl Acetate/Osmanthus geometry", "all four omitted with carrier-matched constant-total replacement", "E2MB plus Verdox only with matched replacement"), ("6,000 uL total", "Ambrettolide fixed", "all iris rows fixed", "DPG matched"), ("pear recognition", "liqueur nuance", "fruit integration", "candy or tropical drift", "target fidelity", "liking"), ("opening_0s", "top_5min", "heart_30min", "late_heart_2h"), "coded blind", "balanced order", "Keep only fruit routes whose loss is repeatable and whose addition improves target fidelity.", "Reject any route that becomes a named candy, tropical, peach, banana, or apricot note."),
        DHI2011ControlledProbeV1("probe:dhi2011:talc-cushion", "Does the talc-textile cushion soften the iris-to-musk seam without blurring identity?", ("selected Benzyl Salicylate/Mimosa/Ethylene Brassylate cushion", "cushion omitted with matched constant-total replacement", "Benzyl Salicylate and Mimosa omitted while Ethylene Brassylate remains"), ("6,000 uL total", "AIMI and Ambrettolide fixed", "DPG matched"), ("silk-talc texture", "iris legibility", "chalk defect", "musk blur", "liking"), ("heart_30min", "late_heart_2h", "drydown_4h"), "coded blind", "balanced order", "Retain the smallest cushion that improves continuity and liking without reducing iris identity.", "Remove a row if its omission has no repeatable loss or if sunscreen, yellow floral, or musk blanket appears."),
        DHI2011ControlledProbeV1("probe:dhi2011:musk-axes", "Are the three musk axes nonredundant?", ("selected Ambrettolide/Ethylene Brassylate/Romandolide geometry", "Romandolide omitted with constant-total replacement", "Ethylene Brassylate omitted with constant-total replacement"), ("Ambrettolide fixed", "6,000 uL total", "all non-musk rows fixed"), ("fruit-skin mediation", "velvet mass", "outward trail", "laundry defect", "iris legibility", "liking"), ("heart_30min", "late_heart_2h", "drydown_4h"), "coded blind", "balanced order", "Retain a support musk only when its distinct axis and omission loss are repeatable.", "Remove Romandolide first if it adds no exterior trail; reduce Ethylene Brassylate if it blurs iris."),
        DHI2011ControlledProbeV1("probe:dhi2011:seam-smoothness", "Are all four major handoffs continuous while their source and target remain legible?", ("selected complete formula", "fruit-orris bridge omitted", "warmth-wood bridge omitted"), ("6,000 uL total", "carrier-matched replacement", "same maturation and application mass"), ("lavender-to-fruit continuity", "fruit-to-orris continuity", "orris-to-warmth continuity", "warmth-to-wood continuity", "source legibility", "target legibility", "liking"), TIME_WINDOWS, "coded blind", "balanced order with hidden repeated control", "Pass a seam only when continuity and both endpoint identities are repeatable; average liking cannot compensate for a failed seam.", "Reject smoothness promotion if any handoff is abrupt, muddy, or achieved by erasing one endpoint."),
    )

    mechanisms = (
        DHI2011MechanismV1("mechanism:version-bounded-object", (DHI2011DepthDimension.OBJECT_IDENTITY, DHI2011DepthDimension.COGNITIVE_CONTEXT, DHI2011DepthDimension.EVIDENCE_QUALITY), ("intent:aimi", "intent:lavender", "intent:cedar", "intent:vetiver"), ("fn:version-lock", "fn:iris-object"), "Version-bounded recognizers prevent attractive but wrong Dior-lineage substitutions from scoring as success.", "A generic iris perfume can be mislabeled as DHI 2011.", "Cross-version contamination or unsupported exact-formula language.", TIME_WINDOWS, "probe:dhi2011:whole-formula", DHI2011EvidenceTier.COLLECTOR_VERSION_EVIDENCE),
        DHI2011MechanismV1("mechanism:iris-internal-anatomy", (DHI2011DepthDimension.INTERNAL_ANATOMY, DHI2011DepthDimension.NONLINEAR_INTERACTION, DHI2011DepthDimension.CONSTRUCTION_COMPLEXITY_DIAGNOSTIC), ("intent:aimi", "intent:alpha-ionone", "intent:alpha-irone", "intent:orivone", "intent:dihydro-beta-ionone", "intent:irotyl", "intent:ultralia", "intent:carrot-seed"), ("fn:iris-object", "fn:iris-mobility", "fn:orris-root", "fn:iris-tail"), "Separate body, movement, root, warm seam, and late tail may create a dimensional orris object without granting credit for count.", "The iris collapses into one flat cosmetic color.", "Any added row is redundant, or one ionone/root material takes over.", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "probe:dhi2011:iris-anatomy", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:pear-liquor-continuum", (DHI2011DepthDimension.INTERNAL_ANATOMY, DHI2011DepthDimension.RELATIONAL_TOPOLOGY, DHI2011DepthDimension.NONLINEAR_INTERACTION), ("intent:e2mb", "intent:verdox", "intent:benzyl-acetate", "intent:osmanthus", "intent:ambrettolide"), ("fn:pear-glint", "fn:ambrette-mediator"), "A flash, green body, floral skin, and suede trace should be absorbed by Ambrettolide into one restrained pear-liqueur membrane.", "Pear remains absent or arrives as a disconnected top note.", "Candy, tropical fruit, apricot, or wine musk becomes independently nameable.", ("opening_0s", "top_5min", "heart_30min", "late_heart_2h"), "probe:dhi2011:pear-continuum", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:ambrette-membrane", (DHI2011DepthDimension.RELATIONAL_TOPOLOGY, DHI2011DepthDimension.TEXTURE_AND_MATERIALITY, DHI2011DepthDimension.NONLINEAR_INTERACTION), ("intent:ambrettolide", "intent:aimi", "intent:alpha-ionone", "intent:verdox", "intent:mimosa"), ("fn:ambrette-mediator", "fn:pear-glint", "fn:talc-cushion", "fn:skin-closure"), "The fruity macrocyclic musk should bind the explicit pear and talc structures to iris and skin rather than impersonating them.", "The fruit/talc relation detaches and the drydown loses continuity.", "Wine musk, fruit candy, or laundry becomes independently nameable.", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "probe:dhi2011:ambrette-omission", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:powder-textile-cushion", (DHI2011DepthDimension.TEXTURE_AND_MATERIALITY, DHI2011DepthDimension.NONLINEAR_INTERACTION, DHI2011DepthDimension.HEDONIC_ARCHITECTURE), ("intent:benzyl-salicylate", "intent:mimosa", "intent:ethylene-brassylate", "intent:aimi"), ("fn:talc-cushion", "fn:musk-velvet", "fn:iris-object"), "Waxy film, natural powder irregularity, and creamy musk mass should turn cosmetic powder into silk textile without erasing iris.", "The heart is chalky or the base arrives as a separate musk block.", "Sunscreen, yellow floral, or anonymous musk blanket becomes the identity.", ("heart_30min", "late_heart_2h", "drydown_4h"), "probe:dhi2011:talc-cushion", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:negative-space", (DHI2011DepthDimension.CONTRAST_AND_NEGATIVE_SPACE, DHI2011DepthDimension.SPATIAL_PERFORMANCE), ("intent:hedione", "intent:iso-e", "intent:benzyl-benzoate"), ("fn:negative-space",), "Fast floral air, transparent woody rear volume, and slow structural mass separate the dense iris foreground from its frame.", "The perfume becomes an opaque sweet powder block.", "Diffusion materials replace the target with a generic radiant woody aura.", ("top_5min", "heart_30min", "late_heart_2h", "drydown_4h"), "probe:dhi2011:whole-formula", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:temporal-tailoring", (DHI2011DepthDimension.TEMPORAL_ARCHITECTURE, DHI2011DepthDimension.PHYSICAL_CHEMISTRY), ("intent:lavender", "intent:linalyl-acetate", "intent:linalool", "intent:e2mb", "intent:hedione", "intent:benzyl-benzoate"), ("fn:lavender-entry", "fn:pear-glint", "fn:negative-space"), "Differential volatility should produce an aromatic veil, fruit glint, iris maximum, and late woody exposure rather than a static pyramid.", "The opening is missing or phase changes are abrupt.", "Lavender persists as subject, or modeled volatility is mistaken for observed evolution.", TIME_WINDOWS, "probe:dhi2011:lavender-frontier", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:warmth-under-iris", (DHI2011DepthDimension.TEXTURE_AND_MATERIALITY, DHI2011DepthDimension.ROBUSTNESS_ANTI_COLLAPSE, DHI2011DepthDimension.HEDONIC_ARCHITECTURE), ("intent:tonkarome", "intent:isobutavan", "intent:orivone"), ("fn:warm-shadow", "fn:coumarinic-shadow", "fn:vanillic-shadow"), "Separate coumarinic, vanillic, and fatty-orris traces should warm the underside of iris while remaining unnamed.", "The heart is cold, thin, and violet-woody.", "Chocolate, tonka, pastry, vanilla, or fougere naming reveals collapse.", ("heart_30min", "late_heart_2h", "drydown_4h"), "probe:dhi2011:cocoa-shadow", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:wood-counterform", (DHI2011DepthDimension.RELATIONAL_TOPOLOGY, DHI2011DepthDimension.TEMPORAL_ARCHITECTURE, DHI2011DepthDimension.ROBUSTNESS_ANTI_COLLAPSE), ("intent:cedar", "intent:vetiver", "intent:vetival", "intent:sandalore", "intent:iso-e", "intent:cashmeran", "intent:dihydro-beta-ionone"), ("fn:wood-return", "fn:wood-softening", "fn:negative-space", "fn:iris-tail"), "Polished vetiver, soft sandal, textile wood, and woody ionone should reveal cedar-vetiver gradually after the iris maximum.", "The base is only cosmetic musk and amber warmth.", "Pencil cedar, earthy vetiver, creamy sandalwood, or generic wood pressure takes over.", ("late_heart_2h", "drydown_4h"), "probe:dhi2011:wood-frontier", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:skin-recurrence", (DHI2011DepthDimension.RELATIONAL_TOPOLOGY, DHI2011DepthDimension.SPATIAL_PERFORMANCE, DHI2011DepthDimension.TEMPORAL_ARCHITECTURE), ("intent:ambrettolide", "intent:ethylene-brassylate", "intent:romandolide", "intent:cashmeran", "intent:cedar", "intent:ultralia"), ("fn:skin-closure", "fn:musk-velvet", "fn:musk-diffusion", "fn:iris-tail"), "Inward fruity skin, creamy velvet, and outward woody diffusion should carry a small pear-talc-iris memory into dry wood.", "The perfume ends as disconnected dry wood.", "Musk becomes detergent-clean, anonymously thick, or independently fruity.", ("late_heart_2h", "drydown_4h"), "probe:dhi2011:musk-axes", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:seam-continuity", (DHI2011DepthDimension.RELATIONAL_TOPOLOGY, DHI2011DepthDimension.TEMPORAL_ARCHITECTURE, DHI2011DepthDimension.HEDONIC_ARCHITECTURE, DHI2011DepthDimension.ROBUSTNESS_ANTI_COLLAPSE), ("intent:linalyl-acetate", "intent:verdox", "intent:ambrettolide", "intent:alpha-ionone", "intent:orivone", "intent:tonkarome", "intent:dihydro-beta-ionone", "intent:sandalore"), ("fn:lavender-entry", "fn:pear-glint", "fn:ambrette-mediator", "fn:iris-mobility", "fn:warm-shadow", "fn:wood-softening"), "Each handoff must share at least two material or facet routes while preserving recognizability of both endpoints.", "One phase cuts abruptly into the next or the perfume becomes muddy.", "Apparent smoothness is obtained by erasing the source or target identity.", TIME_WINDOWS, "probe:dhi2011:seam-smoothness", DHI2011EvidenceTier.PERFUMER_INFERENCE),
        DHI2011MechanismV1("mechanism:separate-endpoints", (DHI2011DepthDimension.HEDONIC_ARCHITECTURE, DHI2011DepthDimension.EVIDENCE_QUALITY), ("intent:aimi", "intent:ambrettolide", "intent:cedar"), ("fn:iris-object", "fn:ambrette-mediator", "fn:wood-return"), "Target fidelity, identity, depth, richness, liking, projection, and defects are recorded separately so a liked off-target perfume cannot masquerade as a match.", "A single score conceals why an arm wins.", "Beauty, OAV, or component count is used as a proxy for the missing endpoint.", TIME_WINDOWS, "probe:dhi2011:whole-formula", DHI2011EvidenceTier.REFERENCE_SAMPLE_TEST_REQUIRED),
    )

    selected_notes = _candidate_notes("Ambrette-Orris Velvet", "iris, musk, or sweetness loses its relational hierarchy")
    cocoa_notes = _candidate_notes("Cocoa-Leather Caricature", "dark edible or leather imagery overrides evidence-supported ambrette and wood")
    clean_notes = _candidate_notes("Clean Soapy Iris", "pressed-shirt freshness turns DHI into a Prada-like clean iris")
    parfum_notes = _candidate_notes("Oud-Sandal Leather", "Dior Homme Parfum architecture contaminates the 05443/A target")
    wall_notes = _candidate_notes("Ionone Wall", "material mass creates a flat lipstick object without ambrette mediation or phase change")
    candidates = (
        _candidate("candidate:ambrette-orris-velvet", "Ambrette-Orris Velvet", "Lavender opens a silk-talc and pear-liqueur membrane around a dimensional iris body; restrained warmth shades it before dry cedar-vetiver and musky textile return.", "ambrette mediates every handoff into and out of the iris object", (3, 3, 3, 3, 3, 3, 3, 3, 2, 3), selected_notes, "a forbidden drift is preferred or the selected geometry is not repeatably distinguishable.", function_ids, "protocol:dhi2011:selected-versus-alternatives"),
        _candidate("candidate:cocoa-leather-caricature", "Cocoa-Leather Caricature", "A dark chocolate lipstick accord rests on leather and sweet amber.", "cocoa and leather replace ambrette mediation", (3, 2, 1, 2, 1, 2, 1, 1, 2, 2), cocoa_notes, "chocolate or leather is named before ambrette, cedar, or vetiver.", ("fn:iris-object", "fn:warm-shadow"), "probe:dhi2011:cocoa-shadow"),
        _candidate("candidate:clean-soapy-iris", "Clean Soapy Iris", "Bright neroli-muguet cleanliness and white musk polish a violet iris over transparent amber woods.", "clean floral volume replaces pear-talc density", (2, 2, 1, 2, 1, 1, 2, 1, 2, 2), clean_notes, "the result is classified as clean soapy iris rather than DHI.", ("fn:iris-object", "fn:negative-space"), "protocol:dhi2011:selected-versus-alternatives"),
        _candidate("candidate:oud-sandal-leather", "Oud-Sandal Leather", "Dense iris is darkened by leather, oud, and creamy sandalwood.", "a leather-wood subject replaces cedar-vetiver return", (0, 2, 0, 1, 1, 2, 1, 1, 1, 2), parfum_notes, "assessors identify Dior Homme Parfum or leather-oud before DHI 2011.", ("fn:iris-object",), "protocol:dhi2011:selected-versus-alternatives"),
        _candidate("candidate:ionone-wall", "Ionone Wall", "A very large methyl-ionone block with vanilla and generic woods maximizes lipstick powder.", "material mass substitutes for internal anatomy and transition", (2, 2, 0, 1, 1, 1, 0, 1, 2, 2), wall_notes, "the formula is static, chalky, or identifiable only as lipstick iris.", ("fn:iris-object",), "probe:dhi2011:iris-anatomy"),
    )

    return DHI2011ArchitectureRequestV1(
        target=target,
        evidence_claims=evidence_claims,
        criteria_priority=tuple(DHI2011Criterion),
        candidates=candidates,
        functions=functions,
        layers=layers,
        transitions=transitions,
        material_intents=material_intents,
        controlled_probes=probes,
        mechanisms=mechanisms,
        time_windows=TIME_WINDOWS,
        formula_binding_ref="formulas/DHI-11_Velours_d_Iris_05443A_30mL_20pct_V3_Smooth.md",
        inventory_execution_state="EXPLORATORY_RAW_VOLUME_BUILD_FROM_LIVE_INVENTORY_TEXT",
    )


def _assessment_map(candidate: DHI2011CandidateV1) -> dict[DHI2011Criterion, DHI2011SupportLevel]:
    return {assessment.criterion: assessment.support_level for assessment in candidate.assessments}


def _dominance(
    left: DHI2011CandidateV1,
    right: DHI2011CandidateV1,
    criteria: tuple[DHI2011Criterion, ...],
) -> DHI2011DominanceRecordV1 | None:
    left_map = _assessment_map(left)
    right_map = _assessment_map(right)
    if any(left_map[criterion] < right_map[criterion] for criterion in criteria):
        return None
    stronger = tuple(criterion for criterion in criteria if left_map[criterion] > right_map[criterion])
    if not stronger:
        return None
    equal = tuple(criterion for criterion in criteria if left_map[criterion] == right_map[criterion])
    return DHI2011DominanceRecordV1(left.candidate_id, right.candidate_id, equal, stronger)


def evaluate_dhi_2011_architecture(
    request: DHI2011ArchitectureRequestV1,
) -> DHI2011ArchitectureResultV1:
    """Validate graph closure and select the non-dominated architecture frontier."""

    criteria = request.criteria_priority
    required_criteria = set(criteria)
    for candidate in request.candidates:
        if set(_assessment_map(candidate)) != required_criteria:
            raise ValueError(f"{candidate.candidate_id} does not assess every criterion")

    function_ids = {item.function_id for item in request.functions}
    layer_ids = {item.layer_id for item in request.layers}
    intent_ids = {item.intent_id for item in request.material_intents}
    probe_ids = {item.probe_id for item in request.controlled_probes}
    for layer in request.layers:
        if not set(layer.owned_function_ids).issubset(function_ids):
            raise ValueError(f"{layer.layer_id} references an unknown function")
    for transition in request.transitions:
        if transition.source_layer_id not in layer_ids or transition.target_layer_id not in layer_ids:
            raise ValueError(f"{transition.transition_id} references an unknown layer")
    for mechanism in request.mechanisms:
        if not set(mechanism.participant_intent_ids).issubset(intent_ids):
            raise ValueError(f"{mechanism.mechanism_id} references an unknown material intent")
        if not set(mechanism.function_ids).issubset(function_ids):
            raise ValueError(f"{mechanism.mechanism_id} references an unknown function")
        if mechanism.falsification_probe_id not in probe_ids:
            raise ValueError(f"{mechanism.mechanism_id} references an unknown probe")

    dominance_records: list[DHI2011DominanceRecordV1] = []
    dominated: set[str] = set()
    for left in request.candidates:
        for right in request.candidates:
            if left is right:
                continue
            record = _dominance(left, right, criteria)
            if record is not None:
                dominance_records.append(record)
                dominated.add(right.candidate_id)
    frontier = tuple(
        candidate.candidate_id
        for candidate in request.candidates
        if candidate.candidate_id not in dominated
    )

    required_dimensions = tuple(
        dimension
        for dimension in DHI2011DepthDimension
        if dimension is not DHI2011DepthDimension.CONSTRUCTION_COMPLEXITY_DIAGNOSTIC
    )
    covered_set = {
        dimension for mechanism in request.mechanisms for dimension in mechanism.dimensions
    }
    covered_dimensions = tuple(
        dimension for dimension in DHI2011DepthDimension if dimension in covered_set
    )
    uncovered_dimensions = tuple(
        dimension for dimension in required_dimensions if dimension not in covered_set
    )

    if uncovered_dimensions:
        state = DHI2011ProgramState.HOLD
        selected = None
    elif len(frontier) == 1:
        state = DHI2011ProgramState.THEORY_SELECTED
        selected = frontier[0]
    else:
        state = DHI2011ProgramState.FRONTIER
        selected = None

    return DHI2011ArchitectureResultV1(
        state=state,
        request_sha256=request.record_sha256,
        selected_candidate_id=selected,
        frontier_candidate_ids=frontier,
        dominance_records=tuple(dominance_records),
        required_dimensions=required_dimensions,
        covered_dimensions=covered_dimensions,
        uncovered_dimensions=uncovered_dimensions,
        reason_codes=(
            "TARGET_LOCKED_TO_05443A",
            "PARETO_SELECTION_NO_SCALAR_BEAUTY_SCORE",
            "ALL_REQUIRED_DEPTH_DIMENSIONS_BOUND_TO_FALSIFICATION",
            "REFERENCE_SAMPLE_REQUIRED_FOR_SIMILARITY",
            "LIVE_INVENTORY_TEXT_USED_FOR_EXPLORATORY_RAW_VOLUME_HANDOFF",
            "ALL_DOWNSTREAM_AUTHORITIES_WITHHELD",
        ),
        claim_ceiling=request.target.claim_ceiling,
        authorities=request.target.authorities,
    )


def build_default_dhi_2011_architecture() -> tuple[
    DHI2011ArchitectureRequestV1, DHI2011ArchitectureResultV1
]:
    request = build_default_dhi_2011_architecture_request()
    return request, evaluate_dhi_2011_architecture(request)


__all__ = [
    "DHI2011ArchitectureRequestV1",
    "DHI2011ArchitectureResultV1",
    "DHI2011AuthorityVectorV1",
    "DHI2011Criterion",
    "DHI2011DepthDimension",
    "DHI2011EvidenceTier",
    "DHI2011ProgramState",
    "DHI2011SupportLevel",
    "TIME_WINDOWS",
    "build_default_dhi_2011_architecture",
    "build_default_dhi_2011_architecture_request",
    "evaluate_dhi_2011_architecture",
]
