from __future__ import annotations

import hashlib
from dataclasses import replace

import pytest

from engine.sensory.panel_contract import (
    BindingState,
    C0ExitDecision,
    GateKind,
    build_c0_construction_lexicon,
    build_c0_protocol_draft,
    evaluate_c0_exit,
)
from engine.sensory.prepilot import (
    ManifestReviewState,
    PrepilotDecision,
    PrepilotManifest,
    apply_prepilot_bundle,
    build_c0_prepilot_bundle_draft,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _complete_payloads(lexicon_sha256: str) -> dict[str, dict[str, object]]:
    attribute_modes = {
        "airiness": "graded_sample_set",
        "separability": "graded_sample_set",
        "density": "graded_sample_set",
        "coherence": "graded_sample_set",
        "target_fidelity": "target_reference_task",
        "contrast": "graded_sample_set",
        "emergence": "component_mixture_comparison",
        "recognition": "blind_target_choice",
    }
    attribute_anchors: dict[str, dict[str, object]] = {
        attribute_id: {
            "anchor_mode": mode,
            "training_reference_permitted": True,
            "low_reference_receipt_sha256": _sha(f"{attribute_id}:low"),
            "mid_reference_receipt_sha256": _sha(f"{attribute_id}:mid"),
            "high_reference_receipt_sha256": _sha(f"{attribute_id}:high"),
        }
        for attribute_id, mode in attribute_modes.items()
    }
    attribute_anchors["pleasantness"] = {
        "anchor_mode": "verbal_scale_only",
        "training_reference_permitted": False,
        "low_reference_receipt_sha256": None,
        "mid_reference_receipt_sha256": None,
        "high_reference_receipt_sha256": None,
    }
    return {
        "sample_manifest": {
            "blind_code_scheme": {
                "format": "uppercase_alphanumeric",
                "length": 6,
            },
            "custodian_role": "independent_code_custodian",
            "sample_identity_map_receipt_sha256": _sha("sample-map"),
            "allocation_concealment": "panel_and_analyst_blinded",
            "code_collision_check": "exhaustive_unique_check",
        },
        "preparation_dose_ppm_manifest": {
            "matrix_id": "ethanol_matrix_lot_bound",
            "concentrate_ppm": 150000,
            "active_application_mass_mg": 1.5,
            "substrate": "standardized_mouillette",
            "carrier_id": "ethanol_lot_bound",
            "preparation_sop_sha256": _sha("preparation-sop"),
            "dose_tolerance_fraction": 0.05,
        },
        "formula_oav_manifest": {
            "formula_manifest_sha256": _sha("formula-manifest"),
            "odt_dataset_sha256": _sha("odt-dataset"),
            "oav_report_sha256": _sha("oav-report"),
            "natural_mixture_oav_policy": "applied_composite_oav",
            "time_windows_seconds": [0, 300, 1800],
            "data_quality_review_receipt_sha256": _sha("oav-quality-review"),
        },
        "randomization_manifest": {
            "sequence_method": "blocked_counterbalanced",
            "seed_commitment_sha256": _sha("seed-commitment"),
            "allocation_receipt_sha256": _sha("allocation"),
            "carryover_rule": "minimum_rest_and_order_model",
            "blinding_roles": ["panelist", "session_operator", "analyst"],
        },
        "anchor_reference_manifest": {
            "lexicon_sha256": lexicon_sha256,
            "attribute_anchors": attribute_anchors,
            "reference_preparation_sop_sha256": _sha("anchor-preparation"),
        },
        "participant_plan": {
            "expertise_strata": [
                "trained_descriptive",
                "perfumer_expert",
                "untrained",
            ],
            "eligibility_rules_sha256": _sha("eligibility"),
            "olfactory_screening_plan_sha256": _sha("screening"),
            "specific_anosmia_policy": "task_relevant_and_receipt_only",
            "training_plan_sha256": _sha("training"),
            "repeat_plan": {"repeats_per_sample": 2},
            "attrition_rule": "preregistered_no_outcome_based_exclusion",
            "privacy_separation_receipt_sha256": _sha("privacy-separation"),
            "qualification_receipt_schema_sha256": _sha("qualification-schema"),
        },
        "environment_timing_manifest": {
            "room_sop_sha256": _sha("room-sop"),
            "temperature_c_range": [21.0, 23.0],
            "relative_humidity_pct_range": [45.0, 55.0],
            "ventilation_rule": "validated_between_sample_clearance",
            "session_duration_limit_minutes": 60,
            "sniff_timepoints_seconds": [0, 300, 1800],
            "rest_interval_seconds": 90,
            "confounder_rules_sha256": _sha("confounders"),
        },
        "analysis_plan": {
            "estimands": [
                "attribute_specific_product_effect",
                "expertise_stratum_interaction",
            ],
            "missing_data_rule": "preregistered_no_single_imputation",
            "multiplicity_rule": "attribute_family_controlled",
            "uncertainty_method": "interval_estimates_preserved",
            "gate_specification_receipts": {
                kind.value: _sha(f"gate:{kind.value}") for kind in GateKind
            },
            "pilot_confirmatory_separation": True,
            "analysis_implementation_receipt_sha256": _sha(
                "analysis-implementation"
            ),
        },
        "ethics_privacy_safety_review": {
            "applicability_determination_receipt_sha256": _sha("applicability"),
            "consent_plan_sha256": _sha("consent-plan"),
            "privacy_plan_sha256": _sha("privacy-plan"),
            "exposure_safety_review_sha256": _sha("exposure-safety"),
            "withdrawal_process": "voluntary_without_penalty",
            "adverse_event_process": "stop_exposure_and_record_receipt",
            "review_jurisdiction": "exact_site_required_before_collection",
        },
    }


def _bindable_bundle():
    lexicon = build_c0_construction_lexicon()
    protocol = build_c0_protocol_draft(lexicon)
    draft = build_c0_prepilot_bundle_draft(lexicon, protocol)
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    manifests = tuple(
        PrepilotManifest.from_payload(
            binding_id=item.binding_id,
            schema_version=item.schema_version,
            payload=payloads[item.binding_id],
            unresolved_items=(),
            review_state=ManifestReviewState.LOCK_CANDIDATE,
            review_receipt_sha256=_sha(f"review:{item.binding_id}"),
        )
        for item in draft.manifests
    )
    return lexicon, protocol, replace(draft, manifests=manifests)


def test_default_prepilot_bundle_is_deterministic_hold() -> None:
    lexicon = build_c0_construction_lexicon()
    protocol = build_c0_protocol_draft(lexicon)
    first = build_c0_prepilot_bundle_draft(lexicon, protocol)
    second = build_c0_prepilot_bundle_draft(lexicon, protocol)

    report = first.readiness()

    assert first.bundle_sha256 == second.bundle_sha256
    assert tuple(item.binding_id for item in first.manifests) == tuple(
        item.binding_id for item in protocol.bindings
    )
    assert report.decision is PrepilotDecision.HOLD
    assert report.bindable_for_protocol is False
    assert report.study_authorized is False
    assert report.release_authority is False
    assert report.model_calibration_authority is False
    assert report.held_manifests == tuple(item.binding_id for item in first.manifests)


def test_draft_manifest_cannot_be_promoted_to_evidence_binding() -> None:
    lexicon = build_c0_construction_lexicon()
    protocol = build_c0_protocol_draft(lexicon)
    bundle = build_c0_prepilot_bundle_draft(lexicon, protocol)

    manifest = bundle.manifests[0]
    assert manifest.missing_required_fields
    assert manifest.is_bindable is False
    with pytest.raises(ValueError, match="not bindable"):
        manifest.to_evidence_binding()


def test_payload_is_copied_into_immutable_canonical_json() -> None:
    payload: dict[str, object] = {
        "blind_code_scheme": {"format": "uppercase_alphanumeric", "length": 6},
        "custodian_role": "custodian",
        "sample_identity_map_receipt_sha256": _sha("map"),
        "allocation_concealment": "concealed",
        "code_collision_check": "checked",
    }
    manifest = PrepilotManifest.from_payload(
        binding_id="sample_manifest",
        schema_version="test.v1",
        payload=payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("review"),
    )
    original_hash = manifest.manifest_sha256

    payload["custodian_role"] = "mutated-after-construction"

    assert manifest.payload["custodian_role"] == "custodian"
    assert manifest.manifest_sha256 == original_hash


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "participant_name",
        "fullName",
        "email",
        "phone",
        "date_of_birth",
        "medical_record",
        "participants",
    ],
)
def test_manifest_rejects_raw_participant_data(forbidden_key: str) -> None:
    with pytest.raises(ValueError, match="raw participant data"):
        PrepilotManifest.from_payload(
            binding_id="participant_plan",
            schema_version="test.v1",
            payload={forbidden_key: "must-not-be-stored"},
            unresolved_items=("fixture",),
            review_state=ManifestReviewState.DRAFT,
            review_receipt_sha256=None,
        )


