from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError

import pytest

from engine.authority_gates import ModeAction, OperatingMode, evaluate_mode_action
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    EvidenceClass,
    ProvenanceRef,
)
from engine.formulation_intelligence.execution_profile import (
    DelegationScope,
    ExecutionCheck,
    ExecutionOutput,
    FormulationExecutionMode,
    FormulationExecutionPlan,
    FormulationRequestKind,
    ResearchScope,
    VerificationScope,
    plan_formulation_execution,
)
from engine.formulation_intelligence.inventory_projection import (
    AliquotState,
    ExactStockRef,
    IdealMaterialSelection,
    IdealProposal,
    StockAvailability,
    project_ideal_to_current_build,
)
from engine.formulation_intelligence.target_compiler import (
    AbstractionLevel,
    TargetAcceptance,
    TargetAcceptanceState,
    TargetBranch,
    TargetBrief,
    TargetMode,
    TargetRequestSource,
    TargetSourceSpan,
    compile_target_intent,
)
from engine.formulation_intelligence.whole_perfume_assembler import (
    assemble_whole_perfume_blueprint,
)


def _provenance() -> ProvenanceRef:
    return ProvenanceRef(
        provenance_id="execution-profile-test-source",
        source_ref="exact execution-profile test declaration",
        evidence_class=EvidenceClass.USER_REPORT,
        independence_key="execution-profile-test-source",
        source_sha256="1" * 64,
    )


def _blueprint():
    raw = "Build a transparent magnolia subject with a mineral drydown."
    branch = TargetBranch(
        branch_id="transparent-magnolia-branch",
        interpretation="transparent magnolia with a mineral drydown",
        claim_keys=("target_identity", "expression"),
        evidence_ids=(),
    )
    brief = TargetBrief(
        request_id="execution profile magnolia",
        mode=TargetMode.CONCEPT_ONLY,
        subject="Magnolia de Verre",
        named_references=(),
        family_neighborhoods=("transparent floral",),
        abstraction_level=AbstractionLevel.RECOGNIZABLE_ABSTRACTION,
        expression_terms=("mineral drydown", "transparent magnolia"),
        exclusions=("generic floral cloud",),
        protected_recognizers=("magnolia petal subject",),
        forbidden_drift=("anonymous woody amber",),
        transformations=(),
        temporal_requests=("opening", "heart", "drydown"),
        matrix_context="ethanol fragrance matrix; concentration unresolved",
        criterion_vocabulary=("recognizer integrity", "transition continuity"),
        reference_evidence=(),
        provenance_refs=(_provenance(),),
        request_source=TargetRequestSource(
            raw_request=raw,
            source_ref="codex://execution-profile-test/target",
            source_sha256="2" * 64,
            span=TargetSourceSpan(start_char=0, end_char=len(raw)),
            origin="direct test request",
        ),
        branches=(branch,),
        conflicts=(),
        unknowns=(),
        acceptance=TargetAcceptance(
            acceptance_id="accepted-transparent-magnolia",
            state=TargetAcceptanceState.ACCEPTED,
            accepted_branch_ids=(branch.branch_id,),
            decision_basis="exact branch accepted for structural design",
            provenance_refs=(_provenance(),),
        ),
    )
    target = compile_target_intent(brief)
    ideal = IdealProposal(
        proposal_id="ideal:execution-profile-magnolia:v1",
        target_intent=target,
        selections=(
            IdealMaterialSelection(
                selection_id="selection:magnolia",
                material_name="Magnolia EO",
                target_function="recognizable magnolia petal subject",
            ),
        ),
        design_notes=("inventory cannot rewrite the ideal",),
    )
    stock = ExactStockRef(
        exact_stock_ref="inventory:test:magnolia-eo:as-supplied",
        material_name="Magnolia EO",
        availability=StockAvailability.OWNED,
        fraction=1.0,
        fraction_basis="neat_as_supplied",
        carrier="none",
        aliquot_state=AliquotState.READY,
        authority_source="exact execution-profile test stock declaration",
        exact_identity=True,
        quantitative_authority=True,
        composition_complete=True,
        authority_notes=("lot chemistry remains unresolved",),
    )
    projection = project_ideal_to_current_build(
        ideal,
        (stock,),
        inventory_content_sha256="a" * 64,
        stock_authority_overlay_sha256="b" * 64,
        stock_authority_snapshot_id="execution-profile-stock-v1",
    )
    return assemble_whole_perfume_blueprint(ideal, projection, (), version=1)


