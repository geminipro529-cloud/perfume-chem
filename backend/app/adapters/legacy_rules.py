"""Deterministic, non-promoting inventory of the legacy rule corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from app.services.lab_rules import (
    RULE_DIAGNOSTIC_CODES,
    RuleCandidateInput,
    RuleEndpointInput,
    canonical_json_sha256,
    compile_rule_batch,
)

LEGACY_RULE_DIAGNOSTIC_CODES = (
    "LEGACY_HARD_PROMOTION_REJECTED",
    "NUMERICAL_CLAIM_WITHOUT_CONTROLLED_EVIDENCE",
    *RULE_DIAGNOSTIC_CODES,
)

_GENERIC_LABELS = {
    "accord",
    "citrus",
    "everything",
    "floral",
    "florals",
    "floral bouquets",
    "marine notes",
    "musks",
    "orange",
    "rose",
    "woods",
}


@dataclass(frozen=True, slots=True)
class LegacyRuleSource:
    path: str
    payload: Any
    source_sha256: str

    def __post_init__(self) -> None:
        path = str(self.path or "").strip().replace("\\", "/")
        digest = str(self.source_sha256 or "").strip().lower()
        if not path:
            raise ValueError("legacy source path must not be empty")
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("legacy source SHA-256 is invalid")
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "source_sha256", digest)


@dataclass(frozen=True, slots=True)
class LegacyRuleInventory:
    candidates: tuple[RuleCandidateInput, ...]
    total_records: int
    source_record_counts: dict[str, int]
    diagnostic_codes: tuple[str, ...]
    invalid_exact_count: int
    blocking_count: int
    numerical_model_count: int
    duplicate_count: int
    cycle_count: int
    report_sha256: str


def _is_generic(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
    if not text:
        return True
    if text in _GENERIC_LABELS:
        return True
    if text.startswith("__") and text.endswith("__"):
        return True
    base = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip(" -:;,")
    if base in _GENERIC_LABELS:
        return True
    if text.startswith("everything"):
        return True
    return any(
        token in text
        for token in (" accord", " notes", " materials", " bouquets")
    )


def _endpoint(
    label: str,
    *,
    identity_resolver: Callable[[str], str | None],
    group_resolver: Mapping[str, str],
) -> RuleEndpointInput:
    normalized = str(label or "").strip()
    group_id = group_resolver.get(normalized.casefold())
    if group_id:
        return RuleEndpointInput(
            kind="GROUP",
            raw_label=normalized,
            group_id=group_id,
        )
    if _is_generic(normalized):
        return RuleEndpointInput(kind="GENERIC_PROSE", raw_label=normalized or "(empty)")
    identity = identity_resolver(normalized)
    if identity:
        return RuleEndpointInput(
            kind="EXACT_IDENTITY",
            raw_label=normalized,
            identity_scope_sha256=identity,
        )
    return RuleEndpointInput(kind="UNRESOLVED", raw_label=normalized or "(empty)")


def _relation(raw_type: str) -> str:
    value = str(raw_type or "").strip().casefold()
    if value in {"synergy", "pairing"}:
        return "SYNERGIZES" if value == "synergy" else "REINFORCES"
    if value in {"conflict", "clash", "rejection", "antagonism"}:
        return "SUPPRESSES"
    if value == "neutral":
        return "NON_EQUIVALENT"
    return "ADDS"


def _slug(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).casefold()).strip("-")
    return text[:160] or "legacy-rule"


def _stable_diagnostics(codes: Sequence[str]) -> tuple[str, ...]:
    present = set(codes)
    ordered = dict.fromkeys(LEGACY_RULE_DIAGNOSTIC_CODES)
    return tuple(code for code in ordered if code in present)


def _records(source: LegacyRuleSource) -> list[tuple[str, dict[str, Any]]]:
    if isinstance(source.payload, list):
        return [
            (f"/{index}", row if isinstance(row, dict) else {"raw_value": row})
            for index, row in enumerate(source.payload)
        ]
    if isinstance(source.payload, dict):
        return [
            (
                "/" + str(key).replace("~", "~0").replace("/", "~1"),
                {
                    "theory_key": str(key),
                    "theory_value": value,
                    "type": "theory",
                    "effect": str(value.get("principle", ""))
                    if isinstance(value, dict)
                    else str(value),
                    "source": source.path,
                },
            )
            for key, value in sorted(source.payload.items(), key=lambda item: str(item[0]))
        ]
    return [("/", {"raw_value": source.payload})]


def inventory_legacy_rule_corpus(
    sources: Sequence[LegacyRuleSource],
    *,
    identity_resolver: Callable[[str], str | None],
    group_resolver: Mapping[str, str] | None = None,
) -> LegacyRuleInventory:
    groups = {
        str(key).casefold(): str(value)
        for key, value in (group_resolver or {}).items()
    }
    candidates: list[RuleCandidateInput] = []
    diagnostics: list[str] = []
    source_counts: dict[str, int] = {}
    for source in sorted(sources, key=lambda item: item.path):
        records = _records(source)
        source_counts[source.path] = len(records)
        for pointer, row in records:
            theory = "theory_key" in row
            subject_label = (
                str(row["theory_key"])
                if theory
                else str(row.get("material_a") or row.get("ingredient_a") or "(missing)")
            )
            object_label = (
                "perfumery-practice"
                if theory
                else str(row.get("material_b") or row.get("ingredient_b") or "(missing)")
            )
            subject = (
                RuleEndpointInput(kind="GENERIC_PROSE", raw_label=subject_label)
                if theory
                else _endpoint(
                    subject_label,
                    identity_resolver=identity_resolver,
                    group_resolver=groups,
                )
            )
            object_endpoint = (
                RuleEndpointInput(kind="GENERIC_PROSE", raw_label=object_label)
                if theory
                else _endpoint(
                    object_label,
                    identity_resolver=identity_resolver,
                    group_resolver=groups,
                )
            )
            unresolved = any(
                endpoint.kind == "UNRESOLVED"
                for endpoint in (subject, object_endpoint)
            )
            generic = any(
                endpoint.kind == "GENERIC_PROSE"
                for endpoint in (subject, object_endpoint)
            )
            if unresolved:
                diagnostics.extend(
                    ("UNRESOLVED_EXACT_IDENTITY", "ORPHAN_REFERENCE")
                )
            if generic:
                diagnostics.append("GENERIC_PROSE")
            if str(row.get("determinism", "")).strip().casefold() == "hard":
                diagnostics.append("LEGACY_HARD_PROMOTION_REJECTED")
            effect_text = str(row.get("effect", ""))
            numerical_claim = (
                row.get("magnitude") is not None
                or row.get("ratio") not in (None, "")
                or bool(re.search(r"\b\d+(?:\.\d+)?\s*(?:x|%)\b", effect_text.casefold()))
            )
            if numerical_claim:
                diagnostics.append(
                    "NUMERICAL_CLAIM_WITHOUT_CONTROLLED_EVIDENCE"
                )
            raw_digest = canonical_json_sha256(row)
            rule_key = _slug(
                f"{source.path}-{pointer}-{subject_label}-{row.get('type', 'theory')}-{object_label}"
            )
            status = "INVALID" if unresolved else "ADVISORY"
            candidates.append(
                RuleCandidateInput(
                    rule_key=rule_key,
                    version=1,
                    subject=subject,
                    relation="ADDS" if theory else _relation(str(row.get("type", ""))),
                    object=object_endpoint,
                    directionality="DIRECTED",
                    matrix_context={},
                    dose_domain={},
                    temporal_domain={},
                    expected_effect={"legacy_text": effect_text},
                    attribute=str(row.get("axis") or "legacy_unspecified"),
                    rationale=effect_text or "Legacy explanatory record.",
                    source_document_version_id=None,
                    source_extraction_id=None,
                    source_locator=str(row.get("source") or ""),
                    evidence_class="LEGACY_PROSE" if theory or generic else "LEGACY_UNVERIFIED",
                    uncertainty={"state": "UNKNOWN"},
                    review_state="UNREVIEWED",
                    status=status,
                    runtime_role="EXPLANATORY",
                    raw_source_path=source.path,
                    raw_json_pointer=pointer,
                    raw_payload_sha256=raw_digest,
                    numerical_model_ref=None,
                )
            )
    batch = compile_rule_batch(tuple(candidates))
    diagnostics.extend(batch.diagnostic_codes)
    stable_diagnostics = _stable_diagnostics(diagnostics)
    invalid_exact_count = sum(
        1
        for candidate in candidates
        if candidate.status == "INVALID"
        and any(
            endpoint.kind == "UNRESOLVED"
            for endpoint in (candidate.subject, candidate.object)
        )
    )
    canonical_candidates = sorted(
        (
            {
                "path": candidate.raw_source_path,
                "pointer": candidate.raw_json_pointer,
                "payload_sha256": candidate.raw_payload_sha256,
                "status": candidate.status,
                "subject_kind": candidate.subject.kind,
                "object_kind": candidate.object.kind,
            }
            for candidate in candidates
        ),
        key=lambda row: (row["path"], row["pointer"], row["payload_sha256"]),
    )
    report_sha256 = canonical_json_sha256(
        {
            "source_record_counts": dict(sorted(source_counts.items())),
            "candidates": canonical_candidates,
            "diagnostics": stable_diagnostics,
            "invalid_exact_count": invalid_exact_count,
        }
    )
    return LegacyRuleInventory(
        candidates=tuple(
            sorted(
                candidates,
                key=lambda item: (item.raw_source_path, item.raw_json_pointer),
            )
        ),
        total_records=len(candidates),
        source_record_counts=dict(sorted(source_counts.items())),
        diagnostic_codes=stable_diagnostics,
        invalid_exact_count=invalid_exact_count,
        blocking_count=sum(
            candidate.runtime_role == "BLOCKING" for candidate in candidates
        ),
        numerical_model_count=sum(
            candidate.numerical_model_ref is not None for candidate in candidates
        ),
        duplicate_count=sum(
            "DUPLICATE_RULE" in rule.diagnostics for rule in batch.rules
        ),
        cycle_count=int("DIRECTED_CYCLE" in batch.diagnostic_codes),
        report_sha256=report_sha256,
    )


__all__ = [
    "LEGACY_RULE_DIAGNOSTIC_CODES",
    "LegacyRuleInventory",
    "LegacyRuleSource",
    "inventory_legacy_rule_corpus",
]
