from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from engine.experiments.missing_chemical_impact import (
    BlindedAllocation,
    CandidateInventoryStatus,
    ComparisonArmBinding,
    ComparisonArmKind,
    ComparisonEvidenceBundle,
    ComparisonProtocolBindings,
    CriterionDirection,
    CriterionOutcome,
    DecisionCriterion,
    ExpectedObservationCell,
    ExpectedObservationManifest,
    FormulaForkManifest,
    FormulaForkRecord,
    ImpactCandidateIdentityBinding,
    ImpactClassification,
    ImpactDecision,
    ImpactPlanState,
    MissingChemicalAssessment,
    MissingChemicalComparisonProtocol,
    MissingChemicalContractError,
    MissingChemicalDecisionReceipt,
    NativeLineageBinding,
    ObservationCellStatus,
    ObservationReceiptBinding,
    ProtocolProjectionAuthorization,
    QualificationReceiptBinding,
    SourceIntegrationState,
    StockReceiptBinding,
    project_lab_experiment_protocol_json,
)
from engine.optimization.contracts import (
    AuthorizedExperimentSet,
    CandidateDose,
    CandidateRole,
    ExperimentProposal,
    GateReceipt,
    GateStatus,
    HumanReviewReceipt,
    MixtureCandidate,
    MixtureDomain,
    NumericRange,
    SelectionStatus,
    StockDefinition,
    canonical_sha256,
)
from engine.optimization.mixture_design import candidate_formula_state_sha256
from engine.optimization.selection import authorize_proposal


def _hash(label: str) -> str:
    return sha256(label.encode("utf-8")).hexdigest()


def _stock_receipt(stock_id: str) -> StockReceiptBinding:
    return StockReceiptBinding(
        stock_id=stock_id,
        exact_stock_ref_sha256=_hash(f"exact:{stock_id}"),
        preparation_receipt_sha256=_hash(f"preparation:{stock_id}"),
        lifecycle_receipt_sha256=_hash(f"lifecycle:{stock_id}"),
    )


def _formula_forks() -> FormulaForkManifest:
    return FormulaForkManifest(
        records=tuple(
            FormulaForkRecord(
                edge_sha256=_hash(f"formula-edge:{candidate_id}"),
                parent_formula_sha256=_hash("parent-formula"),
                child_formula_sha256=_hash(f"formula-version:{candidate_id}"),
                relationship_kind="DESIGN_REVISION",
            )
            for candidate_id in (
                "control",
                "omission",
                "addition",
                "ratio",
                "control-replicate",
            )
        )
    )


def _identity() -> ImpactCandidateIdentityBinding:
    return ImpactCandidateIdentityBinding(
        function_id="clean_patchouli_fraction",
        candidate="Clearwood",
        native_material_id="candidate-material",
        c10_stock_ids=("stock-candidate",),
        identity_crosswalk_receipt_sha256=_hash("clearwood-native-crosswalk"),
    )


def _lineage(
    *,
    include_candidate_stock: bool = True,
    formula_forks: FormulaForkManifest | None = None,
) -> NativeLineageBinding:
    receipts = [_stock_receipt("stock-base")]
    if include_candidate_stock:
        receipts.append(_stock_receipt("stock-candidate"))
    return NativeLineageBinding(
        target_hypothesis_sha256=_hash("target"),
        accepted_target_sha256=_hash("accepted-target"),
        inventory_mapping_sha256=_hash("mapping"),
        build_plan_sha256=_hash("build"),
        parent_formula_sha256=_hash("parent-formula"),
        inventory_snapshot_sha256=_hash("inventory-v5"),
        formula_edge_set_sha256=(formula_forks or _formula_forks()).content_sha256,
        stock_receipts=tuple(receipts),
    )


def _package_payload(
    *,
    integration_state: str = "CONTROLLED_TEST_APPROVED",
    auto_integrated: list[str] | None = None,
    architecture_locked: bool = True,
    classification: str = "ESSENTIAL UNBLOCKER",
) -> dict:
    return {
        "target_formula_id": "TARGET-DEMO-001",
        "architecture_locked": architecture_locked,
        "strongly_covered_functions": ["transparent woody diffusion"],
        "weakly_covered_functions": ["fractional clean-patchouli bridge"],
        "genuinely_missing_functions": ["distinct clean patchouli fraction"],
        "auto_integrated_materials": auto_integrated or [],
        "candidates": [
            {
                "function_id": "clean_patchouli_fraction",
                "candidate": "Clearwood",
                "inventory_status": "OUT_OF_STOCK",
                "classification": classification,
                "nonredundancy": "Current stock does not reproduce the function.",
                "loss_if_omitted": "The bridge remains less differentiated.",
                "overdose_or_failure_mode": "Dry woody flattening.",
                "controlled_comparison": (
                    "Free text only: target versus zero, low, medium, and high."
                ),
                "integration_state": integration_state,
            }
        ],
    }


def _assessment(
    *,
    lineage: NativeLineageBinding | None = None,
    payload: dict | None = None,
) -> MissingChemicalAssessment:
    payload_value = payload or _package_payload()
    return MissingChemicalAssessment.from_package_payload(
        payload_value,
        assessment_id="MCI-001",
        source_package_sha256=_hash("v3-package"),
        expected_payload_sha256=canonical_sha256(payload_value),
        lineage=lineage or _lineage(),
    )


