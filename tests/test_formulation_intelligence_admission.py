from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from hashlib import sha256

import pytest

from engine.formulation_intelligence.admission import (
    MANDATORY_AUTHORITY_EXCLUSIONS,
    TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER,
    AdmissionDecision,
    AdmissionRequest,
    AdmissionStatus,
    ArtifactBinding,
    ArtifactClosure,
    ArtifactKind,
    CampaignArtifactResolutionReceipt,
    CapabilityBinding,
    ModuleAdmissionManifest,
    PreexecutionCampaignReceipt,
    SchemaBinding,
    SourceIdentity,
    TrustedBenchmarkAdmissionPolicy,
    VerificationKind,
    VerificationReceipt,
    VerificationStatus,
    admission_to_evidence_authority_assessment,
    benchmark_request_scope_sha256,
    evaluate_runtime_admission,
    verify_frozen_campaign_artifact_bytes,
)
from engine.formulation_intelligence.benchmark_result import (
    BenchmarkVerifierIdentity,
    EvaluationValidity,
    FrozenBenchmarkEvaluation,
    FrozenBenchmarkVerificationBundle,
    PairOutcome,
)
from engine.formulation_intelligence.contracts import (
    AuthorityCeiling,
    ClaimKind,
    EvidenceClass,
    PlaneAssessment,
    PlaneId,
)
from tests.test_formulation_intelligence_benchmark_result import (
    _campaign_manifest,
)
from tests.test_formulation_intelligence_benchmark_result import (
    _harness as _benchmark_harness,
)

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64
_D = "d" * 64
_F = "f" * 64
_FROZEN_BENCHMARK_SHA256 = "1" * 64
_PERFORMANCE_POLICY_SHA256 = "2" * 64


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _materialized_campaign(tmp_path):
    template = _campaign_manifest()
    artifacts = []
    for binding in template.artifacts:
        payload = f"frozen bytes for {binding.artifact_id}\n".encode()
        path = tmp_path.joinpath(*binding.relative_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        artifacts.append(
            replace(
                binding,
                byte_length=len(payload),
                artifact_sha256=sha256(payload).hexdigest(),
            )
        )
    return replace(template, artifacts=tuple(artifacts))


_BENCHMARK_VERIFIER = BenchmarkVerifierIdentity(
    verifier_id="frozen-benchmark-harness",
    verifier_version="bound-by-receipt",
    verifier_implementation_sha256=_hash("focused deterministic benchmark verifier"),
    independence_key=_hash("focused benchmark verifier independence"),
    deterministic_local_verifier=True,
    admission_authorized=False,
)


def _source(*, state_sha256: str = _A) -> SourceIdentity:
    return SourceIdentity(
        repository_id="perfume-chem",
        source_task_id="admission-flat",
        worktree_path=r"D:\chatbots\perfume-chem",
        branch_ref="codex/add-inventory-materials",
        head_commit="d99ecdca8b0a4bf741bd4dda7bd564649cf05982",
        workspace_state_sha256=state_sha256,
    )


def _manifest(
    *,
    module_id: str = "target_compiler",
    source_sha256: str = _B,
    schema_id: str | None = None,
    schema_sha256: str = _D,
    exclusions: tuple[str, ...] = MANDATORY_AUTHORITY_EXCLUSIONS,
) -> ModuleAdmissionManifest:
    schema_id = schema_id or f"{module_id}:target-intent-v1"
    return ModuleAdmissionManifest(
        module_id=module_id,
        module_path=f"engine/formulation_intelligence/{module_id}.py",
        source_sha256=source_sha256,
        source_artifact_id=f"artifact:{module_id}:source",
        capabilities=(
            CapabilityBinding(
                capability_id=f"{module_id}:compile-target",
                capability_sha256=_C,
            ),
        ),
        schemas=(
            SchemaBinding(
                schema_id=schema_id,
                schema_sha256=schema_sha256,
            ),
        ),
        authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        exclusions=exclusions,
    )


def _closure(
    *,
    module_id: str = "target_compiler",
    source_sha256: str = _B,
) -> ArtifactClosure:
    schema_id = f"{module_id}:target-intent-v1"
    return ArtifactClosure(
        closure_id=f"closure:{module_id}:v1",
        artifacts=(
            ArtifactBinding(
                artifact_id=f"artifact:{module_id}:source",
                artifact_kind=ArtifactKind.SOURCE,
                artifact_path=f"engine/formulation_intelligence/{module_id}.py",
                artifact_sha256=source_sha256,
                dependency_ids=(
                    f"artifact:{module_id}:config",
                    schema_id,
                    f"artifact:{module_id}:data",
                ),
            ),
            ArtifactBinding(
                artifact_id=f"artifact:{module_id}:config",
                artifact_kind=ArtifactKind.CONFIG,
                artifact_path=f"configs/formulation_intelligence/{module_id}.json",
                artifact_sha256=_C,
            ),
            ArtifactBinding(
                artifact_id=schema_id,
                artifact_kind=ArtifactKind.SCHEMA,
                artifact_path=f"schemas/formulation_intelligence/{module_id}.json",
                artifact_sha256=_D,
            ),
            ArtifactBinding(
                artifact_id=f"artifact:{module_id}:data",
                artifact_kind=ArtifactKind.DATA,
                artifact_path=f"data/formulation_intelligence/{module_id}.json",
                artifact_sha256=_F,
            ),
        ),
    )


def _shared_schema_closure(
    manifests: tuple[ModuleAdmissionManifest, ...],
    *,
    shared_schema_id: str,
    shared_schema_sha256: str,
) -> ArtifactClosure:
    artifacts: list[ArtifactBinding] = [
        ArtifactBinding(
            artifact_id=shared_schema_id,
            artifact_kind=ArtifactKind.SCHEMA,
            artifact_path="schemas/formulation_intelligence/plane_assessment_v2.json",
            artifact_sha256=shared_schema_sha256,
        )
    ]
    for manifest in manifests:
        config_id = f"artifact:{manifest.module_id}:config"
        data_id = f"artifact:{manifest.module_id}:data"
        artifacts.extend(
            (
                ArtifactBinding(
                    artifact_id=manifest.source_artifact_id,
                    artifact_kind=ArtifactKind.SOURCE,
                    artifact_path=manifest.module_path,
                    artifact_sha256=manifest.source_sha256,
                    dependency_ids=(config_id, shared_schema_id, data_id),
                ),
                ArtifactBinding(
                    artifact_id=config_id,
                    artifact_kind=ArtifactKind.CONFIG,
                    artifact_path=(f"configs/formulation_intelligence/{manifest.module_id}.json"),
                    artifact_sha256=_C,
                ),
                ArtifactBinding(
                    artifact_id=data_id,
                    artifact_kind=ArtifactKind.DATA,
                    artifact_path=(f"data/formulation_intelligence/{manifest.module_id}.json"),
                    artifact_sha256=_F,
                ),
            )
        )
    return ArtifactClosure(
        closure_id="closure:shared-plane-assessment-schema:v1",
        artifacts=tuple(artifacts),
    )


def _receipt(
    kind: VerificationKind,
    *,
    source: SourceIdentity,
    manifests: tuple[ModuleAdmissionManifest, ...],
    observed_at_utc: str = "2026-09-01T00:00:00Z",
    status: VerificationStatus = VerificationStatus.PASS,
    exit_code: int = 0,
    blockers: tuple[str, ...] = (),
    receipt_id: str | None = None,
    closure: ArtifactClosure | None = None,
    output_sha256: str = _F,
) -> VerificationReceipt:
    module_ids = tuple(item.module_id for item in manifests)
    capability_ids = tuple(
        capability.capability_id for item in manifests for capability in item.capabilities
    )
    schema_ids = tuple(sorted({schema.schema_id for item in manifests for schema in item.schemas}))
    command = f"focused {kind.value} command"
    evidence_dimensions = {
        VerificationKind.TEST: ("tests",),
        VerificationKind.LINT: ("lint",),
        VerificationKind.TYPECHECK: ("types",),
        VerificationKind.FROZEN_BENCHMARK: ("frozen benchmark",),
        VerificationKind.PERFORMANCE_RESOURCE: (
            "latency",
            "memory",
            "throughput",
        ),
    }[kind]
    evidence_set_id = {
        VerificationKind.TEST: "evidence:test:v1",
        VerificationKind.LINT: "evidence:lint:v1",
        VerificationKind.TYPECHECK: "evidence:typecheck:v1",
        VerificationKind.FROZEN_BENCHMARK: ("frozen-benchmark:formulation-intelligence:v1"),
        VerificationKind.PERFORMANCE_RESOURCE: ("performance-resource:formulation-intelligence:v1"),
    }[kind]
    evidence_input_sha256 = {
        VerificationKind.TEST: _A,
        VerificationKind.LINT: _A,
        VerificationKind.TYPECHECK: _A,
        VerificationKind.FROZEN_BENCHMARK: _FROZEN_BENCHMARK_SHA256,
        VerificationKind.PERFORMANCE_RESOURCE: _PERFORMANCE_POLICY_SHA256,
    }[kind]
    return VerificationReceipt(
        receipt_id=receipt_id or f"receipt:{kind.value}",
        verification_kind=kind,
        verification_status=status,
        tool_id={
            VerificationKind.TEST: "pytest",
            VerificationKind.LINT: "ruff",
            VerificationKind.TYPECHECK: "mypy",
            VerificationKind.FROZEN_BENCHMARK: "frozen-benchmark-harness",
            VerificationKind.PERFORMANCE_RESOURCE: "performance-resource-harness",
        }[kind],
        tool_version="bound-by-receipt",
        command=command,
        command_sha256=sha256(command.encode("utf-8")).hexdigest(),
        evidence_set_id=evidence_set_id,
        evidence_input_sha256=evidence_input_sha256,
        evidence_dimensions=evidence_dimensions,
        observed_at_utc=observed_at_utc,
        source_identity_sha256=source.content_sha256,
        module_manifest_sha256s=tuple(item.content_sha256 for item in manifests),
        covered_module_ids=module_ids,
        covered_capability_ids=capability_ids,
        covered_schema_ids=schema_ids,
        artifact_closure_sha256=(closure.content_sha256 if closure is not None else None),
        covered_artifact_ids=(
            tuple(item.artifact_id for item in closure.artifacts) if closure is not None else ()
        ),
        exit_code=exit_code,
        output_sha256=output_sha256,
        blockers=blockers,
    )


def _request(
    *,
    source: SourceIdentity | None = None,
    manifests: tuple[ModuleAdmissionManifest, ...] | None = None,
    receipts: tuple[VerificationReceipt, ...] | None = None,
    closure: ArtifactClosure | None = None,
    as_of_utc: str = "2026-09-01T00:30:00Z",
    benchmark_evaluation: FrozenBenchmarkEvaluation | None = None,
) -> AdmissionRequest:
    source = source or _source()
    manifests = manifests or (_manifest(),)
    if receipts is None:
        receipts = tuple(
            _receipt(kind, source=source, manifests=manifests)
            for kind in (
                VerificationKind.TEST,
                VerificationKind.LINT,
                VerificationKind.TYPECHECK,
            )
        )
    return AdmissionRequest(
        request_id="admission:focused-runtime",
        source_identity=source,
        module_manifests=manifests,
        artifact_closure=closure,
        verification_receipts=receipts,
        required_verification_kinds=tuple(VerificationKind),
        required_exclusions=MANDATORY_AUTHORITY_EXCLUSIONS,
        maximum_authority_ceiling=AuthorityCeiling.STRUCTURAL_ONLY,
        frozen_benchmark_id="frozen-benchmark:formulation-intelligence:v1",
        frozen_benchmark_sha256=_FROZEN_BENCHMARK_SHA256,
        benchmark_challenge_nonce=_hash("focused generic benchmark challenge"),
        frozen_benchmark_verification_bundle=None,
        frozen_benchmark_evaluation=benchmark_evaluation,
        required_benchmark_verifier_identity_sha256=(
            _BENCHMARK_VERIFIER.content_sha256
        ),
        performance_resource_policy_id=("performance-resource:formulation-intelligence:v1"),
        performance_resource_policy_sha256=_PERFORMANCE_POLICY_SHA256,
        as_of_utc=as_of_utc,
        max_receipt_age_seconds=3600,
    )


def _complete_request() -> AdmissionRequest:
    source = _source()
    manifests = (_manifest(),)
    closure = _closure()
    receipts = tuple(
        _receipt(kind, source=source, manifests=manifests, closure=closure)
        for kind in VerificationKind
    )
    return _request(
        source=source,
        manifests=manifests,
        receipts=receipts,
        closure=closure,
    )


def _trusted_complete_request(
    *,
    result_kind: str = "pass",
    evaluated_at_utc: str = "2026-09-02T03:00:00Z",
    verifier_identity: BenchmarkVerifierIdentity | None = None,
    required_verifier_sha256: str | None = None,
) -> AdmissionRequest:
    harness = _benchmark_harness()
    source = _source()
    manifests = (_manifest(),)
    closure = _closure()
    verifier_identity = verifier_identity or harness.verifier_identity
    packet = replace(
        harness.packet,
        source_identity_sha256=source.content_sha256,
        workspace_state_sha256=source.workspace_state_sha256,
        admission_challenge_nonce=_hash("focused trusted benchmark challenge"),
        admission_request_scope_sha256=_hash("placeholder request scope"),
        module_manifest_sha256s=tuple(item.content_sha256 for item in manifests),
        covered_module_ids=tuple(item.module_id for item in manifests),
        covered_capability_ids=tuple(
            capability.capability_id
            for item in manifests
            for capability in item.capabilities
        ),
        covered_schema_ids=tuple(
            sorted({schema.schema_id for item in manifests for schema in item.schemas})
        ),
        artifact_closure_sha256=closure.content_sha256,
        covered_artifact_ids=closure.artifact_ids,
        observed_at_utc=evaluated_at_utc,
    )

    if result_kind == "fail":
        packet = replace(
            packet,
            pair_observations=tuple(
                replace(
                    item,
                    outcome=PairOutcome.TIE,
                    left_score=5,
                    right_score=5,
                    tie_reason="within frozen tie band",
                )
                for item in packet.pair_observations
            ),
        )
    elif result_kind == "hold":
        observations = list(packet.execution_observations)
        observations[0] = replace(
            observations[0],
            validity=EvaluationValidity.INCOMPLETE,
            reason_codes=("run.timeout",),
            used_for_admission=False,
        )
        packet = replace(packet, execution_observations=tuple(observations))
    elif result_kind != "pass":
        raise ValueError("result_kind must be pass, fail, or hold")

    def bundle_for(current_packet) -> FrozenBenchmarkVerificationBundle:
        return FrozenBenchmarkVerificationBundle(
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
            observation_packet=current_packet,
            verifier_identity=verifier_identity,
        )

    bundle = bundle_for(packet)
    evaluation = bundle.recompute()
    preliminary = _request(
        source=source,
        manifests=manifests,
        receipts=(),
        closure=closure,
        as_of_utc="2026-09-02T03:30:00Z",
        benchmark_evaluation=evaluation,
    )
    if required_verifier_sha256 is None:
        required_verifier_sha256 = verifier_identity.content_sha256
    preliminary = AdmissionRequest(
        **{
            **preliminary.constructor_values(),
            "frozen_benchmark_id": harness.definition.benchmark_id,
            "frozen_benchmark_sha256": harness.definition.content_sha256,
            "benchmark_challenge_nonce": packet.admission_challenge_nonce,
            "frozen_benchmark_verification_bundle": bundle,
            "required_benchmark_verifier_identity_sha256": required_verifier_sha256,
        }
    )
    packet = replace(
        packet,
        admission_request_scope_sha256=benchmark_request_scope_sha256(preliminary),
    )
    bundle = bundle_for(packet)
    evaluation = bundle.recompute()
    receipts = tuple(
        _receipt(
            kind,
            source=source,
            manifests=manifests,
            closure=closure,
            observed_at_utc="2026-09-02T03:10:00Z",
            output_sha256=(
                evaluation.content_sha256
                if kind is VerificationKind.FROZEN_BENCHMARK
                else _F
            ),
        )
        for kind in VerificationKind
    )
    receipts = tuple(
        VerificationReceipt(
            **{
                **receipt.constructor_values(),
                "evidence_set_id": harness.definition.benchmark_id,
                "evidence_input_sha256": bundle.content_sha256,
            }
        )
        if receipt.verification_kind is VerificationKind.FROZEN_BENCHMARK
        else receipt
        for receipt in receipts
    )
    return AdmissionRequest(
        **{
            **preliminary.constructor_values(),
            "frozen_benchmark_verification_bundle": bundle,
            "frozen_benchmark_evaluation": evaluation,
            "verification_receipts": receipts,
        }
    )


def _trusted_policy(request: AdmissionRequest) -> TrustedBenchmarkAdmissionPolicy:
    bundle = request.frozen_benchmark_verification_bundle
    assert bundle is not None
    manifest = replace(
        _campaign_manifest(),
        benchmark_id=request.frozen_benchmark_id,
        benchmark_definition_sha256=request.frozen_benchmark_sha256,
        source_identity_sha256=request.source_identity.content_sha256,
        workspace_state_sha256=request.source_identity.workspace_state_sha256,
    )
    resolution = CampaignArtifactResolutionReceipt(
        receipt_id="campaign-artifacts:focused-synthetic:v1",
        campaign_manifest_sha256=manifest.content_sha256,
        resolved_artifact_tree_sha256=_hash("synthetic resolved artifact tree"),
        resolved_artifact_count=len(manifest.artifacts),
        resolved_total_bytes=sum(item.byte_length for item in manifest.artifacts),
        resolved_at_utc="2026-09-02T00:20:00Z",
        benchmark_execution_authorized=False,
        admission_authorized=False,
    )
    preexecution = PreexecutionCampaignReceipt(
        receipt_id="preexecution:focused-synthetic:v1",
        campaign_manifest=manifest,
        artifact_resolution=resolution,
        challenge_nonce=request.benchmark_challenge_nonce,
        execution_ledger_genesis_sha256=_hash("empty synthetic execution ledger"),
        issuer_principal_id="local-admission-controller",
        trust_anchor_id="local-append-only-ledger",
        trust_anchor_receipt_sha256=_hash("synthetic trust anchor receipt"),
        issued_at_utc="2026-09-02T00:30:00Z",
        expires_at_utc="2026-09-03T00:30:00Z",
        campaign_execution_permitted=True,
        admission_authorized=False,
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
    return TrustedBenchmarkAdmissionPolicy(
        policy_id="trusted-policy:focused-benchmark:v1",
        benchmark_id=request.frozen_benchmark_id,
        benchmark_definition_sha256=request.frozen_benchmark_sha256,
        admission_challenge_nonce=request.benchmark_challenge_nonce,
        admission_request_scope_sha256=benchmark_request_scope_sha256(request),
        authorized_verification_bundle_sha256=bundle.content_sha256,
        preexecution_freeze_receipt_sha256=preexecution.content_sha256,
        preexecution_campaign_receipt=preexecution,
        benchmark_preregistered_at_utc="2026-09-02T00:30:00Z",
        verifier_identity=bundle.verifier_identity,
        maximum_receipt_age_seconds=3600,
        live_workspace_bytes_verified=True,
        benchmark_artifact_bytes_verified=True,
        preexecution_definition_bytes_verified=True,
        recursive_closure_verified=True,
        admission_authorized=False,
    )


def _evaluate_trusted(
    request: AdmissionRequest,
    *,
    policy: TrustedBenchmarkAdmissionPolicy | None = None,
) -> AdmissionDecision:
    return evaluate_runtime_admission(
        request,
        trusted_policy=policy or _trusted_policy(request),
        trusted_as_of_utc=request.as_of_utc,
    )


def _replace_benchmark_evaluation(
    request: AdmissionRequest,
    evaluation: FrozenBenchmarkEvaluation,
    *,
    required_verifier_sha256: str | None = None,
) -> AdmissionRequest:
    receipts = tuple(
        VerificationReceipt(
            **{
                **receipt.constructor_values(),
                "output_sha256": evaluation.content_sha256,
            }
        )
        if receipt.verification_kind is VerificationKind.FROZEN_BENCHMARK
        else receipt
        for receipt in request.verification_receipts
    )
    return AdmissionRequest(
        **{
            **request.constructor_values(),
            "frozen_benchmark_evaluation": evaluation,
            "required_benchmark_verifier_identity_sha256": (
                required_verifier_sha256
                or request.required_benchmark_verifier_identity_sha256
            ),
            "verification_receipts": receipts,
        }
    )


def test_campaign_artifacts_are_read_rehashed_and_receipted_before_execution(
    tmp_path,
) -> None:
    manifest = _materialized_campaign(tmp_path)
    resolution = verify_frozen_campaign_artifact_bytes(
        manifest,
        workspace_root=tmp_path,
        resolved_at_utc="2026-09-02T00:00:00Z",
    )

    assert resolution.resolved_artifact_count == len(manifest.artifacts)
    assert resolution.resolved_total_bytes == sum(
        item.byte_length for item in manifest.artifacts
    )
    assert resolution.campaign_manifest_sha256 == manifest.content_sha256
    assert CampaignArtifactResolutionReceipt.from_dict(
        resolution.as_dict()
    ) == resolution

    receipt = PreexecutionCampaignReceipt(
        receipt_id="preexecution:wp13:production:v1",
        campaign_manifest=manifest,
        artifact_resolution=resolution,
        challenge_nonce=_hash("production campaign challenge"),
        execution_ledger_genesis_sha256=_hash("empty execution ledger"),
        issuer_principal_id="local-admission-controller",
        trust_anchor_id="local-append-only-ledger",
        trust_anchor_receipt_sha256=_hash("trusted append-only anchor receipt"),
        issued_at_utc="2026-09-02T00:05:00Z",
        expires_at_utc="2026-09-03T00:05:00Z",
        campaign_execution_permitted=True,
        admission_authorized=False,
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

    assert PreexecutionCampaignReceipt.from_dict(receipt.as_dict()) == receipt
    assert receipt.campaign_execution_permitted is True
    assert receipt.admission_authorized is False
    assert receipt.release_authority is False


def test_campaign_byte_resolution_rejects_missing_or_changed_artifacts(
    tmp_path,
) -> None:
    manifest = _materialized_campaign(tmp_path)
    target = manifest.artifacts[0]
    target_path = tmp_path.joinpath(*target.relative_path.split("/"))
    target_path.write_bytes(b"post-freeze mutation")

    with pytest.raises(ValueError, match="byte length mismatch|SHA-256 mismatch"):
        verify_frozen_campaign_artifact_bytes(
            manifest,
            workspace_root=tmp_path,
            resolved_at_utc="2026-09-02T00:00:00Z",
        )

    target_path.unlink()
    with pytest.raises(ValueError, match="does not exist"):
        verify_frozen_campaign_artifact_bytes(
            manifest,
            workspace_root=tmp_path,
            resolved_at_utc="2026-09-02T00:00:00Z",
        )


def test_generic_exact_fresh_receipts_remain_hold_only() -> None:
    request = _complete_request()

    decision = evaluate_runtime_admission(request)

    assert decision.status is AdmissionStatus.HOLD
    assert decision.request_sha256 == request.content_sha256
    assert decision.admitted_module_ids == ()
    assert decision.pre_admission_verified_module_ids == ()
    assert decision.blockers == (TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER,)
    assert decision.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert decision.exclusions == MANDATORY_AUTHORITY_EXCLUSIONS
    assert decision.benchmark_execution_authorized is False
    assert decision.empirical_authority is False
    assert decision.formula_generation_authorized is False
    assert decision.physical_execution_authorized is False
    assert decision.compounding_authority is False
    assert decision.sensory_authority is False
    assert decision.liking_authority is False
    assert decision.safety_authority is False
    assert decision.stability_authority is False
    assert decision.purchase_authority is False
    assert decision.release_authority is False
    assert decision.verified_benchmark_evaluation_sha256 is None
    assert decision.benchmark_verifier_identity_sha256 is None
    assert decision.trusted_benchmark_policy_sha256 is None


def test_legacy_hash_only_typed_pass_cannot_admit_structurally() -> None:
    request = _trusted_complete_request()
    evaluation = request.frozen_benchmark_evaluation
    assert evaluation is not None

    decision = _evaluate_trusted(request)

    assert decision.status is AdmissionStatus.HOLD
    assert "legacy_benchmark_case_contract_nonadmissible" in decision.blockers
    assert "production_benchmark_corpus_coverage_invalid" in decision.blockers
    assert "production_benchmark_case_minimum_not_met" in decision.blockers
    assert "production_generation_minimum_not_met" in decision.blockers
    assert (
        "preexecution_campaign_artifact_reverification_failed"
        in decision.blockers
    )
    assert decision.admitted_module_ids == ()
    assert decision.pre_admission_verified_module_ids == ()
    assert decision.verified_benchmark_evaluation_sha256 is None
    assert decision.benchmark_verifier_identity_sha256 is None
    assert decision.trusted_benchmark_policy_sha256 is None
    assert decision.authority_ceiling is AuthorityCeiling.STRUCTURAL_ONLY
    assert decision.benchmark_execution_authorized is False
    assert decision.empirical_authority is False
    assert decision.formula_generation_authorized is False
    assert decision.physical_execution_authorized is False
    assert decision.compounding_authority is False
    assert decision.sensory_authority is False
    assert decision.liking_authority is False
    assert decision.safety_authority is False
    assert decision.stability_authority is False
    assert decision.purchase_authority is False
    assert decision.release_authority is False
    assert AdmissionRequest.from_dict(request.as_dict()) == request
    assert AdmissionDecision.from_dict(decision.as_dict()) == decision


def test_bundle_policy_and_trusted_clock_are_each_mandatory() -> None:
    request = _trusted_complete_request()
    policy = _trusted_policy(request)

    no_policy = evaluate_runtime_admission(
        request,
        trusted_as_of_utc=request.as_of_utc,
    )
    no_clock = evaluate_runtime_admission(
        request,
        trusted_policy=policy,
    )
    no_bundle = AdmissionRequest(
        **{
            **request.constructor_values(),
            "frozen_benchmark_verification_bundle": None,
        }
    )
    no_bundle_decision = evaluate_runtime_admission(
        no_bundle,
        trusted_policy=policy,
        trusted_as_of_utc=request.as_of_utc,
    )

    assert "benchmark_result_verifier_policy_untrusted" in no_policy.blockers
    assert "benchmark_result_trusted_clock_missing" in no_clock.blockers
    assert "benchmark_evidence_bundle_missing" in no_bundle_decision.blockers
    for decision in (no_policy, no_clock, no_bundle_decision):
        assert decision.status is AdmissionStatus.HOLD
        assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers
        assert decision.verified_benchmark_evaluation_sha256 is None


def test_out_of_band_policy_binds_exact_bundle_challenge_and_request_scope() -> None:
    request = _trusted_complete_request()
    policy = _trusted_policy(request)
    wrong_bundle_policy = TrustedBenchmarkAdmissionPolicy(
        **{
            **policy.constructor_values(),
            "authorized_verification_bundle_sha256": _A,
        }
    )
    changed_challenge = AdmissionRequest(
        **{
            **request.constructor_values(),
            "benchmark_challenge_nonce": _A,
        }
    )
    changed_request_id = AdmissionRequest(
        **{
            **request.constructor_values(),
            "request_id": "admission:replayed-under-another-request",
        }
    )

    wrong_bundle = _evaluate_trusted(request, policy=wrong_bundle_policy)
    challenge_replay = _evaluate_trusted(changed_challenge, policy=policy)
    scope_replay = _evaluate_trusted(changed_request_id, policy=policy)

    assert "benchmark_result_policy_bundle_mismatch" in wrong_bundle.blockers
    assert "benchmark_result_challenge_mismatch" in challenge_replay.blockers
    assert "benchmark_result_policy_challenge_mismatch" in challenge_replay.blockers
    assert "benchmark_result_request_binding_mismatch" in scope_replay.blockers
    assert "benchmark_result_policy_scope_mismatch" in scope_replay.blockers
    assert all(
        decision.status is AdmissionStatus.HOLD
        for decision in (wrong_bundle, challenge_replay, scope_replay)
    )


def test_trusted_policy_requires_preexecution_definition_freeze() -> None:
    request = _trusted_complete_request()
    policy = _trusted_policy(request)
    assert TrustedBenchmarkAdmissionPolicy.from_dict(policy.as_dict()) == policy

    late_receipt = PreexecutionCampaignReceipt(
        **{
            **policy.preexecution_campaign_receipt.constructor_values(),
            "issued_at_utc": "2026-09-02T01:00:00Z",
        }
    )
    not_preexecution = TrustedBenchmarkAdmissionPolicy(
        **{
            **policy.constructor_values(),
            "preexecution_freeze_receipt_sha256": late_receipt.content_sha256,
            "preexecution_campaign_receipt": late_receipt,
            "benchmark_preregistered_at_utc": late_receipt.issued_at_utc,
        }
    )
    decision = _evaluate_trusted(request, policy=not_preexecution)

    assert decision.status is AdmissionStatus.HOLD
    assert (
        "benchmark_definition_not_preregistered_before_execution"
        in decision.blockers
    )
    assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers

    with pytest.raises(
        ValueError, match="preexecution_definition_bytes_verified"
    ):
        TrustedBenchmarkAdmissionPolicy(
            **{
                **policy.constructor_values(),
                "preexecution_definition_bytes_verified": False,
            }
        )


def test_admitted_decision_cannot_omit_verified_benchmark_trace() -> None:
    request = _trusted_complete_request()
    decision = _evaluate_trusted(request)
    assert decision.status is AdmissionStatus.HOLD

    with pytest.raises(ValueError, match="verified benchmark evaluation"):
        AdmissionDecision(
            **{
                **decision.constructor_values(),
                "status": AdmissionStatus.ADMITTED,
                "admitted_module_ids": ("target_compiler",),
                "pre_admission_verified_module_ids": ("target_compiler",),
                "blockers": (),
                "verified_benchmark_evaluation_sha256": None,
                "benchmark_verifier_identity_sha256": None,
                "trusted_benchmark_policy_sha256": None,
            }
        )


def test_typed_evaluation_requires_exact_receipt_output_bytes() -> None:
    request = _trusted_complete_request()
    receipts = tuple(
        VerificationReceipt(
            **{
                **receipt.constructor_values(),
                "output_sha256": _A,
            }
        )
        if receipt.verification_kind is VerificationKind.FROZEN_BENCHMARK
        else receipt
        for receipt in request.verification_receipts
    )
    request = AdmissionRequest(
        **{
            **request.constructor_values(),
            "verification_receipts": receipts,
        }
    )

    decision = _evaluate_trusted(request)

    assert decision.status is AdmissionStatus.HOLD
    assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers
    assert "benchmark_result_receipt_evaluation_hash_mismatch" in decision.blockers
    assert decision.verified_benchmark_evaluation_sha256 is None
    assert decision.benchmark_verifier_identity_sha256 is None


@pytest.mark.parametrize(
    ("field_name", "replacement", "blocker"),
    (
        ("benchmark_id", "frozen-benchmark:other:v1", "benchmark_result_id_mismatch"),
        ("benchmark_definition_sha256", _A, "benchmark_definition_hash_mismatch"),
        ("source_identity_sha256", _B, "benchmark_result_source_identity_mismatch"),
        ("workspace_state_sha256", _B, "benchmark_result_workspace_state_mismatch"),
        ("module_manifest_sha256s", (_A,), "benchmark_result_manifest_hash_mismatch"),
        ("covered_module_ids", ("module.other",), "benchmark_result_module_coverage_mismatch"),
        (
            "covered_capability_ids",
            ("capability.other",),
            "benchmark_result_capability_coverage_mismatch",
        ),
        ("covered_schema_ids", ("schema.other",), "benchmark_result_schema_coverage_mismatch"),
        (
            "artifact_closure_sha256",
            _A,
            "benchmark_result_artifact_closure_hash_mismatch",
        ),
        (
            "covered_artifact_ids",
            ("artifact.other",),
            "benchmark_result_artifact_coverage_mismatch",
        ),
    ),
)
def test_typed_evaluation_scope_mismatches_fail_closed(
    field_name: str,
    replacement: object,
    blocker: str,
) -> None:
    request = _trusted_complete_request()
    evaluation = request.frozen_benchmark_evaluation
    assert evaluation is not None
    payload = evaluation.as_dict()
    payload[field_name] = replacement
    mismatched = FrozenBenchmarkEvaluation.from_dict(payload)
    request = _replace_benchmark_evaluation(request, mismatched)

    decision = _evaluate_trusted(request)

    assert decision.status is AdmissionStatus.HOLD
    assert "benchmark_evaluation_hash_mismatch" in decision.blockers
    assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers
    assert decision.verified_benchmark_evaluation_sha256 is None


def test_verifier_identity_is_pinned_and_independent() -> None:
    baseline = _trusted_complete_request()
    baseline_policy = _trusted_policy(baseline)
    changed_verifier = BenchmarkVerifierIdentity(
        verifier_id="frozen-benchmark-harness",
        verifier_version="bound-by-receipt",
        verifier_implementation_sha256=_hash("changed verifier implementation"),
        independence_key=_hash("changed independent verifier"),
        deterministic_local_verifier=True,
        admission_authorized=False,
    )
    changed_request = _trusted_complete_request(
        verifier_identity=changed_verifier,
        required_verifier_sha256=_BENCHMARK_VERIFIER.content_sha256,
    )
    changed_decision = _evaluate_trusted(changed_request, policy=baseline_policy)
    assert "benchmark_result_verifier_identity_mismatch" in changed_decision.blockers
    assert changed_decision.status is AdmissionStatus.HOLD

    baseline_bundle = baseline.frozen_benchmark_verification_bundle
    assert baseline_bundle is not None
    colliding_verifier = BenchmarkVerifierIdentity(
        verifier_id="frozen-benchmark-harness",
        verifier_version="bound-by-receipt",
        verifier_implementation_sha256=_hash("colliding verifier implementation"),
        independence_key=(
            baseline_bundle.observation_packet.producer_independence_key
        ),
        deterministic_local_verifier=True,
        admission_authorized=False,
    )
    colliding_request = _trusted_complete_request(verifier_identity=colliding_verifier)
    colliding_decision = _evaluate_trusted(colliding_request)
    assert "benchmark_result_verifier_not_independent" in colliding_decision.blockers
    assert colliding_decision.status is AdmissionStatus.HOLD


@pytest.mark.parametrize(
    ("evaluated_at_utc", "blocker"),
    (
        ("2026-09-02T01:00:00Z", "benchmark_result_stale"),
        ("2026-09-02T03:31:00Z", "benchmark_result_future"),
        (
            "2026-09-02T03:20:00Z",
            "benchmark_result_postverification_order_invalid",
        ),
    ),
)
def test_benchmark_evaluation_freshness_and_receipt_order_fail_closed(
    evaluated_at_utc: str,
    blocker: str,
) -> None:
    request = _trusted_complete_request(evaluated_at_utc=evaluated_at_utc)

    decision = _evaluate_trusted(request)

    assert decision.status is AdmissionStatus.HOLD
    assert blocker in decision.blockers
    assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers


@pytest.mark.parametrize(
    ("result_kind", "status_blocker", "detail_prefix"),
    (
        (
            "fail",
            "benchmark_result_status:fail",
            "benchmark_result_failure:superiority_not_demonstrated",
        ),
        (
            "hold",
            "benchmark_result_status:hold",
            "benchmark_result_hold:execution_cell_requires_one_current_valid_observation",
        ),
    ),
)
def test_legacy_nonpass_result_remains_replayable_but_never_admits(
    result_kind: str,
    status_blocker: str,
    detail_prefix: str,
) -> None:
    request = _trusted_complete_request(result_kind=result_kind)
    evaluation = request.frozen_benchmark_evaluation
    assert evaluation is not None

    decision = _evaluate_trusted(request)

    assert decision.status is AdmissionStatus.HOLD
    assert "legacy_benchmark_case_contract_nonadmissible" in decision.blockers
    assert TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER in decision.blockers
    assert status_blocker.endswith(evaluation.status.value)
    result_codes = (
        evaluation.failure_codes
        if result_kind == "fail"
        else evaluation.hold_codes
    )
    expected_detail = detail_prefix.split(":", maxsplit=1)[1]
    assert any(code.startswith(expected_detail) for code in result_codes)
    assert decision.verified_benchmark_evaluation_sha256 is None
    assert decision.benchmark_verifier_identity_sha256 is None
    assert decision.admitted_module_ids == ()


def test_all_records_are_versioned_strict_round_trippable_and_immutable() -> None:
    request = _complete_request()
    decision = evaluate_runtime_admission(request)

    assert AdmissionRequest.from_dict(request.as_dict()) == request
    assert AdmissionDecision.from_dict(decision.as_dict()) == decision
    assert request.content_sha256 == AdmissionRequest.from_dict(request.as_dict()).content_sha256

    payload = request.as_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="closed schema"):
        AdmissionRequest.from_dict(payload)

    payload = request.as_dict()
    payload["schema_version"] = "admission_request_v0"
    with pytest.raises(ValueError, match="schema_version"):
        AdmissionRequest.from_dict(payload)

    with pytest.raises(FrozenInstanceError):
        request.request_id = "mutated"  # type: ignore[misc]


def test_missing_stale_future_ambiguous_or_failed_receipts_hold() -> None:
    source = _source()
    manifests = (_manifest(),)
    passing = {
        kind: _receipt(kind, source=source, manifests=manifests) for kind in VerificationKind
    }

    missing = _request(
        source=source,
        manifests=manifests,
        receipts=(passing[VerificationKind.LINT], passing[VerificationKind.TYPECHECK]),
    )
    assert "missing_verification:test" in evaluate_runtime_admission(missing).blockers

    stale_test = _receipt(
        VerificationKind.TEST,
        source=source,
        manifests=manifests,
        observed_at_utc="2026-08-31T22:00:00Z",
    )
    stale = _request(
        source=source,
        manifests=manifests,
        receipts=(
            stale_test,
            passing[VerificationKind.LINT],
            passing[VerificationKind.TYPECHECK],
        ),
    )
    assert "stale_verification:test" in evaluate_runtime_admission(stale).blockers

    future_test = _receipt(
        VerificationKind.TEST,
        source=source,
        manifests=manifests,
        observed_at_utc="2026-09-01T00:31:00Z",
    )
    future = _request(
        source=source,
        manifests=manifests,
        receipts=(
            future_test,
            passing[VerificationKind.LINT],
            passing[VerificationKind.TYPECHECK],
        ),
    )
    assert "future_verification:test" in evaluate_runtime_admission(future).blockers

    duplicate_test = _receipt(
        VerificationKind.TEST,
        source=source,
        manifests=manifests,
        receipt_id="receipt:test:duplicate",
    )
    ambiguous = _request(
        source=source,
        manifests=manifests,
        receipts=(*passing.values(), duplicate_test),
    )
    assert "ambiguous_verification:test" in evaluate_runtime_admission(ambiguous).blockers

    failed_test = _receipt(
        VerificationKind.TEST,
        source=source,
        manifests=manifests,
        status=VerificationStatus.FAIL,
        exit_code=1,
        blockers=("one focused test failed",),
    )
    failed = _request(
        source=source,
        manifests=manifests,
        receipts=(
            failed_test,
            passing[VerificationKind.LINT],
            passing[VerificationKind.TYPECHECK],
        ),
    )
    assert "failed_verification:test" in evaluate_runtime_admission(failed).blockers

    for request in (missing, stale, future, ambiguous, failed):
        decision = evaluate_runtime_admission(request)
        assert decision.status is AdmissionStatus.HOLD
        assert decision.admitted_module_ids == ()


def test_source_manifest_and_exact_coverage_mismatches_hold_every_module() -> None:
    source = _source()
    manifests = (
        _manifest(),
        _manifest(module_id="plane_synthesis", source_sha256=_C),
    )
    receipts = list(_receipt(kind, source=source, manifests=manifests) for kind in VerificationKind)

    wrong_source = _source(state_sha256=_B)
    receipts[0] = _receipt(
        VerificationKind.TEST,
        source=wrong_source,
        manifests=manifests,
    )
    source_decision = evaluate_runtime_admission(
        _request(source=source, manifests=manifests, receipts=tuple(receipts))
    )
    assert "source_identity_mismatch:test" in source_decision.blockers
    assert source_decision.admitted_module_ids == ()

    receipts = list(_receipt(kind, source=source, manifests=manifests) for kind in VerificationKind)
    receipts[0] = VerificationReceipt(
        **{
            **receipts[0].constructor_values(),
            "covered_module_ids": ("target_compiler",),
        }
    )
    coverage_decision = evaluate_runtime_admission(
        _request(source=source, manifests=manifests, receipts=tuple(receipts))
    )
    assert "module_coverage_mismatch:test" in coverage_decision.blockers
    assert coverage_decision.admitted_module_ids == ()

    receipts = list(_receipt(kind, source=source, manifests=manifests) for kind in VerificationKind)
    receipts[0] = VerificationReceipt(
        **{
            **receipts[0].constructor_values(),
            "module_manifest_sha256s": (_A,),
        }
    )
    manifest_decision = evaluate_runtime_admission(
        _request(source=source, manifests=manifests, receipts=tuple(receipts))
    )
    assert "manifest_hash_mismatch:test" in manifest_decision.blockers
    assert manifest_decision.admitted_module_ids == ()

    for field_name, replacement, blocker in (
        (
            "covered_capability_ids",
            ("target_compiler:compile-target",),
            "capability_coverage_mismatch:test",
        ),
        (
            "covered_schema_ids",
            ("target_compiler:target-intent-v1",),
            "schema_coverage_mismatch:test",
        ),
    ):
        receipts = list(
            _receipt(kind, source=source, manifests=manifests) for kind in VerificationKind
        )
        receipts[0] = VerificationReceipt(
            **{
                **receipts[0].constructor_values(),
                field_name: replacement,
            }
        )
        decision = evaluate_runtime_admission(
            _request(source=source, manifests=manifests, receipts=tuple(receipts))
        )
        assert blocker in decision.blockers
        assert decision.admitted_module_ids == ()


def test_missing_authority_exclusions_or_excessive_ceiling_hold() -> None:
    source = _source()
    incomplete = _manifest(exclusions=("sensory authority",))
    receipts = tuple(
        _receipt(kind, source=source, manifests=(incomplete,)) for kind in VerificationKind
    )
    decision = evaluate_runtime_admission(
        _request(source=source, manifests=(incomplete,), receipts=receipts)
    )

    assert decision.status is AdmissionStatus.HOLD
    assert any("missing_exclusion" in blocker for blocker in decision.blockers)

    excessive = ModuleAdmissionManifest(
        **{
            **_manifest().constructor_values(),
            "authority_ceiling": AuthorityCeiling.DESIGN_ONLY,
        }
    )
    receipts = tuple(
        _receipt(kind, source=source, manifests=(excessive,)) for kind in VerificationKind
    )
    decision = evaluate_runtime_admission(
        _request(source=source, manifests=(excessive,), receipts=receipts)
    )
    assert "module_authority_exceeds_request:target_compiler" in decision.blockers


def test_duplicate_module_capability_schema_and_receipt_ids_are_rejected() -> None:
    manifest = _manifest()
    with pytest.raises(ValueError, match="module_id"):
        _request(manifests=(manifest, manifest), receipts=())

    with pytest.raises(ValueError, match="capability_id"):
        ModuleAdmissionManifest(
            **{
                **manifest.constructor_values(),
                "capabilities": (manifest.capabilities[0], manifest.capabilities[0]),
            }
        )

    with pytest.raises(ValueError, match="schema_id"):
        ModuleAdmissionManifest(
            **{
                **manifest.constructor_values(),
                "schemas": (manifest.schemas[0], manifest.schemas[0]),
            }
        )

    source = _source()
    receipt = _receipt(
        VerificationKind.TEST,
        source=source,
        manifests=(manifest,),
    )
    with pytest.raises(ValueError, match="receipt_id"):
        _request(receipts=(receipt, receipt))


def test_admission_is_deterministic_and_does_not_execute_a_benchmark() -> None:
    request = _request()

    first = evaluate_runtime_admission(request)
    second = evaluate_runtime_admission(request)

    assert first == second
    assert first.content_sha256 == second.content_sha256
    assert first.evaluated_at_utc == request.as_of_utc
    assert first.status is AdmissionStatus.HOLD
    assert AdmissionDecision.from_dict(first.as_dict()) == first
    assert first.admitted_module_ids == ()
    assert first.pre_admission_verified_module_ids == ()
    assert "missing_artifact_closure" in first.blockers
    assert "missing_verification:frozen_benchmark" in first.blockers
    assert "missing_verification:performance_resource" in first.blockers
    assert first.benchmark_execution_authorized is False


def test_benchmark_and_performance_receipts_are_both_required_and_fresh() -> None:
    complete = _complete_request()

    missing_benchmark = AdmissionRequest(
        **{
            **complete.constructor_values(),
            "verification_receipts": tuple(
                receipt
                for receipt in complete.verification_receipts
                if receipt.verification_kind is not VerificationKind.FROZEN_BENCHMARK
            ),
        }
    )
    decision = evaluate_runtime_admission(missing_benchmark)
    assert decision.status is AdmissionStatus.HOLD
    assert "missing_verification:frozen_benchmark" in decision.blockers
    assert decision.admitted_module_ids == ()

    source = complete.source_identity
    manifests = complete.module_manifests
    closure = complete.artifact_closure
    assert closure is not None
    for stale_kind in (
        VerificationKind.FROZEN_BENCHMARK,
        VerificationKind.PERFORMANCE_RESOURCE,
    ):
        stale_receipt = _receipt(
            stale_kind,
            source=source,
            manifests=manifests,
            closure=closure,
            observed_at_utc="2026-08-31T22:00:00Z",
        )
        stale = AdmissionRequest(
            **{
                **complete.constructor_values(),
                "verification_receipts": tuple(
                    stale_receipt if receipt.verification_kind is stale_kind else receipt
                    for receipt in complete.verification_receipts
                ),
            }
        )
        decision = evaluate_runtime_admission(stale)
        assert decision.status is AdmissionStatus.HOLD
        assert f"stale_verification:{stale_kind.value}" in decision.blockers
        assert decision.admitted_module_ids == ()


def test_benchmark_performance_and_closure_mismatches_never_admit() -> None:
    complete = _complete_request()

    mismatched_benchmark = tuple(
        VerificationReceipt(
            **{
                **receipt.constructor_values(),
                "artifact_closure_sha256": _A,
            }
        )
        if receipt.verification_kind is VerificationKind.FROZEN_BENCHMARK
        else receipt
        for receipt in complete.verification_receipts
    )
    request = AdmissionRequest(
        **{
            **complete.constructor_values(),
            "verification_receipts": mismatched_benchmark,
        }
    )
    decision = evaluate_runtime_admission(request)
    assert decision.status is AdmissionStatus.HOLD
    assert "artifact_closure_hash_mismatch:frozen_benchmark" in decision.blockers

    mismatched_performance = tuple(
        VerificationReceipt(
            **{
                **receipt.constructor_values(),
                "evidence_input_sha256": _A,
            }
        )
        if receipt.verification_kind is VerificationKind.PERFORMANCE_RESOURCE
        else receipt
        for receipt in complete.verification_receipts
    )
    request = AdmissionRequest(
        **{
            **complete.constructor_values(),
            "verification_receipts": mismatched_performance,
        }
    )
    decision = evaluate_runtime_admission(request)
    assert decision.status is AdmissionStatus.HOLD
    assert "evidence_input_mismatch:performance_resource" in decision.blockers
    assert decision.admitted_module_ids == ()


def test_transitive_source_config_schema_data_closure_is_mandatory() -> None:
    source = _source()
    manifests = (_manifest(),)
    incomplete = ArtifactClosure(
        closure_id="closure:incomplete",
        artifacts=(
            ArtifactBinding(
                artifact_id="artifact:target_compiler:source",
                artifact_kind=ArtifactKind.SOURCE,
                artifact_path="engine/formulation_intelligence/target_compiler.py",
                artifact_sha256=_B,
                dependency_ids=("artifact:missing-config",),
            ),
        ),
    )
    receipts = tuple(
        _receipt(kind, source=source, manifests=manifests, closure=incomplete)
        for kind in VerificationKind
    )
    request = _request(
        source=source,
        manifests=manifests,
        receipts=receipts,
        closure=incomplete,
    )

    decision = evaluate_runtime_admission(request)

    assert decision.status is AdmissionStatus.HOLD
    assert "closure_missing_dependency:artifact:missing-config" in decision.blockers
    assert "closure_missing_artifact_kind:config" in decision.blockers
    assert "closure_missing_artifact_kind:schema" in decision.blockers
    assert "closure_missing_artifact_kind:data" in decision.blockers
    assert decision.admitted_module_ids == ()


def _assessment_for(
    request: AdmissionRequest,
    decision: AdmissionDecision | None = None,
) -> PlaneAssessment:
    return admission_to_evidence_authority_assessment(
        request,
        decision or evaluate_runtime_admission(request),
        semantic_target_scope="perfume architecture: iris cathedral",
        temporal_scope="runtime admission snapshot 2026-09-01t00:30:00z",
        matrix_scope="perfume-chem dirty worktree",
    )


def test_pre_admission_adapter_preserves_requirements_hashes_and_unknowns() -> None:
    request = _request()
    decision = evaluate_runtime_admission(request)

    assessment = _assessment_for(request, decision)

    assert assessment.plane_id is PlaneId.EVIDENCE_AUTHORITY
    assert assessment.target_scope == "perfume architecture: iris cathedral"
    assert assessment.temporal_scope == ("runtime admission snapshot 2026-09-01t00:30:00z")
    assert assessment.matrix_scope == "perfume-chem dirty worktree"
    assert assessment.authority_ceiling is AuthorityCeiling.WITHHELD
    assert assessment.support_intervals == ()
    assert assessment.native_criteria == ()
    assert assessment.conflicts == ()
    assert all(
        claim.authority_ceiling is AuthorityCeiling.WITHHELD for claim in assessment.claims
    )
    assert all(claim.claim_kind is not ClaimKind.OBSERVATION for claim in assessment.claims)
    assert all(
        reference.evidence_class is EvidenceClass.HEURISTIC
        for reference in assessment.provenance_refs
    )

    claims = {(claim.claim_key, claim.claim_value) for claim in assessment.claims}
    assert ("runtime_admission.status", "hold") in claims
    assert (
        "runtime_admission.frozen_benchmark.id",
        request.frozen_benchmark_id,
    ) in claims
    assert (
        "runtime_admission.frozen_benchmark.sha256",
        request.frozen_benchmark_sha256,
    ) in claims
    assert (
        "runtime_admission.performance_resource_policy.sha256",
        request.performance_resource_policy_sha256,
    ) in claims
    assert ("runtime_admission.artifact_closure.required", "true") in claims
    assert ("runtime_admission.artifact_closure.state", "absent") in claims
    assert request.content_sha256 in assessment.freshness_hashes
    assert decision.content_sha256 in assessment.freshness_hashes
    assert request.source_identity.workspace_state_sha256 in assessment.freshness_hashes
    assert {
        "missing_artifact_closure",
        "missing_verification:frozen_benchmark",
        "missing_verification:performance_resource",
        TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER,
    }.issubset({unknown.reason for unknown in assessment.unknowns})
    assert set(MANDATORY_AUTHORITY_EXCLUSIONS).issubset(
        {
            claim.claim_value
            for claim in assessment.claims
            if claim.claim_key == "runtime_admission.exclusion"
        }
    )


def test_hold_adapter_is_withheld_and_preserves_static_blockers() -> None:
    request = _request(receipts=())
    decision = evaluate_runtime_admission(request)

    assessment = _assessment_for(request, decision)

    assert decision.status is AdmissionStatus.HOLD
    assert assessment.authority_ceiling is AuthorityCeiling.WITHHELD
    assert all(claim.authority_ceiling is AuthorityCeiling.WITHHELD for claim in assessment.claims)
    assert "missing_verification:test" in {unknown.reason for unknown in assessment.unknowns}
    assert "missing_verification:lint" in {unknown.reason for unknown in assessment.unknowns}
    assert "missing_verification:typecheck" in {unknown.reason for unknown in assessment.unknowns}


def test_synthetic_packet_adapter_remains_withheld_and_non_authorizing() -> None:
    request = _complete_request()
    decision = evaluate_runtime_admission(request)
    assert decision.status is AdmissionStatus.HOLD

    first = _assessment_for(request, decision)
    second = _assessment_for(request, decision)

    assert first == second
    assert first.content_sha256 == second.content_sha256
    assert PlaneAssessment.from_dict(first.as_dict()) == first
    assert first.authority_ceiling is AuthorityCeiling.WITHHELD
    assert {item.reason for item in first.unknowns} == {
        TRUSTED_BENCHMARK_RESULT_REQUIRED_BLOCKER
    }
    assert first.support_intervals == ()
    claim_text = " ".join(
        f"{claim.claim_key}={claim.claim_value}" for claim in first.claims
    ).casefold()
    assert "benchmark_execution_authorized=true" not in claim_text
    assert "formula_generation_authorized=true" not in claim_text
    assert "physical_execution_authorized=true" not in claim_text
    assert "sensory_authority=true" not in claim_text
    assert "liking_authority=true" not in claim_text
    assert "safety_authority=true" not in claim_text
    assert "stability_authority=true" not in claim_text
    assert "release_authority=true" not in claim_text


def test_adapter_rejects_a_decision_from_another_request() -> None:
    request = _request()
    other = _request(source=_source(state_sha256=_B))
    other_decision = evaluate_runtime_admission(other)

    with pytest.raises(ValueError, match="request_sha256"):
        _assessment_for(request, other_decision)


def test_identical_shared_schema_bindings_remain_hold_without_typed_result() -> None:
    shared_schema_id = "plane_assessment_v2"
    source = _source()
    manifests = (
        _manifest(
            module_id="target_compiler",
            source_sha256=_B,
            schema_id=shared_schema_id,
            schema_sha256=_D,
        ),
        _manifest(
            module_id="plane_synthesis",
            source_sha256=_C,
            schema_id=shared_schema_id,
            schema_sha256=_D,
        ),
    )
    closure = _shared_schema_closure(
        manifests,
        shared_schema_id=shared_schema_id,
        shared_schema_sha256=_D,
    )
    receipts = tuple(
        _receipt(kind, source=source, manifests=manifests, closure=closure)
        for kind in VerificationKind
    )
    request = _request(
        source=source,
        manifests=manifests,
        closure=closure,
        receipts=receipts,
    )

    decision = evaluate_runtime_admission(request)

    assert decision.status is AdmissionStatus.HOLD
    assert decision.admitted_module_ids == ()
    assert decision.pre_admission_verified_module_ids == ()
    assert tuple(
        artifact.artifact_id
        for artifact in closure.artifacts
        if artifact.artifact_kind is ArtifactKind.SCHEMA
    ) == (shared_schema_id,)


def test_shared_schema_hash_conflict_blocks_every_consumer() -> None:
    shared_schema_id = "plane_assessment_v2"
    source = _source()
    manifests = (
        _manifest(
            module_id="target_compiler",
            source_sha256=_B,
            schema_id=shared_schema_id,
            schema_sha256=_D,
        ),
        _manifest(
            module_id="plane_synthesis",
            source_sha256=_C,
            schema_id=shared_schema_id,
            schema_sha256=_A,
        ),
    )
    closure = _shared_schema_closure(
        manifests,
        shared_schema_id=shared_schema_id,
        shared_schema_sha256=_D,
    )
    receipts = tuple(
        _receipt(kind, source=source, manifests=manifests, closure=closure)
        for kind in VerificationKind
    )
    request = _request(
        source=source,
        manifests=manifests,
        closure=closure,
        receipts=receipts,
    )

    decision = evaluate_runtime_admission(request)

    assert decision.status is AdmissionStatus.HOLD
    assert decision.admitted_module_ids == ()
    assert {
        ("shared_schema_hash_mismatch:plane_assessment_v2:consumer:target_compiler"),
        ("shared_schema_hash_mismatch:plane_assessment_v2:consumer:plane_synthesis"),
    }.issubset(set(decision.blockers))
