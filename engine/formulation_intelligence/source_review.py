"""Byte-bound advisory source review; not empirical or action admission."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
from functools import lru_cache
from typing import Any, Mapping

FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}
_REVIEW_STATES = {"LEGACY_ADVISORY", "REVIEWED_ADVISORY", "HOLD", "RETRACTED"}
_REVIEW_SCOPES = {
    "LEGACY_ADVISORY_SCOPE_NOT_FULL_TEXT_CERTIFIED",
    "PRIMARY_ABSTRACT",
    "SELECTED_PRIMARY_SECTIONS",
    "FULL_TEXT",
    "DISCOVERY_ONLY",
    "UNAVAILABLE",
}
_ISSUE_STATES = {
    "NOT_INDEPENDENTLY_RECHECKED",
    "NO_ISSUE_REPORTED_IN_BOUND_REVIEW",
    "CORRECTION_REVIEWED",
    "RETRACTED",
    "EXPRESSION_OF_CONCERN",
    "UNKNOWN",
    "NOT_APPLICABLE_MANUFACTURER_DESCRIPTION",
}
_RECORD_FIELDS = {
    "source_id", "source_record_sha256", "reviewed_on", "review_scope",
    "review_state", "correction_retraction_state", "rights_scope",
    "empirical_data_rights", "numeric_calibration_allowed", "reason",
}


def source_record_hash(source: Mapping[str, Any]) -> str:
    """Hash the exact local metadata object, not an unarchived publisher page."""
    return hashlib.sha256(
        json.dumps(source, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                   allow_nan=False).encode("utf-8")
    ).hexdigest()


@lru_cache(maxsize=8)
def _parse_reviews(payload: bytes) -> dict[str, Any]:
    value = json.loads(payload)
    if not isinstance(value, dict) or value.get("schema_version") != "formulation-source-reviews-v1":
        raise ValueError("unsupported source review schema")
    authority = value.get("authority")
    if not isinstance(authority, dict) or set(authority) != set(FALSE_AUTHORITY):
        raise ValueError("invalid source review authority")
    if any(flag is not False for flag in authority.values()):
        raise ValueError("source reviews cannot grant authority")
    if value.get("allowed_use") != "METADATA_AND_ORIGINAL_SUMMARY_ONLY":
        raise ValueError("source review use exceeds advisory rights")
    if value.get("binding_scope") != "CANONICAL_LOCAL_SOURCE_RECORD_NOT_PUBLISHER_PAGE_BYTES":
        raise ValueError("unsupported source binding scope")
    rows = value.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("missing source review records")
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != _RECORD_FIELDS:
            raise ValueError("invalid source review fields")
        source_id = row["source_id"]
        if not isinstance(source_id, str) or not source_id.strip() or source_id in ids:
            raise ValueError("invalid or duplicate source review identity")
        ids.add(source_id)
        if not isinstance(row["source_record_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", row["source_record_sha256"]
        ):
            raise ValueError("invalid source review hash")
        date.fromisoformat(row["reviewed_on"])
        if row["review_state"] not in _REVIEW_STATES or row["review_scope"] not in _REVIEW_SCOPES:
            raise ValueError("invalid source review state or scope")
        if row["correction_retraction_state"] not in _ISSUE_STATES:
            raise ValueError("invalid correction/retraction state")
        if row["rights_scope"] != "METADATA_AND_ORIGINAL_SUMMARY_ONLY":
            raise ValueError("source rights exceed original-summary scope")
        if row["empirical_data_rights"] != "NOT_ADMITTED" or row["numeric_calibration_allowed"] is not False:
            raise ValueError("empirical admission needs a separate governed capability")
        if not isinstance(row["reason"], str) or not row["reason"].strip():
            raise ValueError("source review needs an exact limitation")
        if row["review_state"] == "REVIEWED_ADVISORY" and row["review_scope"] in {
            "LEGACY_ADVISORY_SCOPE_NOT_FULL_TEXT_CERTIFIED", "DISCOVERY_ONLY", "UNAVAILABLE",
        }:
            raise ValueError("reviewed advisory cannot claim an unread source")
    return value


def load_source_reviews(payload: bytes) -> dict[str, Any]:
    return copy.deepcopy(_parse_reviews(payload))


def assess_source_use(source: Mapping[str, Any], review: Mapping[str, Any] | None,
                      *, requested_use: str = "ADVISORY_SUMMARY") -> dict[str, Any]:
    """A review may allow a bounded clue; never data reuse or numerical claims."""
    reason = "ADVISORY_SUMMARY_ONLY"
    allowed = False
    if requested_use != "ADVISORY_SUMMARY":
        reason = "SEPARATE_CAPABILITY_ADMISSION_REQUIRED"
    elif review is None:
        reason = "SOURCE_REVIEW_MISSING"
    elif review.get("source_id") != source.get("source_id") or review.get("source_record_sha256") != source_record_hash(source):
        reason = "SOURCE_REVIEW_BINDING_DRIFT"
    elif review.get("review_scope") not in _REVIEW_SCOPES or review.get("correction_retraction_state") not in _ISSUE_STATES:
        reason = "SOURCE_REVIEW_HOLD"
    elif review.get("correction_retraction_state") == "NOT_APPLICABLE_MANUFACTURER_DESCRIPTION" and source.get("evidence_class") != "MANUFACTURER_DESCRIPTION":
        reason = "SOURCE_ISSUE_SCOPE_MISMATCH"
    elif review.get("correction_retraction_state") in {"RETRACTED", "EXPRESSION_OF_CONCERN", "UNKNOWN"}:
        reason = "SOURCE_ISSUE_HOLD"
    elif review.get("review_state") not in {"LEGACY_ADVISORY", "REVIEWED_ADVISORY"}:
        reason = "SOURCE_REVIEW_HOLD"
    elif review.get("review_scope") in {"DISCOVERY_ONLY", "UNAVAILABLE"}:
        reason = "SOURCE_NOT_REVIEWED"
    elif review.get("review_state") == "REVIEWED_ADVISORY" and review.get("review_scope") == "LEGACY_ADVISORY_SCOPE_NOT_FULL_TEXT_CERTIFIED":
        reason = "SOURCE_NOT_REVIEWED"
    elif review.get("rights_scope") != "METADATA_AND_ORIGINAL_SUMMARY_ONLY" or review.get("empirical_data_rights") != "NOT_ADMITTED" or review.get("numeric_calibration_allowed") is not False:
        reason = "SOURCE_RIGHTS_HOLD"
    else:
        allowed = True
        if review["review_state"] == "LEGACY_ADVISORY":
            reason = "LEGACY_ADVISORY_NOT_NEW_FULL_TEXT_OR_RIGHTS_REVIEW"
    return {
        "source_id": source.get("source_id"), "requested_use": requested_use,
        "allowed": allowed, "reason_code": reason,
        "review_state": review.get("review_state") if review else None,
        "review_scope": review.get("review_scope") if review else None,
        "correction_retraction_state": review.get("correction_retraction_state") if review else None,
        "numeric_calibration_allowed": False,
        "empirical_data_admission": False, **FALSE_AUTHORITY,
    }


def assess_review_bundle(sources: list[dict[str, Any]], payload: bytes) -> dict[str, Any]:
    manifest = _parse_reviews(payload)
    reviews = {row["source_id"]: row for row in manifest["records"]}
    assessments = [assess_source_use(source, reviews.get(source["source_id"])) for source in sources]
    return {
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "assessments": assessments,
        "unavailable_source_ids": [row["source_id"] for row in assessments if not row["allowed"]],
        "authority": dict(FALSE_AUTHORITY),
    }