def _domain() -> MixtureDomain:
    return MixtureDomain(
        domain_id="missing-chemical-demo",
        total_active_mass_mg=NumericRange(8.0, 12.0),
        stocks=(
            StockDefinition(
                stock_id="stock-base",
                material_id="base-material",
                family="base",
                active_mass_fraction=1.0,
                carrier_mass_fractions=(),
                available_raw_mass_mg=100.0,
                minimum_measurable_raw_mass_mg=1.0,
                dispensing_increment_mg=1.0,
                cost_per_raw_mass_mg=0.0,
            ),
            StockDefinition(
                stock_id="stock-candidate",
                material_id="candidate-material",
                family="woody",
                active_mass_fraction=0.1,
                carrier_mass_fractions=(("ethanol", 0.9),),
                available_raw_mass_mg=100.0,
                minimum_measurable_raw_mass_mg=1.0,
                dispensing_increment_mg=1.0,
                cost_per_raw_mass_mg=0.1,
            ),
        ),
        required_gate_ids=("DOSE", "SAFETY"),
    )


def _candidate(
    domain: MixtureDomain,
    candidate_id: str,
    role: CandidateRole,
    doses: tuple[CandidateDose, ...],
    *,
    replicate_of: str | None = None,
    gate_status: GateStatus = GateStatus.PASS,
) -> MixtureCandidate:
    bare = MixtureCandidate(
        candidate_id=candidate_id,
        stage="SCREENING",
        role=role,
        doses=doses,
        replicate_of=replicate_of,
    )
    formula_hash = candidate_formula_state_sha256(domain, bare)
    return replace(
        bare,
        gate_receipts=tuple(
            GateReceipt(
                gate_id=gate_id,
                status=gate_status,
                subject_sha256=formula_hash,
                evidence_sha256=_hash(f"gate:{candidate_id}:{gate_id}"),
                authority="formula-bound current gate",
            )
            for gate_id in domain.required_gate_ids
        ),
    )


def _c10_fixture() -> tuple[
    MixtureDomain,
    tuple[MixtureCandidate, ...],
    ExperimentProposal,
]:
    domain = _domain()
    base = (CandidateDose("stock-base", 10.0, "formula"),)
    candidates = (
        _candidate(domain, "control", CandidateRole.CONTROL, base),
        _candidate(
            domain,
            "omission",
            CandidateRole.SCREENING,
            (CandidateDose("stock-base", 9.0, "formula"),),
        ),
        _candidate(
            domain,
            "addition",
            CandidateRole.SCREENING,
            (
                CandidateDose("stock-base", 10.0, "formula"),
                CandidateDose("stock-candidate", 1.0, "formula"),
            ),
        ),
        _candidate(
            domain,
            "ratio",
            CandidateRole.OPTIMIZATION,
            (
                CandidateDose("stock-base", 10.0, "formula"),
                CandidateDose("stock-candidate", 2.0, "formula"),
            ),
        ),
        _candidate(
            domain,
            "control-replicate",
            CandidateRole.REPLICATE,
            base,
            replicate_of="control",
        ),
    )
    proposal = ExperimentProposal(
        status=SelectionStatus.PROPOSED,
        selected_candidate_ids=tuple(item.candidate_id for item in candidates),
        pareto_candidate_ids=("addition", "omission", "ratio"),
        rejections=(),
        stop_reasons=(),
        blocker_codes=(),
        utilities=(),
        domain_sha256=domain.content_sha256,
        acquisition_policy_sha256=_hash("acquisition-policy"),
    )
    return domain, candidates, proposal


def _arms(
    domain: MixtureDomain,
    candidates: tuple[MixtureCandidate, ...],
) -> tuple[ComparisonArmBinding, ...]:
    by_id = {item.candidate_id: item for item in candidates}
    definitions = (
        ("arm-control", ComparisonArmKind.CONTROL, "control", None),
        ("arm-omission", ComparisonArmKind.OMISSION, "omission", None),
        ("arm-addition", ComparisonArmKind.ADDITION, "addition", None),
        ("arm-ratio", ComparisonArmKind.RATIO, "ratio", None),
        (
            "arm-replicate",
            ComparisonArmKind.REPLICATE,
            "control-replicate",
            "arm-control",
        ),
    )
    return tuple(
        ComparisonArmBinding(
            arm_id=arm_id,
            kind=kind,
            c10_candidate_id=candidate_id,
            c10_formula_state_sha256=candidate_formula_state_sha256(
                domain,
                by_id[candidate_id],
            ),
            formula_version_sha256=_hash(f"formula-version:{candidate_id}"),
            formula_edge_sha256=_hash(f"formula-edge:{candidate_id}"),
            formula_dose_receipt_sha256=_hash(f"dose:{candidate_id}"),
            matrix_manifest_sha256=_hash("matched-matrix"),
            application_manifest_sha256=_hash(f"application:{candidate_id}"),
            application_quantity_kind="raw_application_mass",
            application_quantity_value_text="10.000",
            application_quantity_unit="mg",
            application_quantity_basis="same substrate and application method",
            replicate_of_arm_id=replicate_of,
        )
        for arm_id, kind, candidate_id, replicate_of in definitions
    )