def test_lock_candidate_requires_hashed_review_receipt() -> None:
    with pytest.raises(ValueError, match="review receipt"):
        PrepilotManifest.from_payload(
            binding_id="sample_manifest",
            schema_version="test.v1",
            payload={},
            unresolved_items=("still incomplete",),
            review_state=ManifestReviewState.LOCK_CANDIDATE,
            review_receipt_sha256=None,
        )


def test_complete_bundle_emits_exact_ordered_evidence_bindings() -> None:
    _, _, bundle = _bindable_bundle()

    report = bundle.readiness()
    bindings = bundle.evidence_bindings()

    assert report.decision is PrepilotDecision.BINDABLE
    assert report.bindable_for_protocol is True
    assert report.blockers == ()
    assert tuple(item.binding_id for item in bindings) == tuple(
        item.binding_id for item in bundle.manifests
    )
    assert all(item.state is BindingState.BOUND for item in bindings)
    assert tuple(item.sha256 for item in bindings) == tuple(
        item.manifest_sha256 for item in bundle.manifests
    )


def test_applying_bundle_binds_evidence_but_cannot_create_c0_go() -> None:
    lexicon, protocol, bundle = _bindable_bundle()

    bound_protocol = apply_prepilot_bundle(protocol, bundle)
    exit_report = evaluate_c0_exit(bound_protocol, lexicon, ())

    assert all(item.state is BindingState.BOUND for item in bound_protocol.bindings)
    assert bound_protocol.timepoints_seconds == (0, 300, 1800)
    assert bound_protocol.repeat_count == 2
    assert bound_protocol.protocol_locked is False
    assert bound_protocol.study_authorized is False
    assert bound_protocol.release_authority is False
    assert bound_protocol.model_calibration_authority is False
    assert exit_report.decision is C0ExitDecision.HOLD
    assert exit_report.c0_exit_satisfied is False


