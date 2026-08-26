from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.evidence_contracts import (
    EvidenceBasis,
    EvidenceSourceRef,
    QuantitativeEvidence,
)
from engine.solforge.evidence_review import (
    EVIDENCE_REVIEW_AUTHORITY_FLAGS,
    EvidenceReviewLedgerV1,
    EvidenceSourceTier,
    OAVIntervalEvidence,
    OAVModelTier,
    OAVTimepointEvidenceInput,
    OAVTimepointKey,
    OperativeEvidenceBindingV1,
    SourceQualityAssessmentV1,
    TemporalOAVEvidenceRequest,
    TransferDisposition,
    load_construct_registry,
    load_evidence_source_registry,
    load_evidence_source_registry_v3,
    load_hedonic_protocol_policy,
    load_oav_temporal_policy,
    validate_evidence_review,
)

ROOT = Path(__file__).resolve().parents[1]
CONSTRUCTS = ROOT / "configs/solforge/complexity_construct_registry_v1.json"
SOURCES = ROOT / "configs/solforge/complexity_evidence_sources_v2.json"
SOURCES_V3 = ROOT / "configs/solforge/complexity_evidence_sources_v3.json"
OAV_POLICY = ROOT / "configs/solforge/oav_temporal_policy_v1.json"
HEDONIC_POLICY = ROOT / "configs/solforge/hedonic_protocol_policy_v1.json"


def _assessment(**changes: object) -> SourceQualityAssessmentV1:
    values: dict[str, object] = {
        "source_id": "DAVIDSON-1970",
        "source_record_sha256": "a" * 64,
        "tier": EvidenceSourceTier.STATISTICAL_FOUNDATION,
        "primary_source_ids": (),
        "population_declared": True,
        "matrix_declared": True,
        "endpoint_declared": True,
        "order_control_reported": False,
        "assessor_dependence_reported": False,
        "limitations": ("Statistical model; no perfume sensory result.",),
    }
    values.update(changes)
    return SourceQualityAssessmentV1(**values)


def _binding(**changes: object) -> OperativeEvidenceBindingV1:
    values: dict[str, object] = {
        "requirement_id": "PREFERENCE_TIE_LIKELIHOOD",
        "source_record_sha256": "a" * 64,
        "source_tier": EvidenceSourceTier.STATISTICAL_FOUNDATION,
        "requested_claim": "Fit explicit preference ties with a Davidson likelihood.",
        "demonstrated_scope": "A paired-comparison probability model with ties.",
        "transfer_disposition": TransferDisposition.METHOD_ONLY,
        "limitations": ("Does not establish fragrance liking.",),
        "population_match": False,
        "matrix_match": False,
        "endpoint_match": True,
        "time_match": False,
    }
    values.update(changes)
    return OperativeEvidenceBindingV1(**values)


def _quantitative(value: float, *, unit: str = "mg/m3") -> QuantitativeEvidence:
    return QuantitativeEvidence(
        value=value,
        unit=unit,
        context="ethanol perfume on blotter at 23 C",
        method="calibrated HS-SPME-GC",
        basis=EvidenceBasis.MEASURED,
        source=EvidenceSourceRef(
            source_id="LAB-1",
            source_uri="urn:perfume-chem:lab:1",
            retrieved_on="2026-08-26",
            source_sha256="1" * 64,
        ),
    )


def test_transferable_food_method_cannot_directly_support_perfume_liking() -> None:
    with pytest.raises(ValueError, match="DIRECT transfer requires exact scope"):
        _binding(
            source_tier=EvidenceSourceTier.TRANSFERABLE_SENSORY_METHOD,
            requested_claim="BLIND-A is preferred as a perfume.",
            demonstrated_scope="Temporal dominance in flavored gels.",
            transfer_disposition=TransferDisposition.DIRECT,
            population_match=True,
            matrix_match=False,
            endpoint_match=False,
            time_match=True,
        )


def test_systematic_review_requires_primary_source_traceability() -> None:
    assessment = _assessment(
        source_id="REVIEW-1",
        tier=EvidenceSourceTier.SYSTEMATIC_SYNTHESIS,
        primary_source_ids=(),
        assessor_dependence_reported=True,
        limitations=("Heterogeneous matrices.",),
    )
    assert "PRIMARY_TRACE_MISSING" in assessment.failures