def _allocations(arms: tuple[ComparisonArmBinding, ...]) -> tuple[BlindedAllocation, ...]:
    result: list[BlindedAllocation] = []
    order = 1
    for arm_index, arm in enumerate(arms, start=1):
        for repeat_index in (1, 2):
            result.append(
                BlindedAllocation(
                    allocation_id=f"allocation-{arm_index}-{repeat_index}",
                    arm_id=arm.arm_id,
                    blind_code=f"A{arm_index}{repeat_index}",
                    presentation_order=order,
                    repeat_index=repeat_index,
                )
            )
            order += 1
    return tuple(result)


def _criteria() -> tuple[DecisionCriterion, ...]:
    return (
        DecisionCriterion(
            criterion_id="difference",
            endpoint_id="target-bridge",
            metric="paired blinded difference",
            unit="score_points",
            direction=CriterionDirection.DIFFERENCE,
            threshold_value_text="0",
            equivalence_margin_text=None,
            uncertainty_method="participant-clustered confidence interval",
            missing_data_rule="retain missing rows and hold if estimand is unidentified",
            tie_rule="ties are inconclusive",
        ),
        DecisionCriterion(
            criterion_id="equivalence",
            endpoint_id="off-target-drift",
            metric="paired off-target drift",
            unit="score_points",
            direction=CriterionDirection.EQUIVALENCE,
            threshold_value_text="0",
            equivalence_margin_text="0.5",
            uncertainty_method="participant-clustered confidence interval",
            missing_data_rule="retain missing rows and hold if estimand is unidentified",
            tie_rule="ties are inconclusive",
        ),
    )


def _bindings(**changes: str | None) -> ComparisonProtocolBindings:
    values = {
        "c0_protocol_sha256": _hash("c0-protocol"),
        "sample_manifest_sha256": _hash("sample-manifest"),
        "randomization_manifest_sha256": _hash("randomization"),
        "participant_plan_sha256": _hash("participant-plan"),
        "qualification_policy_sha256": _hash("qualification-policy"),
        "analysis_plan_sha256": _hash("analysis-plan"),
        "uncertainty_plan_sha256": _hash("uncertainty-plan"),
        "environment_timing_manifest_sha256": _hash("environment-timing"),
    }
    values.update(changes)
    return ComparisonProtocolBindings(**values)


def _protocol(
    *,
    state: ImpactPlanState = ImpactPlanState.PROTOCOL_LOCKED,
    assessment: MissingChemicalAssessment | None = None,
    current_lineage: NativeLineageBinding | None = None,
    domain: MixtureDomain | None = None,
    candidates: tuple[MixtureCandidate, ...] | None = None,
    proposal: ExperimentProposal | None = None,
    formula_forks: FormulaForkManifest | None = None,
    identity: ImpactCandidateIdentityBinding | None = None,
    arms: tuple[ComparisonArmBinding, ...] | None = None,
    required_arm_kinds: tuple[ComparisonArmKind, ...] | None = None,
    allocations: tuple[BlindedAllocation, ...] | None = None,
    repeat_count: int = 2,
    timepoints_seconds: tuple[int, ...] = (0, 1800, 7200, 28800, 86400),
    criteria: tuple[DecisionCriterion, ...] | None = None,
    bindings: ComparisonProtocolBindings | None = None,
) -> MissingChemicalComparisonProtocol:
    domain_value, candidate_values, proposal_value = _c10_fixture()
    formula_fork_value = formula_forks or _formula_forks()
    domain_value = domain or domain_value
    candidate_values = candidates or candidate_values
    proposal_value = proposal or proposal_value
    assessment_value = assessment or _assessment()
    lineage_value = current_lineage or assessment_value.lineage
    arm_values = arms or _arms(domain_value, candidate_values)
    return MissingChemicalComparisonProtocol(
        protocol_id="MCI-PROTOCOL-001",
        version=1,
        state=state,
        assessment=assessment_value,
        current_lineage=lineage_value,
        domain=domain_value,
        candidates=candidate_values,
        proposal=proposal_value,
        formula_fork_manifest=formula_fork_value,
        selected_impact_candidate=identity or _identity(),
        arms=arm_values,
        required_arm_kinds=required_arm_kinds or tuple(ComparisonArmKind),
        allocations=allocations if allocations is not None else _allocations(arm_values),
        repeat_count=repeat_count,
        timepoints_seconds=timepoints_seconds,
        criteria=criteria if criteria is not None else _criteria(),
        bindings=bindings or _bindings(),
    )


def _authorized_set(proposal: ExperimentProposal) -> AuthorizedExperimentSet:
    return authorize_proposal(
        proposal,
        HumanReviewReceipt(
            status=GateStatus.PASS,
            subject_sha256=proposal.content_sha256,
            evidence_sha256=_hash("c10-human-review"),
            reviewer_role="qualified human perfumer",
        ),
    )


def _projection_authorization(
    protocol: MissingChemicalComparisonProtocol,
    authorized: AuthorizedExperimentSet,
    *,
    status: GateStatus = GateStatus.PASS,
) -> ProtocolProjectionAuthorization:
    return ProtocolProjectionAuthorization(
        status=status,
        protocol_sha256=protocol.content_sha256,
        c10_authorized_set_sha256=canonical_sha256(authorized),
        existing_bottle_manifest_sha256=_hash("existing-bottle-manifest"),
        physical_review_evidence_sha256=_hash("physical-review"),
        reviewer_role="laboratory custodian",
    )


