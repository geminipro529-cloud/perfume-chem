"""Offline, source-bounded formulation clues, separate from empirical capabilities.

The reviewed pack may guide vocabulary, architecture and comparison questions.
The prior-research census is retrieval metadata only, never executable policy.
Neither path creates stock facts, numerical calibration or action authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
PACK_PATH = ROOT / "data/formulation_knowledge/literature_v1.json"
CORPUS_PATH = ROOT / "data/formulation_knowledge/prior_research_corpus_v1.json"
FALSE_AUTHORITY = {
    "release_authority": False,
    "safety_authority": False,
    "compounding_authority": False,
    "evidence_admission_authorized": False,
}
_SOURCE_CLASSES = {
    "PRIMARY_RESEARCH",
    "PREPRINT",
    "MANUFACTURER_DESCRIPTION",
    "OFFICIAL_STANDARD_SCOPE",
    "LOCAL_RESEARCH_REVIEW",
    "LOCAL_IDENTITY_RECEIPT",
}
_CLAIM_KINDS = {
    "SOURCE_BOUNDED_FACT",
    "MANUFACTURER_DESCRIPTION",
    "FORMULATION_HYPOTHESIS",
}


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _present(text: str, phrase: str) -> bool:
    return bool(_key(phrase) and f" {_key(phrase)} " in f" {_key(text)} ")


def _positive_text(text: str, avoid: Sequence[str]) -> str:
    # This is retrieval masking, not a replacement for the request parser.
    positive = re.sub(r"\b(?:no|not|without|avoid)\s+[^,.;]+", " ", text, flags=re.I)
    for phrase in sorted(avoid, key=len, reverse=True):
        if _key(phrase):
            positive = re.sub(rf"(?<!\w){re.escape(str(phrase))}(?!\w)", " ", positive, flags=re.I)
    return positive


def _safe_local(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or ":" in relative:
        raise ValueError("source path must be repository-relative")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("source path escapes repository")
    return resolved


def _records(value: object, name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"invalid {name} shape")
    return value


def _ids(rows: Sequence[Mapping[str, Any]], key: str) -> set[str]:
    values: set[str] = set()
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"invalid {key}")
        if value in values:
            raise ValueError(f"duplicate {key}")
        values.add(value)
    return values


def _text_list(value: object, name: str, *, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"invalid {name} shape")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"invalid {name} value")


def validate_knowledge_pack(pack: Mapping[str, Any]) -> None:
    """Refuse calibration, authority escalation, ambiguous aliases and bad links."""
    if pack.get("schema_version") != "formulation-literature-knowledge-v1":
        raise ValueError("unknown knowledge schema")
    authority = pack.get("authority")
    if not isinstance(authority, dict) or set(authority) != set(FALSE_AUTHORITY):
        raise ValueError("invalid authority shape")
    if any(value is not False for value in authority.values()):
        raise ValueError("knowledge cannot grant authority")
    if pack.get("numeric_calibrations_admitted") != []:
        raise ValueError("numeric calibration requires a separate capability")
    sources = _records(pack.get("sources"), "sources")
    claims = _records(pack.get("claims"), "claims")
    profiles = _records(pack.get("profiles"), "profiles")
    materials = _records(pack.get("materials"), "materials")
    quarantined = _records(pack.get("quarantined_claims"), "quarantined claims")
    source_ids = _ids(sources, "source_id")
    claim_ids = _ids(claims, "claim_id")
    _ids(profiles, "profile_id")
    _ids(materials, "material_id")
    quarantine_ids = _ids(quarantined, "claim_id")
    if claim_ids & quarantine_ids:
        raise ValueError("quarantined claim cannot be selectable")
    for source in sources:
        if source.get("evidence_class") not in _SOURCE_CLASSES:
            raise ValueError("invalid source class")
        if source.get("rights_scope") != "METADATA_AND_ORIGINAL_SUMMARY_ONLY":
            raise ValueError("source rights exceed metadata scope")
        if source.get("empirical_data_admission") is not False:
            raise ValueError("source is not empirical admission")
        if source.get("review_state") not in {
            "FRESH_PRIMARY_REVIEW",
            "PRIOR_LOCAL_REVIEW",
            "CURRENT_LOCAL_READ",
        }:
            raise ValueError("source is not a reviewed reference")
        url = source.get("url")
        if url:
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("invalid source URL")
        if source.get("local_path"):
            _safe_local(ROOT, source["local_path"])
            if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("local_sha256", ""))):
                raise ValueError("local source is not hash bound")
    allowed_claim_keys = {
        "claim_id",
        "statement",
        "source_ids",
        "tags",
        "kind",
        "scope_limit",
        "numeric_calibration",
    }
    for claim in claims:
        if set(claim) != allowed_claim_keys:
            raise ValueError("unknown claim field or numeric scoring field")
        if claim.get("kind") not in _CLAIM_KINDS or claim.get("numeric_calibration") is not False:
            raise ValueError("invalid claim kind or calibration")
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or not refs or not set(refs) <= source_ids:
            raise ValueError("claim has unavailable source")
        if not isinstance(claim.get("statement"), str) or not claim["statement"].strip():
            raise ValueError("empty claim")
        _text_list(claim.get("tags"), "claim tags")
    aliases: set[str] = set()
    for row in [*profiles, *materials]:
        refs = row.get("claim_ids")
        if not isinstance(refs, list) or not refs or not set(refs) <= claim_ids:
            raise ValueError("profile or material has unavailable claim")
        if "exact_aliases" in row:
            _text_list(row["exact_aliases"], "material aliases")
            _text_list(row.get("vocabulary"), "material vocabulary")
            current = {_key(value) for value in row["exact_aliases"]}
            if not current or "" in current or aliases & current:
                raise ValueError("ambiguous material alias")
            aliases.update(current)
        else:
            _text_list(row.get("anchors"), "profile anchors")
            _text_list(row.get("qualifiers"), "profile qualifiers", allow_empty=True)
        _text_list(row.get("role_slots"), "role slots")


@lru_cache(maxsize=8)
def _parse_pack(payload: bytes) -> dict[str, Any]:
    pack = json.loads(payload)
    if not isinstance(pack, dict):
        raise ValueError("invalid knowledge pack")
    validate_knowledge_pack(pack)
    return pack


@lru_cache(maxsize=8)
def _parse_corpus(payload: bytes) -> dict[str, Any]:
    corpus = json.loads(payload)
    if (
        not isinstance(corpus, dict)
        or corpus.get("schema_version") != "formulation-prior-research-corpus-v1"
    ):
        raise ValueError("invalid research corpus")
    if (
        corpus.get("runtime_claim_authority") is not False
        or corpus.get("reviewed_full_text") is not False
    ):
        raise ValueError("research corpus cannot admit claims")
    rows = _records(corpus.get("records"), "research records")
    _ids(rows, "path")
    for row in rows:
        _safe_local(ROOT, row["path"])
        if not re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256", ""))):
            raise ValueError("invalid research source hash")
        count = row.get("byte_count")
        if type(count) is not int or count < 0:
            raise ValueError("invalid research byte count")
        if "search_terms" in row:
            _text_list(row["search_terms"], "research search terms", allow_empty=True)
    return corpus


def load_knowledge_pack() -> dict[str, Any]:
    return copy.deepcopy(_parse_pack(PACK_PATH.read_bytes()))


def knowledge_fingerprints() -> dict[str, str]:
    return {
        "pack_sha256": hashlib.sha256(PACK_PATH.read_bytes()).hexdigest(),
        "prior_corpus_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
    }


def material_knowledge(name: str) -> dict[str, Any] | None:
    """Exact admitted labels only; never infer a grade from CAS or a family."""
    normalized = _key(name)
    try:
        pack = _parse_pack(PACK_PATH.read_bytes())
    except (OSError, ValueError, TypeError):
        return None
    for material in pack["materials"]:
        if normalized in {_key(alias) for alias in material["exact_aliases"]} and _claims_available(
            pack, material["claim_ids"]
        ):
            return copy.deepcopy(material)
    return None


def _unavailable_sources(pack: Mapping[str, Any]) -> set[str]:
    unavailable = set()
    for source in pack["sources"]:
        if source.get("local_path"):
            try:
                payload = _safe_local(ROOT, source["local_path"]).read_bytes()
            except (OSError, ValueError):
                unavailable.add(source["source_id"])
                continue
            if hashlib.sha256(payload).hexdigest() != source["local_sha256"]:
                unavailable.add(source["source_id"])
    return unavailable


def _claims_available(pack: Mapping[str, Any], claim_ids: Sequence[str]) -> bool:
    unavailable = _unavailable_sources(pack)
    return all(
        not unavailable.intersection(claim["source_ids"])
        for claim in pack["claims"]
        if claim["claim_id"] in claim_ids
    )


def _source_status(record: Mapping[str, Any], root: Path) -> str:
    try:
        payload = _safe_local(root, str(record["path"])).read_bytes()
    except (OSError, ValueError):
        return "SOURCE_UNAVAILABLE"
    if (
        len(payload) != record["byte_count"]
        or hashlib.sha256(payload).hexdigest() != record["sha256"]
    ):
        return "SOURCE_DRIFT_HOLD"
    return "HASH_VERIFIED_REFERENCE_ONLY"


def audit_prior_research(
    *,
    manifest: Mapping[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    corpus = manifest if manifest is not None else _parse_corpus(CORPUS_PATH.read_bytes())
    records = _records(corpus.get("records"), "research records")
    drift = [
        row["path"]
        for row in records
        if _source_status(row, root or ROOT) != "HASH_VERIFIED_REFERENCE_ONLY"
    ]
    return {
        "state": "WITHHOLD_SOURCE_DRIFT" if drift else "REFERENCE_CENSUS_VERIFIED",
        "indexed_record_count": len(records),
        "drifted_paths": drift,
        "runtime_claim_authority": False,
        "reviewed_full_text": False,
    }


def _profiles(pack: Mapping[str, Any], text: str, avoid: Sequence[str]) -> list[dict[str, Any]]:
    result = []
    for profile in pack["profiles"]:
        anchors = profile["anchors"]
        if not any(_present(text, anchor) for anchor in anchors):
            continue
        if any(_present(" ".join(anchors), item) for item in avoid):
            continue
        qualifiers = profile["qualifiers"]
        if qualifiers and not any(_present(text, qualifier) for qualifier in qualifiers):
            continue
        result.append(profile)
    ids = {profile["profile_id"] for profile in result}
    # Bare violet means a petal design hypothesis, not automatic leaf/powder.
    if _present(text, "violet") and not ids & {"violet_leaf", "violet_petals", "violet_powder"}:
        result.extend(
            profile for profile in pack["profiles"] if profile["profile_id"] == "violet_petals"
        )
    return result


def _prior_references(corpus: Mapping[str, Any], text: str, limit: int = 5) -> list[dict[str, Any]]:
    terms = set(_key(text).split()) - {
        "with",
        "without",
        "perfume",
        "fragrance",
        "make",
        "more",
        "the",
        "and",
    }
    matches = []
    for index, row in enumerate(corpus["records"]):
        title_terms = set(_key(f"{row['title']} {row['path']}").split())
        indexed_terms = set(_key(" ".join(row.get("search_terms", ()))).split())
        score = 3 * len(terms & title_terms) + len(terms & indexed_terms)
        if score:
            matches.append((score, index, row))
    matches.sort(key=lambda item: (-item[0], item[1]))
    return [
        {**row, "state": _source_status(row, ROOT), "authority_scope": "SEARCHABLE_REFERENCE_ONLY"}
        for _, _, row in matches[:limit]
    ]


def retrieve_formulation_knowledge(
    request: str,
    *,
    avoid: Sequence[str] = (),
    material_names: Sequence[str] = (),
) -> dict[str, Any]:
    """Retrieve a bounded original-summary packet, without network or writes."""
    base: dict[str, Any] = {
        "schema_version": "formulation-knowledge-context-v1",
        "network_used": False,
        "authority": dict(FALSE_AUTHORITY),
        "numeric_calibrations_admitted": [],
        "pleasantness": None,
        "personal_liking": None,
    }
    try:
        pack_bytes, corpus_bytes = PACK_PATH.read_bytes(), CORPUS_PATH.read_bytes()
        pack, corpus = _parse_pack(pack_bytes), _parse_corpus(corpus_bytes)
    except (OSError, ValueError, TypeError):
        return {
            **base,
            "state": "WITHHOLD_UNKNOWN",
            "reason_codes": ["KNOWLEDGE_MANIFEST_UNAVAILABLE"],
            "pack_sha256": None,
            "prior_corpus_sha256": None,
            "profiles": [],
            "profile_ids": [],
            "claims": [],
            "sources": [],
            "material_bindings": [],
            "prior_references": [],
            "quarantined_claim_ids": [],
            "strongest_clue": None,
        }
    positive = _positive_text(request, avoid)
    unavailable_sources = _unavailable_sources(pack)
    available_claims = {
        claim["claim_id"]
        for claim in pack["claims"]
        if not unavailable_sources.intersection(claim["source_ids"])
    }
    profiles = [
        profile
        for profile in _profiles(pack, positive, avoid)
        if set(profile["claim_ids"]) <= available_claims
    ]
    bindings = [binding for name in material_names if (binding := material_knowledge(name))]
    requested_ids = {claim_id for row in [*profiles, *bindings] for claim_id in row["claim_ids"]}
    ranked = []
    for index, claim in enumerate(pack["claims"]):
        if claim["claim_id"] not in available_claims:
            continue
        score = sum(_present(positive, tag) for tag in claim["tags"])
        if claim["claim_id"] in requested_ids:
            score += 20
        if score:
            ranked.append((score, index, claim))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    claims = [row for _, _, row in ranked[:12]]
    source_ids = {source_id for claim in claims for source_id in claim["source_ids"]}
    references = _prior_references(corpus, positive)
    result = {
        **base,
        "state": "ADVISORY_KNOWLEDGE_AVAILABLE",
        "pack_sha256": hashlib.sha256(pack_bytes).hexdigest(),
        "prior_corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        "profiles": profiles,
        "profile_ids": [row["profile_id"] for row in profiles],
        "claims": claims,
        "sources": [row for row in pack["sources"] if row["source_id"] in source_ids],
        "material_bindings": bindings,
        "prior_references": references,
        "indexed_prior_record_count": len(corpus["records"]),
        "quarantined_claim_ids": [row["claim_id"] for row in pack["quarantined_claims"]],
        "strongest_clue": profiles[0]["clue"]
        if profiles
        else (claims[0]["statement"] if claims else None),
        "reason_codes": [
            "PRIOR_RESEARCH_IS_REFERENCE_ONLY",
            "DESIGN_CLUES_ARE_NOT_NUMERIC_CALIBRATIONS",
        ],
        "unavailable_source_ids": sorted(unavailable_sources),
    }
    return copy.deepcopy(result)


__all__ = [
    "audit_prior_research",
    "knowledge_fingerprints",
    "load_knowledge_pack",
    "material_knowledge",
    "retrieve_formulation_knowledge",
    "validate_knowledge_pack",
]
