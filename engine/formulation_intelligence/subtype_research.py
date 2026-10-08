"""Offline subtype hypotheses with source and immutable parent bindings.

These cards deepen a part of the frozen coverage plan. They never certify a
complete subtype, select materials/doses or grant empirical/action authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from .campaign_reference import recovered_campaign_reference
from .construction_library import (
    FALSE_AUTHORITY,
    LIBRARY_PATH,
    PLAN_PATH,
    _authority,
    _exact_keys,
    _present,
    _text,
    _texts,
)
from .construction_library import (
    _parse as _parse_parent,
)
from .source_review import source_record_hash

PREDECESSOR_PATH = Path(__file__).resolve().parents[2] / "data/formulation_knowledge/subtype_research_v1.json"
V2_PATH = PREDECESSOR_PATH.with_name("subtype_research_v2.json")
V3_PATH = PREDECESSOR_PATH.with_name("subtype_research_v3.json")
SUBTYPE_PATH = PREDECESSOR_PATH.with_name("subtype_research_v4.json")
_SCHEMAS = tuple(f"formulation-subtype-research-v{i}" for i in range(1, 5))
_CARD_KEYS = {
    "subtype_id", "package_id", "planned_subtype", "title", "match_groups",
    "source_bindings", "evidence_summary", "construction_hypothesis",
    "function_map", "negative_space", "comparison", "identity_limits",
    "status", "authority",
}


def validate_subtype_research(value: Mapping[str, Any], parent: Mapping[str, Any]) -> None:
    schema = value.get("schema_version")
    if schema not in _SCHEMAS:
        raise ValueError("unknown subtype schema")
    fields = {
        "schema_version", "version", "review_date", "scope",
        "parent_library_sha256", "plan_sha256", "authority",
        "numeric_calibrations_admitted", "cards",
    }
    hash_fields = ["parent_library_sha256", "plan_sha256"]
    if schema != "formulation-subtype-research-v1":
        fields.update({"predecessor_manifest_sha256", "campaign_identity_holds"})
        hash_fields.append("predecessor_manifest_sha256")
    if schema in _SCHEMAS[2:]:
        fields.update({"taxonomy_additions", "review_addenda"})
    _exact_keys(dict(value), fields, "subtype manifest")
    if value["scope"] != "PARTIAL_SOURCE_BOUND_SUBTYPE_RESEARCH":
        raise ValueError("subtype research is partial and advisory")
    _text(value["version"], "subtype version")
    _text(value["review_date"], "review date")
    date.fromisoformat(value["review_date"])
    for field in hash_fields:
        if not isinstance(value[field], str) or not re.fullmatch(r"[0-9a-f]{64}", value[field]):
            raise ValueError("unbound subtype parent")
    _authority(value["authority"])
    if value["numeric_calibrations_admitted"] != []:
        raise ValueError("subtype cards cannot admit calibration")
    if schema != "formulation-subtype-research-v1":
        _validate_campaign_holds(value["campaign_identity_holds"])
    cards = value["cards"]
    if not isinstance(cards, list) or not 1 <= len(cards) <= 256:
        raise ValueError("invalid subtype collection")
    planned = {p["package_id"]: p for p in parent["packages"]}
    additions = _validate_taxonomy_additions(value.get("taxonomy_additions", []), planned)
    seen: set[str] = set()
    covered: set[tuple[str, str]] = set()
    for card in cards:
        card_fields = _CARD_KEYS
        if schema != "formulation-subtype-research-v1" and isinstance(card, dict) and "exclude_phrases" in card:
            card_fields = _CARD_KEYS | {"exclude_phrases"}
            _texts(card["exclude_phrases"], "excluded identity phrases")
        _exact_keys(card, card_fields, "subtype card")
        for field in ("subtype_id", "package_id", "planned_subtype", "title", "evidence_summary", "construction_hypothesis"):
            _text(card[field], field)
        key = card["subtype_id"]
        scope = (card["package_id"], card["planned_subtype"])
        if key in seen or scope in covered:
            raise ValueError("duplicate subtype or coverage entry")
        seen.add(key)
        covered.add(scope)
        if scope not in additions and (scope[0] not in planned or scope[1] not in planned[scope[0]]["unreviewed_subtypes"]):
            raise ValueError("subtype must bind a frozen parent gap")
        if card["status"] != "UNTESTED_SUBTYPE_HYPOTHESIS":
            raise ValueError("subtype is not an empirical capability")
        _authority(card["authority"])
        groups = card["match_groups"]
        if not isinstance(groups, list) or not 1 <= len(groups) <= 4:
            raise ValueError("subtype needs bounded conjunctive matching")
        for group in groups:
            _texts(group, "match group")
        if len({tuple(g) for g in groups}) != len(groups):
            raise ValueError("duplicate match group")
        for field in ("function_map", "negative_space", "identity_limits"):
            _texts(card[field], field)
        comparison = _exact_keys(card["comparison"], {"control", "change", "question", "stop"}, "subtype comparison")
        for field, text in comparison.items():
            _text(text, field)
        _validate_bindings(card["source_bindings"])
    if not additions <= covered:
        raise ValueError("declared botanical expansion needs a source-bound card")
    _validate_addenda(value.get("review_addenda", []), {c["subtype_id"]: c for c in cards})


def _validate_bindings(bindings: Any) -> None:
    if not isinstance(bindings, list) or not bindings:
        raise ValueError("subtype needs evidence")
    sources: set[str] = set()
    for binding in bindings:
        _exact_keys(binding, {"source_id", "source_record_sha256"}, "subtype source")
        _text(binding["source_id"], "source identity")
        if binding["source_id"] in sources:
            raise ValueError("duplicate subtype source")
        sources.add(binding["source_id"])
        digest = binding["source_record_sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid subtype source hash")


def _validate_taxonomy_additions(rows: Any, planned: Mapping[str, Any]) -> set[tuple[str, str]]:
    if not isinstance(rows, list) or len(rows) > 32:
        raise ValueError("invalid bounded taxonomy expansion")
    seen: set[tuple[str, str]] = set()
    for row in rows:
        _exact_keys(row, {"package_id", "planned_subtype", "botanical_identity", "reason", "authority"}, "taxonomy addition")
        for field in ("package_id", "planned_subtype", "botanical_identity", "reason"):
            _text(row[field], field)
        _authority(row["authority"])
        key = (row["package_id"], row["planned_subtype"])
        if key in seen or key[0] not in planned or key[1] in planned[key[0]]["subtype_scope"]:
            raise ValueError("taxonomy additions cannot duplicate or rewrite frozen scope")
        seen.add(key)
    return seen


def _validate_addenda(rows: Any, cards: Mapping[str, Any]) -> None:
    if not isinstance(rows, list) or len(rows) > 64:
        raise ValueError("invalid research addenda")
    seen: set[str] = set()
    for row in rows:
        _exact_keys(row, {"subtype_id", "target_card_sha256", "source_bindings", "evidence_summary", "identity_limits", "authority"}, "research addendum")
        _text(row["subtype_id"], "addendum target")
        if row["subtype_id"] not in cards or row["subtype_id"] in seen:
            raise ValueError("addendum needs one existing exact subtype")
        if row["target_card_sha256"] != source_record_hash(cards[row["subtype_id"]]):
            raise ValueError("addendum target bytes changed")
        seen.add(row["subtype_id"])
        _text(row["evidence_summary"], "addendum finding")
        _texts(row["identity_limits"], "addendum limits")
        _authority(row["authority"])
        _validate_bindings(row["source_bindings"])


def _validate_campaign_holds(holds: Any) -> None:
    if not isinstance(holds, list) or len(holds) > 64:
        raise ValueError("invalid campaign holds")
    seen: set[str] = set()
    for hold in holds:
        _exact_keys(hold, {
            "campaign_id", "names", "state", "reason", "question",
            "inferred_package_ids", "authority",
        }, "campaign identity hold")
        for field in ("campaign_id", "reason", "question"):
            _text(hold[field], field)
        if hold["campaign_id"] in seen:
            raise ValueError("duplicate campaign identity hold")
        seen.add(hold["campaign_id"])
        _texts(hold["names"], "exact campaign names")
        _authority(hold["authority"])
        if hold["state"] != "HOLD_EXACT_BRIEF_OR_FORMULA_REQUIRED" or hold["inferred_package_ids"] != []:
            raise ValueError("unrecovered campaign cannot infer a fragrance family")


@lru_cache(maxsize=4)
def _parse(payload: bytes, parent_bytes: bytes, plan_bytes: bytes,
           predecessor_bytes: bytes = b"", *ancestor_bytes: bytes) -> dict[str, Any]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("invalid subtype manifest")
    if value.get("parent_library_sha256") != hashlib.sha256(parent_bytes).hexdigest():
        raise ValueError("subtype parent drift")
    if value.get("plan_sha256") != hashlib.sha256(plan_bytes).hexdigest():
        raise ValueError("subtype plan drift")
    validate_subtype_research(value, _parse_parent(parent_bytes, plan_bytes))
    if value["schema_version"] != "formulation-subtype-research-v1":
        if value["predecessor_manifest_sha256"] != hashlib.sha256(predecessor_bytes).hexdigest():
            raise ValueError("subtype predecessor drift")
        predecessor = _parse(predecessor_bytes, parent_bytes, plan_bytes, *ancestor_bytes)
        expected = _SCHEMAS[_SCHEMAS.index(value["schema_version"]) - 1]
        if predecessor["schema_version"] != expected:
            raise ValueError("unsupported subtype predecessor")
        previous_cards = predecessor["cards"]
        if value["cards"][:len(previous_cards)] != previous_cards:
            raise ValueError("subtype successor rewrites prior research")
        if value["schema_version"] in _SCHEMAS[2:] and value["campaign_identity_holds"] != predecessor["campaign_identity_holds"]:
            raise ValueError("research expansion cannot silently resolve a campaign")
        for field in ("taxonomy_additions", "review_addenda"):
            prior = predecessor.get(field, [])
            if value.get(field, [])[:len(prior)] != prior:
                raise ValueError("subtype successor rewrites prior " + field)
    return value


def load_subtype_research() -> dict[str, Any]:
    return copy.deepcopy(_load_payload(SUBTYPE_PATH.read_bytes()))


def _load_payload(payload: bytes) -> dict[str, Any]:
    value = json.loads(payload)
    schema = value.get("schema_version") if isinstance(value, dict) else None
    if schema not in _SCHEMAS:
        raise ValueError("unknown subtype schema")
    # Closed local chain: a manifest can bind bytes, never choose a file path.
    predecessors = (PREDECESSOR_PATH, V2_PATH, V3_PATH)[:_SCHEMAS.index(schema)]
    return _parse(payload, LIBRARY_PATH.read_bytes(), PLAN_PATH.read_bytes(),
                  *(path.read_bytes() for path in reversed(predecessors)))


def retrieve_subtype_research(
    positive_text: str,
    *,
    sources: Sequence[Mapping[str, Any]],
    unavailable_source_ids: Sequence[str],
    limit: int = 4,
) -> dict[str, Any]:
    """Conjunctive phrase matching on caller-masked positive intent only.

    Ordering is retrieval relevance, not ranking of perfume candidates. A
    generic family request must not activate every subtype or rewrite a brief.
    """
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("subtype retrieval limit must be one through eight")
    base: dict[str, Any] = {
        "schema_version": "subtype-research-context-v1",
        "scope": "PARTIAL_ADVISORY_NOT_EMPIRICAL_SUBTYPE_COMPLETION",
        "cards": [], "withheld_subtype_ids": [], "manifest_sha256": None,
        "campaign_identity_holds": [],
        "withheld_addendum_ids": [],
        "authority": dict(FALSE_AUTHORITY), "network_used": False,
        "numeric_calibrations_admitted": [],
    }
    try:
        payload = SUBTYPE_PATH.read_bytes()
        manifest = _load_payload(payload)
    except (OSError, ValueError, TypeError, KeyError):
        return {**base, "state": "WITHHOLD_UNKNOWN", "reason_codes": ["SUBTYPE_MANIFEST_UNAVAILABLE_OR_DRIFTED"]}
    source_map = {row["source_id"]: row for row in sources}
    unavailable = set(unavailable_source_ids)
    def supported(bindings: Sequence[Mapping[str, Any]]) -> bool:
        return all(
            binding["source_id"] not in unavailable
            and binding["source_id"] in source_map
            and source_record_hash(source_map[binding["source_id"]]) == binding["source_record_sha256"]
            for binding in bindings
        )
    addenda = {a["subtype_id"]: a for a in manifest.get("review_addenda", [])}
    withheld_addenda = []
    matches = []
    withheld = []
    for index, card in enumerate(manifest["cards"]):
        if any(_present(positive_text, phrase) for phrase in card.get("exclude_phrases", [])):
            continue
        if not all(any(_present(positive_text, phrase) for phrase in group) for group in card["match_groups"]):
            continue
        if not supported(card["source_bindings"]):
            withheld.append(card["subtype_id"])
            continue
        card = copy.deepcopy(card)
        addendum = addenda.get(card["subtype_id"])
        if addendum is not None:
            if supported(addendum["source_bindings"]):
                card["review_addenda"] = [addendum]
                existing = {b["source_id"] for b in card["source_bindings"]}
                card["source_bindings"].extend(b for b in addendum["source_bindings"] if b["source_id"] not in existing)
            else:
                withheld_addenda.append(card["subtype_id"])
        matches.append((len(card["match_groups"]), index, card))
    matches.sort(key=lambda row: (-row[0], row[1]))
    campaign_holds = [
        copy.deepcopy(hold) for hold in manifest.get("campaign_identity_holds", [])
        if any(_present(positive_text, name) for name in hold["names"])
    ]
    for hold in campaign_holds:
        recovered = recovered_campaign_reference(hold["campaign_id"])
        if recovered is not None:
            # Recovery is not a bound redesign request or current-bottle truth.
            hold["historical_reason"] = hold["reason"]
            hold["reason"] = recovered["runtime_message"]
            hold["question"] = recovered["runtime_question"]
            hold["recovered_reference"] = recovered
    result = {
        **base,
        "state": "ADVISORY_SUBTYPE_RESEARCH_AVAILABLE" if matches else "WITHHOLD_UNKNOWN",
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "parent_library_sha256": manifest["parent_library_sha256"],
        "plan_sha256": manifest["plan_sha256"],
        "predecessor_manifest_sha256": manifest.get("predecessor_manifest_sha256"),
        "campaign_identity_holds": campaign_holds,
        "withheld_addendum_ids": withheld_addenda,
        "cards": [card for _, _, card in matches[:limit]],
        "matched_subtype_count": len(matches), "withheld_subtype_ids": withheld,
        "coverage": {
            "partial_research_cards": len(manifest["cards"]),
            "packages_deepened": len({c["package_id"] for c in manifest["cards"]}),
            "floral_packages_deepened": len({
                c["package_id"] for c in manifest["cards"] if c["package_id"].startswith("FL_")
            }),
            "empirically_validated_subtypes": 0,
            "declared_additional_botanical_scopes": len(manifest.get("taxonomy_additions", [])),
        },
        "reason_codes": ["CONSTRUCTION_IS_A_HYPOTHESIS", "SOURCE_MATRIX_AND_PRODUCT_LIMITS_APPLY"]
        + (["EXACT_CAMPAIGN_IDENTITY_UNRESOLVED"] if campaign_holds else []),
    }
    return copy.deepcopy(result)
