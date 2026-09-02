"""Authority-bounded execution profiles for formulation-intelligence requests.

The profile answers a workflow question that the architectural planes do not:
which evidence and verification work is required for an interactive design
draft, a human-reviewed compounding card, or a release review?  It binds the
complete whole-perfume blueprint and derives every mode policy.  Callers cannot
upgrade the policy by supplying a shorter checklist or a stronger authority.

This module plans work only.  It performs no file, network, process, model,
formula, compounding, or release operation and is not a runtime admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any, Mapping

from engine.authority_gates import ModeAction, OperatingMode, evaluate_mode_action

from .contracts import AuthorityCeiling
from .inventory_projection import (
    _bool,
    _canonical_json_bytes,
    _CanonicalProjectionRecord,
    _digest,
    _mapping,
    _payload,
    _sequence,
    _text,
)
from .whole_perfume_assembler import WholePerfumeBlueprint


class FormulationExecutionMode(str, Enum):
    """Three deliberately different latency and evidence envelopes."""

    FAST_DRAFT = "fast_draft"
    COMPOUNDING_CARD = "compounding_card"
    RELEASE_REVIEW = "release_review"


class FormulationRequestKind(str, Enum):
    NEW_DESIGN = "new_design"
    REVISION = "revision"


class VerificationScope(str, Enum):
    INLINE_ARITHMETIC_AND_SCHEMA = "inline_arithmetic_and_schema"
    FOCUSED_FORMULA_GATES = "focused_formula_gates"
    FULL_RELEASE = "full_release"


class ResearchScope(str, Enum):
    LOCAL_ONLY = "local_only"
    PRIMARY_OR_OFFICIAL_IF_GAP = "primary_or_official_if_gap"


class DelegationScope(str, Enum):
    NONE = "none"
    OPENAI_NATIVE_READ_ONLY = "openai_native_read_only"


class ExecutionCheck(str, Enum):
    ACTIVE_INSTRUCTIONS_BOUND = "active_instructions_bound"
    TARGET_IDENTITY_BOUND = "target_identity_bound"
    TARGET_IDEAL_BUILD_SEPARATED = "target_ideal_build_separated"
    WHOLE_PLANE_BLUEPRINT_BOUND = "whole_plane_blueprint_bound"
    INVENTORY_CONTENT_HASH_BOUND = "inventory_content_hash_bound"
    STOCK_AUTHORITY_OVERLAY_HASH_BOUND = "stock_authority_overlay_hash_bound"
    EXACT_STOCK_RECORDS_HASH_BOUND = "exact_stock_records_hash_bound"
    STOCK_IDENTITY_AND_FRACTION_HOLD_SCAN = (
        "stock_identity_and_fraction_hold_scan"
    )
    ACTIVE_DOSE_PPM_ODT_OAV_SCREEN = "active_dose_ppm_odt_oav_screen"
    COMPOSITE_NATURAL_OAV_OR_UNKNOWN = "composite_natural_oav_or_unknown"
    SUB_TEN_MICROLITER_RAW_DOSE_FLAG = "sub_ten_microliter_raw_dose_flag"
    UNKNOWN_AND_AUTHORITY_CEILING_REPORTED = (
        "unknown_and_authority_ceiling_reported"
    )
    EXACT_FORMULA_PARSE = "exact_formula_parse"
    CARRIER_DISPLACEMENT = "carrier_displacement"
    IMMEDIATE_PARENT_EQUIVALENCE_IF_REVISION = (
        "immediate_parent_equivalence_if_revision"
    )
    OAV_PER_TIME_SCREENING_GUARD = "oav_per_time_screening_guard"
    FOCUSED_IFRA_SCREEN = "focused_ifra_screen"
    MATRIX_MATCHED_CONTROL = "matrix_matched_control"
    PREMIX_ACTIVE_DOSE_GATE = "premix_active_dose_gate"
    FORMULA_ARTIFACT_BINDING = "formula_artifact_binding"
    RELEVANT_FULL_TESTS = "relevant_full_tests"
    FULL_PROJECT_VERIFICATION = "full_project_verification"
    FROZEN_SOL_XHIGH_ADMISSION = "frozen_sol_xhigh_admission"
    HUMAN_SENSORY_EVIDENCE_REVIEW = "human_sensory_evidence_review"
    SAFETY_AND_STABILITY_EVIDENCE_REVIEW = (
        "safety_and_stability_evidence_review"
    )
    HUMAN_RELEASE_DECISION = "human_release_decision"


class ExecutionOutput(str, Enum):
    TARGET_IDEAL_ARCHITECTURE = "target_ideal_architecture"
    CURRENT_INVENTORY_BUILD_DRAFT = "current_inventory_build_draft"
    ACTIVE_DOSE_PPM_ODT_OAV_TABLE = "active_dose_ppm_odt_oav_table"
    ABSTRACT_TEMPORAL_SEQUENCE = "abstract_temporal_sequence"
    UNKNOWNS_AND_AUTHORITY_REPORT = "unknowns_and_authority_report"
    HUMAN_REVIEW_COMPOUNDING_CARD_DRAFT = (
        "human_review_compounding_card_draft"
    )
    MATRIX_MATCHED_CONTROL_DRAFT = "matrix_matched_control_draft"
    RELEASE_REVIEW_RECORD = "release_review_record"


@dataclass(frozen=True, slots=True)
class _ModePolicy:
    operating_mode: OperatingMode
    mode_actions: tuple[ModeAction, ...]
    checks: tuple[ExecutionCheck, ...]
    outputs: tuple[ExecutionOutput, ...]
    verification_scope: VerificationScope
    research_scope: ResearchScope
    delegation_scope: DelegationScope


_FAST_CHECKS = (
    ExecutionCheck.ACTIVE_INSTRUCTIONS_BOUND,
    ExecutionCheck.TARGET_IDENTITY_BOUND,
    ExecutionCheck.TARGET_IDEAL_BUILD_SEPARATED,
    ExecutionCheck.WHOLE_PLANE_BLUEPRINT_BOUND,
    ExecutionCheck.INVENTORY_CONTENT_HASH_BOUND,
    ExecutionCheck.STOCK_AUTHORITY_OVERLAY_HASH_BOUND,
    ExecutionCheck.EXACT_STOCK_RECORDS_HASH_BOUND,
    ExecutionCheck.STOCK_IDENTITY_AND_FRACTION_HOLD_SCAN,
    ExecutionCheck.ACTIVE_DOSE_PPM_ODT_OAV_SCREEN,
    ExecutionCheck.COMPOSITE_NATURAL_OAV_OR_UNKNOWN,
    ExecutionCheck.SUB_TEN_MICROLITER_RAW_DOSE_FLAG,
    ExecutionCheck.UNKNOWN_AND_AUTHORITY_CEILING_REPORTED,
)

_COMPOUNDING_CHECKS = (
    *_FAST_CHECKS,
    ExecutionCheck.EXACT_FORMULA_PARSE,
    ExecutionCheck.CARRIER_DISPLACEMENT,
    ExecutionCheck.IMMEDIATE_PARENT_EQUIVALENCE_IF_REVISION,
    ExecutionCheck.OAV_PER_TIME_SCREENING_GUARD,
    ExecutionCheck.FOCUSED_IFRA_SCREEN,
    ExecutionCheck.MATRIX_MATCHED_CONTROL,
    ExecutionCheck.PREMIX_ACTIVE_DOSE_GATE,
)

_RELEASE_CHECKS = (
    *_COMPOUNDING_CHECKS,
    ExecutionCheck.FORMULA_ARTIFACT_BINDING,
    ExecutionCheck.RELEVANT_FULL_TESTS,
    ExecutionCheck.FULL_PROJECT_VERIFICATION,
    ExecutionCheck.FROZEN_SOL_XHIGH_ADMISSION,
    ExecutionCheck.HUMAN_SENSORY_EVIDENCE_REVIEW,
    ExecutionCheck.SAFETY_AND_STABILITY_EVIDENCE_REVIEW,
    ExecutionCheck.HUMAN_RELEASE_DECISION,
)

_FAST_OUTPUTS = (
    ExecutionOutput.TARGET_IDEAL_ARCHITECTURE,
    ExecutionOutput.CURRENT_INVENTORY_BUILD_DRAFT,
    ExecutionOutput.ACTIVE_DOSE_PPM_ODT_OAV_TABLE,
    ExecutionOutput.ABSTRACT_TEMPORAL_SEQUENCE,
    ExecutionOutput.UNKNOWNS_AND_AUTHORITY_REPORT,
)

_MODE_POLICIES: dict[FormulationExecutionMode, _ModePolicy] = {
    FormulationExecutionMode.FAST_DRAFT: _ModePolicy(
        operating_mode=OperatingMode.CREATIVE_FORMULATION,
        mode_actions=(
            ModeAction.BRIEF_CONTRACT,
            ModeAction.FAMILY_ARCHETYPE,
            ModeAction.FUNCTIONAL_GRAPH,
            ModeAction.CANDIDATE_GENERATION,
            ModeAction.TARGET_VERSION,
            ModeAction.REPORT,
        ),
        checks=_FAST_CHECKS,
        outputs=_FAST_OUTPUTS,
        verification_scope=VerificationScope.INLINE_ARITHMETIC_AND_SCHEMA,
        research_scope=ResearchScope.LOCAL_ONLY,
        delegation_scope=DelegationScope.NONE,
    ),
    FormulationExecutionMode.COMPOUNDING_CARD: _ModePolicy(
        operating_mode=OperatingMode.INVENTORY_MAPPING,
        mode_actions=(
            ModeAction.LOT_MATCHING,
            ModeAction.STOCK_BASIS_CONVERSION,
            ModeAction.SUBSTITUTION,
            ModeAction.MEASURABLE_BUILD_DRAFT,
            ModeAction.REPORT,
        ),
        checks=_COMPOUNDING_CHECKS,
        outputs=(
            *_FAST_OUTPUTS,
            ExecutionOutput.HUMAN_REVIEW_COMPOUNDING_CARD_DRAFT,
            ExecutionOutput.MATRIX_MATCHED_CONTROL_DRAFT,
        ),
        verification_scope=VerificationScope.FOCUSED_FORMULA_GATES,
        research_scope=ResearchScope.LOCAL_ONLY,
        delegation_scope=DelegationScope.NONE,
    ),
    FormulationExecutionMode.RELEASE_REVIEW: _ModePolicy(
        operating_mode=OperatingMode.RELEASE_REVIEW,
        mode_actions=(
            ModeAction.READ_ONLY_REVIEW,
            ModeAction.CLAIM_DECISION,
            ModeAction.HUMAN_TRANSITION,
            ModeAction.REPORT,
        ),
        checks=_RELEASE_CHECKS,
        outputs=(
            *_FAST_OUTPUTS,
            ExecutionOutput.HUMAN_REVIEW_COMPOUNDING_CARD_DRAFT,
            ExecutionOutput.MATRIX_MATCHED_CONTROL_DRAFT,
            ExecutionOutput.RELEASE_REVIEW_RECORD,
        ),
        verification_scope=VerificationScope.FULL_RELEASE,
        research_scope=ResearchScope.PRIMARY_OR_OFFICIAL_IF_GAP,
        delegation_scope=DelegationScope.OPENAI_NATIVE_READ_ONLY,
    ),
}


_AUTHORITY_FLAGS = (
    "formula_execution_authorized",
    "repository_write_authorized",
    "physical_execution_authorized",
    "purchase_authority",
    "observed_smell",
    "sensory_authority",
    "liking_authority",
    "similarity_authority",
    "performance_authority",
    "safety_authority",
    "stability_authority",
    "release_authorized",
)


def _optional_digest(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _digest(value, field_name)


def _execution_plan_id(
    *,
    mode: FormulationExecutionMode,
    request_kind: FormulationRequestKind,
    whole_perfume_blueprint_sha256: str,
    immediate_parent_formula_sha256: str | None,
    policy: _ModePolicy,
    authority_ceiling: AuthorityCeiling,
) -> str:
    payload = {
        "schema_version": "formulation_execution_plan_identity_v1",
        "mode": mode.value,
        "request_kind": request_kind.value,
        "operating_mode": policy.operating_mode.value,
        "mode_actions": [item.value for item in policy.mode_actions],
        "whole_perfume_blueprint_sha256": whole_perfume_blueprint_sha256,
        "immediate_parent_formula_sha256": immediate_parent_formula_sha256,
        "required_checks": [item.value for item in policy.checks],
        "outputs": [item.value for item in policy.outputs],
        "verification_scope": policy.verification_scope.value,
        "research_scope": policy.research_scope.value,
        "delegation_scope": policy.delegation_scope.value,
        "authority_ceiling": authority_ceiling.value,
        "authority_flags": {field_name: False for field_name in _AUTHORITY_FLAGS},
    }
    return "formulation-execution:" + sha256(_canonical_json_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class FormulationExecutionPlan(_CanonicalProjectionRecord):
    """Immutable, lossless workflow receipt with no execution authority."""

    SCHEMA_VERSION = "formulation_execution_plan_v1"

    plan_id: str
    mode: FormulationExecutionMode
    request_kind: FormulationRequestKind
    operating_mode: OperatingMode
    mode_actions: tuple[ModeAction, ...]
    whole_perfume_blueprint: WholePerfumeBlueprint
    whole_perfume_blueprint_sha256: str
    immediate_parent_formula_sha256: str | None
    required_checks: tuple[ExecutionCheck, ...]
    outputs: tuple[ExecutionOutput, ...]
    verification_scope: VerificationScope
    research_scope: ResearchScope
    delegation_scope: DelegationScope
    authority_ceiling: AuthorityCeiling
    formula_execution_authorized: bool = False
    repository_write_authorized: bool = False
    physical_execution_authorized: bool = False
    purchase_authority: bool = False
    observed_smell: bool = False
    sensory_authority: bool = False
    liking_authority: bool = False
    similarity_authority: bool = False
    performance_authority: bool = False
    safety_authority: bool = False
    stability_authority: bool = False
    release_authorized: bool = False

    def __post_init__(self) -> None:
        mode = FormulationExecutionMode(self.mode)
        request_kind = FormulationRequestKind(self.request_kind)
        if not isinstance(self.whole_perfume_blueprint, WholePerfumeBlueprint):
            raise TypeError(
                "whole_perfume_blueprint must be a WholePerfumeBlueprint"
            )
        blueprint_hash = _digest(
            self.whole_perfume_blueprint_sha256,
            "whole_perfume_blueprint_sha256",
        )
        if blueprint_hash != self.whole_perfume_blueprint.content_sha256:
            raise ValueError(
                "whole_perfume_blueprint_sha256 must bind the complete blueprint"
            )
        parent_hash = _optional_digest(
            self.immediate_parent_formula_sha256,
            "immediate_parent_formula_sha256",
        )
        if request_kind is FormulationRequestKind.REVISION and parent_hash is None:
            raise ValueError("revision plans require the immediate parent formula hash")
        if request_kind is FormulationRequestKind.NEW_DESIGN and parent_hash is not None:
            raise ValueError("new-design plans cannot declare an immediate parent")

        policy = _MODE_POLICIES[mode]
        operating_mode = OperatingMode(self.operating_mode)
        mode_actions = tuple(ModeAction(item) for item in self.mode_actions)
        if operating_mode is not policy.operating_mode:
            raise ValueError("operating_mode must be derived from execution profile")
        if mode_actions != policy.mode_actions:
            raise ValueError("mode_actions must equal the complete derived mode policy")
        if any(
            not evaluate_mode_action(operating_mode, action).allowed
            for action in mode_actions
        ):
            raise ValueError("derived mode action is not allowed by authority_gates")
        checks = tuple(ExecutionCheck(item) for item in self.required_checks)
        outputs = tuple(ExecutionOutput(item) for item in self.outputs)
        if checks != policy.checks:
            raise ValueError("required_checks must equal the complete derived mode policy")
        if outputs != policy.outputs:
            raise ValueError("outputs must equal the complete derived mode policy")
        verification = VerificationScope(self.verification_scope)
        research = ResearchScope(self.research_scope)
        delegation = DelegationScope(self.delegation_scope)
        if verification is not policy.verification_scope:
            raise ValueError("verification_scope must be derived from mode")
        if research is not policy.research_scope:
            raise ValueError("research_scope must be derived from mode")
        if delegation is not policy.delegation_scope:
            raise ValueError("delegation_scope must be derived from mode")

        authority = AuthorityCeiling(self.authority_ceiling)
        if authority is not self.whole_perfume_blueprint.authority_ceiling:
            raise ValueError("execution-plan authority must equal blueprint authority")
        for field_name in _AUTHORITY_FLAGS:
            if _bool(getattr(self, field_name), field_name):
                raise ValueError(
                    f"{field_name} cannot be promoted by an execution plan"
                )

        expected_id = _execution_plan_id(
            mode=mode,
            request_kind=request_kind,
            whole_perfume_blueprint_sha256=blueprint_hash,
            immediate_parent_formula_sha256=parent_hash,
            policy=policy,
            authority_ceiling=authority,
        )
        plan_id = _text(self.plan_id, "plan_id")
        if plan_id != expected_id:
            raise ValueError("plan_id does not match complete execution-plan content")

        object.__setattr__(self, "plan_id", plan_id)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "request_kind", request_kind)
        object.__setattr__(self, "operating_mode", operating_mode)
        object.__setattr__(self, "mode_actions", mode_actions)
        object.__setattr__(self, "whole_perfume_blueprint_sha256", blueprint_hash)
        object.__setattr__(self, "immediate_parent_formula_sha256", parent_hash)
        object.__setattr__(self, "required_checks", checks)
        object.__setattr__(self, "outputs", outputs)
        object.__setattr__(self, "verification_scope", verification)
        object.__setattr__(self, "research_scope", research)
        object.__setattr__(self, "delegation_scope", delegation)
        object.__setattr__(self, "authority_ceiling", authority)

    @property
    def target_intent_sha256(self) -> str:
        return self.whole_perfume_blueprint.ideal_proposal.target_intent.content_sha256

    @property
    def ideal_proposal_sha256(self) -> str:
        return self.whole_perfume_blueprint.ideal_proposal.content_sha256

    @property
    def inventory_projection_sha256(self) -> str:
        return self.whole_perfume_blueprint.inventory_projection.content_sha256

    @property
    def inventory_content_sha256(self) -> str:
        return self.whole_perfume_blueprint.inventory_projection.inventory_content_sha256

    @property
    def stock_authority_overlay_sha256(self) -> str:
        projection = self.whole_perfume_blueprint.inventory_projection
        return projection.stock_authority_overlay_sha256

    @property
    def stock_authority_records_sha256(self) -> str:
        projection = self.whole_perfume_blueprint.inventory_projection
        return projection.stock_authority_records_sha256

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FormulationExecutionPlan:
        data = _payload(payload, cls)
        return cls(
            plan_id=data["plan_id"],
            mode=FormulationExecutionMode(data["mode"]),
            request_kind=FormulationRequestKind(data["request_kind"]),
            operating_mode=OperatingMode(data["operating_mode"]),
            mode_actions=tuple(
                ModeAction(item)
                for item in _sequence(data["mode_actions"], "mode_actions")
            ),
            whole_perfume_blueprint=WholePerfumeBlueprint.from_dict(
                _mapping(
                    data["whole_perfume_blueprint"],
                    "whole_perfume_blueprint",
                )
            ),
            whole_perfume_blueprint_sha256=data[
                "whole_perfume_blueprint_sha256"
            ],
            immediate_parent_formula_sha256=data[
                "immediate_parent_formula_sha256"
            ],
            required_checks=tuple(
                ExecutionCheck(item)
                for item in _sequence(data["required_checks"], "required_checks")
            ),
            outputs=tuple(
                ExecutionOutput(item)
                for item in _sequence(data["outputs"], "outputs")
            ),
            verification_scope=VerificationScope(data["verification_scope"]),
            research_scope=ResearchScope(data["research_scope"]),
            delegation_scope=DelegationScope(data["delegation_scope"]),
            authority_ceiling=AuthorityCeiling(data["authority_ceiling"]),
            formula_execution_authorized=_bool(
                data["formula_execution_authorized"],
                "formula_execution_authorized",
            ),
            repository_write_authorized=_bool(
                data["repository_write_authorized"],
                "repository_write_authorized",
            ),
            physical_execution_authorized=_bool(
                data["physical_execution_authorized"],
                "physical_execution_authorized",
            ),
            purchase_authority=_bool(
                data["purchase_authority"], "purchase_authority"
            ),
            observed_smell=_bool(data["observed_smell"], "observed_smell"),
            sensory_authority=_bool(
                data["sensory_authority"], "sensory_authority"
            ),
            liking_authority=_bool(
                data["liking_authority"], "liking_authority"
            ),
            similarity_authority=_bool(
                data["similarity_authority"], "similarity_authority"
            ),
            performance_authority=_bool(
                data["performance_authority"], "performance_authority"
            ),
            safety_authority=_bool(
                data["safety_authority"], "safety_authority"
            ),
            stability_authority=_bool(
                data["stability_authority"], "stability_authority"
            ),
            release_authorized=_bool(
                data["release_authorized"], "release_authorized"
            ),
        )


def plan_formulation_execution(
    whole_perfume_blueprint: WholePerfumeBlueprint,
    *,
    mode: FormulationExecutionMode,
    request_kind: FormulationRequestKind = FormulationRequestKind.NEW_DESIGN,
    immediate_parent_formula_sha256: str | None = None,
) -> FormulationExecutionPlan:
    """Derive one complete mode policy from an exact whole-perfume blueprint."""

    if not isinstance(whole_perfume_blueprint, WholePerfumeBlueprint):
        raise TypeError("whole_perfume_blueprint must be a WholePerfumeBlueprint")
    normalized_mode = FormulationExecutionMode(mode)
    normalized_kind = FormulationRequestKind(request_kind)
    parent_hash = _optional_digest(
        immediate_parent_formula_sha256,
        "immediate_parent_formula_sha256",
    )
    policy = _MODE_POLICIES[normalized_mode]
    authority = whole_perfume_blueprint.authority_ceiling
    plan_id = _execution_plan_id(
        mode=normalized_mode,
        request_kind=normalized_kind,
        whole_perfume_blueprint_sha256=whole_perfume_blueprint.content_sha256,
        immediate_parent_formula_sha256=parent_hash,
        policy=policy,
        authority_ceiling=authority,
    )
    return FormulationExecutionPlan(
        plan_id=plan_id,
        mode=normalized_mode,
        request_kind=normalized_kind,
        operating_mode=policy.operating_mode,
        mode_actions=policy.mode_actions,
        whole_perfume_blueprint=whole_perfume_blueprint,
        whole_perfume_blueprint_sha256=whole_perfume_blueprint.content_sha256,
        immediate_parent_formula_sha256=parent_hash,
        required_checks=policy.checks,
        outputs=policy.outputs,
        verification_scope=policy.verification_scope,
        research_scope=policy.research_scope,
        delegation_scope=policy.delegation_scope,
        authority_ceiling=authority,
    )


__all__ = [
    "DelegationScope",
    "ExecutionCheck",
    "ExecutionOutput",
    "FormulationExecutionMode",
    "FormulationExecutionPlan",
    "FormulationRequestKind",
    "ResearchScope",
    "VerificationScope",
    "plan_formulation_execution",
]