def _expected_manifest(
    protocol: MissingChemicalComparisonProtocol,
) -> ExpectedObservationManifest:
    cells = tuple(
        ExpectedObservationCell(
            cell_id=(f"cell-{allocation.allocation_id}-{timepoint}-{criterion.endpoint_id}"),
            allocation_id=allocation.allocation_id,
            arm_id=allocation.arm_id,
            repeat_index=allocation.repeat_index,
            timepoint_seconds=timepoint,
            endpoint_id=criterion.endpoint_id,
            participant_token="participant-01",
            session_token=f"session-{allocation.repeat_index}",
        )
        for allocation in protocol.allocations
        for timepoint in protocol.timepoints_seconds
        for criterion in protocol.criteria
    )
    return ExpectedObservationManifest(protocol=protocol, cells=cells)


def _observation_receipts(
    protocol: MissingChemicalComparisonProtocol,
    manifest: ExpectedObservationManifest,
    qualification: QualificationReceiptBinding,
    *,
    missing_cell_id: str | None = None,
) -> tuple[ObservationReceiptBinding, ...]:
    c0 = protocol.bindings.c0_protocol_sha256
    assert c0 is not None
    return tuple(
        ObservationReceiptBinding(
            record_sha256=_hash(f"observation:{cell.cell_id}"),
            status=(
                ObservationCellStatus.GOVERNED_MISSING
                if cell.cell_id == missing_cell_id
                else ObservationCellStatus.OBSERVED
            ),
            application_record_sha256=_hash(f"application-record:{cell.allocation_id}"),
            qualification_receipt_sha256=qualification.receipt_sha256,
            c0_protocol_sha256=c0,
            expected_cell_id=cell.cell_id,
            allocation_id=cell.allocation_id,
            arm_id=cell.arm_id,
            repeat_index=cell.repeat_index,
            timepoint_seconds=cell.timepoint_seconds,
            endpoint_id=cell.endpoint_id,
            participant_token=cell.participant_token,
            session_token=cell.session_token,
            missing_reason=(
                "participant response absent under the locked missing-data rule"
                if cell.cell_id == missing_cell_id
                else None
            ),
        )
        for cell in manifest.cells
    )


def _evidence(
    protocol: MissingChemicalComparisonProtocol,
    *,
    missing_cell_id: str | None = None,
) -> ComparisonEvidenceBundle:
    c0 = protocol.bindings.c0_protocol_sha256
    assert c0 is not None
    qualification = QualificationReceiptBinding(
        receipt_sha256=_hash("qualification"),
        c0_protocol_sha256=c0,
    )
    manifest = _expected_manifest(protocol)
    observations = _observation_receipts(
        protocol,
        manifest,
        qualification,
        missing_cell_id=missing_cell_id,
    )
    return ComparisonEvidenceBundle(
        protocol=protocol,
        expected_manifest=manifest,
        qualifications=(qualification,),
        observations=observations,
        analysis_result_sha256=_hash("analysis-result"),
        uncertainty_receipt_sha256=_hash("uncertainty-receipt"),
    )


def test_package_approved_text_remains_candidate_only_and_authority_false() -> None:
    assessment = _assessment()

    assert assessment.state is ImpactPlanState.CANDIDATE_ONLY
    assert assessment.candidates[0].source_integration_state is (
        SourceIntegrationState.CONTROLLED_TEST_APPROVED
    )
    assert assessment.candidates[0].source_controlled_comparison_text.startswith("Free text only")
    assert assessment.package_auto_integrated_materials == ()
    assert not any(
        (
            assessment.formula_authority,
            assessment.inventory_authority,
            assessment.purchase_authority,
            assessment.execution_authorized,
            assessment.scientific_authority,
            assessment.oav_authority,
            assessment.sensory_authority,
            assessment.safety_authority,
            assessment.release_authority,
        )
    )


@pytest.mark.parametrize("classification", [item.value for item in ImpactClassification])
def test_all_package_classifications_are_preserved_without_promotion(
    classification: str,
) -> None:
    assessment = _assessment(payload=_package_payload(classification=classification))

    assert assessment.candidates[0].classification is ImpactClassification(classification)
    assert assessment.state is ImpactPlanState.CANDIDATE_ONLY


def test_architecture_and_auto_integration_are_fail_closed() -> None:
    with pytest.raises(MissingChemicalContractError, match="architecture_locked"):
        _assessment(payload=_package_payload(architecture_locked=False))
    with pytest.raises(MissingChemicalContractError, match="auto_integrated_materials"):
        _assessment(payload=_package_payload(auto_integrated=["Clearwood"]))


def test_package_payload_hash_is_recomputed_and_must_match() -> None:
    payload = _package_payload()
    expected = canonical_sha256(payload)
    payload["target_formula_id"] = "TARGET-MUTATED"

    with pytest.raises(MissingChemicalContractError, match="payload hash"):
        MissingChemicalAssessment.from_package_payload(
            payload,
            assessment_id="MCI-HASH-MISMATCH",
            source_package_sha256=_hash("v3-package"),
            expected_payload_sha256=expected,
            lineage=_lineage(),
        )

    current_payload = _package_payload()
    assessment = _assessment(payload=current_payload)
    assert assessment.source_payload_sha256 == canonical_sha256(current_payload)


