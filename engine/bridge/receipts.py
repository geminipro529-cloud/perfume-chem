"""Canonical JSON hashing and optional HMAC sealing for bridge receipts."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
from typing import Any, Mapping


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for hashing and signing."""

    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def seal_receipt(payload: Mapping[str, Any], signing_key: bytes | None) -> dict[str, Any]:
    """Add a canonical SHA-256 and optional HMAC-SHA256 signature."""

    base = copy.deepcopy(dict(payload))
    base.pop("receipt_sha256", None)
    base.pop("signature", None)
    digest = hashlib.sha256(canonical_json_bytes(base)).hexdigest()
    sealed = {**base, "receipt_sha256": digest}
    if signing_key:
        signature = hmac.new(
            signing_key,
            canonical_json_bytes(sealed),
            hashlib.sha256,
        ).hexdigest()
        sealed["signature"] = {
            "algorithm": "HMAC-SHA256",
            "state": "SIGNED",
            "value": signature,
        }
    else:
        sealed["signature"] = {
            "algorithm": "HMAC-SHA256",
            "state": "UNSIGNED",
        }
    return sealed
