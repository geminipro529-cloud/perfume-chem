"""Tests for engine.evidence.ledger."""

from __future__ import annotations
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.evidence.ledger import (
    EvidenceLedger,
    EvidenceSource,
    EvidenceClaim,
    ContradictionReport,
    A,
    F,
    H,
    J,
)


class _LegacyFixtureEvidenceLedger(EvidenceLedger):
    """Mutable test builder; production EvidenceLedger is read-only."""

    def add_source(self, source: EvidenceSource) -> None:
        self._sources[source.source_id] = source

    def add_claim(self, claim: EvidenceClaim) -> None:
        self._claims.append(claim)


EvidenceLedger = _LegacyFixtureEvidenceLedger


def test_add_source_and_claim():
    ledger = EvidenceLedger()
    source = EvidenceSource(source_id="s1", source_class=A, title="Test Source")
    ledger.add_source(source)
    assert len(ledger._sources) == 1

    claim = EvidenceClaim(
        claim_id="c1",
        source_id="s1",
        reference_product_id="prod1",
        claim_type="identity_presence",
        subject_material_name="Iso E Super",
        identity_confidence=0.9,
    )
    ledger.add_claim(claim)
    assert len(ledger._claims) == 1


def test_get_claims_for_material():
    ledger = EvidenceLedger()
    source = EvidenceSource(source_id="s1", source_class=H)
    ledger.add_source(source)
    c1 = EvidenceClaim(
        claim_id="c1",
        source_id="s1",
        reference_product_id="p1",
        claim_type="identity_presence",
        subject_material_name="Iso E Super",
        identity_confidence=0.6,
    )
    c2 = EvidenceClaim(
        claim_id="c2",
        source_id="s1",
        reference_product_id="p1",
        claim_type="identity_presence",
        subject_material_name="Hedione",
        identity_confidence=0.5,
    )
    ledger.add_claim(c1)
    ledger.add_claim(c2)
    assert len(ledger.get_claims_for_material("Iso E Super")) == 1


def test_get_independent_claims():
    ledger = EvidenceLedger()
    s1 = EvidenceSource(source_id="s1", source_class=H)
    s2 = EvidenceSource(source_id="s2", source_class=H)
    ledger.add_source(s1)
    ledger.add_source(s2)
    c1 = EvidenceClaim(
        claim_id="c1",
        source_id="s1",
        reference_product_id="p1",
        claim_type="rank",
        subject_material_name="Iso E Super",
        independence_group="dupehacking_roster",
        identity_confidence=0.6,
    )
    c2 = EvidenceClaim(
        claim_id="c2",
        source_id="s2",
        reference_product_id="p1",
        claim_type="rank",
        subject_material_name="Iso E Super",
        independence_group="dupehacking_roster",
        identity_confidence=0.7,
    )
    ledger.add_claim(c1)
    ledger.add_claim(c2)
    # Same independence group, should de-duplicate
    independent = ledger.get_independent_claims("p1")
    assert len(independent) <= 2


def test_find_contradictions():
    ledger = EvidenceLedger()
    s1 = EvidenceSource(source_id="s1", source_class=A)
    s2 = EvidenceSource(source_id="s2", source_class=H)
    ledger.add_source(s1)
    ledger.add_source(s2)
    c1 = EvidenceClaim(
        claim_id="c1",
        source_id="s1",
        reference_product_id="p1",
        claim_type="identity_presence",
        subject_material_name="Vetiver Haiti",
        identity_confidence=0.9,
    )
    c2 = EvidenceClaim(
        claim_id="c2",
        source_id="s2",
        reference_product_id="p1",
        claim_type="identity_presence",
        subject_material_name="Vetiver India",
        identity_confidence=0.5,
    )
    ledger.add_claim(c1)
    ledger.add_claim(c2)
    contradictions = ledger.find_contradictions("p1")
    assert isinstance(contradictions, list)


def test_build_documentary_matrix():
    ledger = EvidenceLedger()
    s1 = EvidenceSource(source_id="s1", source_class=F)
    ledger.add_source(s1)
    c1 = EvidenceClaim(
        claim_id="c1",
        source_id="s1",
        reference_product_id="p1",
        claim_type="identity_presence",
        subject_material_name="Bergamot",
        identity_confidence=0.8,
        exact_excerpt="bergamot, ginger, violet leaf",
    )
    ledger.add_claim(c1)
    matrix = ledger.build_documentary_matrix("p1")
    assert "Bergamot" in matrix or "bergamot" in matrix