def test_selected_package_candidate_is_exactly_crosswalked_to_c10_identity() -> None:
    unrelated_key = replace(_identity(), function_id="unrelated_function")
    with pytest.raises(MissingChemicalContractError, match="bound assessment"):
        _protocol(identity=unrelated_key)

    unrelated_material = replace(_identity(), native_material_id="unrelated-material")
    with pytest.raises(MissingChemicalContractError, match="bound native material"):
        _protocol(identity=unrelated_material)

    domain, candidates, proposal = _c10_fixture()
    unrelated_candidates = list(candidates)
    unrelated_candidates[2] = _candidate(
        domain,
        "addition",
        CandidateRole.SCREENING,
        (CandidateDose("stock-base", 10.0, "formula"),),
    )
    with pytest.raises(MissingChemicalContractError, match="assessed native material"):
        _protocol(
            domain=domain,
            candidates=tuple(unrelated_candidates),
            proposal=proposal,
        )


def test_formula_fork_hashes_must_be_members_of_the_native_manifest() -> None:
    domain, candidates, proposal = _c10_fixture()
    arms = list(_arms(domain, candidates))
    arms[2] = replace(arms[2], formula_edge_sha256=_hash("unrelated-edge"))

    with pytest.raises(MissingChemicalContractError, match="native formula fork"):
        _protocol(
            domain=domain,
            candidates=candidates,
            proposal=proposal,
            arms=tuple(arms),
        )

    child_mismatch = list(_arms(domain, candidates))
    child_mismatch[2] = replace(
        child_mismatch[2],
        formula_version_sha256=_hash("unrelated-child-formula"),
    )
    with pytest.raises(MissingChemicalContractError, match="native formula fork"):
        _protocol(
            domain=domain,
            candidates=candidates,
            proposal=proposal,
            arms=tuple(child_mismatch),
        )

    stale_manifest = FormulaForkManifest(
        records=(
            replace(
                _formula_forks().records[0],
                relationship_kind="STOCK_NORMALIZATION",
            ),
            *_formula_forks().records[1:],
        )
    )
    with pytest.raises(MissingChemicalContractError, match="manifest is stale"):
        _protocol(formula_forks=stale_manifest)


def test_locked_protocol_reuses_c10_and_is_deterministically_hashed() -> None:
    first = _protocol()
    second = _protocol(
        arms=tuple(reversed(first.arms)),
        allocations=tuple(reversed(first.allocations)),
        criteria=tuple(reversed(first.criteria)),
        required_arm_kinds=tuple(reversed(first.required_arm_kinds)),
    )

    assert first.state is ImpactPlanState.PROTOCOL_LOCKED
    assert first.content_sha256 == second.content_sha256
    assert {item.kind for item in first.arms} == set(ComparisonArmKind)
    assert not first.execution_authorized


@pytest.mark.parametrize(
    "field_name",
    [
        "target_hypothesis_sha256",
        "accepted_target_sha256",
        "inventory_mapping_sha256",
        "build_plan_sha256",
        "parent_formula_sha256",
        "inventory_snapshot_sha256",
        "formula_edge_set_sha256",
    ],
)
def test_stale_native_lineage_hashes_fail(field_name: str) -> None:
    assessment = _assessment()
    stale = replace(assessment.lineage, **{field_name: _hash(f"stale:{field_name}")})

    with pytest.raises(MissingChemicalContractError, match="lineage is stale"):
        _protocol(assessment=assessment, current_lineage=stale)


def test_missing_stock_receipt_and_stale_formula_state_fail() -> None:
    lineage = _lineage(include_candidate_stock=False)
    assessment = _assessment(lineage=lineage)
    with pytest.raises(MissingChemicalContractError, match="stock/preparation receipts"):
        _protocol(assessment=assessment, current_lineage=lineage)

    domain, candidates, _ = _c10_fixture()
    arms = list(_arms(domain, candidates))
    arms[2] = replace(arms[2], c10_formula_state_sha256=_hash("stale-formula"))
    with pytest.raises(MissingChemicalContractError, match="formula-state hash"):
        _protocol(domain=domain, candidates=candidates, arms=tuple(arms))


def test_failed_c10_gate_and_mismatched_replicate_fail() -> None:
    domain, candidates, proposal = _c10_fixture()
    bad = list(candidates)
    bad[2] = _candidate(
        domain,
        "addition",
        CandidateRole.SCREENING,
        bad[2].doses,
        gate_status=GateStatus.FAIL,
    )
    with pytest.raises(MissingChemicalContractError, match="HARD_GATE_NOT_PASS"):
        _protocol(domain=domain, candidates=tuple(bad), proposal=proposal)

    arms = list(_arms(domain, candidates))
    arms[-1] = replace(arms[-1], replicate_of_arm_id="arm-addition")
    with pytest.raises(MissingChemicalContractError, match="replicate target"):
        _protocol(domain=domain, candidates=candidates, proposal=proposal, arms=tuple(arms))


@pytest.mark.parametrize(
    ("change", "match"),
    [
        ("missing_randomization", "randomization_manifest_sha256"),
        ("missing_required_arm", "required arm kinds are missing"),
        ("matrix_mismatch", "matched matrix"),
        ("application_mismatch", "matched application"),
        ("one_repeat", "repeat_count"),
        ("no_timepoints", "timepoints_seconds"),
        ("no_criteria", "decision criteria"),
        ("no_allocations", "does not have every required repeat"),
    ],
)
def test_lock_rejects_incomplete_protocol(change: str, match: str) -> None:
    domain, candidates, _ = _c10_fixture()
    arms = list(_arms(domain, candidates))
    kwargs: dict = {}
    if change == "missing_randomization":
        kwargs["bindings"] = _bindings(randomization_manifest_sha256=None)
    elif change == "missing_required_arm":
        kwargs["arms"] = tuple(item for item in arms if item.kind is not ComparisonArmKind.RATIO)
    elif change == "matrix_mismatch":
        arms[1] = replace(arms[1], matrix_manifest_sha256=_hash("other-matrix"))
        kwargs["arms"] = tuple(arms)
    elif change == "application_mismatch":
        arms[1] = replace(arms[1], application_quantity_value_text="9.5")
        kwargs["arms"] = tuple(arms)
    elif change == "one_repeat":
        kwargs["repeat_count"] = 1
    elif change == "no_timepoints":
        kwargs["timepoints_seconds"] = ()
    elif change == "no_criteria":
        kwargs["criteria"] = ()
    elif change == "no_allocations":
        kwargs["allocations"] = ()

    with pytest.raises(MissingChemicalContractError, match=match):
        _protocol(domain=domain, candidates=candidates, **kwargs)