def test_direct_binding_requires_direct_tier_and_complete_scope_match() -> None:
    binding = _binding(
        source_tier=EvidenceSourceTier.DIRECT_FINE_FRAGRANCE,
        transfer_disposition=TransferDisposition.DIRECT,
        population_match=True,
        matrix_match=True,
        endpoint_match=True,
        time_match=True,
    )
    assert binding.failures == ()
    assert OperativeEvidenceBindingV1.from_dict(binding.as_dict()) == binding


def test_review_ledger_is_closed_hashable_and_rejects_unknown_binding() -> None:
    assessment = _assessment()
    binding = _binding()
    ledger = EvidenceReviewLedgerV1(
        source_seed_manifest_sha256="b" * 64,
        construct_registry_sha256="c" * 64,
        assessments=(assessment,),
        operative_bindings=(binding,),
        unresolved_questions=("Fine-fragrance transfer remains untested.",),
    )
    assert EvidenceReviewLedgerV1.from_dict(ledger.as_dict()) == ledger
    assert ledger.as_dict()["authority_flags"] == EVIDENCE_REVIEW_AUTHORITY_FLAGS
    assert ledger.record_sha256 == hashlib.sha256(ledger.canonical_bytes()).hexdigest()
    assert validate_evidence_review(ledger) == ()

    unknown = _binding(source_record_sha256="d" * 64)
    invalid = EvidenceReviewLedgerV1(
        source_seed_manifest_sha256=ledger.source_seed_manifest_sha256,
        construct_registry_sha256=ledger.construct_registry_sha256,
        assessments=ledger.assessments,
        operative_bindings=(unknown,),
        unresolved_questions=ledger.unresolved_questions,
    )
    assert validate_evidence_review(invalid) == (
        "binding PREFERENCE_TIE_LIKELIHOOD references an unknown source record",
    )


def test_construct_registry_is_closed_and_separates_all_criteria(tmp_path: Path) -> None:
    registry = load_construct_registry(CONSTRUCTS)
    assert tuple(item["construct_id"] for item in registry["constructs"]) == (
        "LIKING",
        "PERCEIVED_RICHNESS",
        "PERCEIVED_DEPTH",
        "CONFIGURATIONAL_INTEGRATION",
        "HIERARCHY_CONTRAST",
        "TEMPORAL_DIFFERENTIATION",
        "TARGET_FIDELITY",
        "INTENSITY",
        "FAMILIARITY",
        "DETECTABILITY",
    )
    assert registry["authority_flags"] == EVIDENCE_REVIEW_AUTHORITY_FLAGS

    payload = json.loads(CONSTRUCTS.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="closed schema"):
        load_construct_registry(bad)


def test_source_registry_has_hashable_primary_and_authoritative_records() -> None:
    records = load_evidence_source_registry(SOURCES)
    assert len(records) >= 27
    assert tuple(item.source_id for item in records) == tuple(
        sorted(item.source_id for item in records)
    )
    assert len({item.record_sha256 for item in records}) == len(records)
    assert {item.stable_identifier for item in records} >= {
        "doi:10.1080/01621459.1970.10481082",
        "doi:10.1111/j.1745-459x.1989.tb00463.x",
        "iso:11136:2014",
        "astm:e2263-25",
    }


