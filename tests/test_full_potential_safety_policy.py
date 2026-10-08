from __future__ import annotations

import json

import pytest

from engine.research.safety_policy import (
    SafetyPolicyError,
    effective_policy,
    policy_record,
    require_effective_policy,
    resolve_category4_screening,
)


def test_51st_is_effective_and_52nd_remains_pending() -> None:
    assert effective_policy().policy_id == "IFRA_51ST_AMENDMENT"
    pending = policy_record("IFRA_52ND_AMENDMENT")
    assert pending.status == "PENDING_NOTIFICATION"
    assert pending.notification_date is None
    with pytest.raises(SafetyPolicyError, match="cannot be selected"):
        require_effective_policy(pending.policy_id)


def test_exact_identity_and_admitted_alias_resolve_only_as_screening() -> None:
    exact = resolve_category4_screening("  Benzyl   Salicylate ")
    admitted_alias = resolve_category4_screening("alpha isomethyl ionone")
    no_standard = resolve_category4_screening("Ambrox Super")

    assert exact.match_state == "EXPLICIT_APPLICABLE_LIMIT"
    assert exact.maximum_finished_product_pct == 7.3
    assert admitted_alias.canonical_material == "Alpha Isomethyl Ionone"
    assert admitted_alias.maximum_finished_product_pct == 30.0
    assert no_standard.match_state == "NO_MATCHING_RECORD"
    assert no_standard.maximum_finished_product_pct is None
    assert exact.as_dict()["regulatory_compliance_determination"] is False
    assert all(
        exact.as_dict()[key] is False
        for key in (
            "release_authority",
            "safety_authority",
            "compounding_authority",
            "evidence_admission_authorized",
        )
    )


def test_substrings_and_unknowns_never_borrow_a_limit() -> None:
    partial = resolve_category4_screening("Ambrox")
    substring = resolve_category4_screening("Super")

    assert partial.match_state == "NO_MATCHING_RECORD"
    assert substring.match_state == "NO_MATCHING_RECORD"
    assert partial.validation_state == "WITHHOLD_UNKNOWN"
    assert partial.maximum_finished_product_pct is None


def test_manifest_cannot_activate_pending_policy(tmp_path) -> None:
    from engine.research.safety_policy import _DEFAULT_MANIFEST  # noqa: PLC0415

    payload = json.loads(_DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    payload["effective_policy_id"] = "IFRA_52ND_AMENDMENT"
    target = tmp_path / "bad-policy.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SafetyPolicyError, match="exactly one"):
        effective_policy(target)
