from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from engine.calibration.hashing import canonical_json_bytes, stable_json_hash
from engine.sensory.lab_projection import (
    C0_FULL_ARTIFACT_IDS,
    C0_OPAQUE_EXTERNAL_ARTIFACT_IDS,
    C0ArtifactReceipt,
    C0ExpectedObservationCell,
    C0PackageHoldEnvelope,
    build_package_c0_hold_envelope,
    project_complete_c0_to_lab,
)
from engine.sensory.panel_contract import (
    C0ExitDecision,
    ExpertiseStratum,
    GateDirection,
    GateKind,
    GateOutcome,
    PanelAttributeRating,
    PanelGateSpecification,
    PanelObservation,
    PanelPerformanceResult,
    ParticipantQualificationReceipt,
    StudyPartition,
    build_c0_construction_lexicon,
    build_c0_protocol_draft,
    evaluate_c0_exit,
)
from engine.sensory.prepilot import (
    ManifestReviewState,
    PrepilotManifest,
    apply_prepilot_bundle,
    build_c0_prepilot_bundle_draft,
)


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _package_payload() -> dict[str, object]:
    fixture = Path("tests/fixtures/c0_prepilot_v3_source_20260810.json")
    provenance_path = fixture.with_suffix(".provenance.json")
    raw = fixture.read_bytes()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["copy_policy"] == "EXACT_BYTE_COPY_NO_RECONSTRUCTION"
    assert provenance["preserved_path"] == fixture.as_posix()
    assert provenance["original_byte_size"] == len(raw) == 1773
    assert provenance["original_sha256"] == hashlib.sha256(raw).hexdigest()
    value = json.loads(raw)
    assert isinstance(value, dict)
    return value


def _complete_payloads(lexicon_sha256: str) -> dict[str, dict[str, object]]:
    modes = {
        "airiness": "graded_sample_set",
        "separability": "graded_sample_set",
        "density": "graded_sample_set",
        "coherence": "graded_sample_set",
        "target_fidelity": "target_reference_task",
        "contrast": "graded_sample_set",
        "emergence": "component_mixture_comparison",
        "recognition": "blind_target_choice",
    }
    anchors: dict[str, dict[str, object]] = {
        attribute_id: {
            "anchor_mode": mode,
            "training_reference_permitted": True,
            "low_reference_receipt_sha256": _sha(f"{attribute_id}:low"),
            "mid_reference_receipt_sha256": _sha(f"{attribute_id}:mid"),
            "high_reference_receipt_sha256": _sha(f"{attribute_id}:high"),
        }
        for attribute_id, mode in modes.items()
    }
    anchors["pleasantness"] = {
        "anchor_mode": "verbal_scale_only",
        "training_reference_permitted": False,
        "low_reference_receipt_sha256": None,
        "mid_reference_receipt_sha256": None,
        "high_reference_receipt_sha256": None,
    }
    return {
        "sample_manifest": {
            "blind_code_scheme": {"format": "uppercase_alphanumeric", "length": 6},
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
            "attribute_anchors": anchors,
            "reference_preparation_sop_sha256": _sha("anchor-preparation"),
        },
        "participant_plan": {
            "expertise_strata": ["trained_descriptive", "untrained"],
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
            "analysis_implementation_receipt_sha256": _sha("analysis-implementation"),
        },
        "ethics_privacy_safety_review": {
            "applicability_determination_receipt_sha256": _sha("applicability"),
            "consent_plan_sha256": _sha("consent-plan"),
            "privacy_plan_sha256": _sha("privacy-plan"),
            "exposure_safety_review_sha256": _sha("exposure-safety"),
            "withdrawal_process": "voluntary_without_penalty",
            "adverse_event_process": "stop_exposure_and_record_receipt",
            "review_jurisdiction": "synthetic_persistence_fit_only",
        },
    }


