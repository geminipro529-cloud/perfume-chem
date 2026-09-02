from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError, dataclass, replace
from hashlib import sha256
from pathlib import Path

import pytest

from engine.formulation_intelligence.benchmark import (
    PUBLIC_AUTHORITY_EXCLUSIONS,
    AnonymizedArm,
    ArmPromptReceipt,
    BenchmarkCase,
    BenchmarkRunReceipt,
    BlindLabelAssignment,
    BlindLabelMapping,
    CorpusPartition,
    GateDomain,
    HardGateRequirement,
    InvariantRequirements,
    JudgeReceipt,
    NonCompensatoryGateContract,
    RecursiveClosureReceiptRef,
    RunStatus,
    SealedPublicCorpus,
    load_sealed_public_corpus,
)
from engine.formulation_intelligence.benchmark_result import (
    ArmRoleAssignment,
    ArmRoleInstruction,
    ArmRoleMapping,
    BenchmarkArmRole,
    BenchmarkEvaluationStatus,
    BenchmarkExecutionMatrix,
    BenchmarkVerifierIdentity,
    BlindedPairAssignment,
    CampaignArtifactAudience,
    CampaignArtifactBinding,
    CampaignArtifactKind,
    EvaluationValidity,
    ExactRatio,
    ExecutionCellObservation,
    ExecutionCellSpec,
    ExecutionOrder,
    FrozenBenchmarkDefinition,
    FrozenBenchmarkObservationPacket,
    FrozenBenchmarkVerificationBundle,
    FrozenCampaignManifest,
    HardGateObservation,
    ObservationDisposition,
    PairJudgeObservation,
    PairOutcome,
    PartitionScope,
    SuperiorityDecisionContract,
    blinded_pair_assignment_commitment_sha256,
    blinded_pair_schedule_sha256,
    build_minimum_seed_order_execution_matrix,
    evaluate_frozen_benchmark_result,
    execution_cell_config_sha256,
    execution_cell_id,
    pair_schedule_commitment_sha256,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _record_list_hash(values: tuple[object, ...]) -> str:
    payload = [item.as_dict() for item in values]
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _closure() -> RecursiveClosureReceiptRef:
    return RecursiveClosureReceiptRef(
        receipt_id="closure:synthetic:v1",
        receipt_sha256=_hash("closure-receipt"),
        closure_manifest_sha256=_hash("closure-manifest"),
    )


def _campaign_manifest() -> FrozenCampaignManifest:
    corpus = load_sealed_public_corpus(
        FIXTURES / "formulation_intelligence_benchmark_v1.json",
        FIXTURES / "formulation_intelligence_benchmark_v1.sha256",
    )
    private_audiences = {
        CampaignArtifactKind.PRIVATE_ANSWER_KEY_SET: (
            CampaignArtifactAudience.SCORER_ONLY
        ),
        CampaignArtifactKind.BLIND_LABEL_MAP: (
            CampaignArtifactAudience.UNBLINDER_ONLY
        ),
        CampaignArtifactKind.ARM_ROLE_MAP: (
            CampaignArtifactAudience.UNBLINDER_ONLY
        ),
        CampaignArtifactKind.SCORER_ROSTER: (
            CampaignArtifactAudience.VERIFIER_ONLY
        ),
    }
    artifacts = tuple(
        CampaignArtifactBinding(
            artifact_id=f"artifact:{kind.value}",
            artifact_kind=kind,
            relative_path=f"campaign/{kind.value}.json",
            byte_length=index + 1,
            artifact_sha256=_hash(f"campaign artifact {kind.value}"),
            audience=private_audiences.get(
                kind, CampaignArtifactAudience.VERIFIER_ONLY
            ),
            dependency_ids=(),
        )
        for index, kind in enumerate(CampaignArtifactKind)
    )
    return FrozenCampaignManifest(
        campaign_id="wp13.production.campaign.v1",
        benchmark_id="wp13.production.v1",
        benchmark_definition_sha256=_hash("production definition"),
        source_identity_sha256=_hash("production source identity"),
        workspace_state_sha256=_hash("production workspace state"),
        generation_plan_sha256=_hash("production generation plan"),
        artifacts=artifacts,
        case_ids=tuple(case.case_id for case in corpus.cases),
        arm_ids=tuple(arm.arm_id for arm in corpus.anonymized_arms),
        independent_generation_count_per_case_arm=2,
        unique_generation_group_count=220,
        presentation_cell_count=440,
        model_provider_id="openai",
        model_snapshot_id="gpt-5.6-sol",
        reasoning_level="xhigh",
        authority_exclusions=PUBLIC_AUTHORITY_EXCLUSIONS,
        sealed=True,
        benchmark_execution_authorized=False,
        empirical_authority=False,
        admission_authorized=False,
    )


def _case(
    case_id: str, *, partition: CorpusPartition, safe_no_change: bool
) -> BenchmarkCase:
    prompt = f"Synthetic frozen benchmark case {case_id}."
    tags = ["synthetic"]
    if safe_no_change:
        tags.append("safe_no_change")
    return BenchmarkCase(
        case_id=case_id,
        partition=partition,
        family_key=f"family.{case_id}",
        prompt_text=prompt,
        prompt_sha256=_hash(prompt),
        challenge_tags=tuple(tags),
        invariants=InvariantRequirements(
            required_evidence_keys=("target.identity",),
            authority_keys=("authority.ceiling",),
            inventory_keys=("inventory.stock",),
            protocol_keys=("protocol.blind",),
        ),
    )


def _synthetic_corpus() -> SealedPublicCorpus:
    cases = (
        _case(
            "case.cross.01",
            partition=CorpusPartition.CROSS_FAMILY,
            safe_no_change=False,
        ),
        _case(
            "case.held.02",
            partition=CorpusPartition.HELD_OUT,
            safe_no_change=True,
        ),
    )
    arms = tuple(AnonymizedArm(arm_id=f"arm-{index:08x}") for index in range(1, 6))
    return SealedPublicCorpus(
        corpus_id="synthetic.wp13.v1",
        sealed=True,
        cases=cases,
        anonymized_arms=arms,
        authority_exclusions=PUBLIC_AUTHORITY_EXCLUSIONS,
        benchmark_execution_authorized=False,
        empirical_authority=False,
    )


def _role_mapping(corpus: SealedPublicCorpus) -> ArmRoleMapping:
    roles = tuple(BenchmarkArmRole)
    assignments = tuple(
        ArmRoleAssignment(arm_id=arm.arm_id, role=role)
        for arm, role in zip(corpus.anonymized_arms, roles, strict=True)
    )
    return ArmRoleMapping(
        mapping_id="private.roles.synthetic.v1",
        assignments=assignments,
        mapping_sha256=_record_list_hash(assignments),
    )


def _blind_mapping(corpus: SealedPublicCorpus) -> BlindLabelMapping:
    assignments = tuple(
        BlindLabelAssignment(blind_label=f"label-{index:02d}", arm_id=arm.arm_id)
        for index, arm in enumerate(corpus.anonymized_arms, start=1)
    )
    return BlindLabelMapping(
        mapping_id="private.blind.synthetic.v1",
        assignments=assignments,
        mapping_sha256=_record_list_hash(assignments),
    )


def _gate_contract() -> NonCompensatoryGateContract:
    return NonCompensatoryGateContract(
        contract_id="synthetic.noncompensatory.v1",
        hard_gates=tuple(
            HardGateRequirement(
                gate_key=f"critical.{domain.value}",
                domain=domain,
                maximum_critical_errors=0,
                compensable_by_prose_quality=False,
            )
            for domain in GateDomain
        ),
        required_superiority_endpoint_keys=("target.fidelity",),
        exact_keyed_correctness_compensable=False,
        safe_no_change_required=True,
        held_out_family_required=True,
        seed_order_stability_required=True,
        admission_authorized=False,
    )


def _superiority_contract() -> SuperiorityDecisionContract:
    return SuperiorityDecisionContract(
        contract_id="synthetic.superiority.v1",
        benchmark_model_id="gpt-5.6-sol",
        frozen_reasoning_level="xhigh",
        role_instructions=tuple(
            ArmRoleInstruction(
                role=role,
                instruction_sha256=_hash(f"instruction:{role.value}"),
            )
            for role in BenchmarkArmRole
        ),
        required_comparator_roles=(
            BenchmarkArmRole.PLAIN_SOL_XHIGH,
            BenchmarkArmRole.LENGTH_MATCHED_PLACEBO,
        ),
        required_endpoint_keys=("target.fidelity",),
        minimum_independent_scorers=2,
        minimum_evaluable_pairs_per_endpoint=1,
        minimum_win_fraction=ExactRatio(numerator=3, denominator=5),
        minimum_net_wins=1,
        required_pair_orientations=(ExecutionOrder.AB, ExecutionOrder.BA),
        ties_retained=True,
        invalid_or_not_evaluable_blocks=True,
        safe_no_change_required=True,
        held_out_required=True,
        seed_order_stability_required=True,
        admission_authorized=False,
    )


def _matrix(
    corpus: SealedPublicCorpus, *, seeds: tuple[int, ...] = (0, 1)
) -> BenchmarkExecutionMatrix:
    cells: list[ExecutionCellSpec] = []
    base_config_sha256 = _hash("synthetic frozen execution configuration")
    for case in corpus.cases:
        for arm in corpus.anonymized_arms:
            for seed in seeds:
                for order in ExecutionOrder:
                    cell_id = execution_cell_id(
                        case_id=case.case_id,
                        arm_id=arm.arm_id,
                        seed=seed,
                        order=order,
                        repeat_index=0,
                    )
                    cells.append(
                        ExecutionCellSpec(
                            cell_id=cell_id,
                            case_id=case.case_id,
                            arm_id=arm.arm_id,
                            seed=seed,
                            order=order,
                            repeat_index=0,
                            execution_config_sha256=execution_cell_config_sha256(
                                frozen_execution_config_sha256=base_config_sha256,
                                case_id=case.case_id,
                                arm_id=arm.arm_id,
                                seed=seed,
                                repeat_index=0,
                            ),
                        )
                    )
    return BenchmarkExecutionMatrix(
        matrix_id="synthetic.matrix.v1",
        corpus_sha256=corpus.content_sha256,
        frozen_execution_config_sha256=base_config_sha256,
        case_ids=tuple(item.case_id for item in corpus.cases),
        arm_ids=tuple(item.arm_id for item in corpus.anonymized_arms),
        seeds=seeds,
        orders=(ExecutionOrder.AB, ExecutionOrder.BA),
        repeat_count=1,
        cells=tuple(cells),
        sealed=True,
        benchmark_execution_authorized=False,
    )


@dataclass(frozen=True)
class _Harness:
    corpus: SealedPublicCorpus
    definition: FrozenBenchmarkDefinition
    matrix: BenchmarkExecutionMatrix
    gate_contract: NonCompensatoryGateContract
    superiority_contract: SuperiorityDecisionContract
    blind_mapping: BlindLabelMapping
    role_mapping: ArmRoleMapping
    prompt_receipts: tuple[ArmPromptReceipt, ...]
    run_receipts: tuple[BenchmarkRunReceipt, ...]
    judge_receipts: tuple[JudgeReceipt, ...]
    packet: FrozenBenchmarkObservationPacket
    verifier_identity: BenchmarkVerifierIdentity

    def evaluate(self):
        return evaluate_frozen_benchmark_result(
            corpus=self.corpus,
            definition=self.definition,
            execution_matrix=self.matrix,
            gate_contract=self.gate_contract,
            superiority_contract=self.superiority_contract,
            scorer_mapping=self.blind_mapping,
            arm_role_mapping=self.role_mapping,
            prompt_receipts=self.prompt_receipts,
            run_receipts=self.run_receipts,
            judge_receipts=self.judge_receipts,
            observation_packet=self.packet,
            verifier_identity=self.verifier_identity,
        )


def _harness(
    *,
    seeds: tuple[int, ...] = (0, 1),
    corpus: SealedPublicCorpus | None = None,
) -> _Harness:
    corpus = corpus or _synthetic_corpus()
    role_mapping = _role_mapping(corpus)
    blind_mapping = _blind_mapping(corpus)
    gate_contract = _gate_contract()
    superiority_contract = _superiority_contract()
    matrix = _matrix(corpus, seeds=seeds)
    closure = _closure()
    verifier_identity = BenchmarkVerifierIdentity(
        verifier_id="local.benchmark.result.verifier",
        verifier_version="v1",
        verifier_implementation_sha256=_hash("benchmark-result-implementation"),
        independence_key=_hash("independent-local-verifier"),
        deterministic_local_verifier=True,
        admission_authorized=False,
    )
    instruction_by_role = {
        item.role: item.instruction_sha256
        for item in superiority_contract.role_instructions
    }
    role_by_arm = {item.arm_id: item.role for item in role_mapping.assignments}
    label_by_arm = {item.arm_id: item.blind_label for item in blind_mapping.assignments}

    prompt_receipts = tuple(
        ArmPromptReceipt(
            receipt_id=f"prompt:{case.case_id}:{arm.arm_id}",
            corpus_sha256=corpus.content_sha256,
            case_id=case.case_id,
            arm_id=arm.arm_id,
            case_prompt_sha256=case.prompt_sha256,
            arm_instruction_sha256=instruction_by_role[role_by_arm[arm.arm_id]],
            rendered_prompt_sha256=_hash(f"rendered:{case.case_id}:{arm.arm_id}"),
            recursive_closure=closure,
        )
        for case in corpus.cases
        for arm in corpus.anonymized_arms
    )
    prompt_by_case_arm = {
        (item.case_id, item.arm_id): item for item in prompt_receipts
    }
    run_receipts: list[BenchmarkRunReceipt] = []
    run_by_generation: dict[
        tuple[str, str, int, int], BenchmarkRunReceipt
    ] = {}
    execution_observations: list[ExecutionCellObservation] = []
    for index, cell in enumerate(matrix.cells):
        prompt = prompt_by_case_arm[(cell.case_id, cell.arm_id)]
        generation_key = (
            cell.case_id,
            cell.arm_id,
            cell.seed,
            cell.repeat_index,
        )
        run = run_by_generation.get(generation_key)
        if run is None:
            run_index = len(run_by_generation)
            run = BenchmarkRunReceipt(
                run_id=f"run:{run_index:04d}",
                arm_prompt_receipt_sha256=prompt.content_sha256,
                execution_config_sha256=cell.execution_config_sha256,
                provider_id="openai",
                model_id="gpt-5.6-sol",
                reasoning_level="xhigh",
                status=RunStatus.COMPLETED,
                output_sha256=_hash(f"output:{generation_key!r}"),
                started_at_utc="2026-09-02T01:00:00Z",
                finished_at_utc="2026-09-02T01:00:01Z",
                input_tokens=10,
                output_tokens=20,
                recursive_closure=closure,
            )
            run_by_generation[generation_key] = run
            run_receipts.append(run)
        else:
            assert run.execution_config_sha256 == cell.execution_config_sha256
        execution_observations.append(
            ExecutionCellObservation(
                observation_id=f"exec:{index:04d}",
                cell_id=cell.cell_id,
                prompt_receipt_sha256=prompt.content_sha256,
                run_receipt_sha256=run.content_sha256,
                validity=EvaluationValidity.VALID,
                reason_codes=(),
                used_for_admission=True,
                disposition=ObservationDisposition.CURRENT,
                supersedes_observation_sha256=None,
            )
        )

    arm_by_role = {item.role: item.arm_id for item in role_mapping.assignments}
    cell_by_key = {
        (item.case_id, item.arm_id, item.seed, item.order): item
        for item in matrix.cells
    }
    rubric_sha256 = _hash("synthetic-rubric")
    pair_assignments: list[BlindedPairAssignment] = []
    pair_observations: list[PairJudgeObservation] = []
    judge_receipts: list[JudgeReceipt] = []
    pair_index = 0
    for case in corpus.cases:
        for comparator in superiority_contract.required_comparator_roles:
            for seed in matrix.seeds:
                for orientation in ExecutionOrder:
                    integrated_arm = arm_by_role[
                        BenchmarkArmRole.INTEGRATED_CANDIDATE
                    ]
                    comparator_arm = arm_by_role[comparator]
                    left_arm, right_arm = (
                        (integrated_arm, comparator_arm)
                        if orientation is ExecutionOrder.AB
                        else (comparator_arm, integrated_arm)
                    )
                    pair_id = f"pair:{pair_index:04d}"
                    bundle_sha256 = _hash(f"bundle:{pair_id}")
                    swap_group_id = (
                        f"swap:{case.case_id}:{comparator.value}:seed-{seed}"
                    )
                    left_cell_id = cell_by_key[
                        (case.case_id, left_arm, seed, orientation)
                    ].cell_id
                    right_cell_id = cell_by_key[
                        (case.case_id, right_arm, seed, orientation)
                    ].cell_id
                    schedule_sha256 = blinded_pair_schedule_sha256(
                        pair_id=pair_id,
                        swap_group_id=swap_group_id,
                        case_id=case.case_id,
                        endpoint_key="target.fidelity",
                        seed=seed,
                        repeat_index=0,
                        planned_orientation=orientation,
                        left_cell_id=left_cell_id,
                        right_cell_id=right_cell_id,
                        left_blind_label=label_by_arm[left_arm],
                        right_blind_label=label_by_arm[right_arm],
                    )
                    assignment = BlindedPairAssignment(
                        pair_id=pair_id,
                        swap_group_id=swap_group_id,
                        case_id=case.case_id,
                        endpoint_key="target.fidelity",
                        seed=seed,
                        repeat_index=0,
                        planned_orientation=orientation,
                        realized_orientation=orientation,
                        left_cell_id=left_cell_id,
                        right_cell_id=right_cell_id,
                        left_blind_label=label_by_arm[left_arm],
                        right_blind_label=label_by_arm[right_arm],
                        blinded_bundle_sha256=bundle_sha256,
                        schedule_sha256=schedule_sha256,
                        assignment_commitment_sha256=(
                            blinded_pair_assignment_commitment_sha256(
                                pair_id=pair_id,
                                schedule_sha256=schedule_sha256,
                            )
                        ),
                        validity=EvaluationValidity.VALID,
                        reason_codes=(),
                    )
                    pair_assignments.append(assignment)
                    for scorer_index in range(2):
                        artifact_sha256 = _hash(
                            f"score:{pair_id}:{scorer_index}"
                        )
                        judge = JudgeReceipt(
                            judge_receipt_id=(
                                f"judge:{pair_index:04d}:{scorer_index}"
                            ),
                            blinded_bundle_sha256=bundle_sha256,
                            rubric_sha256=rubric_sha256,
                            scorer_provider_id="openai",
                            scorer_identity=f"independent-judge-{scorer_index}",
                            scorer_config_sha256=_hash(
                                f"judge-config:{scorer_index}"
                            ),
                            score_artifact_sha256=artifact_sha256,
                            observed_at_utc="2026-09-02T02:00:00Z",
                            blind_mapping_embedded=False,
                            recursive_closure=closure,
                        )
                        judge_receipts.append(judge)
                        left_score, right_score, outcome = (
                            (9, 1, PairOutcome.LEFT)
                            if orientation is ExecutionOrder.AB
                            else (1, 9, PairOutcome.RIGHT)
                        )
                        pair_observations.append(
                            PairJudgeObservation(
                                observation_id=(
                                    f"pair-score:{pair_index:04d}:{scorer_index}"
                                ),
                                pair_id=pair_id,
                                endpoint_key="target.fidelity",
                                judge_receipt_sha256=judge.content_sha256,
                                outcome=outcome,
                                left_score=left_score,
                                right_score=right_score,
                                tie_reason=None,
                                reason_codes=(),
                                critical_error_codes=(),
                                evidence_artifact_sha256=artifact_sha256,
                                validity=EvaluationValidity.VALID,
                                used_for_admission=True,
                                disposition=ObservationDisposition.CURRENT,
                                supersedes_observation_sha256=None,
                            )
                        )
                    pair_index += 1

    gate_judges: list[JudgeReceipt] = []
    for scorer_index in range(2):
        artifact_sha256 = _hash(f"gate-score:{scorer_index}")
        gate_judges.append(
            JudgeReceipt(
                judge_receipt_id=f"judge:gates:{scorer_index}",
                blinded_bundle_sha256=_hash(f"gate-bundle:{scorer_index}"),
                rubric_sha256=rubric_sha256,
                scorer_provider_id="openai",
                scorer_identity=f"independent-judge-{scorer_index}",
                scorer_config_sha256=_hash(f"judge-config:{scorer_index}"),
                score_artifact_sha256=artifact_sha256,
                observed_at_utc="2026-09-02T02:00:00Z",
                blind_mapping_embedded=False,
                recursive_closure=closure,
            )
        )
    judge_receipts.extend(gate_judges)
    hard_gate_observations = tuple(
        HardGateObservation(
            observation_id=f"gate:{cell_index:04d}:{gate_index:02d}:{scorer_index}",
            cell_id=cell.cell_id,
            gate_key=gate.gate_key,
            judge_receipt_sha256=gate_judges[scorer_index].content_sha256,
            critical_error_count=0,
            evidence_artifact_sha256=gate_judges[scorer_index].score_artifact_sha256,
            validity=EvaluationValidity.VALID,
            reason_codes=(),
            used_for_admission=True,
            disposition=ObservationDisposition.CURRENT,
            supersedes_observation_sha256=None,
        )
        for cell_index, cell in enumerate(matrix.cells)
        for gate_index, gate in enumerate(gate_contract.hard_gates)
        for scorer_index in range(2)
    )

    definition = FrozenBenchmarkDefinition(
        definition_id="synthetic.definition.v1",
        benchmark_id="synthetic.wp13.v1",
        fixture_bytes_sha256=_hash("synthetic-fixture-bytes"),
        canonical_corpus_sha256=corpus.content_sha256,
        execution_matrix_sha256=matrix.content_sha256,
        gate_contract_sha256=gate_contract.content_sha256,
        superiority_contract_sha256=superiority_contract.content_sha256,
        blind_label_mapping_sha256=blind_mapping.mapping_sha256,
        arm_role_mapping_sha256=role_mapping.mapping_sha256,
        pair_schedule_commitment_sha256=pair_schedule_commitment_sha256(
            pair_assignments
        ),
        rubric_sha256=rubric_sha256,
        scorer_protocol_sha256=_hash("synthetic-scorer-protocol"),
        recursive_closure_required=True,
        benchmark_execution_authorized=False,
        empirical_authority=False,
    )
    packet = FrozenBenchmarkObservationPacket(
        result_id="synthetic.result.v1",
        benchmark_id=definition.benchmark_id,
        benchmark_definition_sha256=definition.content_sha256,
        fixture_bytes_sha256=definition.fixture_bytes_sha256,
        canonical_corpus_sha256=corpus.content_sha256,
        source_identity_sha256=_hash("source-identity"),
        workspace_state_sha256=_hash("workspace-state"),
        admission_challenge_nonce=_hash("synthetic admission challenge"),
        admission_request_scope_sha256=_hash("synthetic admission request scope"),
        producer_independence_key=_hash("benchmark-result-producer"),
        module_manifest_sha256s=(_hash("module-manifest"),),
        covered_module_ids=("module.synthetic",),
        covered_capability_ids=("capability.synthetic",),
        covered_schema_ids=("schema.synthetic",),
        artifact_closure_sha256=_hash("artifact-closure"),
        covered_artifact_ids=("artifact.synthetic",),
        execution_matrix_sha256=matrix.content_sha256,
        gate_contract_sha256=gate_contract.content_sha256,
        superiority_contract_sha256=superiority_contract.content_sha256,
        rubric_sha256=rubric_sha256,
        scorer_protocol_sha256=definition.scorer_protocol_sha256,
        blind_mapping_sha256=blind_mapping.mapping_sha256,
        arm_role_mapping_sha256=role_mapping.mapping_sha256,
        prompt_receipt_sha256s=tuple(item.content_sha256 for item in prompt_receipts),
        run_receipt_sha256s=tuple(item.content_sha256 for item in run_receipts),
        judge_receipt_sha256s=tuple(item.content_sha256 for item in judge_receipts),
        execution_observations=tuple(execution_observations),
        pair_assignments=tuple(pair_assignments),
        pair_observations=tuple(pair_observations),
        hard_gate_observations=hard_gate_observations,
        observed_at_utc="2026-09-02T03:00:00Z",
        recursive_closure=closure,
        authority_exclusions=PUBLIC_AUTHORITY_EXCLUSIONS,
        benchmark_execution_authorized=False,
        runtime_admission_authorized=False,
        empirical_authority=False,
        formula_authority=False,
        physical_execution_authority=False,
        compounding_authority=False,
        sensory_authority=False,
        liking_authority=False,
        safety_authority=False,
        stability_authority=False,
        purchase_authority=False,
        release_authority=False,
    )
    return _Harness(
        corpus=corpus,
        definition=definition,
        matrix=matrix,
        gate_contract=gate_contract,
        superiority_contract=superiority_contract,
        blind_mapping=blind_mapping,
        role_mapping=role_mapping,
        prompt_receipts=prompt_receipts,
        run_receipts=tuple(run_receipts),
        judge_receipts=tuple(judge_receipts),
        packet=packet,
        verifier_identity=verifier_identity,
    )


def test_complete_frozen_result_is_derived_without_granting_authority() -> None:
    harness = _harness()
    evaluation = harness.evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.PASS
    assert evaluation.benchmark_contract_satisfied is True
    assert evaluation.failure_codes == ()
    assert evaluation.hold_codes == ()
    assert all(summary.heterogeneous == 0 for summary in evaluation.comparison_summaries)
    assert all(summary.not_evaluable == 0 for summary in evaluation.comparison_summaries)
    assert {
        item.partition_scope for item in evaluation.comparison_summaries
    } == set(PartitionScope)
    assert all(
        summary.pair_count == 2
        for summary in evaluation.comparison_summaries
        if summary.partition_scope is PartitionScope.ALL
    )
    assert all(
        summary.pair_count == 1
        for summary in evaluation.comparison_summaries
        if summary.partition_scope is PartitionScope.HELD_OUT
    )
    assert evaluation.admission_authorized is False
    assert evaluation.formula_authority is False
    assert evaluation.physical_execution_authority is False
    assert evaluation.sensory_authority is False
    assert evaluation.liking_authority is False
    assert evaluation.safety_authority is False
    assert evaluation.stability_authority is False
    assert evaluation.release_authority is False


def test_result_records_are_closed_frozen_and_roundtrip() -> None:
    harness = _harness()
    packet = harness.packet
    evaluation = harness.evaluate()

    assert FrozenBenchmarkObservationPacket.from_dict(packet.as_dict()) == packet
    assert FrozenBenchmarkDefinition.from_dict(harness.definition.as_dict()) == harness.definition
    assert type(evaluation).from_dict(evaluation.as_dict()) == evaluation
    assert packet.content_sha256 == FrozenBenchmarkObservationPacket.from_dict(
        packet.as_dict()
    ).content_sha256
    with pytest.raises(FrozenInstanceError):
        packet.result_id = "changed"  # type: ignore[misc]
    payload = packet.as_dict()
    payload["extra"] = True
    with pytest.raises(ValueError, match="closed schema"):
        FrozenBenchmarkObservationPacket.from_dict(payload)


def test_complete_verification_bundle_roundtrips_and_recomputes_exactly() -> None:
    harness = _harness()
    bundle = FrozenBenchmarkVerificationBundle(
        corpus=harness.corpus,
        definition=harness.definition,
        execution_matrix=harness.matrix,
        gate_contract=harness.gate_contract,
        superiority_contract=harness.superiority_contract,
        scorer_mapping=harness.blind_mapping,
        arm_role_mapping=harness.role_mapping,
        prompt_receipts=harness.prompt_receipts,
        run_receipts=harness.run_receipts,
        judge_receipts=harness.judge_receipts,
        observation_packet=harness.packet,
        verifier_identity=harness.verifier_identity,
    )

    restored = FrozenBenchmarkVerificationBundle.from_dict(bundle.as_dict())

    assert restored == bundle
    assert restored.content_sha256 == bundle.content_sha256
    assert restored.recompute() == harness.evaluate()


def test_public_fixture_has_22_by_5_base_cells_and_held_out_guards() -> None:
    corpus = load_sealed_public_corpus(
        FIXTURES / "formulation_intelligence_benchmark_v1.json",
        FIXTURES / "formulation_intelligence_benchmark_v1.sha256",
    )

    assert len(corpus.cases) == 22
    assert len(corpus.anonymized_arms) == 5
    assert len({(case.case_id, arm.arm_id) for case in corpus.cases for arm in corpus.anonymized_arms}) == 110
    assert sum(case.partition is CorpusPartition.HELD_OUT for case in corpus.cases) == 3
    assert sum("safe_no_change" in case.challenge_tags for case in corpus.cases) == 2


def test_frozen_campaign_manifest_is_closed_complete_and_hash_stable() -> None:
    manifest = _campaign_manifest()
    restored = FrozenCampaignManifest.from_dict(manifest.as_dict())

    assert restored == manifest
    assert restored.content_sha256 == manifest.content_sha256
    assert manifest.unique_generation_group_count == 220
    assert manifest.presentation_cell_count == 440
    assert {item.artifact_kind for item in manifest.artifacts} == set(
        CampaignArtifactKind
    )


def test_campaign_manifest_rejects_missing_artifacts_and_unsafe_audiences() -> None:
    manifest = _campaign_manifest()
    with pytest.raises(ValueError, match="missing required artifact kinds"):
        replace(manifest, artifacts=manifest.artifacts[:-1])

    answer_key_index = next(
        index
        for index, item in enumerate(manifest.artifacts)
        if item.artifact_kind is CampaignArtifactKind.PRIVATE_ANSWER_KEY_SET
    )
    changed = list(manifest.artifacts)
    changed[answer_key_index] = replace(
        changed[answer_key_index],
        audience=CampaignArtifactAudience.PUBLIC_MODEL_INPUT,
    )
    with pytest.raises(ValueError, match="unsafe artifact audience"):
        replace(manifest, artifacts=tuple(changed))


def test_campaign_manifest_rejects_path_escape_cycles_and_false_counts() -> None:
    manifest = _campaign_manifest()
    with pytest.raises(ValueError, match="campaign artifact root"):
        replace(manifest.artifacts[0], relative_path="../private-answer-key.json")
    with pytest.raises(ValueError, match="at least 220"):
        replace(manifest, unique_generation_group_count=219)
    with pytest.raises(ValueError, match="AB and BA"):
        replace(manifest, presentation_cell_count=220)

    changed = list(manifest.artifacts)
    first = changed[0]
    second = changed[1]
    changed[0] = replace(first, dependency_ids=(second.artifact_id,))
    changed[1] = replace(second, dependency_ids=(first.artifact_id,))
    with pytest.raises(ValueError, match="acyclic"):
        replace(manifest, artifacts=tuple(changed))


def test_minimum_public_seed_order_matrix_is_nonvacuous_and_hash_bound() -> None:
    corpus = load_sealed_public_corpus(
        FIXTURES / "formulation_intelligence_benchmark_v1.json",
        FIXTURES / "formulation_intelligence_benchmark_v1.sha256",
    )
    base_config_sha256 = _hash("openai:gpt-5.6-sol:xhigh:frozen-output-contract")
    matrix = build_minimum_seed_order_execution_matrix(
        corpus=corpus,
        matrix_id="wp13.minimum.seed-order.v1",
        frozen_execution_config_sha256=base_config_sha256,
    )

    assert len(matrix.cells) == 22 * 5 * 2 * 2 * 1
    assert matrix.seeds == (0, 1)
    assert matrix.orders == (ExecutionOrder.AB, ExecutionOrder.BA)
    assert matrix.repeat_count == 1
    assert matrix.benchmark_execution_authorized is False
    assert BenchmarkExecutionMatrix.from_dict(matrix.as_dict()) == matrix
    assert build_minimum_seed_order_execution_matrix(
        corpus=corpus,
        matrix_id="wp13.minimum.seed-order.v1",
        frozen_execution_config_sha256=base_config_sha256,
        seeds=(1, 0),
    ) == matrix
    first = matrix.cells[0]
    assert first.execution_config_sha256 == execution_cell_config_sha256(
        frozen_execution_config_sha256=base_config_sha256,
        case_id=first.case_id,
        arm_id=first.arm_id,
        seed=first.seed,
        repeat_index=first.repeat_index,
    )
    assert len({item.execution_config_sha256 for item in matrix.cells}) == 22 * 5 * 2
    for case in corpus.cases:
        for arm in corpus.anonymized_arms:
            for seed in matrix.seeds:
                configs = {
                    item.execution_config_sha256
                    for item in matrix.cells
                    if (
                        item.case_id == case.case_id
                        and item.arm_id == arm.arm_id
                        and item.seed == seed
                    )
                }
                assert len(configs) == 1

    with pytest.raises(ValueError, match="at least two distinct seeds"):
        build_minimum_seed_order_execution_matrix(
            corpus=corpus,
            matrix_id="wp13.vacuous.seed-order.v1",
            frozen_execution_config_sha256=base_config_sha256,
            seeds=(0,),
        )


def test_execution_matrix_requires_exact_case_arm_seed_order_repeat_product() -> None:
    matrix = _matrix(_synthetic_corpus())
    assert len(matrix.cells) == 2 * 5 * 2 * 2 * 1
    assert len({item.execution_config_sha256 for item in matrix.cells}) == 2 * 5 * 2
    with pytest.raises(ValueError, match="exactly cover"):
        replace(matrix, cells=matrix.cells[:-1])
    with pytest.raises(ValueError, match="AB and BA"):
        replace(matrix, orders=(ExecutionOrder.AB,))
    seed_zero = next(item for item in matrix.cells if item.seed == 0)
    seed_one_index = next(
        index
        for index, item in enumerate(matrix.cells)
        if (
            item.case_id == seed_zero.case_id
            and item.arm_id == seed_zero.arm_id
            and item.seed == 1
            and item.order is seed_zero.order
        )
    )
    aliased = list(matrix.cells)
    aliased[seed_one_index] = replace(
        aliased[seed_one_index],
        execution_config_sha256=seed_zero.execution_config_sha256,
    )
    with pytest.raises(ValueError, match="configuration does not bind"):
        replace(matrix, cells=tuple(aliased))


def test_evaluator_refuses_vacuous_one_seed_stability_claim() -> None:
    evaluation = _harness(seeds=(0,)).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "seed_stability_design_insufficient" in evaluation.hold_codes


def test_ab_ba_reuses_one_run_but_replicates_cannot_share_it() -> None:
    harness = _harness()
    assert len(harness.matrix.cells) == 2 * 5 * 2 * 2
    assert len(harness.run_receipts) == 2 * 5 * 2

    cell_by_id = {item.cell_id: item for item in harness.matrix.cells}
    observations_by_generation: dict[
        tuple[str, str, int, int], list[ExecutionCellObservation]
    ] = {}
    for observation in harness.packet.execution_observations:
        cell = cell_by_id[observation.cell_id]
        observations_by_generation.setdefault(
            (cell.case_id, cell.arm_id, cell.seed, cell.repeat_index), []
        ).append(observation)
    assert all(
        len({item.run_receipt_sha256 for item in observations}) == 1
        for observations in observations_by_generation.values()
    )

    generation_keys = tuple(observations_by_generation)
    seed_zero_key = next(key for key in generation_keys if key[2] == 0)
    seed_one_key = next(
        key
        for key in generation_keys
        if key[:2] == seed_zero_key[:2] and key[2] == 1
    )
    seed_zero_run_sha256 = observations_by_generation[seed_zero_key][
        0
    ].run_receipt_sha256
    seed_one_run_sha256 = observations_by_generation[seed_one_key][
        0
    ].run_receipt_sha256
    changed_observations = tuple(
        replace(item, run_receipt_sha256=seed_zero_run_sha256)
        if cell_by_id[item.cell_id].case_id == seed_one_key[0]
        and cell_by_id[item.cell_id].arm_id == seed_one_key[1]
        and cell_by_id[item.cell_id].seed == seed_one_key[2]
        and cell_by_id[item.cell_id].repeat_index == seed_one_key[3]
        else item
        for item in harness.packet.execution_observations
    )
    retained_runs = tuple(
        item
        for item in harness.run_receipts
        if item.content_sha256 != seed_one_run_sha256
    )
    changed_packet = replace(
        harness.packet,
        run_receipt_sha256s=tuple(item.content_sha256 for item in retained_runs),
        execution_observations=changed_observations,
    )
    changed_harness = replace(
        harness,
        run_receipts=retained_runs,
        packet=changed_packet,
    )

    evaluation = changed_harness.evaluate()
    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "generation_run_reused_across_replicates" in evaluation.hold_codes


def test_ab_ba_cannot_use_separately_generated_outputs() -> None:
    harness = _harness()
    cell_by_id = {item.cell_id: item for item in harness.matrix.cells}
    first_observation = harness.packet.execution_observations[0]
    first_cell = cell_by_id[first_observation.cell_id]
    paired_observations = [
        item
        for item in harness.packet.execution_observations
        if (
            cell_by_id[item.cell_id].case_id == first_cell.case_id
            and cell_by_id[item.cell_id].arm_id == first_cell.arm_id
            and cell_by_id[item.cell_id].seed == first_cell.seed
            and cell_by_id[item.cell_id].repeat_index == first_cell.repeat_index
        )
    ]
    assert len(paired_observations) == 2
    original_run = next(
        item
        for item in harness.run_receipts
        if item.content_sha256 == first_observation.run_receipt_sha256
    )
    alternate_run = replace(
        original_run,
        run_id="run:separate-ab-ba-generation",
        output_sha256=_hash("separately regenerated presentation output"),
    )
    changed_observations = tuple(
        replace(item, run_receipt_sha256=alternate_run.content_sha256)
        if item.cell_id == paired_observations[1].cell_id
        else item
        for item in harness.packet.execution_observations
    )
    runs = (*harness.run_receipts, alternate_run)
    changed_packet = replace(
        harness.packet,
        run_receipt_sha256s=tuple(item.content_sha256 for item in runs),
        execution_observations=changed_observations,
    )
    evaluation = replace(
        harness,
        run_receipts=runs,
        packet=changed_packet,
    ).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "generation_output_not_reused_across_ab_ba" in evaluation.hold_codes


def test_pair_schedule_commitment_is_derived_before_outputs() -> None:
    assignment = _harness().packet.pair_assignments[0]
    expected_schedule = blinded_pair_schedule_sha256(
        pair_id=assignment.pair_id,
        swap_group_id=assignment.swap_group_id,
        case_id=assignment.case_id,
        endpoint_key=assignment.endpoint_key,
        seed=assignment.seed,
        repeat_index=assignment.repeat_index,
        planned_orientation=assignment.planned_orientation,
        left_cell_id=assignment.left_cell_id,
        right_cell_id=assignment.right_cell_id,
        left_blind_label=assignment.left_blind_label,
        right_blind_label=assignment.right_blind_label,
    )
    assert assignment.schedule_sha256 == expected_schedule
    assert assignment.assignment_commitment_sha256 == (
        blinded_pair_assignment_commitment_sha256(
            pair_id=assignment.pair_id,
            schedule_sha256=expected_schedule,
        )
    )

    with pytest.raises(ValueError, match="preregistered pair fields"):
        replace(assignment, case_id="case.changed.after-seeing-output")
    with pytest.raises(ValueError, match="does not bind the pair schedule"):
        replace(
            assignment,
            assignment_commitment_sha256=_hash("post-hoc assignment"),
        )

    changed_output_bundle = replace(
        assignment,
        blinded_bundle_sha256=_hash("different observed output bundle"),
    )
    assert changed_output_bundle.schedule_sha256 == assignment.schedule_sha256


def test_private_role_mapping_is_hash_bound_and_not_in_public_corpus() -> None:
    corpus = _synthetic_corpus()
    mapping = _role_mapping(corpus)
    assert ArmRoleMapping.from_dict(mapping.as_dict()) == mapping
    assert "integrated_candidate" not in json.dumps(corpus.as_dict(), sort_keys=True)
    with pytest.raises(ValueError, match="mapping_sha256"):
        replace(mapping, mapping_sha256=_hash("wrong"))


def test_all_ties_are_retained_but_do_not_demonstrate_superiority() -> None:
    harness = _harness()
    ties = tuple(
        replace(
            item,
            outcome=PairOutcome.TIE,
            left_score=5,
            right_score=5,
            tie_reason="within frozen tie band",
        )
        for item in harness.packet.pair_observations
    )
    packet = replace(harness.packet, pair_observations=ties)
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.FAIL
    assert any(code.startswith("superiority_not_demonstrated") for code in evaluation.failure_codes)
    assert all(summary.ties == summary.pair_count for summary in evaluation.comparison_summaries)
    assert all(summary.integrated_wins == 0 for summary in evaluation.comparison_summaries)
    assert all(summary.comparator_wins == 0 for summary in evaluation.comparison_summaries)


def test_ab_ba_win_to_tie_variation_is_not_stable() -> None:
    harness = _harness()
    target = next(
        item
        for item in harness.packet.pair_assignments
        if item.seed == 0 and item.planned_orientation is ExecutionOrder.AB
    )
    observations = tuple(
        replace(
            item,
            outcome=PairOutcome.TIE,
            left_score=5,
            right_score=5,
            tie_reason="frozen tie band",
        )
        if item.pair_id == target.pair_id
        else item
        for item in harness.packet.pair_observations
    )
    evaluation = replace(
        harness,
        packet=replace(harness.packet, pair_observations=observations),
    ).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "ab_ba_outcome_instability" in evaluation.hold_codes


def test_cross_replicate_win_to_tie_variation_is_not_stable() -> None:
    harness = _harness()
    cell_by_id = {item.cell_id: item for item in harness.matrix.cells}
    role_by_arm = {
        item.arm_id: item.role for item in harness.role_mapping.assignments
    }

    def comparator_role(assignment: BlindedPairAssignment) -> BenchmarkArmRole:
        roles = {
            role_by_arm[cell_by_id[assignment.left_cell_id].arm_id],
            role_by_arm[cell_by_id[assignment.right_cell_id].arm_id],
        }
        roles.remove(BenchmarkArmRole.INTEGRATED_CANDIDATE)
        return next(iter(roles))

    reference = harness.packet.pair_assignments[0]
    reference_comparator = comparator_role(reference)
    target_pair_ids = {
        item.pair_id
        for item in harness.packet.pair_assignments
        if (
            item.case_id == reference.case_id
            and item.endpoint_key == reference.endpoint_key
            and item.seed == 1
            and comparator_role(item) is reference_comparator
        )
    }
    assert len(target_pair_ids) == 2
    observations = tuple(
        replace(
            item,
            outcome=PairOutcome.TIE,
            left_score=5,
            right_score=5,
            tie_reason="frozen tie band",
        )
        if item.pair_id in target_pair_ids
        else item
        for item in harness.packet.pair_observations
    )
    evaluation = replace(
        harness,
        packet=replace(harness.packet, pair_observations=observations),
    ).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "ab_ba_outcome_instability" not in evaluation.hold_codes
    assert "seed_repeat_outcome_instability" in evaluation.hold_codes


def test_conflicting_independent_scorers_are_heterogeneous_not_majority_voted() -> None:
    harness = _harness()
    first_pair = harness.packet.pair_assignments[0]
    observations = list(harness.packet.pair_observations)
    indexes = [index for index, item in enumerate(observations) if item.pair_id == first_pair.pair_id]
    assert len(indexes) == 2
    changed = observations[indexes[1]]
    observations[indexes[1]] = replace(
        changed,
        outcome=(
            PairOutcome.RIGHT
            if changed.outcome is PairOutcome.LEFT
            else PairOutcome.LEFT
        ),
        left_score=changed.right_score,
        right_score=changed.left_score,
    )
    packet = replace(harness.packet, pair_observations=tuple(observations))
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert any(code.startswith("heterogeneous_scorer_evidence") for code in evaluation.hold_codes)
    assert any(summary.heterogeneous == 1 for summary in evaluation.comparison_summaries)


@pytest.mark.parametrize(
    "critical_role",
    (
        BenchmarkArmRole.INTEGRATED_CANDIDATE,
        BenchmarkArmRole.SAFE_COUNTERCASE,
    ),
)
def test_one_candidate_or_safe_countercase_gate_error_is_noncompensatory(
    critical_role: BenchmarkArmRole,
) -> None:
    harness = _harness()
    cell_by_id = {item.cell_id: item for item in harness.matrix.cells}
    role_by_arm = {
        item.arm_id: item.role for item in harness.role_mapping.assignments
    }
    observations = list(harness.packet.hard_gate_observations)
    target_index = next(
        index
        for index, item in enumerate(observations)
        if role_by_arm[cell_by_id[item.cell_id].arm_id] is critical_role
    )
    observations[target_index] = replace(
        observations[target_index], critical_error_count=1
    )
    packet = replace(harness.packet, hard_gate_observations=tuple(observations))
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.FAIL
    gate_key = observations[target_index].gate_key
    assert gate_key in evaluation.hard_gate_violation_keys
    assert f"critical_gate_{gate_key}_failed" in evaluation.failure_codes


@pytest.mark.parametrize(
    "diagnostic_role",
    (
        BenchmarkArmRole.PLAIN_SOL_XHIGH,
        BenchmarkArmRole.LENGTH_MATCHED_PLACEBO,
        BenchmarkArmRole.ABLATION,
    ),
)
def test_comparator_or_ablation_error_does_not_fail_candidate_admission(
    diagnostic_role: BenchmarkArmRole,
) -> None:
    harness = _harness()
    cell_by_id = {item.cell_id: item for item in harness.matrix.cells}
    role_by_arm = {
        item.arm_id: item.role for item in harness.role_mapping.assignments
    }
    observations = list(harness.packet.hard_gate_observations)
    target_index = next(
        index
        for index, item in enumerate(observations)
        if role_by_arm[cell_by_id[item.cell_id].arm_id]
        is diagnostic_role
    )
    observations[target_index] = replace(
        observations[target_index], critical_error_count=1
    )
    packet = replace(
        harness.packet, hard_gate_observations=tuple(observations)
    )
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.PASS
    assert observations[target_index].gate_key not in (
        evaluation.hard_gate_violation_keys
    )


def test_side_unattributed_pair_critical_error_holds_instead_of_failing() -> None:
    harness = _harness()
    observations = list(harness.packet.pair_observations)
    observations[0] = replace(
        observations[0], critical_error_codes=("inventory.unresolved",)
    )
    packet = replace(harness.packet, pair_observations=tuple(observations))
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "pair_observation_critical_error_unattributed" in evaluation.hold_codes
    assert "pair_observation_critical_error" not in evaluation.failure_codes


def test_invalid_current_execution_attempt_is_retained_and_blocks() -> None:
    harness = _harness()
    observations = list(harness.packet.execution_observations)
    original = observations[0]
    observations[0] = replace(
        original,
        validity=EvaluationValidity.INCOMPLETE,
        reason_codes=("run.timeout",),
        used_for_admission=False,
    )
    packet = replace(harness.packet, execution_observations=tuple(observations))
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "execution_cell_requires_one_current_valid_observation" in evaluation.hold_codes
    assert packet.execution_observations[0].validity is EvaluationValidity.INCOMPLETE


def test_order_confounding_is_a_durable_noncompensatory_failure() -> None:
    harness = _harness()
    assignments = list(harness.packet.pair_assignments)
    original = assignments[0]
    assignments[0] = replace(
        original,
        realized_orientation=(
            ExecutionOrder.BA
            if original.planned_orientation is ExecutionOrder.AB
            else ExecutionOrder.AB
        ),
        validity=EvaluationValidity.ORDER_CONFOUNDED,
        reason_codes=("realized.order.mismatch",),
    )
    packet = replace(harness.packet, pair_assignments=tuple(assignments))
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.FAIL
    assert "realized_order_confounded" in evaluation.failure_codes
    assert packet.pair_assignments[0].validity is EvaluationValidity.ORDER_CONFOUNDED


def test_mapping_and_receipt_drift_hold_instead_of_inferred_success() -> None:
    harness = _harness()
    packet = replace(harness.packet, arm_role_mapping_sha256=_hash("wrong-role-map"))
    evaluation = replace(harness, packet=packet).evaluate()
    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "arm_role_mapping_hash_mismatch" in evaluation.hold_codes

    changed_run = replace(harness.run_receipts[0], reasoning_level="ultra")
    runs = (changed_run, *harness.run_receipts[1:])
    run_hashes = tuple(item.content_sha256 for item in runs)
    execution = tuple(
        replace(item, run_receipt_sha256=changed_run.content_sha256)
        if item.run_receipt_sha256 == harness.run_receipts[0].content_sha256
        else item
        for item in harness.packet.execution_observations
    )
    packet = replace(
        harness.packet,
        run_receipt_sha256s=run_hashes,
        execution_observations=execution,
    )
    evaluation = replace(harness, run_receipts=runs, packet=packet).evaluate()
    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "benchmark_reasoning_level_mismatch" in evaluation.hold_codes


def test_verifier_identity_is_pinned_and_independent_from_producer_and_scorers() -> None:
    harness = _harness()
    passing = harness.evaluate()
    assert passing.status is BenchmarkEvaluationStatus.PASS

    producer_collision = replace(
        harness.verifier_identity,
        independence_key=harness.packet.producer_independence_key,
    )
    evaluation = replace(harness, verifier_identity=producer_collision).evaluate()
    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "benchmark_verifier_matches_result_producer" in evaluation.hold_codes

    scorer_collision = replace(
        harness.verifier_identity,
        independence_key=passing.scorer_independence_keys[0],
    )
    evaluation = replace(harness, verifier_identity=scorer_collision).evaluate()
    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "benchmark_verifier_matches_scorer" in evaluation.hold_codes


def test_one_scorer_identity_with_multiple_configs_is_not_independent() -> None:
    harness = _harness()
    rewritten_judges = tuple(
        replace(item, scorer_identity="one-declared-scorer")
        for item in harness.judge_receipts
    )
    judge_hash_map = {
        original.content_sha256: rewritten.content_sha256
        for original, rewritten in zip(
            harness.judge_receipts, rewritten_judges, strict=True
        )
    }
    packet = replace(
        harness.packet,
        judge_receipt_sha256s=tuple(
            item.content_sha256 for item in rewritten_judges
        ),
        pair_observations=tuple(
            replace(
                item,
                judge_receipt_sha256=judge_hash_map[item.judge_receipt_sha256],
            )
            for item in harness.packet.pair_observations
        ),
        hard_gate_observations=tuple(
            replace(
                item,
                judge_receipt_sha256=judge_hash_map[item.judge_receipt_sha256],
            )
            for item in harness.packet.hard_gate_observations
        ),
    )

    evaluation = replace(
        harness,
        judge_receipts=rewritten_judges,
        packet=packet,
    ).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "pair_independent_scorer_count_insufficient" in evaluation.hold_codes
    assert "hard_gate_independent_scorer_count_insufficient" in evaluation.hold_codes
    assert len(evaluation.scorer_independence_keys) == 1


def test_true_authority_flags_and_invalid_scores_are_rejected() -> None:
    harness = _harness()
    with pytest.raises(ValueError, match="cannot grant authority"):
        replace(harness.packet, release_authority=True)
    with pytest.raises(TypeError, match="integer"):
        replace(harness.packet.pair_observations[0], left_score=True)
    with pytest.raises(TypeError, match="integer"):
        replace(harness.packet.pair_observations[0], left_score=float("nan"))


def test_valid_provenance_tombstone_cannot_disappear_from_admission() -> None:
    harness = _harness()
    current = harness.packet.pair_observations[0]
    tombstone = replace(
        current,
        observation_id="pair-score:tombstone:0001",
        disposition=ObservationDisposition.PROVENANCE_TOMBSTONE,
        used_for_admission=False,
    )
    packet = replace(
        harness.packet,
        pair_observations=(*harness.packet.pair_observations, tombstone),
    )
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "pair_valid_observation_superseded" in evaluation.hold_codes
    assert any(
        item.disposition is ObservationDisposition.PROVENANCE_TOMBSTONE
        for item in packet.pair_observations
    )


def test_valid_pair_observation_cannot_be_erased_by_supersession() -> None:
    harness = _harness()
    original = harness.packet.pair_observations[0]
    superseded = replace(
        original,
        observation_id="pair-score:superseded-valid:0001",
        disposition=ObservationDisposition.SUPERSEDED,
        used_for_admission=False,
    )
    replacement = replace(
        original,
        observation_id="pair-score:replacement:0001",
        supersedes_observation_sha256=superseded.content_sha256,
    )
    packet = replace(
        harness.packet,
        pair_observations=(
            replacement,
            superseded,
            *harness.packet.pair_observations[1:],
        ),
    )
    evaluation = replace(harness, packet=packet).evaluate()

    assert evaluation.status is BenchmarkEvaluationStatus.HOLD
    assert "pair_valid_observation_superseded" in evaluation.hold_codes


def test_benchmark_result_import_is_direct_and_pipeline_free() -> None:
    code = """
import json, sys
import engine.formulation_intelligence.benchmark_result as module
print(json.dumps({
  'module': module.__name__,
  'pipeline_loaded': any(name.startswith('engine.pipeline') for name in sys.modules),
  'torch_loaded': 'torch' in sys.modules,
  'faiss_loaded': 'faiss' in sys.modules,
  'requests_loaded': 'requests' in sys.modules,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[1],
    )
    payload = json.loads(completed.stdout)
    assert payload == {
        "module": "engine.formulation_intelligence.benchmark_result",
        "pipeline_loaded": False,
        "torch_loaded": False,
        "faiss_loaded": False,
        "requests_loaded": False,
    }
