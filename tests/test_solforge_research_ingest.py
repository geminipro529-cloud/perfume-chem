from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from engine.solforge.research import ResearchEvidenceClass, ResearchEvidenceRecordV1
from engine.solforge.research_ingest import (
    build_metadata_envelope,
    freeze_evidence_review_ledger,
    freeze_ledger,
    load_evidence_review_ledger,
    merge_records,
    normalize_stable_identifier,
    validate_frozen_evidence_review_ledger,
    validate_frozen_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/research/solforge/research_evidence_records_v1.json"
LEDGER_HASH = ROOT / "data/research/solforge/research_evidence_records_v1.sha256"
REVIEW_LEDGER = ROOT / "data/research/solforge/research_evidence_records_v2.json"
REVIEW_LEDGER_HASH = (
    ROOT / "data/research/solforge/research_evidence_records_v2.sha256"
)


def _record(summary: str = "Directly supported result.") -> ResearchEvidenceRecordV1:
    return ResearchEvidenceRecordV1(
        source_id="LIU-2020",
        stable_identifier="pmid:33093474",
        uri="https://pubmed.ncbi.nlm.nih.gov/33093474/",
        title="Assessment of odor hedonic perception",
        authors=("Liu DT",),
        publication_year=2020,
        retrieved_on="2026-08-26",
        source_kind="PRIMARY_RESEARCH",
        evidence_class=ResearchEvidenceClass.GENERAL_OLFACTION_PSYCHOPHYSICS,
        study_design="multicenter method-development and test-retest study",
        stimuli="pairwise oppositely valenced odor pens",
        population="162 normosmic participants across four experiments",
        apparatus="Sniffin' Sticks and additional felt-tip odor pens",
        endpoints=("hedonic range", "hedonic direction", "intensity"),
        direct_result_summary=summary,
        limitations=("Clinical method-development stimuli were not perfumes.",),
        applicability=("Supports pairwise liking and test-retest protocol design only.",),
        rights="OPEN_ACCESS_METADATA_AND_DERIVED_SUMMARY_ONLY",
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("https://doi.org/10.1038/S41598-020-74967-0", "doi:10.1038/s41598-020-74967-0"),
        ("DOI: 10.1093/CHEMSE/BJX031", "doi:10.1093/chemse/bjx031"),
        ("PMID 33093474", "pmid:33093474"),
        ("PMCID PMC7581750", "pmcid:pmc7581750"),
    ],
)
def test_stable_identifier_normalization(value: str, expected: str) -> None:
    assert normalize_stable_identifier(value) == expected


def test_unknown_identifier_is_not_guessed() -> None:
    with pytest.raises(ValueError, match="unsupported stable identifier"):
        normalize_stable_identifier("a paper by Liu")


def test_metadata_envelope_keeps_acquisition_time_outside_stable_core() -> None:
    envelope = build_metadata_envelope(
        stable_identifier="pmid:33093474",
        search_status="RESOLVED",
        title="Assessment of odor hedonic perception",
        publication_status="PUBLISHED",
        related_notice_ids=("doi:10.1000/correction",),
        acquired_at_utc="2026-08-26T01:02:03+00:00",
    )
    assert "acquired_at_utc" not in envelope["stable_metadata"]
    assert envelope["stable_metadata"]["related_notice_ids"] == [
        "doi:10.1000/correction"
    ]
    assert envelope["acquired_at_utc"] == "2026-08-26T01:02:03+00:00"


def test_network_failure_is_explicitly_unresolved() -> None:
    envelope = build_metadata_envelope(
        stable_identifier="doi:10.1000/unavailable",
        search_status="UNRESOLVED",
        title=None,
        publication_status="UNKNOWN",
        related_notice_ids=(),
        acquired_at_utc="2026-08-26T01:02:03+00:00",
    )
    assert envelope["stable_metadata"]["search_status"] == "UNRESOLVED"
    assert envelope["stable_metadata"]["title"] is None


def test_duplicate_merge_is_exact_and_conflicting_results_are_preserved() -> None:
    record = _record()
    assert merge_records((record, record)) == (record,)
    with pytest.raises(ValueError, match="conflicting duplicate source"):
        merge_records((record, _record("A different direct result.")))


def test_rights_do_not_allow_unlicensed_retained_bytes() -> None:
    with pytest.raises(ValueError, match="rights"):
        ResearchEvidenceRecordV1.from_dict(
            {
                **_record().as_dict(),
                "retained_source_sha256": "a" * 64,
            }
        )


def test_initial_ledger_is_complete_valid_and_exactly_frozen(tmp_path: Path) -> None:
    result = validate_frozen_ledger(LEDGER, LEDGER_HASH)
    assert result == ()
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert len(payload["records"]) == 10
    assert {row["source_id"] for row in payload["records"]} >= {
        "FRANK-2017",
        "MCCLINTOCK-2020",
        "LABBE-2009",
        "ZHOU-2024",
        "ARSHAMIAN-2022",
        "LIU-2020",
    }
    output = tmp_path / "ledger.sha256"
    freeze_ledger(LEDGER, output)
    assert output.read_text(encoding="utf-8").split()[0] == hashlib.sha256(
        LEDGER.read_bytes()
    ).hexdigest()


def test_v2_review_ledger_is_canonical_sorted_and_frozen(tmp_path: Path) -> None:
    ledger = load_evidence_review_ledger(REVIEW_LEDGER)
    source_ids = [item.source_id for item in ledger.assessments]
    assert source_ids == sorted(source_ids)
    assert len(source_ids) >= 27
    assert validate_frozen_evidence_review_ledger(
        REVIEW_LEDGER, REVIEW_LEDGER_HASH
    ) == ()

    output = tmp_path / "review.sha256"
    digest = freeze_evidence_review_ledger(REVIEW_LEDGER, output)
    assert digest == hashlib.sha256(REVIEW_LEDGER.read_bytes()).hexdigest()
    assert output.read_text(encoding="utf-8") == (
        f"{digest}  {REVIEW_LEDGER.name}\n"
    )


def test_v2_review_ledger_rejects_conflicting_stable_source_hashes(
    tmp_path: Path,
) -> None:
    payload = json.loads(REVIEW_LEDGER.read_text(encoding="utf-8"))
    payload["assessments"].append(
        {
            **payload["assessments"][0],
            "source_record_sha256": "f" * 64,
        }
    )
    bad = tmp_path / "duplicate.json"
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate source_id"):
        load_evidence_review_ledger(bad)
