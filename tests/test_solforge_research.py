from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from engine.solforge.research import (
    RESEARCH_AUTHORITY_FLAGS,
    ResearchConflictV1,
    ResearchEvidenceClass,
    ResearchEvidenceRecordV1,
    ResearchLedgerV1,
    validate_research_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
SEEDS = ROOT / "configs/solforge/research_source_seeds_v1.json"


def _record(**changes) -> ResearchEvidenceRecordV1:
    values = {
        "source_id": "FRANK-2017",
        "stable_identifier": "doi:10.1093/chemse/bjx031",
        "uri": "https://doi.org/10.1093/chemse/bjx031",
        "title": "Recognition of the Component Odors in Mixtures",
        "authors": ("Frank ME", "Fletcher DB", "Hettinger TP"),
        "publication_year": 2017,
        "retrieved_on": "2026-08-26",
        "source_kind": "PRIMARY_RESEARCH",
        "evidence_class": ResearchEvidenceClass.DIRECT_PERFUMERY_PSYCHOPHYSICS,
        "study_design": "controlled human selective-adaptation experiment",
        "stimuli": "water-soluble two-, three-, and four-component odor mixtures",
        "population": "14 human assessors in the reported experimental analysis",
        "apparatus": "controlled adapt-test odor presentations",
        "endpoints": ("component identification",),
        "direct_result_summary": "Selective adaptation changed component identification within the tested mixtures.",
        "limitations": ("The stimuli were not finished perfumes.",),
        "applicability": (
            "Supports omission and adaptation hypotheses, not formula-specific sensory claims.",
        ),
        "rights": "METADATA_AND_DERIVED_SUMMARY_ONLY",
        "retained_source_sha256": None,
        "short_extract": None,
    }
    values.update(changes)
    return ResearchEvidenceRecordV1(**values)


def _ledger(*records: ResearchEvidenceRecordV1) -> ResearchLedgerV1:
    return ResearchLedgerV1(
        source_seed_manifest_sha256=hashlib.sha256(SEEDS.read_bytes()).hexdigest(),
        records=records,
        conflicts=(),
        unresolved_questions=("Transfer from simple mixtures to finished perfume remains untested.",),
    )


def test_research_record_round_trips_and_is_non_promoting() -> None:
    record = _record()
    assert ResearchEvidenceRecordV1.from_dict(record.as_dict()) == record
    assert record.as_dict()["authority_flags"] == RESEARCH_AUTHORITY_FLAGS
    assert record.record_sha256 == hashlib.sha256(record.canonical_bytes()).hexdigest()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"stable_identifier": "Frank paper"}, "stable_identifier"),
        ({"uri": "not a uri"}, "uri"),
        ({"retrieved_on": "26 August"}, "retrieved_on"),
        ({"applicability": ()}, "applicability"),
        ({"limitations": ()}, "limitations"),
        ({"endpoints": ()}, "endpoints"),
    ],
)
def test_research_record_requires_scoped_source_and_study_metadata(
    changes: dict, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _record(**changes)


def test_supplier_source_cannot_claim_direct_psychophysics() -> None:
    with pytest.raises(ValueError, match="supplier"):
        _record(source_kind="SUPPLIER")
    supplier = _record(
        source_kind="SUPPLIER",
        evidence_class=ResearchEvidenceClass.SUPPLIER_OR_TRADE_DESCRIPTION,
    )
    assert supplier.evidence_class is ResearchEvidenceClass.SUPPLIER_OR_TRADE_DESCRIPTION


def test_retained_bytes_require_exact_hash_and_extract_is_short() -> None:
    with pytest.raises(ValueError, match="retained_source_sha256"):
        _record(retained_source_sha256="bad")
    with pytest.raises(ValueError, match="short_extract"):
        _record(short_extract="word " * 26)


def test_conflict_must_link_known_distinct_records() -> None:
    first = _record()
    second = replace(
        first,
        source_id="CONTRARY-2024",
        stable_identifier="pmid:39000000",
        uri="https://pubmed.ncbi.nlm.nih.gov/39000000/",
    )
    conflict = ResearchConflictV1(
        conflict_id="C1",
        linked_record_sha256=(first.record_sha256, second.record_sha256),
        question="How well do simple-mixture effects transfer to perfume?",
        conflict_summary="The studies use different stimuli and scopes.",
        resolution_state="UNRESOLVED",
    )
    ledger = replace(_ledger(first, second), conflicts=(conflict,))
    assert validate_research_ledger(ledger) == ()
    bad = replace(
        conflict, linked_record_sha256=(first.record_sha256, "f" * 64)
    )
    assert "unknown record hash" in validate_research_ledger(
        replace(ledger, conflicts=(bad,))
    )[0]


def test_ledger_rejects_duplicate_sources_and_true_authority() -> None:
    record = _record()
    assert "duplicate source_id" in validate_research_ledger(_ledger(record, record))[0]
    payload = _ledger(record).as_dict()
    payload["authority_flags"]["hedonic"] = True
    with pytest.raises(ValueError, match="authority_flags"):
        ResearchLedgerV1.from_dict(payload)


def test_seed_manifest_has_all_method_seeds_and_no_claim_authority() -> None:
    payload = json.loads(SEEDS.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "solforge_research_source_seeds_v1"
    assert len(payload["seeds"]) == 17
    assert {seed["seed_id"] for seed in payload["seeds"]} == {
        "FRANK-2017",
        "MCCLINTOCK-2020",
        "LABBE-2009",
        "PINEAU-2009",
        "MEYNERS-PINEAU-2010",
        "CASTURA-2016",
        "MACFIE-1989",
        "ZHOU-2024",
        "ARSHAMIAN-2022",
        "LIU-2020",
        "NIST-MIXTURE-DESIGN",
        "ISO-8586-2023",
        "ISO-13299-2016",
        "ISO-11136-2014",
        "LINDLEY-1956",
        "CHALONER-VERDINELLI-1995",
        "ATKINSON-FEDOROV-1975",
    }
    assert all(
        seed["authority"] == "METHOD_OR_HYPOTHESIS_ONLY"
        for seed in payload["seeds"]
    )
