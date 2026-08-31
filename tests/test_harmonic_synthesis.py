from __future__ import annotations

import pytest

from engine.material_capability_atlas import build_material_capability_atlas
from engine.perception.harmonic_synthesis import (
    HarmonicAssertionKind,
    HarmonicAssertionV1,
    HarmonicEvidenceState,
    HarmonicMaterialIntentV1,
    HarmonicMaterialState,
    HarmonicModuleReportV1,
    HarmonicModuleState,
    HarmonicRelationV1,
    HarmonicSynthesisRequestV1,
    HarmonicSynthesisState,
    HarmonicTargetContractV1,
    synthesize_harmonically,
)


def _target() -> HarmonicTargetContractV1:
    return HarmonicTargetContractV1(
        target_id="CYP-02",
        target_identity=(
            "a polished Cypress EO perfume whose French cypress remains the sole named "
            "subject while a floral heart reveals its beauty"
        ),
        primary_subject="Cypress EO",
        supporting_subjects=("Magnolia-Orris dual-register heart",),
        positive_invariants=(
            "cypress remains identifiable from opening through drydown",
            "floral luminosity relieves the aromatic-green severity",
            "rooted depth does not turn into a generic woody-amber wall",
        ),
        forbidden_drift=(
            "photorealistic cypress tree",
            "functional cleaner",
            "generic iris perfume",
            "opaque woody-amber takeover",
        ),
        ideal_formula_ref="target://cyp-02/ideal/v1",
        current_inventory_build_ref="inventory://cyp-02/current/v1",
        claim_ceiling="COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY",
    )


def _assertion(
    module_id: str,
    *,
    claim_key: str,
    claim_value: str,
    scope_key: str = "target:CYP-02",
    evidence_state: HarmonicEvidenceState = HarmonicEvidenceState.COMPUTATIONAL_DESIGN,
) -> HarmonicAssertionV1:
    return HarmonicAssertionV1(
        assertion_id=f"{module_id}:{claim_key}:{claim_value}",
        module_id=module_id,
        scope_key=scope_key,
        claim_key=claim_key,
        claim_value=claim_value,
        kind=HarmonicAssertionKind.REQUIREMENT,
        evidence_state=evidence_state,
        rationale="target-linked module statement with no scalar beauty authority",
        source_refs=(f"module://{module_id}/v1",),
    )


def _report(
    module_id: str,
    *,
    state: HarmonicModuleState = HarmonicModuleState.READY,
    assertions: tuple[HarmonicAssertionV1, ...] = (),
    blockers: tuple[str, ...] = (),
) -> HarmonicModuleReportV1:
    return HarmonicModuleReportV1(
        module_id=module_id,
        module_sha256=(module_id.encode("utf-8").hex() + "0" * 64)[:64],
        state=state,
        assertions=assertions,
        blockers=blockers,
        next_action="run the exact controlled comparison named by this module",
        authority_flags=(),
    )


def _reports() -> tuple[HarmonicModuleReportV1, ...]:
    return (
        _report(
            "material-capability-atlas",
            assertions=(
                _assertion(
                    "material-capability-atlas",
                    claim_key="material.Cypress EO.current_state",
                    claim_value="OWNED_EXECUTABLE",
                    evidence_state=HarmonicEvidenceState.CURRENT_INVENTORY,
                ),
            ),
        ),
        _report(
            "family-depth",
            assertions=(
                _assertion(
                    "family-depth",
                    claim_key="heart.identity",
                    claim_value="magnolia-orris-dual-register",
                ),
            ),
        ),
        _report(
            "architectural-delta",
            assertions=(
                _assertion(
                    "architectural-delta",
                    claim_key="heart.identity",
                    claim_value="magnolia-orris-dual-register",
                ),
            ),
        ),
        _report(
            "temporal-ledger",
            state=HarmonicModuleState.WITHHELD,
            blockers=("NO_BLINDED_TEMPORAL_OBSERVATIONS",),
        ),
        _report(
            "hedonic-preference",
            state=HarmonicModuleState.WITHHELD,
            blockers=("NO_SCOPED_BLINDED_PREFERENCE_DATA",),
        ),
    )


