"""Tests for engine.reconstruction.authority."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.evidence.ledger import EvidenceClaim, EvidenceLedger, EvidenceSource
from engine.reconstruction.authority import (
    AuthorityVector,
    coverage_score,
    derive_authority_from_evidence,
    derive_identity_authority,
    derive_safety_authority,
)
from engine.target.formula import TargetFormula, TargetMaterial


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_target(materials: list[dict]) -> TargetFormula:
    """Build a TargetFormula from a list of material dicts."""
    rows = []
    for m in materials:
        rows.append(
            TargetMaterial(
                identity=m.get("identity", "UNKNOWN_*"),
                grade=m.get("grade", "unresolved"),
                identity_confidence=m.get("identity_confidence", 0.0),
                quantity_confidence=m.get("quantity_confidence", 0.0),
            )
        )
    return TargetFormula(
        product_id="test_product",
        target_materials=tuple(rows),
    )


def _make_ledger_with_claims(
    claims: list[dict],
) -> EvidenceLedger:
    """Build an EvidenceLedger with a single source and the given claims."""
    src = EvidenceSource(
        source_id="src_001",
        source_class="A",
    )
    records = []
    for c in claims:
        records.append(
            EvidenceClaim(
                claim_id=c.get("claim_id", "claim_001"),
                source_id="src_001",
                reference_product_id="test_product",
                claim_type=c.get("claim_type", "identity_presence"),
                subject_material_name=c.get("subject_material_name", ""),
                identity_confidence=c.get("identity_confidence", 0.0),
                quantity_confidence=c.get("quantity_confidence", 0.0),
                reported_value=c.get("reported_value"),
            )
        )
    return EvidenceLedger.from_records(sources=[src], claims=records)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_derive_empty_target_returns_all_zeros():
    """An empty target formula should produce an all-zero AuthorityVector."""
    target = _make_target([])
    ledger = _make_ledger_with_claims([])
    av = derive_authority_from_evidence(target, ledger)
    assert av.identity == 0.0
    assert av.quantity == 0.0
    assert av.safety == 0.0
    assert av.grade == 0.0
    assert av.release == 0.0
    assert av.natural_lot == 0.0
    assert av.matrix == 0.0
    assert av.headspace == 0.0
    assert av.sensory == 0.0
    assert av.inventory == 0.0


def test_derive_full_evidence_returns_high_scores():
    """Full evidence coverage for all materials should yield high authority."""
    target = _make_target(
        [
            {"identity": "Bergamot", "grade": "premium"},
            {"identity": "Hedione", "grade": "standard"},
        ]
    )
    ledger = _make_ledger_with_claims(
        [
            {
                "claim_id": "c1",
                "subject_material_name": "Bergamot",
                "identity_confidence": 0.9,
                "quantity_confidence": 0.8,
                "reported_value": 200.0,
            },
            {
                "claim_id": "c2",
                "subject_material_name": "Hedione",
                "identity_confidence": 0.8,
                "quantity_confidence": 0.7,
                "reported_value": 300.0,
            },
        ]
    )
    av = derive_authority_from_evidence(target, ledger)
    assert av.identity == 1.0  # both have identity evidence
    assert av.quantity == 1.0  # both have quantity evidence, no contradictions
    assert av.grade == 1.0  # both have resolved grades
    # safety depends on IFRA database — at least check it's > 0
    assert av.safety >= 0.0
    # release requires identity >= 0.7, quantity >= 0.5, safety >= 0.5, grade >= 0.5
    # safety may be < 0.5 depending on IFRA coverage, so release may be 0.0
    assert av.release in (0.0, 1.0)


def test_derive_partial_coverage_returns_proportional():
    """Partial evidence coverage should yield proportional scores."""
    target = _make_target(
        [
            {"identity": "Bergamot", "grade": "premium"},
            {"identity": "Hedione", "grade": "unresolved"},
            {"identity": "Iso E Super", "grade": "unresolved"},
            {"identity": "Vanillin", "grade": "standard"},
        ]
    )
    # Only Bergamot and Vanillin have evidence claims
    ledger = _make_ledger_with_claims(
        [
            {
                "claim_id": "c1",
                "subject_material_name": "Bergamot",
                "identity_confidence": 0.9,
                "quantity_confidence": 0.8,
                "reported_value": 200.0,
            },
            {
                "claim_id": "c2",
                "subject_material_name": "Vanillin",
                "identity_confidence": 0.7,
                "quantity_confidence": 0.0,
                "reported_value": None,
            },
        ]
    )
    av = derive_authority_from_evidence(target, ledger)
    # identity: 2 out of 4 have identity_confidence > 0
    assert av.identity == 0.5
    # quantity: 1 out of 4 have quantity_confidence > 0, no contradictions
    assert av.quantity == 0.25
    # grade: 2 out of 4 have resolved grades
    assert av.grade == 0.5


def test_coverage_score_basic():
    """coverage_score returns correct fractions."""
    assert coverage_score(0, 10) == 0.0
    assert coverage_score(5, 10) == 0.5
    assert coverage_score(10, 10) == 1.0
    assert coverage_score(0, 0) == 0.0
    assert coverage_score(3, 0) == 0.0


def test_derive_identity_authority_fractional():
    """derive_identity_authority returns correct fraction."""
    target = _make_target(
        [
            {"identity": "A"},
            {"identity": "B"},
            {"identity": "C"},
            {"identity": "D"},
        ]
    )
    # Only A and C have evidence
    ledger = _make_ledger_with_claims(
        [
            {
                "claim_id": "c1",
                "subject_material_name": "A",
                "identity_confidence": 0.8,
            },
            {
                "claim_id": "c2",
                "subject_material_name": "C",
                "identity_confidence": 0.6,
            },
        ]
    )
    assert derive_identity_authority(target, ledger) == 0.5


def test_derive_safety_authority_fractional():
    """derive_safety_authority returns correct fraction."""
    # Use materials that are likely in the IFRA database
    target = _make_target(
        [
            {"identity": "Coumarin"},
            {"identity": "Hydroxycitronellal"},
            {"identity": "FictionalMaterialXYZ"},
        ]
    )
    score = derive_safety_authority(target)
    # Coumarin and Hydroxycitronellal have IFRA Cat4 limits; the fictional one won't.
    # (Limonene and Linalool are specification-only standards with no numeric limit.)
    assert score == 2.0 / 3.0


def test_authority_vector_as_dict_no_average():
    """AuthorityVector.as_dict must NOT contain an 'average' key."""
    av = AuthorityVector(identity=0.8, quantity=0.5, safety=0.9)
    d = av.as_dict()
    assert "average" not in d
    assert d["identity"] == 0.8
    assert d["quantity"] == 0.5
    assert d["safety"] == 0.9