def _synthetic_graph():
    lexicon = build_c0_construction_lexicon()
    draft_protocol = build_c0_protocol_draft(lexicon)
    draft_bundle = build_c0_prepilot_bundle_draft(lexicon, draft_protocol)
    payloads = _complete_payloads(lexicon.lexicon_sha256)
    bundle = replace(
        draft_bundle,
        manifests=tuple(
            PrepilotManifest.from_payload(
                binding_id=item.binding_id,
                schema_version=item.schema_version,
                payload=payloads[item.binding_id],
                unresolved_items=(),
                review_state=ManifestReviewState.LOCK_CANDIDATE,
                review_receipt_sha256=_sha(f"review:{item.binding_id}"),
            )
            for item in draft_bundle.manifests
        ),
    )
    bound_protocol = apply_prepilot_bundle(draft_protocol, bundle)
    gate_specs = tuple(
        PanelGateSpecification.locked(
            gate_id=f"{kind.value}_gate",
            kind=kind,
            metric=f"synthetic_{kind.value}_metric",
            unit="unitless",
            direction=GateDirection.AT_LEAST,
            threshold=Decimal("0.5"),
            success_rule="PASS only at or above the preregistered threshold.",
            failure_rule="FAIL below the preregistered threshold.",
            inconclusive_rule="HOLD when the result is missing or unstable.",
        )
        for kind in GateKind
    )
    protocol = replace(
        bound_protocol,
        panel_gate_specs=gate_specs,
        expertise_strata=(
            ExpertiseStratum.TRAINED_DESCRIPTIVE,
            ExpertiseStratum.UNTRAINED,
        ),
        protocol_locked=True,
    )
    qualifications = (
        ParticipantQualificationReceipt(
            participant_token_sha256=_sha("participant:trained"),
            expertise_stratum=ExpertiseStratum.TRAINED_DESCRIPTIVE,
            protocol_sha256=protocol.protocol_sha256,
            consent_receipt_sha256=_sha("consent:trained"),
            privacy_notice_sha256=_sha("privacy:trained"),
            eligibility_receipt_sha256=_sha("eligibility:trained"),
            olfactory_screening_receipt_sha256=_sha("screening:trained"),
            specific_anosmia_screen_receipt_sha256=_sha("anosmia:trained"),
            training_receipt_sha256=_sha("training:trained"),
        ),
        ParticipantQualificationReceipt(
            participant_token_sha256=_sha("participant:untrained"),
            expertise_stratum=ExpertiseStratum.UNTRAINED,
            protocol_sha256=protocol.protocol_sha256,
            consent_receipt_sha256=_sha("consent:untrained"),
            privacy_notice_sha256=_sha("privacy:untrained"),
            eligibility_receipt_sha256=_sha("eligibility:untrained"),
            olfactory_screening_receipt_sha256=_sha("screening:untrained"),
            specific_anosmia_screen_receipt_sha256=None,
            training_receipt_sha256=None,
        ),
    )
    expected: list[C0ExpectedObservationCell] = []
    observations: list[PanelObservation] = []
    ratings = tuple(
        PanelAttributeRating(attribute_id=item.attribute_id, value=Decimal("5"))
        for item in lexicon.attributes
    )
    for receipt in qualifications:
        for blind_code in ("K7Q", "M2R"):
            for repeat_index in (1, 2):
                session = _sha(f"session:{receipt.participant_token_sha256}:{repeat_index}")
                for timepoint in protocol.timepoints_seconds:
                    cell = C0ExpectedObservationCell(
                        blind_code=blind_code,
                        participant_token_sha256=receipt.participant_token_sha256,
                        qualification_receipt_sha256=receipt.receipt_sha256,
                        session_token_sha256=session,
                        repeat_index=repeat_index,
                        sniff_time_seconds=timepoint,
                    )
                    expected.append(cell)
                    observations.append(
                        PanelObservation(
                            observation_token_sha256=_sha(f"observation:{cell.key}"),
                            blind_code=blind_code,
                            participant_token_sha256=receipt.participant_token_sha256,
                            qualification_receipt_sha256=receipt.receipt_sha256,
                            protocol_sha256=protocol.protocol_sha256,
                            lexicon_sha256=lexicon.lexicon_sha256,
                            session_token_sha256=session,
                            repeat_index=repeat_index,
                            sniff_time_seconds=timepoint,
                            ratings=ratings,
                        )
                    )
    analysis_plan_sha256 = next(
        item.sha256 for item in protocol.bindings if item.binding_id == "analysis_plan"
    )
    assert analysis_plan_sha256 is not None
    results = tuple(
        PanelPerformanceResult(
            gate_kind=spec.kind,
            gate_spec_sha256=spec.spec_sha256,
            outcome=GateOutcome.PASS,
            observed_value=Decimal("1"),
            result_receipt_sha256=_sha(f"result:{spec.kind.value}"),
            participant_set_sha256=_sha("participant-set"),
            analysis_plan_sha256=analysis_plan_sha256,
            study_partition=StudyPartition.PILOT,
        )
        for spec in protocol.panel_gate_specs
    )
    exit_report = evaluate_c0_exit(protocol, lexicon, results)
    assert exit_report.decision is C0ExitDecision.GO

    manifests = {item.binding_id: item for item in bundle.manifests}
    source_payload_sha256 = stable_json_hash(_package_payload())
    hash_by_id = {
        "C0_PREPILOT_PROTOCOL": protocol.protocol_sha256,
        "LEXICON": lexicon.lexicon_sha256,
        "ATTRIBUTE_ANCHOR_CANDIDATES": manifests["anchor_reference_manifest"].manifest_sha256,
        "SAMPLE_PREPARATION_MANIFEST": manifests["preparation_dose_ppm_manifest"].manifest_sha256,
        "APPARATUS_VALIDATION": _sha("synthetic:apparatus-validation"),
        "SAFETY_ETHICS_PRIVACY_HOLD": manifests["ethics_privacy_safety_review"].manifest_sha256,
        "PARTICIPANT_QUALIFICATION": stable_json_hash(
            [
                item.as_dict()
                for item in sorted(
                    qualifications,
                    key=lambda receipt: receipt.participant_token_sha256,
                )
            ]
        ),
        "ENVIRONMENT_TIMING": manifests["environment_timing_manifest"].manifest_sha256,
        "RANDOMIZATION_LEDGER": manifests["randomization_manifest"].manifest_sha256,
        "BLIND_CODE_KEY": manifests["sample_manifest"].manifest_sha256,
        "OBSERVATION_SCHEMA": _sha("synthetic:observation-schema"),
        "ANALYSIS_PLAN": manifests["analysis_plan"].manifest_sha256,
        "STOP_GO_GATES": stable_json_hash([item.as_dict() for item in protocol.panel_gate_specs]),
        "DEVIATION_LOG": _sha("synthetic:deviation-log"),
        "RESULTS_RECEIPT": stable_json_hash([item.as_dict() for item in results]),
        "SOURCE_MANIFEST": source_payload_sha256,
        "DECISION_RECORD": stable_json_hash(exit_report.as_dict()),
    }
    registry = tuple(
        C0ArtifactReceipt.bound(artifact_id, hash_by_id[artifact_id])
        for artifact_id in C0_FULL_ARTIFACT_IDS
    )
    return {
        "source_payload_sha256": source_payload_sha256,
        "artifact_registry": registry,
        "lexicon": lexicon,
        "protocol": protocol,
        "prepilot_bundle": bundle,
        "qualification_receipts": qualifications,
        "expected_observation_manifest": tuple(expected),
        "observations": tuple(observations),
        "panel_performance_results": results,
        "exit_report": exit_report,
    }