def _relation() -> HarmonicRelationV1:
    return HarmonicRelationV1(
        relation_id="rel_cypress_flower_relief",
        source_node="role.cypress_subject",
        target_node="role.magnolia_orris_heart",
        relation_kind="TENSION_RELIEF",
        target_link=(
            "the floral heart rounds and illuminates Cypress EO without replacing its identity"
        ),
        omission_loss="cypress remains severe, linear, and less inviting",
        failure_mode="the heart becomes a separate generic iris perfume",
        temporal_windows=("OPENING", "HEART", "LATE_HEART", "DRYDOWN"),
        probe_ref="comparison://cyp-02/heart-frontier/v1",
        module_ids=("family-depth", "architectural-delta"),
    )


def _request(
    *,
    reports: tuple[HarmonicModuleReportV1, ...] | None = None,
    material_intents: tuple[HarmonicMaterialIntentV1, ...] | None = None,
) -> HarmonicSynthesisRequestV1:
    return HarmonicSynthesisRequestV1(
        target=_target(),
        required_module_ids=(
            "material-capability-atlas",
            "family-depth",
            "architectural-delta",
            "temporal-ledger",
            "hedonic-preference",
        ),
        design_gate_module_ids=(
            "material-capability-atlas",
            "family-depth",
            "architectural-delta",
        ),
        module_reports=reports or _reports(),
        relations=(_relation(),),
        material_intents=material_intents
        or (
            HarmonicMaterialIntentV1(
                intent_id="use_cypress_subject",
                material_name="Cypress EO",
                role_id="role.cypress_subject",
                target_function="sole named subject and aromatic-green vertical spine",
                ideal_required=True,
                current_build_intent=True,
                quantitative_required=True,
                omission_loss="the perfume loses its named subject",
                failure_mode="overdose becomes harsh, terpene-heavy, or cleaning-like",
            ),
        ),
        no_change_reason="all target functions are already closed without another relation",
    )


def test_withheld_temporal_and_preference_evidence_caps_claims_but_not_design() -> None:
    atlas = build_material_capability_atlas()

    result = synthesize_harmonically(_request(), atlas=atlas)

    assert result.state is HarmonicSynthesisState.DESIGN_READY
    assert result.structural_blockers == ()
    assert result.empirical_gaps == (
        "hedonic-preference:NO_SCOPED_BLINDED_PREFERENCE_DATA",
        "temporal-ledger:NO_BLINDED_TEMPORAL_OBSERVATIONS",
    )
    assert result.material_dispositions[0].state is HarmonicMaterialState.CURRENT_READY
    assert result.claim_ceiling == "COMPUTATIONAL_EXPERIMENT_DESIGN_ONLY"


def test_repeated_module_claims_are_deduplicated_not_counted_as_votes() -> None:
    atlas = build_material_capability_atlas()
    reports = (
        *_reports(),
        _report(
            "extra-review-one",
            assertions=(
                _assertion(
                    "extra-review-one",
                    claim_key="heart.identity",
                    claim_value="magnolia-orris-dual-register",
                ),
            ),
        ),
        _report(
            "extra-review-two",
            assertions=(
                _assertion(
                    "extra-review-two",
                    claim_key="heart.identity",
                    claim_value="magnolia-orris-dual-register",
                ),
            ),
        ),
    )
    request = _request(reports=reports)
    request = HarmonicSynthesisRequestV1(
        target=request.target,
        required_module_ids=(*request.required_module_ids, "extra-review-one", "extra-review-two"),
        design_gate_module_ids=request.design_gate_module_ids,
        module_reports=request.module_reports,
        relations=request.relations,
        material_intents=request.material_intents,
        no_change_reason=request.no_change_reason,
    )

    result = synthesize_harmonically(request, atlas=atlas)
    resolved = next(item for item in result.resolved_claims if item.claim_key == "heart.identity")

    assert resolved.claim_value == "magnolia-orris-dual-register"
    assert resolved.supporting_module_ids == (
        "architectural-delta",
        "extra-review-one",
        "extra-review-two",
        "family-depth",
    )
    assert result.vote_counting_used is False


