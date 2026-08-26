from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.solforge.evidence_review import (
    EVIDENCE_REVIEW_AUTHORITY_FLAGS,
    EvidenceReviewLedgerV1,
    EvidenceSourceTier,
    OperativeEvidenceBindingV1,
    SourceQualityAssessmentV1,
    TransferDisposition,
    load_construct_registry,
    load_evidence_source_registry,
    validate_evidence_review,
)

ROOT = Path(__file__).resolve().parents[1]
CONSTRUCTS = ROOT / "configs/solforge/complexity_construct_registry_v1.json"
SOURCES = ROOT / "configs/solforge/complexity_evidence_sources_v2.json"


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
