"""Literature rule inventory and provenance checks for the live pipeline.

This module does not try to solve "all literature". It defines the operational
coverage contract the pipeline can actually verify today:

- in-repo English knowledge sources
- the French literature manifest
- structured knowledge-graph assets that encode deterministic craft/science rules
- semantic-search index freshness for the knowledge corpus
- tiered reference database (wired from future_modules/literature_references.py)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.material_resolver import resolve_material

# ── Wire future_modules literature reference database ──────────────────
_LITERATURE_DB_LOADED = False
_ALL_REFERENCES: tuple[Any, ...] = ()
_TOPIC_REFERENCES: dict[str, tuple[str, ...]] = {}
_cite_fn: Any = None
_get_ref_fn: Any = None
_get_topic_refs_fn: Any = None
_get_refs_by_tier_fn: Any = None
_get_tier_counts_fn: Any = None

try:
    # future_modules sits at the repo root, same level as engine/
    _repo_root = Path(__file__).resolve().parents[2]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from future_modules.literature_references import (
        ALL_REFERENCES as _ALL_REFS,
        TOPIC_REFERENCES as _TOPIC_REFS,
        cite as _cite,
        get_reference as _get_ref,
        get_references_by_topic as _get_topic_refs,
        get_references_by_tier as _get_refs_by_tier,
        get_tier_counts as _get_tier_counts,
    )

    _ALL_REFERENCES = _ALL_REFS
    _TOPIC_REFERENCES = _TOPIC_REFS
    _cite_fn = _cite
    _get_ref_fn = _get_ref
    _get_topic_refs_fn = _get_topic_refs
    _get_refs_by_tier_fn = _get_refs_by_tier
    _get_tier_counts_fn = _get_tier_counts
    _LITERATURE_DB_LOADED = True
except ImportError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
KG_DIR = PROJECT_ROOT / "data" / "knowledge_graph"
EMBEDDING_DIR = PROJECT_ROOT / "data" / "embeddings"
FRENCH_MANIFEST = (
    KNOWLEDGE_DIR / "literature" / "French_Perfume_Literature_Pipeline_Manifest.md"
)

STRUCTURED_RULE_FILES = {
    "theory_rules": KG_DIR / "theory_rules.json",
    "pairing_rules": KG_DIR / "pairing_rules.json",
    "synergy_matrix": KG_DIR / "synergy_matrix.json",
    "accords": KG_DIR / "accords.json",
}


@dataclass(frozen=True, slots=True)
class LiteratureRuleContract:
    status: str
    english_sources: int
    french_manifest_entries: int
    deterministic_rule_entries: int
    advisory_rule_entries: int
    searchable_sources: int
    index_fresh: bool
    rebuild_recommended: bool
    deferred_french_entries: int
    warnings: tuple[str, ...]
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "english_sources": self.english_sources,
            "french_manifest_entries": self.french_manifest_entries,
            "deterministic_rule_entries": self.deterministic_rule_entries,
            "advisory_rule_entries": self.advisory_rule_entries,
            "searchable_sources": self.searchable_sources,
            "index_fresh": self.index_fresh,
            "rebuild_recommended": self.rebuild_recommended,
            "deferred_french_entries": self.deferred_french_entries,
            "warnings": list(self.warnings),
            "details": dict(self.details),
        }


@dataclass(frozen=True, slots=True)
class KnowledgeRuleQualityContract:
    status: str
    total_entries: int
    valid_entries: int
    advisory_entries: int
    invalid_entries: int
    orphan_material_refs: int
    generic_material_refs: int
    warnings: tuple[str, ...]
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_entries": self.total_entries,
            "valid_entries": self.valid_entries,
            "advisory_entries": self.advisory_entries,
            "invalid_entries": self.invalid_entries,
            "orphan_material_refs": self.orphan_material_refs,
            "generic_material_refs": self.generic_material_refs,
            "warnings": list(self.warnings),
            "details": dict(self.details),
        }


def _safe_load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _collect_english_sources() -> list[Path]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return [path for path in KNOWLEDGE_DIR.rglob("*.md") if path != FRENCH_MANIFEST]


def _parse_french_manifest() -> dict[str, Any]:
    if not FRENCH_MANIFEST.exists():
        return {"entries": 0, "deferred": 0, "tiers": {}}

    text = FRENCH_MANIFEST.read_text(encoding="utf-8", errors="replace")
    entries = re.findall(r"^###\s+\d+\.\s+", text, flags=re.MULTILINE)
    tiers = {
        "tier_a": len(re.findall(r"^##\s+Tier A", text, flags=re.MULTILINE)),
        "tier_b": len(re.findall(r"^##\s+Tier B", text, flags=re.MULTILINE)),
    }
    deferred = len(
        re.findall(
            r"\bStatus:\s*\n?\s*-\s*full text not confirmed", text, flags=re.IGNORECASE
        )
    )
    return {"entries": len(entries), "deferred": deferred, "tiers": tiers}


def _knowledge_index_status(source_files: list[Path]) -> dict[str, Any]:
    chunk_map = EMBEDDING_DIR / "chunk_map.json"
    index_path = EMBEDDING_DIR / "knowledge_index.faiss"
    npy_path = EMBEDDING_DIR / "embeddings.npy"

    if not source_files:
        return {
            "searchable_sources": 0,
            "index_fresh": False,
            "rebuild_recommended": False,
            "reason": "no_knowledge_sources",
        }

    if not chunk_map.exists():
        return {
            "searchable_sources": 0,
            "index_fresh": False,
            "rebuild_recommended": True,
            "reason": "chunk_map_missing",
        }

    latest_source_mtime = max(path.stat().st_mtime for path in source_files)
    artifact_mtime = max(
        path.stat().st_mtime
        for path in (chunk_map, index_path, npy_path)
        if path.exists()
    )
    try:
        chunk_payload = json.loads(chunk_map.read_text(encoding="utf-8"))
        searchable_sources = len(
            {row.get("source", "") for row in chunk_payload if row.get("source")}
        )
    except Exception:
        searchable_sources = 0

    index_fresh = artifact_mtime >= latest_source_mtime
    return {
        "searchable_sources": searchable_sources,
        "index_fresh": index_fresh,
        "rebuild_recommended": not index_fresh,
        "reason": "stale_index" if not index_fresh else "up_to_date",
    }


def _structured_rule_counts() -> dict[str, Any]:
    deterministic = 0
    advisory = 0
    by_file: dict[str, int] = {}
    missing_files: list[str] = []

    for key, path in STRUCTURED_RULE_FILES.items():
        if not path.exists():
            missing_files.append(key)
            by_file[key] = 0
            continue
        payload = _safe_load_json(path)
        if isinstance(payload, dict):
            count = len(payload)
            deterministic += count
            by_file[key] = count
            continue
        if isinstance(payload, list):
            by_file[key] = len(payload)
            for row in payload:
                source = str((row or {}).get("source", "")).lower()
                effect = str((row or {}).get("effect", "")).lower()
                if any(
                    token in source or token in effect
                    for token in ("philosophy", "aesthetic", "journal", "narrative")
                ):
                    advisory += 1
                else:
                    deterministic += 1
            continue
        by_file[key] = 0

    return {
        "deterministic": deterministic,
        "advisory": advisory,
        "by_file": by_file,
        "missing_files": missing_files,
    }


def _normalized_rule_metadata(
    row: dict[str, Any], *, source_hint: str, runtime_consumers: list[str]
) -> dict[str, Any]:
    payload = dict(row)
    payload.setdefault("source", source_hint)
    payload.setdefault(
        "language", "en" if "french" not in source_hint.lower() else "fr"
    )
    payload.setdefault("runtime_consumers", runtime_consumers)
    payload.setdefault("confidence", "medium")
    if "determinism" not in payload:
        payload["determinism"] = "advisory"
    if (
        payload.get("type") in {"synergy", "conflict"}
        and payload.get("material_a")
        and payload.get("material_b")
    ):
        if row.get("determinism") in (None, ""):
            payload["determinism"] = "hard"
    return payload


_GENERIC_TOKENS = {
    "citrus",
    "orange",
    "rose",
    "jasmine",
    "woods",
    "musks",
    "florals",
    "floral bouquets",
    "marine notes",
    "heavy musks",
    "everything",
    "goal",
    "amplifier",
    "target",
    "ratio",
    "__avoid__",
    "__carles_rule__",
}


def _is_generic_reference(value: str) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return True
    if text in _GENERIC_TOKENS:
        return True
    if text.startswith("__") and text.endswith("__"):
        return True
    label = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip(" -—–:")
    if label in _GENERIC_TOKENS:
        return True
    if re.match(
        r"^(heavy|light|soft|clean|fresh|green|woody|floral|marine)\s+"
        r"(musks|woods|florals|notes|materials|bouquets)\b",
        label,
    ):
        return True
    if text.startswith("everything"):
        return True
    if any(token in text for token in (" accord", " notes", " materials", " bouquets")):
        return True
    return False


def _vp_from_resolved(resolved) -> float | None:
    reg = getattr(resolved, "registry_material", None)
    if reg is not None:
        value = getattr(reg, "vp_25c_pa", None) or getattr(reg, "vp_25c", None)
        if value is not None:
            try:
                return float(value)
            except Exception:
                return None
    profile = getattr(resolved, "profile", None)
    value = getattr(profile, "vp", None) if profile is not None else None
    try:
        return float(value) if value is not None else None
    except Exception:
        return None


def _note_from_resolved(resolved) -> str:
    profile = getattr(resolved, "profile", None)
    return str(getattr(profile, "note", "heart") or "heart").lower()


def build_knowledge_rule_quality_contract() -> KnowledgeRuleQualityContract:
    warnings: list[str] = []
    invalid_entries = 0
    advisory_entries = 0
    valid_entries = 0
    orphan_material_refs = 0
    generic_material_refs = 0
    total_entries = 0
    by_file: dict[str, dict[str, int]] = {}
    examples: dict[str, list[dict[str, Any]]] = {}

    list_files = {
        "pairing_rules": STRUCTURED_RULE_FILES["pairing_rules"],
        "synergy_matrix": STRUCTURED_RULE_FILES["synergy_matrix"],
    }

    for label, path in list_files.items():
        payload = _safe_load_json(path)
        rows = payload if isinstance(payload, list) else []
        file_stats = {
            "entries": len(rows),
            "valid": 0,
            "advisory": 0,
            "invalid": 0,
            "orphan_refs": 0,
            "generic_refs": 0,
        }
        file_examples: list[dict[str, Any]] = []
        for raw_row in rows:
            if not isinstance(raw_row, dict):
                invalid_entries += 1
                file_stats["invalid"] += 1
                continue
            total_entries += 1
            row = _normalized_rule_metadata(
                raw_row,
                source_hint=str(raw_row.get("source", label)),
                runtime_consumers=[
                    "release_preflight",
                    "formula_scoring",
                    "interventions",
                ],
            )
            a = str(row.get("material_a", "")).strip()
            b = str(row.get("material_b", "")).strip()
            validation_status = "valid"
            reasons: list[str] = []
            generic_refs = sum(1 for value in (a, b) if _is_generic_reference(value))
            generic_material_refs += generic_refs
            file_stats["generic_refs"] += generic_refs

            resolved_a = None if _is_generic_reference(a) else resolve_material(a)
            resolved_b = None if _is_generic_reference(b) else resolve_material(b)

            if resolved_a is not None and not resolved_a.is_known:
                orphan_material_refs += 1
                file_stats["orphan_refs"] += 1
                reasons.append(f"unknown:{a}")
            if resolved_b is not None and not resolved_b.is_known:
                orphan_material_refs += 1
                file_stats["orphan_refs"] += 1
                reasons.append(f"unknown:{b}")

            if row.get("source") in (None, "", label):
                reasons.append("weak_source")
            if row.get("confidence") == "medium" and (
                "source" not in raw_row or "confidence" not in raw_row
            ):
                reasons.append("defaulted_metadata")

            if (
                resolved_a is not None
                and resolved_b is not None
                and resolved_a.is_known
                and resolved_b.is_known
            ):
                note_a = _note_from_resolved(resolved_a)
                note_b = _note_from_resolved(resolved_b)
                if row.get("type") == "synergy" and {note_a, note_b} == {"top", "base"}:
                    reasons.append("extreme_note_window_gap")
                vp_a = _vp_from_resolved(resolved_a)
                vp_b = _vp_from_resolved(resolved_b)
                if (
                    vp_a is not None
                    and vp_b is not None
                    and vp_a < 0.05
                    and vp_b < 0.05
                    and row.get("type") == "synergy"
                ):
                    reasons.append("low_joint_volatility")

            if any(reason.startswith("unknown:") for reason in reasons):
                validation_status = "invalid"
                invalid_entries += 1
                file_stats["invalid"] += 1
            elif reasons:
                validation_status = "advisory"
                advisory_entries += 1
                file_stats["advisory"] += 1
            else:
                valid_entries += 1
                file_stats["valid"] += 1

            if len(file_examples) < 8 and validation_status != "valid":
                file_examples.append(
                    {
                        "material_a": a,
                        "material_b": b,
                        "validation_status": validation_status,
                        "reasons": reasons,
                    }
                )

        by_file[label] = file_stats
        if file_examples:
            examples[label] = file_examples

    dict_files = {
        "theory_rules": STRUCTURED_RULE_FILES["theory_rules"],
        "accords": STRUCTURED_RULE_FILES["accords"],
    }
    for label, path in dict_files.items():
        payload = _safe_load_json(path)
        count = len(payload) if isinstance(payload, dict) else 0
        total_entries += count
        by_file[label] = {
            "entries": count,
            "valid": count,
            "advisory": 0,
            "invalid": 0,
            "orphan_refs": 0,
            "generic_refs": 0,
        }
        valid_entries += count

    status = "PASS"
    if invalid_entries > 0:
        status = "WARN"
        warnings.append(
            f"{invalid_entries} structured rules reference unknown materials."
        )
    if generic_material_refs > 0:
        status = "WARN"
        warnings.append(
            f"{generic_material_refs} rule references are generic/advisory rather than exact materials."
        )
    if advisory_entries > max(10, valid_entries):
        status = "WARN"
        warnings.append(
            "A large share of rule entries are advisory/degraded rather than exact-runtime rules."
        )
    if total_entries == 0:
        status = "FAIL"
        warnings.append("No structured knowledge rules were loaded.")

    return KnowledgeRuleQualityContract(
        status=status,
        total_entries=total_entries,
        valid_entries=valid_entries,
        advisory_entries=advisory_entries,
        invalid_entries=invalid_entries,
        orphan_material_refs=orphan_material_refs,
        generic_material_refs=generic_material_refs,
        warnings=tuple(warnings),
        details={"by_file": by_file, "examples": examples},
    )


def build_literature_rule_contract() -> LiteratureRuleContract:
    english_sources = _collect_english_sources()
    manifest = _parse_french_manifest()
    index = _knowledge_index_status(
        english_sources + ([FRENCH_MANIFEST] if FRENCH_MANIFEST.exists() else [])
    )
    rule_counts = _structured_rule_counts()

    warnings: list[str] = []
    status = "PASS"
    if manifest["entries"] == 0:
        status = "WARN"
        warnings.append("French literature manifest missing or empty.")
    if rule_counts["missing_files"]:
        status = "WARN"
        warnings.append(
            "Missing structured rule files: "
            + ", ".join(sorted(rule_counts["missing_files"]))
        )
    if index["rebuild_recommended"]:
        status = "WARN"
        warnings.append("Knowledge index is stale relative to source literature.")
    if rule_counts["deterministic"] == 0:
        status = "FAIL"
        warnings.append(
            "No deterministic structured rule entries available for runtime consumers."
        )

    details = {
        "structured_rule_files": rule_counts["by_file"],
        "missing_rule_files": rule_counts["missing_files"],
        "french_manifest": manifest,
        "knowledge_index": index,
    }
    return LiteratureRuleContract(
        status=status,
        english_sources=len(english_sources),
        french_manifest_entries=int(manifest["entries"]),
        deterministic_rule_entries=int(rule_counts["deterministic"]),
        advisory_rule_entries=int(rule_counts["advisory"]),
        searchable_sources=int(index["searchable_sources"]),
        index_fresh=bool(index["index_fresh"]),
        rebuild_recommended=bool(index["rebuild_recommended"]),
        deferred_french_entries=int(manifest["deferred"]),
        warnings=tuple(warnings),
        details=details,
    )