def test_real_package_candidate_preserves_full_unbound_hold_denominator() -> None:
    envelope = build_package_c0_hold_envelope(_package_payload())

    payload = envelope.as_dict()
    assert tuple(item["artifact_id"] for item in payload["artifact_registry"]) == (
        C0_FULL_ARTIFACT_IDS
    )
    assert all(item["state"] == "UNBOUND" for item in payload["artifact_registry"])
    assert payload["claim_domain"] == "SEALED_STATIC_GLASS_HEADSPACE"
    assert payload["pleasantness_in_go_decision"] is False
    assert payload["human_execution_authorized"] is False
    assert payload["transfer_claims"] == []
    assert payload["decision_state"] == "HOLD"
    assert payload["source_payload"] == _package_payload()


def test_real_package_candidate_rejects_artifact_promotion_or_transfer_claim() -> None:
    promoted = _package_payload()
    promoted["artifacts"]["APPARATUS_VALIDATION"] = {  # type: ignore[index]
        "state": "BOUND",
        "hash": _sha("invented"),
    }
    with pytest.raises(ValueError, match="must remain UNBOUND"):
        build_package_c0_hold_envelope(promoted)

    transferred = _package_payload()
    transferred["transfer_claims"] = ["blotter"]
    with pytest.raises(ValueError, match="transfer claims"):
        build_package_c0_hold_envelope(transferred)


def test_direct_real_hold_constructor_revalidates_domain_and_source_contract() -> None:
    envelope = build_package_c0_hold_envelope(_package_payload())

    with pytest.raises(ValueError, match="claim domain"):
        C0PackageHoldEnvelope(
            source_payload_json=envelope.source_payload_json,
            source_payload_sha256=envelope.source_payload_sha256,
            artifact_registry=envelope.artifact_registry,
            claim_domain="BLOTTER",
        )

    altered = envelope.source_payload
    altered["decision_state"] = "GO"
    with pytest.raises(ValueError, match="must remain HOLD"):
        C0PackageHoldEnvelope(
            source_payload_json=json.dumps(altered),
            source_payload_sha256=stable_json_hash(altered),
            artifact_registry=envelope.artifact_registry,
        )