def test_three_repetitions_cannot_outvote_one_incompatible_exact_scope_claim() -> None:
    atlas = build_material_capability_atlas()
    conflicting = _report(
        "independent-critic",
        assertions=(
            _assertion(
                "independent-critic",
                claim_key="heart.identity",
                claim_value="generic-iris-heart",
            ),
        ),
    )
    request = _request(reports=(*_reports(), conflicting))
    request = HarmonicSynthesisRequestV1(
        target=request.target,
        required_module_ids=(*request.required_module_ids, "independent-critic"),
        design_gate_module_ids=request.design_gate_module_ids,
        module_reports=request.module_reports,
        relations=request.relations,
        material_intents=request.material_intents,
        no_change_reason=request.no_change_reason,
    )

    result = synthesize_harmonically(request, atlas=atlas)

    assert result.state is HarmonicSynthesisState.HOLD
    assert result.tensions[0].claim_key == "heart.identity"
    assert result.tensions[0].incompatible_values == (
        "generic-iris-heart",
        "magnolia-orris-dual-register",
    )
    assert result.vote_counting_used is False


def test_inventory_cannot_rewrite_target_but_can_hold_current_build_execution() -> None:
    atlas = build_material_capability_atlas()
    intents = (
        HarmonicMaterialIntentV1(
            intent_id="ideal_ethylene_brassylate",
            material_name="Ethylene Brassylate",
            role_id="role.skin_musk",
            target_function="quiet skin diffusion only if target-linked",
            ideal_required=False,
            current_build_intent=False,
            quantitative_required=False,
            omission_loss="possibly none; zero musk remains valid",
            failure_mode="laundry-soft musk blur",
        ),
        HarmonicMaterialIntentV1(
            intent_id="current_benzyl_salicylate",
            material_name="Benzyl Salicylate",
            role_id="role.floral_fixation",
            target_function="slow floral continuity",
            ideal_required=True,
            current_build_intent=True,
            quantitative_required=True,
            omission_loss="floral heart may shorten",
            failure_mode="heavy salicylate veil",
        ),
    )

    result = synthesize_harmonically(_request(material_intents=intents), atlas=atlas)

    assert result.target.target_identity == _target().target_identity
    assert result.state is HarmonicSynthesisState.HOLD
    assert result.material_dispositions[1].state is HarmonicMaterialState.CURRENT_HOLD
    assert any("Benzyl Salicylate" in item for item in result.structural_blockers)


def test_relation_without_omission_loss_or_probe_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="omission_loss"):
        HarmonicRelationV1(
            relation_id="bad_relation",
            source_node="role.a",
            target_node="role.b",
            relation_kind="BRIDGE",
            target_link="rhetorical bridge only",
            omission_loss="",
            failure_mode="unknown",
            temporal_windows=("HEART",),
            probe_ref="comparison://bad",
            module_ids=("family-depth",),
        )


def test_harmonic_result_never_grants_formula_sensory_or_release_authority() -> None:
    result = synthesize_harmonically(
        _request(),
        atlas=build_material_capability_atlas(),
    )

    for field_name in (
        "formula_mutation_authorized",
        "physical_execution_authorized",
        "compounding_authorized",
        "purchase_authority",
        "sensory_authority",
        "hedonic_authority",
        "similarity_authority",
        "performance_authority",
        "safety_authority",
        "stability_authority",
        "release_authority",
    ):
        assert getattr(result, field_name) is False