def test_unknown_application_basis_and_dose_fail_before_lock() -> None:
    domain, candidates, _ = _c10_fixture()
    arm = _arms(domain, candidates)[0]
    with pytest.raises(MissingChemicalContractError, match="basis must not be empty"):
        replace(arm, application_quantity_basis="")
    with pytest.raises(MissingChemicalContractError, match="must be positive"):
        replace(arm, application_quantity_value_text="0")


def test_c10_authorization_alone_is_not_physical_projection_authority() -> None:
    protocol = _protocol()
    _, _, proposal = _c10_fixture()
    authorized = _authorized_set(proposal)

    failed = _projection_authorization(protocol, authorized, status=GateStatus.FAIL)
    with pytest.raises(MissingChemicalContractError, match="must PASS"):
        project_lab_experiment_protocol_json(protocol, authorized, failed)

    projected = project_lab_experiment_protocol_json(
        protocol,
        authorized,
        _projection_authorization(protocol, authorized),
    )
    assert projected["projection"]["requires_existing_bottle_ids"] is True
    assert projected["projection"]["samples_created"] is False
    assert projected["projection"]["lab_rows_written"] is False
    assert projected["projection"]["execution_authorized"] is False
    assert projected["execution_authorized"] is False


def test_proposed_protocol_cannot_project_or_accept_observations() -> None:
    proposed = _protocol(state=ImpactPlanState.PROTOCOL_PROPOSED, allocations=())
    _, _, proposal = _c10_fixture()
    authorized = _authorized_set(proposal)
    authorization = ProtocolProjectionAuthorization(
        status=GateStatus.PASS,
        protocol_sha256=proposed.content_sha256,
        c10_authorized_set_sha256=canonical_sha256(authorized),
        existing_bottle_manifest_sha256=_hash("bottles"),
        physical_review_evidence_sha256=_hash("review"),
        reviewer_role="custodian",
    )
    with pytest.raises(MissingChemicalContractError, match="locked protocol"):
        project_lab_experiment_protocol_json(proposed, authorized, authorization)
    with pytest.raises(MissingChemicalContractError, match="locked protocol"):
        ExpectedObservationManifest(protocol=proposed, cells=())


def test_c0_qualification_and_observation_protocol_mismatches_fail() -> None:
    protocol = _protocol()
    c0 = protocol.bindings.c0_protocol_sha256
    assert c0 is not None
    qualification = QualificationReceiptBinding(
        receipt_sha256=_hash("qualification"),
        c0_protocol_sha256=_hash("wrong-c0"),
    )
    manifest = _expected_manifest(protocol)
    observations = _observation_receipts(protocol, manifest, qualification)
    with pytest.raises(MissingChemicalContractError, match="qualification receipt"):
        ComparisonEvidenceBundle(
            protocol=protocol,
            expected_manifest=manifest,
            qualifications=(qualification,),
            observations=observations,
            analysis_result_sha256=_hash("analysis"),
            uncertainty_receipt_sha256=_hash("uncertainty"),
        )


def test_expected_observation_manifest_requires_the_complete_locked_grid() -> None:
    protocol = _protocol()
    manifest = _expected_manifest(protocol)
    expected_count = (
        len(protocol.allocations) * len(protocol.timepoints_seconds) * len(protocol.criteria)
    )
    assert len(manifest.cells) == expected_count == 100

    with pytest.raises(MissingChemicalContractError, match="cover every"):
        ExpectedObservationManifest(protocol=protocol, cells=manifest.cells[:-1])

    with pytest.raises(MissingChemicalContractError, match="cell IDs must be unique"):
        ExpectedObservationManifest(
            protocol=protocol,
            cells=(manifest.cells[0], *manifest.cells[:-1]),
        )

    first = manifest.cells[0]
    wrong = replace(first, repeat_index=first.repeat_index + 1)
    with pytest.raises(MissingChemicalContractError, match="frozen allocation"):
        ExpectedObservationManifest(
            protocol=protocol,
            cells=(wrong, *manifest.cells[1:]),
        )


def test_one_observation_cannot_support_a_full_protocol_decision() -> None:
    protocol = _protocol()
    manifest = _expected_manifest(protocol)
    c0 = protocol.bindings.c0_protocol_sha256
    assert c0 is not None
    qualification = QualificationReceiptBinding(
        receipt_sha256=_hash("qualification"),
        c0_protocol_sha256=c0,
    )
    observations = _observation_receipts(protocol, manifest, qualification)

    with pytest.raises(MissingChemicalContractError, match="every frozen expected cell"):
        ComparisonEvidenceBundle(
            protocol=protocol,
            expected_manifest=manifest,
            qualifications=(qualification,),
            observations=observations[:1],
            analysis_result_sha256=_hash("analysis"),
            uncertainty_receipt_sha256=_hash("uncertainty"),
        )


