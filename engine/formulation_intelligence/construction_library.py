"""Source-bound construction dossiers, not quantitative or action capabilities.

The frozen research plan is a coverage inventory, not executable policy. This
separate, versioned library reviews initial construction questions and exposes
unreviewed subtype scope explicitly. Retrieval is local, bounded and read-only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence

from .source_review import source_record_hash

ROOT = Path(__file__).resolve().parents[2]
LIBRARY_PATH = ROOT / "data/formulation_knowledge/construction_library_v1.json"
PLAN_PATH = ROOT / "data/formulation_knowledge/research_coverage_plan_v1.json"
FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}
_PACKAGE_KEYS = {
    "package_id", "title", "domain", "anchors", "recognizers", "negative_space",
    "subtype_scope", "reviewed_core_facets", "unreviewed_subtypes",
    "source_bindings", "functional_graph", "architectures", "comparison",
    "limits", "authority", "state",
}


def _exact_keys(value: object, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"invalid {name} fields")
    return value


def _texts(value: object, name: str, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"invalid {name} list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"invalid {name} text")
    if len(set(value)) != len(value):
        raise ValueError(f"duplicate {name}")
    return value


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"invalid {name} text")


def _authority(value: object) -> None:
    row = _exact_keys(value, set(FALSE_AUTHORITY), "authority")
    if any(item is not False for item in row.values()):
        raise ValueError("construction guidance cannot grant authority")


def validate_construction_library(library: Mapping[str, Any], plan: Mapping[str, Any]) -> None:
    _exact_keys(dict(library), {
        "schema_version", "version", "review_date", "scope", "plan_sha256",
        "authority", "numeric_calibrations_admitted", "packages", "cross_domain",
    }, "library")
    if library["schema_version"] != "formulation-construction-library-v1":
        raise ValueError("unknown construction schema")
    if library["scope"] != "INITIAL_SOURCE_BOUND_ADVISORY_CONSTRUCTION":
        raise ValueError("invalid construction scope")
    _text(library["version"], "version")
    _text(library["review_date"], "review date")
    date.fromisoformat(library["review_date"])
    if not re.fullmatch(r"[0-9a-f]{64}", str(library["plan_sha256"])):
        raise ValueError("unbound coverage plan")
    _authority(library["authority"])
    if library["numeric_calibrations_admitted"] != []:
        raise ValueError("quantitative models require separate admission")
    planned = {row["package_id"]: row for row in plan["construction_packages"]}
    packages = library["packages"]
    if not isinstance(packages, list) or len(packages) != len(planned):
        raise ValueError("incomplete construction coverage")
    seen: set[str] = set()
    for package in packages:
        row = _exact_keys(package, _PACKAGE_KEYS, "package")
        key = row["package_id"]
        if key not in planned or key in seen:
            raise ValueError("unknown or duplicate package")
        seen.add(key)
        expected = planned[key]
        if row["title"] != expected["title"] or row["domain"] != expected["domain"]:
            raise ValueError("coverage identity drift")
        if row["state"] != "ADVISORY_CONSTRUCTION_DOSSIER":
            raise ValueError("invalid package state")
        _authority(row["authority"])
        for field in ("anchors", "recognizers", "negative_space", "limits"):
            _texts(row[field], field)
        scope = _texts(row["subtype_scope"], "subtype scope")
        core = _texts(row["reviewed_core_facets"], "reviewed core")
        uncovered = _texts(row["unreviewed_subtypes"], "unreviewed subtypes", empty=True)
        if scope != expected["subtype_scope"] or set(core) & set(uncovered) or set(core) | set(uncovered) != set(scope):
            raise ValueError("subtype coverage must close without silently promoting gaps")
        bindings = row["source_bindings"]
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("construction needs source bindings")
        source_ids: set[str] = set()
        for binding in bindings:
            _exact_keys(binding, {"source_id", "source_record_sha256"}, "source binding")
            source_id = binding["source_id"]
            if not isinstance(source_id, str) or not source_id or source_id in source_ids:
                raise ValueError("duplicate or invalid source binding")
            source_ids.add(source_id)
            if not re.fullmatch(r"[0-9a-f]{64}", str(binding["source_record_sha256"])):
                raise ValueError("unbound construction source")
        graph = _exact_keys(row["functional_graph"], {"nodes", "edges"}, "functional graph")
        nodes = graph["nodes"]
        if not isinstance(nodes, list) or len(nodes) < 2:
            raise ValueError("construction graph needs distinct functions")
        node_ids: set[str] = set()
        for node in nodes:
            _exact_keys(node, {"role_id", "function", "material_examples", "identity_scope", "source_ids", "support", "time_scope", "protection_scope"}, "role node")
            if node["role_id"] in node_ids or not isinstance(node["role_id"], str):
                raise ValueError("duplicate role")
            node_ids.add(node["role_id"])
            _text(node["role_id"], "role identity")
            _text(node["function"], "role function")
            for field in ("material_examples", "source_ids"):
                _texts(node[field], field)
            if not set(node["source_ids"]) <= source_ids:
                raise ValueError("orphan role source")
            if node["support"] != "SOURCE_DESCRIPTOR_TO_FUNCTION_HYPOTHESIS" or node["time_scope"] != "DESIGN_INTENT_NOT_MEASURED" or node["protection_scope"] != "LOCKED_REQUEST_ONLY_NOT_LIBRARY_POLICY":
                raise ValueError("unmeasured role cannot claim calibration")
            if node["identity_scope"] != "EXACT_SOURCE_ENTITIES_NOT_STOCK_BINDINGS":
                raise ValueError("role examples are not inventory aliases")
        edges = graph["edges"]
        if not isinstance(edges, list) or not edges:
            raise ValueError("missing functional connections")
        for edge in edges:
            _exact_keys(edge, {"from", "to", "relationship", "support"}, "role edge")
            _text(edge["relationship"], "role relationship")
            if edge["from"] not in node_ids or edge["to"] not in node_ids or edge["from"] == edge["to"] or edge["support"] != "UNMEASURED_INTERACTION_HYPOTHESIS":
                raise ValueError("invalid role relationship")
        architectures = row["architectures"]
        if not isinstance(architectures, list) or len(architectures) != 2:
            raise ValueError("construction needs two bounded alternatives")
        signatures = set()
        names = set()
        for architecture in architectures:
            _exact_keys(architecture, {"name", "roles", "intent", "risk", "status"}, "architecture")
            for field in ("name", "intent", "risk"):
                _text(architecture[field], field)
            if architecture["name"] in names:
                raise ValueError("duplicate architecture identity")
            names.add(architecture["name"])
            roles = _texts(architecture["roles"], "architecture roles")
            if not set(roles) <= node_ids or architecture["status"] != "UNTESTED_FORMULATION_HYPOTHESIS":
                raise ValueError("architecture is not an empirical capability")
            signatures.add((tuple(roles), architecture["intent"]))
        if len(signatures) != 2:
            raise ValueError("alternatives cannot be duplicate decoration")
        comparison = _exact_keys(row["comparison"], {"control", "change", "question", "observe", "stop", "claim_limit"}, "comparison")
        if any(not isinstance(value, str) or not value.strip() for value in comparison.values()):
            raise ValueError("incomplete comparison")
    if seen != set(planned):
        raise ValueError("missing package")
    cross = _exact_keys(library["cross_domain"], {"scientific_fronts", "market_segments", "product_formats", "commercial_panel_tracks"}, "cross-domain")
    for field, id_key in (("scientific_fronts", "front_id"), ("market_segments", "segment_id"), ("product_formats", "format_id"), ("commercial_panel_tracks", "track_id")):
        records = cross[field]
        if not isinstance(records, list) or {row[id_key] for row in records} != {row[id_key] for row in plan[field]} or len(records) != len(plan[field]):
            raise ValueError("cross-domain coverage drift")
        for record in records:
            _exact_keys(record, {id_key, "requirement", "state", "authority"}, "cross-domain record")
            if record["state"] != "QUESTION_AND_BOUNDARY_DEFINED_NOT_CAPABILITY_ADMISSION" or not isinstance(record["requirement"], str) or not record["requirement"]:
                raise ValueError("cross-domain question cannot be promoted")
            _authority(record["authority"])


@lru_cache(maxsize=4)
def _parse(payload: bytes, plan_payload: bytes) -> dict[str, Any]:
    library, plan = json.loads(payload), json.loads(plan_payload)
    if not isinstance(library, dict) or not isinstance(plan, dict):
        raise ValueError("invalid construction manifests")
    if hashlib.sha256(plan_payload).hexdigest() != library.get("plan_sha256"):
        raise ValueError("frozen coverage plan drift")
    validate_construction_library(library, plan)
    return library


def load_construction_library() -> dict[str, Any]:
    return copy.deepcopy(_parse(LIBRARY_PATH.read_bytes(), PLAN_PATH.read_bytes()))


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


def _present(text: str, phrase: str) -> bool:
    return bool(_key(phrase) and f" {_key(phrase)} " in f" {_key(text)} ")


def retrieve_construction_dossiers(
    positive_text: str,
    *,
    sources: Sequence[Mapping[str, Any]],
    unavailable_source_ids: Sequence[str],
    limit: int = 4,
) -> dict[str, Any]:
    """Input text is already negation-masked by the request-aware caller.

    Relevance orders retrieval only, never candidates or hedonic endpoints.
    A changed or unavailable source withholds only its dependent dossiers.
    """
    base: dict[str, Any] = {
        "schema_version": "construction-context-v1", "authority": dict(FALSE_AUTHORITY),
        "network_used": False, "numeric_calibrations_admitted": [],
        "dossiers": [], "withheld_package_ids": [], "library_sha256": None,
        "scope": "INITIAL_ADVISORY_NOT_EXHAUSTIVE_SUBTYPE_REVIEW",
    }
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("construction retrieval limit must be one through eight")
    try:
        payload = LIBRARY_PATH.read_bytes()
        plan_payload = PLAN_PATH.read_bytes()
        library = _parse(payload, plan_payload)
    except (OSError, ValueError, TypeError, KeyError):
        return {**base, "state": "WITHHOLD_UNKNOWN", "reason_codes": ["CONSTRUCTION_MANIFEST_UNAVAILABLE_OR_DRIFTED"]}
    source_map = {row["source_id"]: row for row in sources}
    unavailable = set(unavailable_source_ids)
    matches = []
    withheld = []
    for index, package in enumerate(library["packages"]):
        relevance = sum(_present(positive_text, anchor) for anchor in package["anchors"])
        if not relevance:
            continue
        valid = all(
            binding["source_id"] not in unavailable
            and binding["source_id"] in source_map
            and source_record_hash(source_map[binding["source_id"]]) == binding["source_record_sha256"]
            for binding in package["source_bindings"]
        )
        if not valid:
            withheld.append(package["package_id"])
        else:
            matches.append((relevance, index, package))
    matches.sort(key=lambda item: (-item[0], item[1]))
    core_count = sum(len(row["reviewed_core_facets"]) for row in library["packages"])
    gaps = sum(len(row["unreviewed_subtypes"]) for row in library["packages"])
    result = {
        **base,
        "state": "ADVISORY_CONSTRUCTION_AVAILABLE" if matches else "WITHHOLD_UNKNOWN",
        "library_sha256": hashlib.sha256(payload).hexdigest(),
        "plan_sha256": hashlib.sha256(plan_payload).hexdigest(),
        "dossiers": [row for _, _, row in matches[:limit]],
        "matched_package_count": len(matches),
        "withheld_package_ids": withheld,
        "coverage": {
            "initial_package_dossiers": len(library["packages"]),
            "source_bound_core_scope_entries": core_count,
            "unreviewed_subtype_scope_entries": gaps,
            "empirically_validated_packages": 0,
            **{field: len(rows) for field, rows in library["cross_domain"].items()},
        },
        "reason_codes": ["ARCHITECTURES_AND_INTERACTIONS_ARE_UNTESTED", "QUANTITATIVE_ENDPOINTS_REQUIRE_SEPARATE_CAPABILITIES"],
    }
    return copy.deepcopy(result)


__all__ = ["load_construction_library", "retrieve_construction_dossiers", "validate_construction_library"]