def test_complete_projection_is_deterministic_and_preserves_native_hashes() -> None:
    graph = _synthetic_graph()

    first = project_complete_c0_to_lab(**graph)
    second = project_complete_c0_to_lab(**graph)

    assert first.projection_sha256 == second.projection_sha256
    assert first.experiment_protocol["protocol_sha256"] == graph["protocol"].protocol_sha256
    assert (
        stable_json_hash(first.experiment_protocol["protocol"]) == graph["protocol"].protocol_sha256
    )
    assert len(first.experiment_protocol["artifact_registry"]) == 17
    assert len(first.application_records) == 8
    assert len(first.observation_records) == 24
    assert first.outcome["c0_exit_report"]["decision"] == "go"
    assert first.outcome["study_authority"] is False
    assert first.outcome["release_authority"] is False
    assert first.experiment_protocol["persistence_fit_scope"] == ("STORAGE_FIDELITY_ONLY")
    assert first.experiment_protocol["semantic_revalidation_required_after_readback"] is True


def test_canonical_projection_fixture_is_exact_engine_output() -> None:
    projection = project_complete_c0_to_lab(**_synthetic_graph())
    fixture = Path("tests/fixtures/c0_lab_persistence_projection_v1.json")
    sidecar = fixture.with_suffix(".sha256")
    expected = canonical_json_bytes(projection.as_dict()) + b"\n"

    assert fixture.read_bytes() == expected
    expected_sha256 = hashlib.sha256(expected).hexdigest()
    assert sidecar.read_text(encoding="utf-8") == (f"{expected_sha256}  {fixture.name}\n")


def test_projection_hash_is_invariant_to_equivalent_tuple_permutations() -> None:
    graph = _synthetic_graph()
    canonical = project_complete_c0_to_lab(**graph)
    permuted = project_complete_c0_to_lab(
        **{
            **graph,
            "qualification_receipts": tuple(reversed(graph["qualification_receipts"])),
            "expected_observation_manifest": tuple(
                reversed(graph["expected_observation_manifest"])
            ),
            "observations": tuple(reversed(graph["observations"])),
            "panel_performance_results": tuple(reversed(graph["panel_performance_results"])),
        }
    )

    assert permuted.projection_sha256 == canonical.projection_sha256
    assert permuted.as_dict() == canonical.as_dict()


def test_projection_rejects_duplicate_or_missing_observation_cells() -> None:
    graph = _synthetic_graph()
    duplicate_manifest = (
        *graph["expected_observation_manifest"],
        graph["expected_observation_manifest"][0],
    )
    with pytest.raises(ValueError, match="duplicate cells"):
        project_complete_c0_to_lab(**{**graph, "expected_observation_manifest": duplicate_manifest})

    with pytest.raises(ValueError, match="coverage mismatch: missing=1"):
        project_complete_c0_to_lab(**{**graph, "observations": graph["observations"][:-1]})


def test_projection_preserves_opaque_external_hash_and_rejects_missing_stratum() -> None:
    graph = _synthetic_graph()
    registry = list(graph["artifact_registry"])
    index = C0_FULL_ARTIFACT_IDS.index("OBSERVATION_SCHEMA")
    registry[index] = C0ArtifactReceipt.bound("OBSERVATION_SCHEMA", _sha("other"))
    projection = project_complete_c0_to_lab(**{**graph, "artifact_registry": tuple(registry)})
    assert projection.experiment_protocol["opaque_external_artifact_ids"] == list(
        C0_OPAQUE_EXTERNAL_ARTIFACT_IDS
    )
    assert projection.experiment_protocol["artifact_registry"][index]["artifact_sha256"] == _sha(
        "other"
    )

    with pytest.raises(ValueError, match="trained and untrained"):
        project_complete_c0_to_lab(
            **{
                **graph,
                "qualification_receipts": graph["qualification_receipts"][:1],
            }
        )


def test_projection_rejects_native_registry_hash_mismatch() -> None:
    graph = _synthetic_graph()
    registry = list(graph["artifact_registry"])
    index = C0_FULL_ARTIFACT_IDS.index("LEXICON")
    registry[index] = C0ArtifactReceipt.bound("LEXICON", _sha("wrong-lexicon"))

    with pytest.raises(ValueError, match="hash mismatch for LEXICON"):
        project_complete_c0_to_lab(**{**graph, "artifact_registry": tuple(registry)})


def test_projection_rejects_exit_report_not_replayed_from_exact_results() -> None:
    graph = _synthetic_graph()
    wrong_exit = replace(
        graph["exit_report"],
        decision=C0ExitDecision.HOLD,
        c0_exit_satisfied=False,
    )

    with pytest.raises(ValueError, match="deterministic C0 evaluation"):
        project_complete_c0_to_lab(**{**graph, "exit_report": wrong_exit})
