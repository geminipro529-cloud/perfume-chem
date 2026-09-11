"""Per-flower peer-reviewed evidence layer for the soliflore structures.

Companion to :mod:`engine.knowledge.soliflore_structures`, which stores 19
single-flower templates with an *unsourced* ``hedonic`` string and
``hedonic_score``. This module attaches, for each flower, real peer-reviewed
literature covering:

* ``odor_chemistry`` — GC-MS / GC-O / AEDA of the flower's key odorants,
* ``hedonics`` — pleasantness / hedonic perception findings,
* ``architecture`` — bloom, emission dynamics and flower-structure evidence,
* ``mixture_perception`` / ``olfactory_white`` / ``bouquet_chemistry`` — for the
  ``mixed_florals`` bouquet group.

Every URL in the dataset was resolved (Crossref API / HTTP 2xx) at build time;
:func:`validate_floral_evidence` re-checks structure and minimum coverage.
Nothing here is a measured sensory claim — it is an evidence-classed citation
layer (``PEER_REVIEWED_LITERATURE``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "floral_hedonic_evidence_v1"
EVIDENCE_CLASS = "PEER_REVIEWED_LITERATURE"
MIN_REFS_PER_FLOWER = 5

FLORAL_EVIDENCE_CATEGORIES: tuple[str, ...] = (
    "odor_chemistry",
    "hedonics",
    "architecture",
    "mixture_perception",
    "olfactory_white",
    "bouquet_chemistry",
)

# The mixed/bouquet group is not a single-flower SolifloreType.
MIXED_FLORALS_KEY = "mixed_florals"

_DATA_FILENAME = "floral_hedonic_evidence.json"


def _repo_root() -> Path:
    # engine/knowledge/floral_hedonic_evidence.py -> repo root
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class FloralEvidenceRef:
    title: str
    authors: str
    journal: str
    year: int
    url: str
    category: str
    used_for: str
    tier: str = "A_peer_reviewed"

    @property
    def is_doi(self) -> bool:
        return "doi.org/" in self.url

    def as_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "url": self.url,
            "category": self.category,
            "used_for": self.used_for,
            "tier": self.tier,
            "is_doi": self.is_doi,
        }


@dataclass(frozen=True, slots=True)
class FloralEvidence:
    flower: str
    refs: tuple[FloralEvidenceRef, ...]

    @property
    def citation_count(self) -> int:
        return len(self.refs)

    @property
    def citations(self) -> tuple[str, ...]:
        return tuple(ref.url for ref in self.refs)

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({ref.category for ref in self.refs}))

    def _by_category(self, category: str) -> tuple[FloralEvidenceRef, ...]:
        return tuple(ref for ref in self.refs if ref.category == category)

    @property
    def odor_chemistry_refs(self) -> tuple[FloralEvidenceRef, ...]:
        return self._by_category("odor_chemistry")

    @property
    def hedonics_refs(self) -> tuple[FloralEvidenceRef, ...]:
        return self._by_category("hedonics")

    @property
    def architecture_refs(self) -> tuple[FloralEvidenceRef, ...]:
        return self._by_category("architecture")

    def as_dict(self) -> dict[str, Any]:
        return {
            "flower": self.flower,
            "citation_count": self.citation_count,
            "categories": list(self.categories),
            "refs": [ref.as_dict() for ref in self.refs],
        }


def _coerce_ref(flower: str, raw: Mapping[str, Any]) -> FloralEvidenceRef:
    category = str(raw.get("category", "")).strip()
    if category not in FLORAL_EVIDENCE_CATEGORIES:
        raise ValueError(f"{flower}: unknown evidence category {category!r}")
    return FloralEvidenceRef(
        title=str(raw["title"]).strip(),
        authors=str(raw["authors"]).strip(),
        journal=str(raw["journal"]).strip(),
        year=int(raw["year"]),
        url=str(raw["url"]).strip(),
        category=category,
        used_for=str(raw.get("used_for", "")).strip(),
    )


@lru_cache(maxsize=4)
def load_floral_evidence(path: str | None = None) -> dict[str, FloralEvidence]:
    """Load the per-flower evidence registry keyed by flower name."""
    target = Path(path) if path else _repo_root() / "data" / "knowledge_graph" / _DATA_FILENAME
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("floral evidence schema mismatch")
    flowers = payload.get("flowers")
    if not isinstance(flowers, Mapping) or not flowers:
        raise ValueError("floral evidence payload has no flowers")
    out: dict[str, FloralEvidence] = {}
    for flower, refs in flowers.items():
        if not isinstance(refs, list) or not refs:
            raise ValueError(f"{flower}: no references")
        out[str(flower)] = FloralEvidence(
            flower=str(flower),
            refs=tuple(_coerce_ref(str(flower), raw) for raw in refs),
        )
    return out


def flower_evidence_keys() -> tuple[str, ...]:
    return tuple(sorted(load_floral_evidence()))


@lru_cache(maxsize=4)
def load_floral_hedonics_gaps(path: str | None = None) -> dict[str, str]:
    """Flowers with no dedicated peer-reviewed hedonic study (documented gaps)."""
    target = Path(path) if path else _repo_root() / "data" / "knowledge_graph" / _DATA_FILENAME
    payload = json.loads(target.read_text(encoding="utf-8"))
    gaps = payload.get("hedonics_gaps") or {}
    return {str(k): str(v) for k, v in gaps.items()}


def get_floral_evidence(flower: str) -> FloralEvidence | None:
    return load_floral_evidence().get(flower.strip().lower())


def all_floral_evidence() -> tuple[FloralEvidence, ...]:
    return tuple(load_floral_evidence()[key] for key in flower_evidence_keys())


def soliflore_evidence_for(soliflore_type: Any) -> FloralEvidence | None:
    """Return the evidence row for a SolifloreType or its string value."""
    value = getattr(soliflore_type, "value", soliflore_type)
    return get_floral_evidence(str(value))


def floral_evidence_coverage() -> dict[str, Any]:
    registry = load_floral_evidence()
    counts = {flower: ev.citation_count for flower, ev in registry.items()}
    missing_hedonics = sorted(
        flower for flower, ev in registry.items() if not ev.hedonics_refs
    )
    return {
        "flowers": len(counts),
        "total_refs": sum(counts.values()),
        "min_refs_per_flower": MIN_REFS_PER_FLOWER,
        "counts": counts,
        "below_minimum": sorted(f for f, c in counts.items() if c < MIN_REFS_PER_FLOWER),
        "flowers_missing_hedonics": missing_hedonics,
        "documented_hedonics_gaps": load_floral_hedonics_gaps(),
    }


def validate_floral_evidence() -> None:
    """Structural + coverage validation; raises on any violation."""
    registry = load_floral_evidence()
    if MIXED_FLORALS_KEY not in registry:
        raise ValueError("missing mixed_florals bouquet group")
    for flower, evidence in registry.items():
        if evidence.citation_count < MIN_REFS_PER_FLOWER:
            raise ValueError(
                f"{flower}: {evidence.citation_count} refs < minimum {MIN_REFS_PER_FLOWER}"
            )
        for ref in evidence.refs:
            if not ref.url.startswith("https://"):
                raise ValueError(f"{flower}: non-https citation {ref.url}")
            if not ref.title or not ref.journal or not ref.authors:
                raise ValueError(f"{flower}: incomplete reference {ref.title!r}")


__all__ = [
    "SCHEMA_VERSION",
    "EVIDENCE_CLASS",
    "MIN_REFS_PER_FLOWER",
    "FLORAL_EVIDENCE_CATEGORIES",
    "MIXED_FLORALS_KEY",
    "FloralEvidenceRef",
    "FloralEvidence",
    "load_floral_evidence",
    "load_floral_hedonics_gaps",
    "flower_evidence_keys",
    "get_floral_evidence",
    "all_floral_evidence",
    "soliflore_evidence_for",
    "floral_evidence_coverage",
    "validate_floral_evidence",
]