def test_temporal_oav_interfaces_freeze_time_interval_and_protocol_identity() -> None:
    key = OAVTimepointKey(
        protocol_sha256="a" * 64,
        sample_id="BLIND-A",
        material_id="MAT-1",
        time_seconds=300,
        endpoint="HEADSPACE_CONCENTRATION",
    )
    interval = OAVIntervalEvidence(
        p05=_quantitative(1.0),
        p50=_quantitative(2.0),
        p95=_quantitative(4.0),
    )
    cell = OAVTimepointEvidenceInput(
        key=key,
        exact_stock_ref="stock:MAT-1",
        active_mass_g=0.01,
        headspace_interval=interval,
        threshold_interval=interval,
        model_tier=OAVModelTier.T4_MEASURED,
        context_sha256="b" * 64,
    )
    request = TemporalOAVEvidenceRequest(
        formula_sha256="c" * 64,
        dose_receipt_sha256="d" * 64,
        protocol_sha256="a" * 64,
        measurement_context_sha256="b" * 64,
        cells=(cell,),
    )
    assert request.cells[0].key.time_seconds == 300
    assert request.as_dict()["cells"][0]["model_tier"] == "T4_MEASURED"
    round_trip = json.loads(
        json.dumps(request.as_dict(), sort_keys=True, separators=(",", ":"))
    )
    assert TemporalOAVEvidenceRequest.from_dict(round_trip) == request

    with pytest.raises(ValueError, match="nonnegative integer seconds"):
        OAVTimepointKey(
            protocol_sha256="a" * 64,
            sample_id="BLIND-A",
            material_id="MAT-1",
            time_seconds=-1,
            endpoint="HEADSPACE_CONCENTRATION",
        )
    with pytest.raises(ValueError, match="P05 <= P50 <= P95"):
        OAVIntervalEvidence(
            p05=_quantitative(2.0),
            p50=_quantitative(1.0),
            p95=_quantitative(4.0),
        )
    with pytest.raises(ValueError, match="protocol_sha256"):
        TemporalOAVEvidenceRequest(
            formula_sha256="c" * 64,
            dose_receipt_sha256="d" * 64,
            protocol_sha256="e" * 64,
            measurement_context_sha256="b" * 64,
            cells=(cell,),
        )


def test_temporal_oav_policy_is_closed_and_has_no_universal_timepoints(
    tmp_path: Path,
) -> None:
    policy = load_oav_temporal_policy(OAV_POLICY)
    assert policy["canonical_time"]["unit"] == "SECOND"
    assert policy["canonical_time"]["universal_timepoints"] == []
    assert policy["model_tiers"] == [
        "T0_UNKNOWN",
        "T1_TRANSFERRED",
        "T2_MODELED",
        "T3_CALIBRATED_MODELED",
        "T4_MEASURED",
    ]
    assert policy["oav_interval_calculation"] == {
        "p05": "headspace_p05 / threshold_p95",
        "p50": "headspace_p50 / threshold_p50",
        "p95": "headspace_p95 / threshold_p05",
    }
    assert policy["threshold_cancellation"]["incompatible_state"] == (
        "THRESHOLD_CANCELLATION_INCOMPATIBLE"
    )

    payload = json.loads(OAV_POLICY.read_text(encoding="utf-8"))
    payload["canonical_time"]["universal_timepoints"] = [300]
    bad = tmp_path / "bad-oav-policy.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen decisions"):
        load_oav_temporal_policy(bad)


def test_hedonic_policy_separates_criteria_scopes_and_proxy_features(
    tmp_path: Path,
) -> None:
    policy = load_hedonic_protocol_policy(HEDONIC_POLICY)
    assert policy["criteria"] == [
        "TARGET_FIDELITY",
        "DEPTH",
        "RICHNESS",
        "LIKING",
    ]
    assert policy["protocol_scopes"] == [
        "OWNER",
        "TRAINED_PANEL",
        "CONSUMER_POPULATION",
    ]
    assert policy["criterion_policy"]["synthetic_beauty_score"] is False
    assert set(policy["forbidden_directional_features"]) >= {
        "OAV",
        "FORMULA_COMPOSITION",
        "BRAND",
        "PRICE",
        "LUXURY_LANGUAGE",
    }

    payload = json.loads(HEDONIC_POLICY.read_text(encoding="utf-8"))
    payload["criteria"] = ["BEAUTY"]
    bad = tmp_path / "bad-hedonic-policy.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="frozen decisions"):
        load_hedonic_protocol_policy(bad)


def test_v3_source_overlay_preserves_every_v2_record_exactly() -> None:
    predecessor = load_evidence_source_registry(SOURCES)
    records = load_evidence_source_registry_v3(SOURCES_V3, SOURCES)
    predecessor_by_id = {item.source_id: item for item in predecessor}
    records_by_id = {item.source_id: item for item in records}
    assert len(records) > len(predecessor)
    assert all(
        records_by_id[source_id].canonical_bytes() == record.canonical_bytes()
        for source_id, record in predecessor_by_id.items()
    )
    assert {item.source_id for item in records} >= {
        "ASTM-E679-26",
        "ISO-13301-2018",
        "ISO-8586-2023",
        "HADJIEFSTATHIOU-2025",
        "LIU-2020",
    }