def _authority_flags(plan: FormulationExecutionPlan) -> tuple[bool, ...]:
    return (
        plan.formula_execution_authorized,
        plan.repository_write_authorized,
        plan.physical_execution_authorized,
        plan.purchase_authority,
        plan.observed_smell,
        plan.sensory_authority,
        plan.liking_authority,
        plan.similarity_authority,
        plan.performance_authority,
        plan.safety_authority,
        plan.stability_authority,
        plan.release_authorized,
    )


def test_fast_draft_is_hash_bound_local_and_non_executable() -> None:
    blueprint = _blueprint()
    plan = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.FAST_DRAFT,
    )

    assert plan.whole_perfume_blueprint == blueprint
    assert plan.whole_perfume_blueprint_sha256 == blueprint.content_sha256
    assert plan.target_intent_sha256 == blueprint.ideal_proposal.target_intent.content_sha256
    assert plan.ideal_proposal_sha256 == blueprint.ideal_proposal.content_sha256
    assert plan.inventory_projection_sha256 == blueprint.inventory_projection.content_sha256
    assert plan.inventory_content_sha256 == "a" * 64
    assert plan.stock_authority_overlay_sha256 == "b" * 64
    assert plan.stock_authority_records_sha256 == (
        blueprint.inventory_projection.stock_authority_records_sha256
    )
    assert plan.verification_scope is VerificationScope.INLINE_ARITHMETIC_AND_SCHEMA
    assert plan.research_scope is ResearchScope.LOCAL_ONLY
    assert plan.delegation_scope is DelegationScope.NONE
    assert plan.operating_mode is OperatingMode.CREATIVE_FORMULATION
    assert ModeAction.CANDIDATE_GENERATION in plan.mode_actions
    assert all(
        evaluate_mode_action(plan.operating_mode, action).allowed
        for action in plan.mode_actions
    )
    assert ExecutionCheck.ACTIVE_DOSE_PPM_ODT_OAV_SCREEN in plan.required_checks
    assert ExecutionCheck.COMPOSITE_NATURAL_OAV_OR_UNKNOWN in plan.required_checks
    assert ExecutionCheck.FULL_PROJECT_VERIFICATION not in plan.required_checks
    assert ExecutionOutput.ABSTRACT_TEMPORAL_SEQUENCE in plan.outputs
    assert ExecutionOutput.HUMAN_REVIEW_COMPOUNDING_CARD_DRAFT not in plan.outputs
    assert plan.authority_ceiling is blueprint.authority_ceiling
    assert plan.authority_ceiling is AuthorityCeiling.WITHHELD
    assert not any(_authority_flags(plan))

    restored = FormulationExecutionPlan.from_dict(plan.as_dict())
    assert restored == plan
    assert restored.content_sha256 == plan.content_sha256
    with pytest.raises(FrozenInstanceError):
        plan.release_authorized = True  # type: ignore[misc]