def test_bundle_rejects_wrong_base_protocol_identity() -> None:
    _, protocol, bundle = _bindable_bundle()
    wrong_protocol = replace(protocol, version=protocol.version + 1)

    with pytest.raises(ValueError, match="base protocol hash"):
        apply_prepilot_bundle(wrong_protocol, bundle)


def test_pleasantness_cannot_use_training_reference_samples() -> None:
    lexicon, protocol, bundle = _bindable_bundle()
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    anchor_payload = payloads["anchor_reference_manifest"]
    attribute_anchors = anchor_payload["attribute_anchors"]
    assert isinstance(attribute_anchors, dict)
    pleasantness = attribute_anchors["pleasantness"]
    assert isinstance(pleasantness, dict)
    pleasantness["training_reference_permitted"] = True
    bad_anchor = PrepilotManifest.from_payload(
        binding_id="anchor_reference_manifest",
        schema_version="test.v1",
        payload=anchor_payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("anchor-review"),
    )
    manifests = tuple(
        bad_anchor if item.binding_id == "anchor_reference_manifest" else item
        for item in bundle.manifests
    )
    bad_bundle = replace(bundle, manifests=manifests)

    report = bad_bundle.readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("pleasantness" in item for item in report.blockers)


def test_anchor_manifest_must_cover_every_lexicon_attribute() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    anchor_payload = payloads["anchor_reference_manifest"]
    attribute_anchors = anchor_payload["attribute_anchors"]
    assert isinstance(attribute_anchors, dict)
    del attribute_anchors["emergence"]
    incomplete = PrepilotManifest.from_payload(
        binding_id="anchor_reference_manifest",
        schema_version="test.v1",
        payload=anchor_payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("anchor-review"),
    )
    manifests = tuple(
        incomplete if item.binding_id == "anchor_reference_manifest" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("every lexicon attribute" in item for item in report.blockers)


def test_invalid_composite_oav_policy_holds_formula_manifest() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    formula_payload = payloads["formula_oav_manifest"]
    formula_payload["natural_mixture_oav_policy"] = "monomolecular_only"
    invalid = PrepilotManifest.from_payload(
        binding_id="formula_oav_manifest",
        schema_version="test.v1",
        payload=formula_payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("oav-review"),
    )
    manifests = tuple(
        invalid if item.binding_id == "formula_oav_manifest" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("composite OAV" in item for item in report.blockers)


def test_construction_anchor_mode_must_match_the_frozen_strategy() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    anchor_payload = payloads["anchor_reference_manifest"]
    attribute_anchors = anchor_payload["attribute_anchors"]
    assert isinstance(attribute_anchors, dict)
    airiness = attribute_anchors["airiness"]
    assert isinstance(airiness, dict)
    airiness["anchor_mode"] = "unreviewed_mode"
    invalid = PrepilotManifest.from_payload(
        binding_id="anchor_reference_manifest",
        schema_version="test.v1",
        payload=anchor_payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("anchor-review"),
    )
    manifests = tuple(
        invalid if item.binding_id == "anchor_reference_manifest" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("frozen reference mode" in item for item in report.blockers)


def test_participant_strata_validation_fails_closed_on_non_strings() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payload = _complete_payloads(lexicon.lexicon_sha256)["participant_plan"]
    payload["expertise_strata"] = [{"raw": "participant-data"}]
    invalid = PrepilotManifest.from_payload(
        binding_id="participant_plan",
        schema_version="test.v1",
        payload=payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("participant-review"),
    )
    manifests = tuple(
        invalid if item.binding_id == "participant_plan" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("unique string list" in item for item in report.blockers)


def test_gate_specification_receipts_must_be_sha256_digests() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payload = _complete_payloads(lexicon.lexicon_sha256)["analysis_plan"]
    receipts = payload["gate_specification_receipts"]
    assert isinstance(receipts, dict)
    receipts[GateKind.DISCRIMINATION.value] = "not-a-digest"
    invalid = PrepilotManifest.from_payload(
        binding_id="analysis_plan",
        schema_version="test.v1",
        payload=payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("analysis-review"),
    )
    manifests = tuple(
        invalid if item.binding_id == "analysis_plan" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("gate specification receipt" in item for item in report.blockers)


def test_oav_windows_must_cover_every_sensory_sniff_timepoint() -> None:
    lexicon, _, bundle = _bindable_bundle()
    payload = _complete_payloads(lexicon.lexicon_sha256)["formula_oav_manifest"]
    payload["time_windows_seconds"] = [0, 300]
    invalid = PrepilotManifest.from_payload(
        binding_id="formula_oav_manifest",
        schema_version="test.v1",
        payload=payload,
        unresolved_items=(),
        review_state=ManifestReviewState.LOCK_CANDIDATE,
        review_receipt_sha256=_sha("oav-review"),
    )
    manifests = tuple(
        invalid if item.binding_id == "formula_oav_manifest" else item
        for item in bundle.manifests
    )

    report = replace(bundle, manifests=manifests).readiness()

    assert report.decision is PrepilotDecision.HOLD
    assert any("every sensory sniff timepoint" in item for item in report.blockers)
