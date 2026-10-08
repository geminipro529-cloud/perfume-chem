"""Atomic, no-overwrite staging for incoming-review bridge packets."""

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID

from engine.bridge.canary import verify_inventory
from engine.bridge.config import BridgeSettings
from engine.bridge.errors import BridgeBlocked
from engine.bridge.receipts import canonical_json_bytes, seal_receipt

CONFIRMATION = "STAGE INCOMING REVIEW ONLY"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_full_pass(settings: BridgeSettings, canary_receipt: Mapping[str, Any]) -> None:
    if canary_receipt.get("state") != "PASS" or canary_receipt.get("canary_mode") != "full":
        raise BridgeBlocked("packet staging requires a fresh full PASS canary receipt")
    if canary_receipt.get("signature", {}).get("state") != "SIGNED":
        raise BridgeBlocked("packet staging requires a signed canary receipt")
    repository = canary_receipt.get("repository", {})
    if (
        repository.get("root_status") != "PASS"
        or repository.get("origin_status") != "PASS"
        or repository.get("dirty") is not False
    ):
        raise BridgeBlocked("repository identity or clean-tree guard is not satisfied")
    if canary_receipt.get("inventory", {}).get("status") != "PASS":
        raise BridgeBlocked("inventory authority guard is not satisfied")
    if canary_receipt.get("protocol", {}).get("status") != "PASS":
        raise BridgeBlocked("protocol authority guard is not satisfied")
    if canary_receipt.get("verification", {}).get("status") != "PASS":
        raise BridgeBlocked("repository-native verification did not pass")
    if canary_receipt.get("runtime", {}).get("workbench_import", {}).get("status") != "PASS":
        raise BridgeBlocked("PerfumeWorkbench import did not pass")
    if not settings.packet_writes_enabled:
        raise BridgeBlocked("packet writes are disabled")
    if settings.signing_key is None:
        raise BridgeBlocked("packet staging requires a configured signing key")


def _validate_packet(settings: BridgeSettings, packet: Mapping[str, Any]) -> tuple[str, str]:
    if packet.get("protocol") != "Chat Bridge Protocol v2.1":
        raise BridgeBlocked("packet protocol identity is not Chat Bridge Protocol v2.1")
    conversation_id = str(packet.get("conversation_id", ""))
    if conversation_id != settings.conversation_id:
        raise BridgeBlocked("packet conversation is not the authorized work hub")
    try:
        UUID(conversation_id)
    except ValueError as exc:
        raise BridgeBlocked("conversation_id is not a valid UUID") from exc
    nonce = str(packet.get("nonce", ""))
    try:
        parsed_nonce = UUID(nonce)
    except ValueError as exc:
        raise BridgeBlocked("packet nonce is not a valid UUID") from exc
    if str(parsed_nonce) != nonce.lower():
        raise BridgeBlocked("packet nonce must use canonical UUID form")
    if packet.get("authority") != "INCOMING_REVIEW_ONLY":
        raise BridgeBlocked("packet authority must be INCOMING_REVIEW_ONLY")
    if packet.get("canonical_mutation_authorized") is not False:
        raise BridgeBlocked("canonical mutation must remain explicitly false")
    if packet.get("formula_mutation_authorized") is not False:
        raise BridgeBlocked("formula mutation must remain explicitly false")
    return conversation_id, nonce


def _reverify_protocol(settings: BridgeSettings) -> str:
    if settings.protocol_sha256 is None:
        raise BridgeBlocked("the exact protocol SHA-256 is not configured")
    protocol_path = settings.repo_root / settings.protocol_relative_path
    if not protocol_path.is_file():
        raise BridgeBlocked("the exact bridge protocol file is missing")
    raw = protocol_path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual.lower() != settings.protocol_sha256.lower():
        raise BridgeBlocked("the bridge protocol SHA-256 changed after the canary")
    try:
        protocol_text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BridgeBlocked("the bridge protocol is not UTF-8 text") from exc
    if "Chat Bridge Protocol v2.1" not in protocol_text:
        raise BridgeBlocked("the bridge protocol identity marker is missing")
    return actual


def stage_review_packet(
    settings: BridgeSettings,
    packet: Mapping[str, Any],
    canary_receipt: Mapping[str, Any],
    confirmation: str,
) -> dict[str, Any]:
    """Stage one signed packet without overwrite or canonical promotion."""

    if confirmation != CONFIRMATION:
        raise BridgeBlocked(f"confirmation must exactly equal {CONFIRMATION!r}")
    _require_full_pass(settings, canary_receipt)
    conversation_id, nonce = _validate_packet(settings, packet)

    current_inventory = verify_inventory(settings)
    if current_inventory.get("status") != "PASS":
        raise BridgeBlocked("Inventory V5 changed after the canary")
    protocol_sha = _reverify_protocol(settings)

    inbox = (
        settings.repo_root
        / "chat_bridge"
        / "complex_perfumery"
        / "inbox"
        / conversation_id
    )
    target = inbox / nonce
    resolved_root = settings.repo_root.resolve()
    resolved_inbox = inbox.resolve(strict=False)
    try:
        resolved_inbox.relative_to(resolved_root)
    except ValueError as exc:
        raise BridgeBlocked("packet destination escapes the repository") from exc

    inbox.mkdir(parents=True, exist_ok=True)
    try:
        target.mkdir(exist_ok=False)
    except FileExistsError as exc:
        raise BridgeBlocked("packet directory already exists; overwrite is forbidden") from exc

    staged_payload = dict(packet)
    staged_payload["bridge_intake"] = {
        "staged_at_utc": _utc_now(),
        "bridge_version": canary_receipt.get("bridge_version"),
        "canary_receipt_sha256": canary_receipt.get("receipt_sha256"),
        "protocol_sha256": protocol_sha,
        "inventory_sha256": current_inventory.get("sha256"),
        "repository_head": canary_receipt.get("repository", {}).get("head"),
        "promotion_state": "NOT_PROMOTED",
        "canonical_mutation_authorized": False,
        "formula_mutation_authorized": False,
    }
    sealed_packet = seal_receipt(staged_payload, settings.signing_key)
    packet_bytes = canonical_json_bytes(sealed_packet) + b"\n"
    packet_path = target / "PACKET.json"
    try:
        with packet_path.open("xb") as handle:
            handle.write(packet_bytes)
            handle.flush()
        if packet_path.read_bytes() != packet_bytes:
            raise BridgeBlocked("packet readback did not match written bytes")
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise

    receipt = {
        "schema": "perfume-chem-bridge-stage-receipt-v1",
        "state": "STAGED_INCOMING_REVIEW_ONLY",
        "packet_path": str(packet_path),
        "packet_bytes": len(packet_bytes),
        "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "conversation_id": conversation_id,
        "nonce": nonce,
        "repository_head_before_stage": canary_receipt.get("repository", {}).get("head"),
        "canonical_mutation_authorized": False,
        "formula_mutation_authorized": False,
        "canonical_promotion_claimed": False,
    }
    return seal_receipt(receipt, settings.signing_key)
