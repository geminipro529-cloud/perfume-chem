"""Read-only, byte-bound historical campaign recovery; never a build resolver."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "data/governance/campaign_reference_chimie_lhomme_v1.json"
MANIFEST_SHA256 = "8ab669919d6633d440a7691f5b431ea6323807f6614d9d9d6598ac50d1cd166a"
SOURCE_PATHS = (
    "data/research/campaign_recovery/chimie_lhomme_v1/source_formula.md",
    "data/research/campaign_recovery/chimie_lhomme_v1/source_identity_handoff.md",
    "data/research/campaign_recovery/chimie_lhomme_v1/chat_corrections.json",
)


def recovered_campaign_reference(campaign_id: str) -> dict[str, Any] | None:
    """Return compact provenance only when every reviewed local byte still matches.

    This closed registry cannot select an arbitrary file or read the user's chat
    store at runtime. Quantitative rows are archived, not imported into inventory,
    generated designs or bottle history. Missing bytes leave the original hold.
    """
    if campaign_id != "CHIMIE_LHOMME":
        return None
    try:
        raw = MANIFEST_PATH.read_bytes()
        if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
            return None
        value = json.loads(raw)
        if tuple(row["path"] for row in value["sources"]) != SOURCE_PATHS:
            return None
        for row in value["sources"]:
            if hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() != row["sha256"]:
                return None
        return copy.deepcopy({
            "state": value["state"],
            "campaign_id": value["campaign_id"],
            "accepted_identity": value["accepted_identity"],
            "not_equivalent_to": value["not_equivalent_to"],
            "manifest_path": "data/governance/campaign_reference_chimie_lhomme_v1.json",
            "manifest_sha256": MANIFEST_SHA256,
            "sources": [{"path": row["path"], "sha256": row["sha256"]} for row in value["sources"]],
            "totals": value["totals"],
            "runtime_message": value["runtime_message"],
            "runtime_question": value["runtime_question"],
            "runtime_scope": value["runtime_scope"],
            "current_inventory_binding": value["current_inventory_binding"],
            "historical_design_is_current_bottle": False,
            "formula_action": "NO_CHANGE",
            "authority": value["authority"],
        })
    except (OSError, ValueError, KeyError, TypeError):
        return None
