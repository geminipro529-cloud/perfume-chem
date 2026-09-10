"""Rights-aware metadata intake and deterministic research-ledger freezing."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from engine.evidence_contracts import canonical_json_bytes, sha256_hex
from engine.solforge.evidence_review import (
    EVIDENCE_REVIEW_AUTHORITY_FLAGS,
    INTERFACE_FREEZE_POLICY_DECISIONS,
    TEMPORAL_OAV_INTERFACE_FIELDS,
    EvidenceReviewLedgerV1,
    EvidenceReviewLedgerV2,
    load_construct_registry,
    load_evidence_source_registry_v3,
    load_evidence_source_registry_v3_additions,
    load_hedonic_protocol_policy,
    load_oav_temporal_policy,
    validate_evidence_review,
    validate_evidence_review_v3,
)
from engine.solforge.research import (
    ResearchEvidenceRecordV1,
    ResearchLedgerV1,
    validate_research_ledger,
)

_DOI_RE = re.compile(r"(?:https?://doi\.org/|doi:\s*)?(10\.\d{4,9}/\S+)$", re.I)
_PMID_RE = re.compile(r"(?:pmid[:\s]+)(\d+)$", re.I)
_PMCID_RE = re.compile(r"(?:pmcid[:\s]+)(PMC\d+)$", re.I)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_V2_REVIEW_LEDGER = (
    _PROJECT_ROOT / "data/research/solforge/research_evidence_records_v2.json"
)
_V2_SOURCE_REGISTRY = (
    _PROJECT_ROOT / "configs/solforge/complexity_evidence_sources_v2.json"
)
_V3_SOURCE_REGISTRY = (
    _PROJECT_ROOT / "configs/solforge/complexity_evidence_sources_v3.json"
)
_CONSTRUCT_REGISTRY = (
    _PROJECT_ROOT / "configs/solforge/complexity_construct_registry_v1.json"
)
_OAV_TEMPORAL_POLICY = _PROJECT_ROOT / "configs/solforge/oav_temporal_policy_v1.json"
_HEDONIC_PROTOCOL_POLICY = (
    _PROJECT_ROOT / "configs/solforge/hedonic_protocol_policy_v1.json"
)

_INTERFACE_ARTIFACT_IDS = (
    "baseline",
    "construct_registry",
    "evidence_ledger_v2",
    "evidence_ledger_v3",
    "evidence_review_source",
    "evidence_review_tests",
    "evidence_sources_v2",
    "evidence_sources_v3",
    "hedonic_protocol_policy",
    "oav_temporal_policy",
    "research_ingest_source",
    "research_ingest_tests",
)


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


def load_evidence_review_ledger_v3(
    path: Path,
    *,
    predecessor_path: Path = _V2_REVIEW_LEDGER,
    source_registry_path: Path = _V3_SOURCE_REGISTRY,
    source_predecessor_path: Path = _V2_SOURCE_REGISTRY,
    construct_registry_path: Path = _CONSTRUCT_REGISTRY,
    oav_policy_path: Path = _OAV_TEMPORAL_POLICY,
    hedonic_policy_path: Path = _HEDONIC_PROTOCOL_POLICY,
) -> EvidenceReviewLedgerV2:
    """Load the canonical V3 overlay and validate every bound predecessor."""

    input_path = Path(path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    ledger = EvidenceReviewLedgerV2.from_dict(payload)
    observed_predecessor = sha256_hex(Path(predecessor_path).read_bytes())
    if ledger.predecessor_ledger_sha256 != observed_predecessor:
        raise ValueError("predecessor ledger SHA-256 mismatch")
    predecessor = load_evidence_review_ledger(predecessor_path)

    observed_sources = sha256_hex(Path(source_registry_path).read_bytes())
    if ledger.source_seed_manifest_sha256 != observed_sources:
        raise ValueError("V3 source registry SHA-256 mismatch")
    source_records = load_evidence_source_registry_v3(
        source_registry_path, source_predecessor_path
    )
    additions = load_evidence_source_registry_v3_additions(
        source_registry_path, source_predecessor_path
    )

    load_construct_registry(construct_registry_path)
    if ledger.construct_registry_sha256 != sha256_hex(
        Path(construct_registry_path).read_bytes()
    ):
        raise ValueError("construct registry SHA-256 mismatch")
    load_oav_temporal_policy(oav_policy_path)
    if ledger.oav_temporal_policy_sha256 != sha256_hex(
        Path(oav_policy_path).read_bytes()
    ):
        raise ValueError("OAV temporal policy SHA-256 mismatch")
    load_hedonic_protocol_policy(hedonic_policy_path)
    if ledger.hedonic_protocol_policy_sha256 != sha256_hex(
        Path(hedonic_policy_path).read_bytes()
    ):
        raise ValueError("hedonic protocol policy SHA-256 mismatch")

    if not additions:
        raise ValueError("V3 source registry requires an additive overlay")
    if tuple(item.source_id for item in ledger.added_assessments) != tuple(
        sorted(item.source_id for item in ledger.added_assessments)
    ):
        raise ValueError("V3 added_assessments must be sorted by source_id")
    if tuple(
        item.requirement_id for item in ledger.added_operative_bindings
    ) != tuple(sorted(item.requirement_id for item in ledger.added_operative_bindings)):
        raise ValueError("V3 added_operative_bindings must be sorted by requirement_id")
    issues = validate_evidence_review_v3(ledger, predecessor, source_records)
    if issues:
        raise ValueError("; ".join(issues))
    expected = ledger.canonical_bytes() + b"\n"
    if input_path.read_bytes() != expected:
        raise ValueError("V3 evidence review ledger is not canonical JSON")
    return ledger


def freeze_evidence_review_ledger_v3(input_path: Path, sha_output: Path) -> str:
    """Validate and freeze exact canonical V3 review-ledger bytes."""

    load_evidence_review_ledger_v3(input_path)
    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    Path(sha_output).parent.mkdir(parents=True, exist_ok=True)
    Path(sha_output).write_text(
        f"{digest}  {Path(input_path).name}\n", encoding="utf-8", newline="\n"
    )
    return digest


def validate_frozen_evidence_review_ledger_v3(
    input_path: Path, sha_path: Path
) -> tuple[str, ...]:
    """Return exact validation and sidecar failures for the V3 overlay."""

    issues: list[str] = []
    try:
        load_evidence_review_ledger_v3(input_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        issues.append(f"V3 evidence review ledger validation failed: {exc}")
    try:
        expected = Path(sha_path).read_text(encoding="utf-8").split()[0]
        observed = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
        if expected != observed:
            issues.append("V3 evidence review ledger SHA-256 sidecar mismatch")
    except (OSError, UnicodeError, IndexError):
        issues.append("V3 evidence review ledger SHA-256 sidecar is unavailable")
    return tuple(issues)


def load_interface_receipt(path: Path) -> dict[str, object]:
    """Load the closed canonical interface receipt without following its paths."""

    input_path = Path(path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "artifacts",
        "interfaces",
        "policy_decisions",
        "authority_flags",
    }:
        raise ValueError("interface receipt does not match the closed schema")
    if payload["schema_version"] != "temporal_oav_hedonic_interface_freeze_v1":
        raise ValueError("interface receipt schema_version is invalid")
    if payload["authority_flags"] != EVIDENCE_REVIEW_AUTHORITY_FLAGS:
        raise ValueError("interface receipt authority_flags are invalid")
    if payload["interfaces"] != TEMPORAL_OAV_INTERFACE_FIELDS:
        raise ValueError("interface receipt fields do not match frozen interfaces")
    if payload["policy_decisions"] != list(INTERFACE_FREEZE_POLICY_DECISIONS):
        raise ValueError("interface receipt policy decisions are invalid")
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, list):
        raise TypeError("interface receipt artifacts must be a list")
    artifact_ids: list[str] = []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != {
            "artifact_id",
            "path",
            "sha256",
        }:
            raise ValueError("interface receipt artifact does not match the schema")
        artifact_id = artifact["artifact_id"]
        artifact_path = artifact["path"]
        if not isinstance(artifact_id, str) or not isinstance(artifact_path, str):
            raise TypeError("interface receipt artifact identity and path must be text")
        if (
            not artifact_path
            or "\\" in artifact_path
            or Path(artifact_path).is_absolute()
            or ".." in Path(artifact_path).parts
        ):
            raise ValueError("interface receipt artifact path must be repository-relative")
        artifact_sha256 = artifact["sha256"]
        if (
            not isinstance(artifact_sha256, str)
            or _SHA256_RE.fullmatch(artifact_sha256) is None
        ):
            raise ValueError("interface receipt artifact sha256 is invalid")
        artifact_ids.append(artifact_id)
    if tuple(artifact_ids) != _INTERFACE_ARTIFACT_IDS:
        raise ValueError("interface receipt artifact identifiers or order are invalid")
    if input_path.read_bytes() != canonical_json_bytes(payload) + b"\n":
        raise ValueError("interface receipt is not canonical JSON")
    return payload


def _validate_interface_artifacts(
    payload: dict[str, object], repo_root: Path
) -> tuple[str, ...]:
    issues: list[str] = []
    root = Path(repo_root).resolve()
    for artifact in payload["artifacts"]:
        artifact_path = (root / artifact["path"]).resolve()
        try:
            artifact_path.relative_to(root)
        except ValueError:
            issues.append(f"artifact path escapes repository: {artifact['artifact_id']}")
            continue
        try:
            observed = sha256_hex(artifact_path.read_bytes())
        except OSError:
            issues.append(f"artifact is unavailable: {artifact['artifact_id']}")
            continue
        if observed != artifact["sha256"]:
            issues.append(f"artifact SHA-256 mismatch: {artifact['artifact_id']}")
    return tuple(issues)


def validate_frozen_interface_receipt(
    input_path: Path,
    sha_path: Path,
    *,
    repo_root: Path = _PROJECT_ROOT,
) -> tuple[str, ...]:
    """Validate canonical receipt, bound artifact bytes, and receipt sidecar."""

    issues: list[str] = []
    payload: dict[str, object] | None = None
    try:
        payload = load_interface_receipt(input_path)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        issues.append(f"interface receipt validation failed: {exc}")
    if payload is not None:
        issues.extend(_validate_interface_artifacts(payload, repo_root))
    try:
        expected = Path(sha_path).read_text(encoding="utf-8").split()[0]
        observed = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
        if expected != observed:
            issues.append("interface receipt SHA-256 sidecar mismatch")
    except (OSError, UnicodeError, IndexError):
        issues.append("interface receipt SHA-256 sidecar is unavailable")
    return tuple(issues)


def freeze_interface_receipt(
    input_path: Path,
    sha_output: Path,
    *,
    repo_root: Path = _PROJECT_ROOT,
) -> str:
    """Freeze an interface receipt only after all bound bytes validate."""

    payload = load_interface_receipt(input_path)
    issues = _validate_interface_artifacts(payload, repo_root)
    if issues:
        raise ValueError("; ".join(issues))
    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    Path(sha_output).parent.mkdir(parents=True, exist_ok=True)
    Path(sha_output).write_text(
        f"{digest}  {Path(input_path).name}\n", encoding="utf-8", newline="\n"
    )
    return digest


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
    validate_v3 = subparsers.add_parser("validate-v3")
    validate_v3.add_argument("--input", type=Path, required=True)
    freeze_v3 = subparsers.add_parser("freeze-v3")
    freeze_v3.add_argument("--input", type=Path, required=True)
    freeze_v3.add_argument("--sha-output", type=Path, required=True)
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
    if args.action == "validate-v3":
        load_evidence_review_ledger_v3(args.input)
        return 0
    if args.action == "freeze-v3":
        freeze_evidence_review_ledger_v3(args.input, args.sha_output)
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
    "freeze_evidence_review_ledger_v3",
    "freeze_interface_receipt",
    "freeze_ledger",
    "load_evidence_review_ledger",
    "load_evidence_review_ledger_v3",
    "load_interface_receipt",
    "load_ledger",
    "merge_records",
    "normalize_stable_identifier",
    "validate_frozen_evidence_review_ledger",
    "validate_frozen_evidence_review_ledger_v3",
    "validate_frozen_interface_receipt",
    "validate_frozen_ledger",
]