def test_observation_receipt_must_match_all_frozen_cell_dimensions() -> None:
    protocol = _protocol()
    manifest = _expected_manifest(protocol)
    c0 = protocol.bindings.c0_protocol_sha256
    assert c0 is not None
    qualification = QualificationReceiptBinding(
        receipt_sha256=_hash("qualification"),
        c0_protocol_sha256=c0,
    )
    observations = list(_observation_receipts(protocol, manifest, qualification))
    observations[0] = replace(
        observations[0],
        timepoint_seconds=observations[0].timepoint_seconds + 1,
    )

    with pytest.raises(MissingChemicalContractError, match="frozen expected cell"):
        ComparisonEvidenceBundle(
            protocol=protocol,
            expected_manifest=manifest,
            qualifications=(qualification,),
            observations=tuple(observations),
            analysis_result_sha256=_hash("analysis"),
            uncertainty_receipt_sha256=_hash("uncertainty"),
        )


def test_governed_missing_cell_is_explicit_and_blocks_directional_review() -> None:
    protocol = _protocol()
    missing_cell_id = _expected_manifest(protocol).cells[0].cell_id
    evidence = _evidence(protocol, missing_cell_id=missing_cell_id)
    outcomes = tuple(
        CriterionOutcome(
            criterion_id=criterion.criterion_id,
            estimate_value_text=(
                "0.0" if criterion.direction is CriterionDirection.EQUIVALENCE else "1.0"
            ),
            standard_uncertainty_text="0.1",
            unit=criterion.unit,
            tie=False,
            missing_reason=None,
        )
        for criterion in protocol.criteria
    )

    assert evidence.governed_missing_count == 1
    with pytest.raises(MissingChemicalContractError, match="cannot support"):
        MissingChemicalDecisionReceipt(
            receipt_id="MCI-MISSING-DIRECTIONAL",
            protocol=protocol,
            evidence=evidence,
            decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
            outcomes=outcomes,
            reviewer_evidence_sha256=_hash("missing-directional-review"),
        )


def test_decision_preserves_null_and_tie_and_withholds_directional_claim() -> None:
    protocol = _protocol()
    evidence = _evidence(protocol)
    outcomes = (
        CriterionOutcome(
            criterion_id="difference",
            estimate_value_text="1.25",
            standard_uncertainty_text="0.20",
            unit="score_points",
            tie=False,
            missing_reason=None,
        ),
        CriterionOutcome(
            criterion_id="equivalence",
            estimate_value_text=None,
            standard_uncertainty_text=None,
            unit="score_points",
            tie=True,
            missing_reason="one arm lacks a valid response row",
        ),
    )
    receipt = MissingChemicalDecisionReceipt(
        receipt_id="MCI-DECISION-001",
        protocol=protocol,
        evidence=evidence,
        decision=ImpactDecision.INCONCLUSIVE,
        outcomes=outcomes,
        reviewer_evidence_sha256=_hash("decision-review"),
    )

    assert receipt.outcomes[1].estimate_value_text is None
    assert receipt.outcomes[1].tie is True
    assert receipt.decision is ImpactDecision.INCONCLUSIVE
    assert not any(
        (
            receipt.formula_authority,
            receipt.inventory_authority,
            receipt.purchase_authority,
            receipt.execution_authorized,
            receipt.scientific_authority,
            receipt.oav_authority,
            receipt.sensory_authority,
            receipt.safety_authority,
            receipt.release_authority,
        )
    )
    with pytest.raises(MissingChemicalContractError, match="cannot support"):
        MissingChemicalDecisionReceipt(
            receipt_id="MCI-DECISION-002",
            protocol=protocol,
            evidence=evidence,
            decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
            outcomes=outcomes,
            reviewer_evidence_sha256=_hash("decision-review-2"),
        )


def test_outcome_unit_must_match_the_locked_criterion() -> None:
    protocol = _protocol()
    evidence = _evidence(protocol)
    outcomes = tuple(
        CriterionOutcome(
            criterion_id=criterion.criterion_id,
            estimate_value_text="1.0",
            standard_uncertainty_text="0.1",
            unit=("WRONG_UNIT" if index == 0 else criterion.unit),
            tie=False,
            missing_reason=None,
        )
        for index, criterion in enumerate(protocol.criteria)
    )

    with pytest.raises(MissingChemicalContractError, match="unit does not match"):
        MissingChemicalDecisionReceipt(
            receipt_id="MCI-WRONG-UNIT",
            protocol=protocol,
            evidence=evidence,
            decision=ImpactDecision.HOLD,
            outcomes=outcomes,
            reviewer_evidence_sha256=_hash("wrong-unit-review"),
        )


