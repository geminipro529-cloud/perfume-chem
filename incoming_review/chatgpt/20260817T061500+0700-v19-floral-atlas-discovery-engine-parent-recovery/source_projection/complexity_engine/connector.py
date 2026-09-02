from __future__ import annotations

import re
from typing import Any

from consultant_core import sha256_json

_HASH = re.compile(r"^[0-9a-fA-F]{64}$")


def validate_connector_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    connector_id = str(receipt.get("connector_id") or "").lower()
    canary = str(receipt.get("canary_state") or "NOT_RUN").upper()

    if not receipt.get("server_identity"):
        failures.append("server_identity is required.")
    if not receipt.get("protocol_version"):
        failures.append("protocol_version is required.")
    if not receipt.get("transport"):
        failures.append("transport is required.")
    if not receipt.get("toolsets"):
        failures.append("At least one toolset/capability is required.")

    if canary != "PASS":
        failures.append("A registry record, tag, or link is not an attached connector; a scoped canary must pass.")
    else:
        if not receipt.get("canary_nonce"):
            failures.append("PASS canary requires canary_nonce.")
        for field in ("canary_request_hash", "canary_response_hash"):
            if not _HASH.fullmatch(str(receipt.get(field) or "")):
                failures.append(f"PASS canary requires a 64-hex {field}.")
        if not receipt.get("canary_observed_at"):
            failures.append("PASS canary requires canary_observed_at.")
        scope = receipt.get("capability_scope")
        if not isinstance(scope, list) or not scope or not all(str(x).strip() for x in scope):
            failures.append("PASS canary requires a non-empty capability_scope list.")

    write_requested = bool(receipt.get("write_requested"))
    if write_requested:
        if receipt.get("read_only", True):
            failures.append("Write was requested but the receipt is read-only.")
        if str(receipt.get("write_canary_state") or "NOT_RUN").upper() != "PASS":
            failures.append("Write capability requires a separate reversible write canary.")
        if str(receipt.get("rollback_state") or "NOT_RUN").upper() != "PASS":
            failures.append("Write capability requires a verified rollback receipt.")
        if not receipt.get("authorization_receipt"):
            failures.append("Write capability requires an authorization receipt.")
        if not receipt.get("write_target"):
            failures.append("Write capability requires an exact bounded write_target.")

    attached = canary == "PASS" and not failures
    if attached:
        state = "AVAILABLE_READ_ONLY" if receipt.get("read_only", True) else "AVAILABLE_SCOPED_WRITE"
    elif canary == "FAIL":
        state = "FAILED_CANARY"
    else:
        state = "UNAVAILABLE"

    result = {
        "state": state,
        "connector_id": connector_id or None,
        "attached": attached,
        "read_only": bool(receipt.get("read_only", True)),
        "write_authorized": state == "AVAILABLE_SCOPED_WRITE",
        "registry_metadata_present": bool(receipt.get("registry_metadata_present")),
        "canary_receipt_complete": canary == "PASS" and not any("canary" in x.lower() or "capability_scope" in x for x in failures),
        "failures": failures,
        "security_requirements": [
            "least-privilege capability scope",
            "server identity binding",
            "authorization and audit receipt",
            "nonce and request/response hash binding",
            "reversible write canary and rollback for writes",
            "untrusted server output treated as data, not instructions",
            "stderr or OpenTelemetry observability without protocol stdout corruption",
            "no secrets in package artifacts",
        ],
        "boundary": "Connector discovery, canary success, authorization, and attachment are different facts.",
        "input_hash": sha256_json(receipt),
    }
    result["result_hash"] = sha256_json(result)
    return result
