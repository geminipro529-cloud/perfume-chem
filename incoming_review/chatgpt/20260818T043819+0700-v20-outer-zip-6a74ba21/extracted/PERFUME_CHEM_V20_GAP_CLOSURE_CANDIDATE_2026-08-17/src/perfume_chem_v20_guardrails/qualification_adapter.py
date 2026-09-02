"""Lossless legacy Qualification v1 to current-policy adapter.

The raw legacy result is preserved. G14 and aggregate quality-score behavior are
marked non-governing for the current policy rather than rewritten in place.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from .canonical import sha256_payload


NON_GOVERNING_CURRENT_GATES = frozenset({"G14"})


@dataclass(frozen=True)
class LegacyQualificationAdapterResult:
    fixture_id: str
    legacy_raw_preserved: Mapping[str, Any]
    legacy_state: str
    current_policy_state: str
    normalized_expected_failed_gates: tuple[str, ...]
    normalized_observed_failed_gates: tuple[str, ...]
    current_policy_gate_sets_match: bool
    legacy_fixture_still_quarantined: bool
    authority_promoted: bool
    adapter_hash: str


def adapt_legacy_qualification(
    *,
    fixture_id: str,
    expected_state: str,
    observed_state: str,
    expected_failed_gates: Iterable[str],
    observed_failed_gates: Iterable[str],
    raw_record: Mapping[str, Any],
) -> LegacyQualificationAdapterResult:
    raw = deepcopy(dict(raw_record))
    expected = tuple(sorted(set(expected_failed_gates)))
    observed = tuple(sorted(set(observed_failed_gates)))
    normalized_expected = tuple(gate for gate in expected if gate not in NON_GOVERNING_CURRENT_GATES)
    normalized_observed = tuple(gate for gate in observed if gate not in NON_GOVERNING_CURRENT_GATES)
    gate_match = normalized_expected == normalized_observed

    if expected_state != observed_state:
        current_state = "HOLD_LEGACY_STATE_MISMATCH"
    elif gate_match:
        current_state = "CURRENT_POLICY_COMPATIBLE__LEGACY_G14_NON_GOVERNING"
    else:
        current_state = "HOLD_CURRENT_POLICY_GATE_MISMATCH"

    # The legacy artifact contains binary JSON numbers. Preserve the parsed raw
    # record unchanged, but bind it through a transport digest rather than
    # allowing those floats into the current exact-quantity canonicalizer.
    legacy_raw_digest = hashlib.sha256(
        json.dumps(raw, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
    payload = {
        "fixture_id": fixture_id,
        "legacy_state": observed_state,
        "current_policy_state": current_state,
        "normalized_expected_failed_gates": list(normalized_expected),
        "normalized_observed_failed_gates": list(normalized_observed),
        "current_policy_gate_sets_match": gate_match,
        "legacy_fixture_still_quarantined": True,
        "authority_promoted": False,
        "legacy_raw_digest": legacy_raw_digest,
    }
    return LegacyQualificationAdapterResult(
        fixture_id=fixture_id,
        legacy_raw_preserved=raw,
        legacy_state=observed_state,
        current_policy_state=current_state,
        normalized_expected_failed_gates=normalized_expected,
        normalized_observed_failed_gates=normalized_observed,
        current_policy_gate_sets_match=gate_match,
        legacy_fixture_still_quarantined=True,
        authority_promoted=False,
        adapter_hash=sha256_payload(payload, domain="PERFUME_CHEM_LEGACY_QUALIFICATION_ADAPTER_V20"),
    )
