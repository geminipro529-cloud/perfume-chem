"""Versioned IFRA policy selection and exact-identity screening boundaries.

The effective amendment and the locally executable screening subset are two
different objects.  The former is policy status; the latter is incomplete
software data and cannot establish regulatory compliance or product safety.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

from engine.research.contracts import FALSE_ACTION_AUTHORITY

_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_MANIFEST = (
    _ROOT / "data" / "governance" / "ifra_policy_status_20260927.json"
)

PolicyStatus = Literal["EFFECTIVE_BUILT_IN_POLICY", "PENDING_NOTIFICATION"]
MatchState = Literal[
    "EXPLICIT_APPLICABLE_LIMIT",
    "EXPLICIT_DOCUMENTED_NOT_RESTRICTED",
    "NO_MATCHING_RECORD",
]


class SafetyPolicyError(ValueError):
    """Raised when the policy manifest is malformed or an inactive policy is used."""


@dataclass(frozen=True, slots=True)
class PolicyRecordV1:
    policy_id: str
    amendment: int
    status: PolicyStatus
    notification_date: str | None
    expected_notification_window: str | None
    official_sources: tuple[dict[str, str], ...]
    notification_required_before_activation: bool


@dataclass(frozen=True, slots=True)
class ScreeningResultV1:
    policy_id: str
    policy_status: PolicyStatus
    dataset_id: str
    dataset_sha256: str
    material_query: str
    canonical_material: str | None
    match_state: MatchState
    maximum_finished_product_pct: float | None
    validation_state: Literal["ADVISORY_FINDINGS", "WITHHOLD_UNKNOWN"]
    coverage_state: str
    regulatory_compliance_determination: bool = False
    release_authority: bool = False
    safety_authority: bool = False
    compounding_authority: bool = False
    evidence_admission_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ifra-screening-result-v1",
            "policy_id": self.policy_id,
            "policy_status": self.policy_status,
            "dataset_id": self.dataset_id,
            "dataset_sha256": self.dataset_sha256,
            "material_query": self.material_query,
            "canonical_material": self.canonical_material,
            "match_state": self.match_state,
            "maximum_finished_product_pct": self.maximum_finished_product_pct,
            "validation_state": self.validation_state,
            "coverage_state": self.coverage_state,
            "regulatory_compliance_determination": False,
            **FALSE_ACTION_AUTHORITY,
        }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity_key(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SafetyPolicyError("material identity must be non-empty text")
    return " ".join(value.split()).casefold()


def load_policy_manifest(path: Path = _DEFAULT_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "ifra-policy-status-v1":
        raise SafetyPolicyError("unsupported IFRA policy manifest schema")
    policies = payload.get("policies")
    if not isinstance(policies, list) or not policies:
        raise SafetyPolicyError("IFRA policy manifest requires policies")
    identifiers = [record.get("policy_id") for record in policies]
    if len(identifiers) != len(set(identifiers)):
        raise SafetyPolicyError("IFRA policy identifiers must be unique")
    effective_id = payload.get("effective_policy_id")
    effective = [
        record
        for record in policies
        if record.get("status") == "EFFECTIVE_BUILT_IN_POLICY"
    ]
    if len(effective) != 1 or effective[0].get("policy_id") != effective_id:
        raise SafetyPolicyError("exactly one declared IFRA policy must be effective")
    for record in policies:
        if record.get("status") == "PENDING_NOTIFICATION" and record.get(
            "notification_date"
        ) is not None:
            raise SafetyPolicyError("pending IFRA policy cannot have a notification date")
    authority = payload.get("authority", {})
    if any(authority.get(key) is not False for key in FALSE_ACTION_AUTHORITY):
        raise SafetyPolicyError("IFRA policy manifest cannot grant action authority")
    if authority.get("regulatory_compliance_determination") is not False:
        raise SafetyPolicyError("screening manifest cannot grant compliance authority")
    dataset = payload.get("runtime_dataset", {})
    source_path = _ROOT / str(dataset.get("source_path", ""))
    expected_hash = dataset.get("source_sha256")
    if not source_path.is_file() or _file_sha256(source_path) != expected_hash:
        raise SafetyPolicyError("IFRA screening source does not match its bound hash")
    if dataset.get("policy_id") != effective_id:
        raise SafetyPolicyError("runtime IFRA subset must bind the effective policy")
    return payload


def policy_record(
    policy_id: str, path: Path = _DEFAULT_MANIFEST
) -> PolicyRecordV1:
    payload = load_policy_manifest(path)
    record = next(
        (
            item
            for item in payload["policies"]
            if item.get("policy_id") == policy_id
        ),
        None,
    )
    if record is None:
        raise SafetyPolicyError(f"unknown IFRA policy: {policy_id}")
    return PolicyRecordV1(
        policy_id=record["policy_id"],
        amendment=int(record["amendment"]),
        status=record["status"],
        notification_date=record.get("notification_date"),
        expected_notification_window=record.get("expected_notification_window"),
        official_sources=tuple(record.get("official_sources", ())),
        notification_required_before_activation=bool(
            record.get("notification_required_before_activation")
        ),
    )


def effective_policy(path: Path = _DEFAULT_MANIFEST) -> PolicyRecordV1:
    payload = load_policy_manifest(path)
    return policy_record(payload["effective_policy_id"], path)


def require_effective_policy(
    policy_id: str, path: Path = _DEFAULT_MANIFEST
) -> PolicyRecordV1:
    record = policy_record(policy_id, path)
    if record.status != "EFFECTIVE_BUILT_IN_POLICY":
        raise SafetyPolicyError(
            f"IFRA policy {policy_id} is {record.status} and cannot be selected"
        )
    return record


def resolve_category4_screening(
    material: str,
    *,
    policy_id: str | None = None,
    path: Path = _DEFAULT_MANIFEST,
) -> ScreeningResultV1:
    """Resolve only exact identities and explicitly admitted aliases.

    The returned limit is a legacy screening datum under the effective policy,
    never a complete IFRA or regulatory determination.
    """

    payload = load_policy_manifest(path)
    selected_id = policy_id or payload["effective_policy_id"]
    selected = require_effective_policy(selected_id, path)
    dataset = payload["runtime_dataset"]
    if selected.policy_id != dataset["policy_id"]:
        raise SafetyPolicyError("no runtime screening dataset for selected policy")

    from engine.ifra_standards import load_ifra_table  # noqa: PLC0415

    # Sourced Cat 4 table: its canonical names and aliases resolve exactly
    # (case/whitespace-insensitive, no substring matching). Restricted
    # materials carry their limit and prohibited ones 0.0; every other status
    # has no numeric limit and falls through to the manifest records below.
    ifra_table = load_ifra_table()
    table: dict[str, tuple[str, float]] = {}
    for record in ifra_table.materials.values():
        if record.status == "restricted" and record.cat4_limit_pct is not None:
            value = float(record.cat4_limit_pct)
        elif record.status == "prohibited":
            value = 0.0
        else:
            continue
        for name in (record.name, *record.aliases):
            key = _identity_key(name)
            if key in table and table[key][0] != record.name:
                raise SafetyPolicyError("normalized IFRA screening identity collision")
            table[key] = (record.name, value)
    aliases = {
        _identity_key(alias): _identity_key(target)
        for alias, target in dataset.get("admitted_aliases", {}).items()
    }
    documented_unrestricted = {
        _identity_key(value)
        for value in dataset.get("documented_not_restricted", [])
    }
    query_key = _identity_key(material)
    resolved_key = aliases.get(query_key, query_key)
    source_hash = dataset["source_sha256"]
    common = {
        "policy_id": selected.policy_id,
        "policy_status": selected.status,
        "dataset_id": dataset["dataset_id"],
        "dataset_sha256": source_hash,
        "material_query": material,
        "coverage_state": dataset["coverage_state"],
    }
    if resolved_key in table:
        canonical, value = table[resolved_key]
        return ScreeningResultV1(
            **common,
            canonical_material=canonical,
            match_state="EXPLICIT_APPLICABLE_LIMIT",
            maximum_finished_product_pct=value,
            validation_state="ADVISORY_FINDINGS",
        )
    if resolved_key in documented_unrestricted:
        return ScreeningResultV1(
            **common,
            canonical_material=next(
                value
                for value in dataset["documented_not_restricted"]
                if _identity_key(value) == resolved_key
            ),
            match_state="EXPLICIT_DOCUMENTED_NOT_RESTRICTED",
            maximum_finished_product_pct=None,
            validation_state="ADVISORY_FINDINGS",
        )
    return ScreeningResultV1(
        **common,
        canonical_material=None,
        match_state="NO_MATCHING_RECORD",
        maximum_finished_product_pct=None,
        validation_state="WITHHOLD_UNKNOWN",
    )


__all__ = [
    "PolicyRecordV1",
    "SafetyPolicyError",
    "ScreeningResultV1",
    "effective_policy",
    "load_policy_manifest",
    "policy_record",
    "require_effective_policy",
    "resolve_category4_screening",
]
