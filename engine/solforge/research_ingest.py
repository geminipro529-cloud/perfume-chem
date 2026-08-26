"""Rights-aware metadata intake and deterministic research-ledger freezing."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from engine.solforge.evidence_review import (
    EvidenceReviewLedgerV1,
    validate_evidence_review,
)
from engine.solforge.research import (
    ResearchEvidenceRecordV1,
    ResearchLedgerV1,
    validate_research_ledger,
)

_DOI_RE = re.compile(r"(?:https?://doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)$", re.I)
_PMID_RE = re.compile(r"(?:pmid[:\s]+)(\d+)$", re.I)
_PMCID_RE = re.compile(r"(?:pmcid[:\s]+)(PMC\d+)$", re.I)


def normalize_stable_identifier(value: str) -> str:
    """Normalize supported identifiers without guessing an unknown citation."""

    text = value.strip()
    doi = _DOI_RE.fullmatch(text)
    if doi:
        return "doi:" + doi.group(1).rstrip(".,").casefold()
    pmid = _PMID_RE.fullmatch(text)
    if pmid:
        return "pmid:" + pmid.group(1)
    pmcid = _PMCID_RE.fullmatch(text)
    if pmcid:
        return "pmcid:" + pmcid.group(1).casefold()
    raise ValueError("unsupported stable identifier")


def build_metadata_envelope(
    *,
    stable_identifier: str,
    search_status: str,
    title: str | None,
    publication_status: str,
    related_notice_ids: tuple[str, ...],
    acquired_at_utc: str,
) -> dict[str, object]:
    """Keep volatile acquisition time outside the stable metadata core."""

    status = search_status.strip().upper()
    if status not in {"RESOLVED", "UNRESOLVED"}:
        raise ValueError("search_status is invalid")
    return {
        "stable_metadata": {
            "stable_identifier": normalize_stable_identifier(stable_identifier),
            "search_status": status,
            "title": title.strip() if isinstance(title, str) and title.strip() else None,
            "publication_status": publication_status.strip().upper(),
            "related_notice_ids": list(related_notice_ids),
        },
        "acquired_at_utc": acquired_at_utc,
    }


def fetch_metadata(
    stable_identifier: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
) -> dict[str, object]:
    """Fetch official DOI/PubMed metadata or return an explicit unresolved record."""

    identifier = normalize_stable_identifier(stable_identifier)
    headers = {"User-Agent": "Perfume-Chem-SolForge/1.0"}
    if identifier.startswith("doi:"):
        url = "https://doi.org/" + identifier.removeprefix("doi:")
        headers["Accept"] = "application/vnd.citationstyles.csl+json"
    else:
        pmid = identifier.removeprefix("pmid:")
        url = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
            f"?db=pubmed&id={pmid}&retmode=json"
        )
    acquired = datetime.now(timezone.utc).isoformat()
    try:
        request = urllib.request.Request(url, headers=headers)
        with opener(request, timeout=20) as response:
            metadata = json.loads(response.read().decode("utf-8"))
        title = metadata.get("title")
        if identifier.startswith("pmid:"):
            uid = identifier.removeprefix("pmid:")
            title = metadata.get("result", {}).get(uid, {}).get("title")
        return build_metadata_envelope(
            stable_identifier=identifier,
            search_status="RESOLVED",
            title=title,
            publication_status="PUBLISHED",
            related_notice_ids=(),
            acquired_at_utc=acquired,
        )
    except (OSError, ValueError, KeyError, urllib.error.URLError, json.JSONDecodeError):
        return build_metadata_envelope(
            stable_identifier=identifier,
            search_status="UNRESOLVED",
            title=None,
            publication_status="UNKNOWN",
            related_notice_ids=(),
            acquired_at_utc=acquired,
        )


def merge_records(
    records: tuple[ResearchEvidenceRecordV1, ...],
) -> tuple[ResearchEvidenceRecordV1, ...]:
    """Deduplicate exact source records and reject conflicting silent replacement."""

    by_identifier: dict[str, ResearchEvidenceRecordV1] = {}
    for record in records:
        key = record.stable_identifier.casefold()
        previous = by_identifier.get(key)
        if previous is not None and previous.record_sha256 != record.record_sha256:
            raise ValueError(f"conflicting duplicate source: {record.stable_identifier}")
        by_identifier[key] = record
    return tuple(sorted(by_identifier.values(), key=lambda item: item.source_id))


def load_ledger(path: Path) -> ResearchLedgerV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    ledger = ResearchLedgerV1.from_dict(payload)
    issues = validate_research_ledger(ledger)
    if issues:
        raise ValueError("; ".join(issues))
    return ledger


def freeze_ledger(input_path: Path, sha_output: Path) -> str:
    """Validate exact ledger bytes, then write their RFC-style SHA sidecar."""

    load_ledger(input_path)
    import hashlib

    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    Path(sha_output).parent.mkdir(parents=True, exist_ok=True)
    Path(sha_output).write_text(
        f"{digest}  {Path(input_path).name}\n", encoding="utf-8", newline="\n"
    )
    return digest


def validate_frozen_ledger(input_path: Path, sha_path: Path) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        load_ledger(input_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        issues.append(f"ledger validation failed: {exc}")
    try:
        expected = Path(sha_path).read_text(encoding="utf-8").split()[0]
        import hashlib

        observed = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
        if expected != observed:
            issues.append("ledger SHA-256 sidecar mismatch")
    except (OSError, UnicodeError, IndexError):
        issues.append("ledger SHA-256 sidecar is unavailable")
    return tuple(issues)


def load_evidence_review_ledger(path: Path) -> EvidenceReviewLedgerV1:
    """Load a canonical V2 review ledger and validate every cross-reference."""

    input_path = Path(path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    ledger = EvidenceReviewLedgerV1.from_dict(payload)
    issues = validate_evidence_review(ledger)
    if issues:
        raise ValueError("; ".join(issues))
    if not ledger.source_records:
        raise ValueError("V2 evidence review ledger requires source_records")
    if tuple(item.source_id for item in ledger.source_records) != tuple(
        sorted(item.source_id for item in ledger.source_records)
    ):
        raise ValueError("source_records must be sorted by source_id")
    if tuple(item.source_id for item in ledger.assessments) != tuple(
        sorted(item.source_id for item in ledger.assessments)
    ):
        raise ValueError("assessments must be sorted by source_id")
    if tuple(item.requirement_id for item in ledger.operative_bindings) != tuple(
        sorted(item.requirement_id for item in ledger.operative_bindings)
    ):
        raise ValueError("operative_bindings must be sorted by requirement_id")
    expected = ledger.canonical_bytes() + b"\n"
    if input_path.read_bytes() != expected:
        raise ValueError("V2 evidence review ledger is not canonical JSON")
    return ledger


def freeze_evidence_review_ledger(input_path: Path, sha_output: Path) -> str:
    """Validate and freeze the exact canonical V2 review-ledger bytes."""

    load_evidence_review_ledger(input_path)
    import hashlib

    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    Path(sha_output).parent.mkdir(parents=True, exist_ok=True)
    Path(sha_output).write_text(
        f"{digest}  {Path(input_path).name}\n", encoding="utf-8", newline="\n"
    )
    return digest


def validate_frozen_evidence_review_ledger(
    input_path: Path, sha_path: Path
) -> tuple[str, ...]:
    """Return exact validation and sidecar failures for a V2 review ledger."""

    issues: list[str] = []
    try:
        load_evidence_review_ledger(input_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        issues.append(f"evidence review ledger validation failed: {exc}")
    try:
        expected = Path(sha_path).read_text(encoding="utf-8").split()[0]
        import hashlib

        observed = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
        if expected != observed:
            issues.append("evidence review ledger SHA-256 sidecar mismatch")
    except (OSError, UnicodeError, IndexError):
        issues.append("evidence review ledger SHA-256 sidecar is unavailable")
    return tuple(issues)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    fetch = subparsers.add_parser("fetch-metadata")
    fetch.add_argument("--identifier", required=True)
    fetch.add_argument("--output", type=Path, required=True)
    ingest = subparsers.add_parser("ingest-record")
    ingest.add_argument("--ledger", type=Path, required=True)
    ingest.add_argument("--record", type=Path, required=True)
    ingest.add_argument("--output", type=Path, required=True)
    validate = subparsers.add_parser("validate-ledger")
    validate.add_argument("--input", type=Path, required=True)
    freeze = subparsers.add_parser("freeze-ledger")
    freeze.add_argument("--input", type=Path, required=True)
    freeze.add_argument("--sha-output", type=Path, required=True)
    validate_v2 = subparsers.add_parser("validate-v2")
    validate_v2.add_argument("--input", type=Path, required=True)
    freeze_v2 = subparsers.add_parser("freeze-v2")
    freeze_v2.add_argument("--input", type=Path, required=True)
    freeze_v2.add_argument("--sha-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.action == "fetch-metadata":
        payload = fetch_metadata(args.identifier)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return 0
    if args.action == "validate-ledger":
        load_ledger(args.input)
        return 0
    if args.action == "freeze-ledger":
        freeze_ledger(args.input, args.sha_output)
        return 0
    if args.action == "validate-v2":
        load_evidence_review_ledger(args.input)
        return 0
    if args.action == "freeze-v2":
        freeze_evidence_review_ledger(args.input, args.sha_output)
        return 0
    ledger = load_ledger(args.ledger)
    record = ResearchEvidenceRecordV1.from_dict(
        json.loads(args.record.read_text(encoding="utf-8"))
    )
    merged = ResearchLedgerV1(
        source_seed_manifest_sha256=ledger.source_seed_manifest_sha256,
        records=merge_records((*ledger.records, record)),
        conflicts=ledger.conflicts,
        unresolved_questions=ledger.unresolved_questions,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(merged.canonical_bytes() + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "build_metadata_envelope",
    "fetch_metadata",
    "freeze_evidence_review_ledger",
    "freeze_ledger",
    "load_evidence_review_ledger",
    "load_ledger",
    "merge_records",
    "normalize_stable_identifier",
    "validate_frozen_evidence_review_ledger",
    "validate_frozen_ledger",
]
