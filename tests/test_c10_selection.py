from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from engine.evidence.unsupported_science import (
    C9_LEGACY_SURFACES,
    C10Use,
    UnsupportedOutcome,
)
from engine.optimization import (
    AcquisitionPolicy,
    AcquisitionTerm,
    C10ContractError,
    CampaignState,
    CandidateDose,
    CandidateEvaluation,
    CandidateRole,
    DesignStage,
    GateReceipt,
    GateStatus,
    HumanReviewReceipt,
    MixtureCandidate,
    MixtureDomain,
    NumericRange,
    ObjectiveAuthority,
    ObjectiveDirection,
    ObjectiveEstimate,
    SelectionStatus,
    StockDefinition,
    StopPolicy,
    StopReason,
    assess_objective_authority,
    authorize_proposal,
    candidate_formula_state_sha256,
    select_experiments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HASH_A = "a" * 64
HASH_B = "b" * 64


def _domain() -> MixtureDomain:
    return MixtureDomain(
        domain_id="selection-domain-v1",
        total_active_mass_mg=NumericRange(4.0, 4.0),
        stocks=(
            StockDefinition(
                stock_id="stock-a",
                material_id="material-a",
                family="floral",
                active_mass_fraction=1.0,
                carrier_mass_fractions=(),
                available_raw_mass_mg=20.0,
                minimum_measurable_raw_mass_mg=1.0,
                dispensing_increment_mg=1.0,
                cost_per_raw_mass_mg=1.0,
            ),
            StockDefinition(
                stock_id="stock-b",
                material_id="material-b",
                family="woody",
                active_mass_fraction=1.0,
                carrier_mass_fractions=(),
                available_raw_mass_mg=20.0,
                minimum_measurable_raw_mass_mg=1.0,
                dispensing_increment_mg=1.0,
                cost_per_raw_mass_mg=2.0,
            ),
        ),
        required_gate_ids=("safety", "action_permission", "applicability"),
        maximum_candidates=20,
    )


def _candidate(
    domain: MixtureDomain,
    candidate_id: str,
    a_mass: float,
    *,
    role: CandidateRole,
    replicate_of: str | None = None,
    gate_status: GateStatus = GateStatus.PASS,
) -> MixtureCandidate:
    bare = MixtureCandidate(
        candidate_id=candidate_id,
        stage=DesignStage.SCREENING,
        role=role,
        doses=(
            CandidateDose("stock-a", a_mass, "formula"),
            CandidateDose("stock-b", 4.0 - a_mass, "formula"),
        ),
        replicate_of=replicate_of,
    )
    formula_hash = candidate_formula_state_sha256(domain, bare)
    receipts = tuple(
        GateReceipt(
            gate_id=gate_id,
            status=gate_status,
            subject_sha256=formula_hash,
            evidence_sha256=HASH_A,
            authority=f"versioned-{gate_id}-v1",
        )
        for gate_id in domain.required_gate_ids
    )
    return replace(bare, gate_receipts=receipts)


def _estimate(
    name: str,
    value: float,
    direction: ObjectiveDirection,
    *,
    uncertainty: float = 0.0,
    authority: ObjectiveAuthority = ObjectiveAuthority.MEASURED,
    source_ids: tuple[str, ...] = ("lab:measured-v1",),
    model_release_id: str = "",
    held_out_receipt_sha256: str = "",
    build_d_receipt=None,
) -> ObjectiveEstimate:
    return ObjectiveEstimate(
        name=name,
        value=value,
        standard_uncertainty=uncertainty,
        unit="dimensionless",
        direction=direction,
        authority=authority,
        applicability_scope="selection-domain-v1",
        source_ids=source_ids,
        model_release_id=model_release_id,
        held_out_receipt_sha256=held_out_receipt_sha256,
        build_d_receipt=build_d_receipt,
    )


def _evaluation(candidate_id: str, quality: float, distance: float) -> CandidateEvaluation:
    return CandidateEvaluation(
        candidate_id=candidate_id,
        objectives=(
            _estimate("quality", quality, ObjectiveDirection.MAXIMIZE, uncertainty=0.05),
            _estimate(
                "target_profile_distance",
                distance,
                ObjectiveDirection.MINIMIZE,
                uncertainty=0.02,
            ),
        ),
        acquisition_estimates=(
            _estimate(
                "expected_information_gain",
                quality,
                ObjectiveDirection.MAXIMIZE,
                uncertainty=0.05,
                authority=ObjectiveAuthority.CALIBRATED_HELD_OUT,
                source_ids=("model:information-v1",),
                model_release_id="information-model@sha256:" + HASH_A,
                held_out_receipt_sha256=HASH_B,
            ),
            _estimate(
                "expected_improvement",
                max(0.0, 1.0 - distance),
                ObjectiveDirection.MAXIMIZE,
                uncertainty=0.02,
                authority=ObjectiveAuthority.CALIBRATED_HELD_OUT,
                source_ids=("model:improvement-v1",),
                model_release_id="improvement-model@sha256:" + HASH_A,
                held_out_receipt_sha256=HASH_B,
            ),
            _estimate(
                "experimental_cost",
                distance * 10.0 + 1.0,
                ObjectiveDirection.MINIMIZE,
                authority=ObjectiveAuthority.COMPUTED_RESOURCE,
                source_ids=("engine.optimization:stock-cost-v1",),
            ),
        ),
    )


def _policy(max_new: int = 2) -> AcquisitionPolicy:
    return AcquisitionPolicy(
        policy_id="c10-acquisition-v1",
        version="1.0.0",
        terms=(
            AcquisitionTerm(
                "expected_information_gain",
                ObjectiveDirection.MAXIMIZE,
                0.0,
                1.0,
                3.0,
            ),
            AcquisitionTerm(
                "expected_improvement",
                ObjectiveDirection.MAXIMIZE,
                0.0,
                1.0,
                2.0,
            ),
            AcquisitionTerm(
                "experimental_cost",
                ObjectiveDirection.MINIMIZE,
                0.0,
                20.0,
                1.0,
            ),
        ),
        maximum_new_candidates=max_new,
    )


def _stop_policy() -> StopPolicy:
    return StopPolicy(
        policy_id="c10-stop-v1",
        minimum_expected_information_gain=0.05,
        minimum_expected_improvement=0.05,
        budget_limit=100.0,
        maximum_protected_attribute_risk=0.5,
    )


def _campaign(**changes: Any) -> CampaignState:
    values: dict[str, Any] = {
        "spent_budget": 0.0,
        "protected_attribute_risk": 0.0,
        "unavailable_data_dominates": False,
        "unavailable_data_evidence_sha256": "",
        "sensory_plateau": False,
        "sensory_plateau_evidence_sha256": "",
    }
    values.update(changes)
    return CampaignState(**values)


def _selection_fixture():
    domain = _domain()
    control = _candidate(domain, "control", 2.0, role=CandidateRole.CONTROL)
    replicate = _candidate(
        domain,
        "control-replicate",
        2.0,
        role=CandidateRole.REPLICATE,
        replicate_of="control",
    )
    best_quality = _candidate(domain, "candidate-a", 3.0, role=CandidateRole.SCREENING)
    best_distance = _candidate(domain, "candidate-b", 1.0, role=CandidateRole.SCREENING)
    dominated = _candidate(domain, "candidate-c", 2.0, role=CandidateRole.SCREENING)
    evaluations = (
        _evaluation("candidate-a", quality=0.9, distance=0.4),
        _evaluation("candidate-b", quality=0.6, distance=0.1),
        _evaluation("candidate-c", quality=0.5, distance=0.5),
    )
    return domain, (control, replicate, best_quality, best_distance, dominated), evaluations


def test_c9_optimizer_authority_inventory_has_exact_current_counts() -> None:
    counts: dict[C10Use, int] = {}
    for record in C9_LEGACY_SURFACES:
        counts[record.c10_use] = counts.get(record.c10_use, 0) + 1

    assert len(C9_LEGACY_SURFACES) == 19
    assert counts == {
        C10Use.CAPABILITY_BOUNDARY_ONLY: 2,
        C10Use.CALIBRATED_MODEL_REQUIRED: 1,
        C10Use.FORBIDDEN_NUMERIC_AUTHORITY: 15,
        C10Use.ABSTENTION_ONLY: 1,
    }


@pytest.mark.parametrize(
    "surface_id",
    [
        record.surface_id
        for record in C9_LEGACY_SURFACES
        if record.c10_use is not C10Use.CALIBRATED_MODEL_REQUIRED
    ],
)
def test_c9_noncalibratable_legacy_surfaces_cannot_supply_numeric_objectives(
    surface_id: str,
) -> None:
    estimate = _estimate(
        "legacy-number",
        0.5,
        ObjectiveDirection.MAXIMIZE,
        source_ids=(surface_id,),
    )

    assessment = assess_objective_authority(estimate)

    assert assessment.accepted is False
    assert assessment.reason_codes


def test_c0_pm032_requires_calibrated_release_and_held_out_receipt() -> None:
    uncalibrated = _estimate(
        "arrhenius-rate",
        0.5,
        ObjectiveDirection.MINIMIZE,
        source_ids=("C0-PM-032",),
    )
    calibrated = replace(
        uncalibrated,
        authority=ObjectiveAuthority.CALIBRATED_HELD_OUT,
        model_release_id="aging-model@sha256:" + HASH_A,
        held_out_receipt_sha256=HASH_B,
    )

    assert assess_objective_authority(uncalibrated).accepted is False
    assert assess_objective_authority(calibrated).accepted is True


@pytest.mark.parametrize("outcome", list(UnsupportedOutcome))
def test_build_d_outcomes_are_withheld_without_exact_validation_receipt(
    outcome: UnsupportedOutcome,
) -> None:
    estimate = _estimate(
        outcome.value,
        0.5,
        ObjectiveDirection.MAXIMIZE,
        source_ids=("model:unsupported-outcome",),
    )

    assessment = assess_objective_authority(estimate)

    assert assessment.accepted is False
    assert "BUILD_D_RECEIPT_REQUIRED" in assessment.reason_codes


@pytest.mark.parametrize(
    "field_change",
    [
        {"standard_uncertainty": -0.1},
        {"unit": ""},
        {"applicability_scope": ""},
        {"source_ids": ()},
    ],
)
def test_objective_requires_visible_uncertainty_unit_scope_and_source(
    field_change: dict,
) -> None:
    base = _estimate("quality", 0.5, ObjectiveDirection.MAXIMIZE)
    with pytest.raises(C10ContractError):
        replace(base, **field_change)


def test_selection_filters_hard_gates_then_pareto_then_explicit_utility(monkeypatch) -> None:
    domain, candidates, evaluations = _selection_fixture()

    proposal = select_experiments(
        domain=domain,
        candidates=candidates,
        evaluations=evaluations,
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=_campaign(),
    )

    assert proposal.status is SelectionStatus.PROPOSED
    assert proposal.execution_authorized is False
    assert proposal.pareto_candidate_ids == ("candidate-a", "candidate-b")
    assert proposal.selected_candidate_ids[:2] == ("control", "control-replicate")
    assert set(proposal.selected_candidate_ids[2:]) == {"candidate-a", "candidate-b"}
    assert {(item.candidate_id, item.reason_codes) for item in proposal.rejections} == {
        ("candidate-c", ("PARETO_DOMINATED",))
    }
    utility_by_id = {item.candidate_id: item for item in proposal.utilities}
    assert set(utility_by_id) == {"candidate-a", "candidate-b"}
    for utility in utility_by_id.values():
        assert {item.name for item in utility.contributions} == {
            "expected_information_gain",
            "expected_improvement",
            "experimental_cost",
        }
        assert utility.score == pytest.approx(
            sum(item.weighted_contribution for item in utility.contributions)
            / sum(item.weight for item in utility.contributions)
        )


def test_infeasible_candidates_never_reach_acquisition_scoring(monkeypatch) -> None:
    import engine.optimization.selection as selection_module

    domain = _domain()
    bad = _candidate(
        domain,
        "bad",
        3.0,
        role=CandidateRole.SCREENING,
        gate_status=GateStatus.FAIL,
    )

    def explode(*args, **kwargs):
        raise AssertionError("acquisition scoring was called")

    monkeypatch.setattr(selection_module, "score_candidate_utility", explode)
    proposal = select_experiments(
        domain=domain,
        candidates=(bad,),
        evaluations=(_evaluation("bad", 0.9, 0.1),),
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=_campaign(),
    )

    assert proposal.status is SelectionStatus.STOPPED
    assert StopReason.NO_FEASIBLE_CANDIDATE in proposal.stop_reasons


def test_selection_blocks_missing_control_or_exact_replicate() -> None:
    domain, candidates, evaluations = _selection_fixture()
    without_control = tuple(item for item in candidates if item.role is not CandidateRole.CONTROL)
    mismatched_replicate = replace(
        candidates[1],
        doses=(
            CandidateDose("stock-a", 1.0, "formula"),
            CandidateDose("stock-b", 3.0, "formula"),
        ),
        gate_receipts=(),
    )
    mismatched_replicate = _candidate(
        domain,
        mismatched_replicate.candidate_id,
        1.0,
        role=CandidateRole.REPLICATE,
        replicate_of="control",
    )

    missing = select_experiments(
        domain=domain,
        candidates=without_control,
        evaluations=evaluations,
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=_campaign(),
    )
    mismatched = select_experiments(
        domain=domain,
        candidates=(candidates[0], mismatched_replicate, *candidates[2:]),
        evaluations=evaluations,
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=_campaign(),
    )

    assert missing.status is SelectionStatus.BLOCKED
    assert "MISSING_CONTROL" in missing.blocker_codes
    assert mismatched.status is SelectionStatus.BLOCKED
    assert "REPLICATE_COMPOSITION_MISMATCH" in mismatched.blocker_codes


@pytest.mark.parametrize(
    ("evaluations", "campaign", "expected_reason"),
    [
        (
            (
                _evaluation("candidate-a", 0.01, 0.99),
                _evaluation("candidate-b", 0.01, 0.99),
                _evaluation("candidate-c", 0.01, 0.99),
            ),
            _campaign(),
            StopReason.INFORMATION_GAIN_BELOW_THRESHOLD,
        ),
        (None, _campaign(spent_budget=100.0), StopReason.BUDGET_EXHAUSTED),
        (
            None,
            _campaign(
                unavailable_data_dominates=True,
                unavailable_data_evidence_sha256=HASH_A,
            ),
            StopReason.UNAVAILABLE_DATA_DOMINATES,
        ),
        (
            None,
            _campaign(protected_attribute_risk=0.6),
            StopReason.PROTECTED_ATTRIBUTE_RISK,
        ),
        (
            None,
            _campaign(
                sensory_plateau=True,
                sensory_plateau_evidence_sha256=HASH_A,
            ),
            StopReason.SENSORY_PLATEAU,
        ),
    ],
)
def test_preregistered_stop_conditions_return_no_new_experiments(
    evaluations,
    campaign: CampaignState,
    expected_reason: StopReason,
) -> None:
    domain, candidates, default_evaluations = _selection_fixture()
    proposal = select_experiments(
        domain=domain,
        candidates=candidates,
        evaluations=evaluations or default_evaluations,
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=campaign,
    )

    assert proposal.status is SelectionStatus.STOPPED
    assert proposal.selected_candidate_ids == ()
    assert expected_reason in proposal.stop_reasons


def test_stop_evidence_flags_require_bound_evidence_hashes() -> None:
    with pytest.raises(C10ContractError):
        _campaign(unavailable_data_dominates=True)
    with pytest.raises(C10ContractError):
        _campaign(sensory_plateau=True)


def test_proposal_requires_exact_hash_pass_human_review_before_execution() -> None:
    domain, candidates, evaluations = _selection_fixture()
    proposal = select_experiments(
        domain=domain,
        candidates=candidates,
        evaluations=evaluations,
        acquisition_policy=_policy(),
        stop_policy=_stop_policy(),
        campaign_state=_campaign(),
    )
    wrong = HumanReviewReceipt(
        status=GateStatus.PASS,
        subject_sha256=HASH_A,
        evidence_sha256=HASH_B,
        reviewer_role="qualified human perfumer",
    )
    correct = replace(wrong, subject_sha256=proposal.content_sha256)

    with pytest.raises(C10ContractError):
        authorize_proposal(proposal, wrong)
    authorized = authorize_proposal(proposal, correct)

    assert authorized.execution_authorized is True
    assert authorized.proposal_sha256 == proposal.content_sha256
    assert authorized.selected_candidate_ids == proposal.selected_candidate_ids


def test_selection_serialization_is_stable_across_python_hash_seeds() -> None:
    script = r"""
import json
from dataclasses import replace
from engine.optimization import *

domain = MixtureDomain(
    domain_id="seed-domain",
    total_active_mass_mg=NumericRange(2, 2),
    stocks=(
        StockDefinition("a", "a", "f", 1, (), 10, 1, 1, 1),
        StockDefinition("b", "b", "g", 1, (), 10, 1, 1, 1),
    ),
    required_gate_ids=("safety", "action_permission", "applicability"),
)
def candidate(identifier, role, a, replicate_of=None):
    bare = MixtureCandidate(identifier, DesignStage.SCREENING, role,
        (CandidateDose("a", a, "m"), CandidateDose("b", 2-a, "m")), (), replicate_of)
    h = candidate_formula_state_sha256(domain, bare)
    gates = tuple(GateReceipt(g, GateStatus.PASS, h, "e"*64, "v1") for g in domain.required_gate_ids)
    return replace(bare, gate_receipts=gates)
def estimate(name, value, direction, authority=ObjectiveAuthority.MEASURED):
    kwargs = {}
    if authority is ObjectiveAuthority.CALIBRATED_HELD_OUT:
        kwargs = {"model_release_id":"m@sha256:"+"a"*64,"held_out_receipt_sha256":"b"*64}
    return ObjectiveEstimate(name, value, 0, "u", direction, authority, "seed-domain", ("source",), **kwargs)
candidates=(candidate("control", CandidateRole.CONTROL, 1), candidate("rep", CandidateRole.REPLICATE, 1, "control"), candidate("x", CandidateRole.SCREENING, 2))
evaluations=(CandidateEvaluation("x", (estimate("quality", .8, ObjectiveDirection.MAXIMIZE),), (estimate("expected_information_gain", .8, ObjectiveDirection.MAXIMIZE, ObjectiveAuthority.CALIBRATED_HELD_OUT),)),)
policy=AcquisitionPolicy("p","1",(AcquisitionTerm("expected_information_gain",ObjectiveDirection.MAXIMIZE,0,1,1),),1)
stop=StopPolicy("s",.01,.01,10,.5)
state=CampaignState(0,0,False,"",False,"")
proposal=select_experiments(domain=domain,candidates=candidates,evaluations=evaluations,acquisition_policy=policy,stop_policy=stop,campaign_state=state)
print(json.dumps(proposal.as_dict(), sort_keys=True, separators=(",",":")))
"""
    outputs = []
    for seed in (2, 7):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        assert completed.stderr == ""
        outputs.append(json.loads(completed.stdout))
    assert outputs[0] == outputs[1]
