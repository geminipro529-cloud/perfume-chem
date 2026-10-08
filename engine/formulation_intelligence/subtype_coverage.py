"""Source-bound explanations of remaining subtype implementation requirements."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from engine.research.contracts import FALSE_ACTION_AUTHORITY

PATH = Path(__file__).resolve().parents[2] / "data/formulation_knowledge/subtype_implementation_dispositions_v1.json"
SHA256 = "6ebb46b2ecd4a751d1c2275be68d4d15ff0d185ef3b02d3f29c2a2e672ea741a"
SUBTYPE_SHA256 = "14eef313a501262a63c839577d3b9cf48124441c1dbc1a03a2fcda1f17225c83"


def load_dispositions() -> dict[str, Any]:
    raw = PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError("subtype disposition bytes drifted")
    value = json.loads(raw)
    if (value["schema_version"] != "subtype-implementation-dispositions-v1"
            or value["subtype_manifest_sha256"] != SUBTYPE_SHA256
            or value["authority"] != FALSE_ACTION_AUTHORITY):
        raise ValueError("subtype disposition contract mismatch")
    rows = value["dispositions"]
    if len(rows) != 132 or len({r["subtype_id"] for r in rows}) != 132:
        raise ValueError("incomplete subtype disposition census")
    return value


def coverage_for_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """No evidence promotion or inference of stock availability from a mapping."""
    result: dict[str, Any] = {
        "schema_version": "subtype-implementation-coverage-v1",
        "state": "ADVISORY_COVERAGE", "manifest_sha256": None, "items": [],
        "research_complete": False, "sensory_validation": "NOT_TESTED",
        "authority": dict(FALSE_ACTION_AUTHORITY),
    }
    try:
        # Lazy import avoids coupling source retrieval to adapter dispatch.
        from engine.formulation_intelligence.architecture_bridge import _support_error

        value = load_dispositions()
        if context.get("subtype_research_sha256") != SUBTYPE_SHA256:
            raise ValueError("subtype context drifted")
        result["manifest_sha256"] = SHA256
        rows = {r["subtype_id"]: r for r in value["dispositions"]}
        for card in context.get("subtype_context", {}).get("cards", ()):
            row = rows.get(card["subtype_id"])
            if row is None:
                continue
            if _support_error(row, card, context):
                raise ValueError("disposition source closure unavailable")
            result["items"].append(copy.deepcopy(row))
    except (OSError, ValueError, TypeError, KeyError):
        result.update(state="WITHHOLD_UNKNOWN", items=[], reason="SUBTYPE_DISPOSITION_UNAVAILABLE_OR_DRIFTED")
    return result