def test_modes_escalate_evidence_work_without_escalating_authority() -> None:
    blueprint = _blueprint()
    fast = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.FAST_DRAFT,
    )
    card = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.COMPOUNDING_CARD,
    )
    release = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.RELEASE_REVIEW,
    )

    assert set(fast.required_checks) < set(card.required_checks) < set(
        release.required_checks
    )
    assert set(fast.outputs) < set(card.outputs) < set(release.outputs)
    assert card.verification_scope is VerificationScope.FOCUSED_FORMULA_GATES
    assert card.operating_mode is OperatingMode.INVENTORY_MAPPING
    assert ModeAction.MEASURABLE_BUILD_DRAFT in card.mode_actions
    assert release.verification_scope is VerificationScope.FULL_RELEASE
    assert release.operating_mode is OperatingMode.RELEASE_REVIEW
    assert ModeAction.READ_ONLY_REVIEW in release.mode_actions
    assert ModeAction.ATOMIC_COMMIT not in release.mode_actions
    assert release.research_scope is ResearchScope.PRIMARY_OR_OFFICIAL_IF_GAP
    assert release.delegation_scope is DelegationScope.OPENAI_NATIVE_READ_ONLY
    assert ExecutionCheck.PREMIX_ACTIVE_DOSE_GATE in card.required_checks
    assert ExecutionCheck.FROZEN_SOL_XHIGH_ADMISSION in release.required_checks
    assert ExecutionCheck.HUMAN_RELEASE_DECISION in release.required_checks
    assert {item.authority_ceiling for item in (fast, card, release)} == {
        blueprint.authority_ceiling
    }
    assert all(not any(_authority_flags(item)) for item in (fast, card, release))


def test_revision_requires_exact_immediate_parent_and_new_design_rejects_one() -> None:
    blueprint = _blueprint()
    with pytest.raises(ValueError, match="immediate parent"):
        plan_formulation_execution(
            blueprint,
            mode=FormulationExecutionMode.COMPOUNDING_CARD,
            request_kind=FormulationRequestKind.REVISION,
        )

    revision = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.COMPOUNDING_CARD,
        request_kind=FormulationRequestKind.REVISION,
        immediate_parent_formula_sha256="c" * 64,
    )
    assert revision.immediate_parent_formula_sha256 == "c" * 64
    assert ExecutionCheck.IMMEDIATE_PARENT_EQUIVALENCE_IF_REVISION in (
        revision.required_checks
    )

    with pytest.raises(ValueError, match="new-design"):
        plan_formulation_execution(
            blueprint,
            mode=FormulationExecutionMode.FAST_DRAFT,
            immediate_parent_formula_sha256="d" * 64,
        )


def test_caller_cannot_shorten_policy_forge_hash_or_promote_authority() -> None:
    plan = plan_formulation_execution(
        _blueprint(),
        mode=FormulationExecutionMode.FAST_DRAFT,
    )

    shortened = deepcopy(plan.as_dict())
    shortened["required_checks"] = shortened["required_checks"][:-1]
    with pytest.raises(ValueError, match="complete derived mode policy"):
        FormulationExecutionPlan.from_dict(shortened)

    forged_hash = deepcopy(plan.as_dict())
    forged_hash["whole_perfume_blueprint_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="complete blueprint"):
        FormulationExecutionPlan.from_dict(forged_hash)

    promoted = deepcopy(plan.as_dict())
    promoted["physical_execution_authorized"] = True
    with pytest.raises(ValueError, match="cannot be promoted"):
        FormulationExecutionPlan.from_dict(promoted)

    extra = deepcopy(plan.as_dict())
    extra["web_search_allowed"] = True
    with pytest.raises(ValueError, match="not closed"):
        FormulationExecutionPlan.from_dict(extra)


def test_plan_identity_changes_with_mode_parent_or_bound_blueprint() -> None:
    blueprint = _blueprint()
    fast = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.FAST_DRAFT,
    )
    card = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.COMPOUNDING_CARD,
    )
    revision = plan_formulation_execution(
        blueprint,
        mode=FormulationExecutionMode.COMPOUNDING_CARD,
        request_kind=FormulationRequestKind.REVISION,
        immediate_parent_formula_sha256="e" * 64,
    )

    assert len({fast.plan_id, card.plan_id, revision.plan_id}) == 3

    fabricated = deepcopy(fast.as_dict())
    fabricated["plan_id"] = card.plan_id
    with pytest.raises(ValueError, match="complete execution-plan content"):
        FormulationExecutionPlan.from_dict(fabricated)