def test_signed_negative_difference_estimate_is_preserved_and_evaluated() -> None:
    criterion = DecisionCriterion(
        criterion_id="signed-difference",
        endpoint_id="signed-effect",
        metric="paired signed effect",
        unit="score_points",
        direction=CriterionDirection.DIFFERENCE,
        threshold_value_text="0.5",
        equivalence_margin_text=None,
        uncertainty_method="locked standard uncertainty",
        missing_data_rule="hold on missing",
        tie_rule="ties are inconclusive",
    )
    protocol = _protocol(criteria=(criterion,))
    evidence = _evidence(protocol)
    outcome = CriterionOutcome(
        criterion_id=criterion.criterion_id,
        estimate_value_text="-1.0",
        standard_uncertainty_text="0.1",
        unit=criterion.unit,
        tie=False,
        missing_reason=None,
    )
    receipt = MissingChemicalDecisionReceipt(
        receipt_id="MCI-SIGNED-NEGATIVE",
        protocol=protocol,
        evidence=evidence,
        decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
        outcomes=(outcome,),
        reviewer_evidence_sha256=_hash("signed-negative-review"),
    )

    assert receipt.outcomes[0].estimate_value_text == "-1.0"
    assert receipt.criterion_evaluations == ((criterion.criterion_id, True),)


@pytest.mark.parametrize(
    ("direction", "threshold", "margin", "estimate", "uncertainty"),
    [
        (CriterionDirection.DIFFERENCE, "0.5", None, "1.0", "2.0"),
        (CriterionDirection.EQUIVALENCE, "0", "0.5", "0.0", "1.0"),
    ],
)
def test_wide_uncertainty_cannot_support_difference_or_equivalence(
    direction: CriterionDirection,
    threshold: str,
    margin: str | None,
    estimate: str,
    uncertainty: str,
) -> None:
    criterion = DecisionCriterion(
        criterion_id=f"wide-{direction.value.casefold()}",
        endpoint_id="wide-uncertainty",
        metric="interval-bound effect",
        unit="score_points",
        direction=direction,
        threshold_value_text=threshold,
        equivalence_margin_text=margin,
        uncertainty_method="locked standard uncertainty",
        missing_data_rule="hold on missing",
        tie_rule="ties are inconclusive",
    )
    protocol = _protocol(criteria=(criterion,))
    evidence = _evidence(protocol)
    outcome = CriterionOutcome(
        criterion_id=criterion.criterion_id,
        estimate_value_text=estimate,
        standard_uncertainty_text=uncertainty,
        unit=criterion.unit,
        tie=False,
        missing_reason=None,
    )

    with pytest.raises(MissingChemicalContractError, match="every locked criterion"):
        MissingChemicalDecisionReceipt(
            receipt_id=f"MCI-WIDE-{direction.value}",
            protocol=protocol,
            evidence=evidence,
            decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
            outcomes=(outcome,),
            reviewer_evidence_sha256=_hash(f"wide:{direction.value}"),
        )


def test_unmet_at_least_criterion_cannot_support_further_review() -> None:
    criterion = DecisionCriterion(
        criterion_id="minimum-benefit",
        endpoint_id="minimum-benefit-endpoint",
        metric="minimum paired benefit",
        unit="score_points",
        direction=CriterionDirection.AT_LEAST,
        threshold_value_text="2.0",
        equivalence_margin_text=None,
        uncertainty_method="locked standard uncertainty",
        missing_data_rule="hold on missing",
        tie_rule="ties are inconclusive",
    )
    protocol = _protocol(criteria=(criterion,))
    evidence = _evidence(protocol)
    outcome = CriterionOutcome(
        criterion_id=criterion.criterion_id,
        estimate_value_text="1.0",
        standard_uncertainty_text="0.1",
        unit=criterion.unit,
        tie=False,
        missing_reason=None,
    )

    with pytest.raises(MissingChemicalContractError, match="every locked criterion"):
        MissingChemicalDecisionReceipt(
            receipt_id="MCI-UNMET-AT-LEAST",
            protocol=protocol,
            evidence=evidence,
            decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
            outcomes=(outcome,),
            reviewer_evidence_sha256=_hash("unmet-at-least-review"),
        )


def test_complete_decision_only_supports_further_review_not_mutation() -> None:
    protocol = _protocol()
    evidence = _evidence(protocol)
    outcomes = tuple(
        CriterionOutcome(
            criterion_id=criterion.criterion_id,
            estimate_value_text=(
                "0.0" if criterion.direction is CriterionDirection.EQUIVALENCE else "1.0"
            ),
            standard_uncertainty_text="0.1",
            unit=criterion.unit,
            tie=False,
            missing_reason=None,
        )
        for criterion in protocol.criteria
    )
    receipt = MissingChemicalDecisionReceipt(
        receipt_id="MCI-DECISION-COMPLETE",
        protocol=protocol,
        evidence=evidence,
        decision=ImpactDecision.SUPPORTS_FURTHER_REVIEW,
        outcomes=outcomes,
        reviewer_evidence_sha256=_hash("decision-review-complete"),
    )

    payload = receipt.as_dict()
    assert payload["decision"] == "SUPPORTS_FURTHER_REVIEW"
    assert payload["formula_authority"] is False
    assert payload["purchase_authority"] is False
    assert payload["release_authority"] is False


def test_p3_module_has_no_backend_or_migration_dependency() -> None:
    source = (
        __import__(
            "pathlib",
            fromlist=["Path"],
        )
        .Path("engine/experiments/missing_chemical_impact.py")
        .read_text(encoding="utf-8")
    )

    assert "sqlalchemy" not in source
    assert "backend" not in source
    assert "alembic" not in source
    assert "engine.experiments.planner" not in source
    assert "engine.intervention" not in source
    assert (
        CandidateInventoryStatus.OUT_OF_STOCK.value
        in _package_payload()["candidates"][0]["inventory_status"]
    )
