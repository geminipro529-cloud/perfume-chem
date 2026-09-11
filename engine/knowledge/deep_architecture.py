"""Deep Architecture — literature-backed texture/depth/layering knowledge surface.

This module is the *knowledge* side of the Deep Architecture capability. It owns:
  * the seven structural dimensions and their authority labels;
  * the peer-reviewed evidence registry (collected via Europe PMC/Crossref,
    merged with the curated registries in ``performance_engineering`` and
    ``floral_hedonic_evidence``);
  * per-family/subfamily/archetype target profiles with tolerant ranges;
  * validation of evidence quotas and profile coverage.

It deliberately carries no optimizer score arithmetic (that lives in
``engine.optimizer.scoring`` and remains opt-in) and grants no sensory,
sillage, longevity, safety, or release authority. ``spatial_projection`` is a
PREDICTED_PHYSICAL axis only and must never be reported as observed sillage.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

DIMENSIONS: tuple[str, ...] = (
    "texture",
    "depth_stacking",
    "temporal_layering",
    "spatial_projection",
    "integration_capacity",
    "function_balance",
    "legibility_coherence",
)


@dataclass(frozen=True, slots=True)
class DeepArchitectureConfig:
    """Opt-in switch for the Deep Architecture scoring block.

    Default ``enabled=False`` keeps every existing optimizer score and golden
    output byte-identical. When enabled, ``FormulaScorer.score`` attaches a
    ``deep_architecture`` block (advisory only; never changes the composite).
    """

    enabled: bool = False
    profile: str = "auto"
    include_evidence_counts: bool = True

AUTHORITY_STRUCTURAL = "STRUCTURAL_ARCHITECTURE"
AUTHORITY_PREDICTED_PHYSICAL = "PREDICTED_PHYSICAL"

DIMENSION_AUTHORITY: dict[str, str] = {
    dim: AUTHORITY_STRUCTURAL for dim in DIMENSIONS
}
DIMENSION_AUTHORITY["spatial_projection"] = AUTHORITY_PREDICTED_PHYSICAL

MIN_DIMENSION_REFS = 10
SCHEMA_VERSION = "deep_architecture_evidence_v1"
PROFILES_SCHEMA_VERSION = "deep_architecture_profiles_v1"

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "engine_data"
EVIDENCE_PATH = _DATA_DIR / "deep_architecture_evidence.json"
PROFILES_PATH = _DATA_DIR / "deep_architecture_profiles.json"

# Curated peer-reviewed refs already verified in this project, mapped onto the
# deep-architecture dimensions.
_DOMAIN_TO_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "theory": ("depth_stacking", "legibility_coherence", "function_balance", "integration_capacity"),
    "neuroscience": ("integration_capacity", "temporal_layering"),
    "hedonism": ("legibility_coherence",),
    "architecture": ("depth_stacking", "integration_capacity", "legibility_coherence"),
    "function": ("depth_stacking", "temporal_layering", "spatial_projection",
                 "integration_capacity", "function_balance"),
}

_YEAR_RE = re.compile(r"(19|20)\d{2}")


def dimension_authority(dimension: str) -> str:
    try:
        return DIMENSION_AUTHORITY[dimension]
    except KeyError as exc:  # pragma: no cover - guarded by callers
        raise ValueError(f"unknown deep-architecture dimension: {dimension}") from exc


def _ref_key(ref: Mapping[str, Any]) -> str:
    doi = str(ref.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    return "url:" + str(ref.get("url") or "").strip().lower()


@lru_cache(maxsize=1)
def load_collected_evidence() -> dict[str, Any]:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("deep architecture evidence schema mismatch")
    return payload


@lru_cache(maxsize=1)
def _curated_dimension_refs() -> dict[str, tuple[dict[str, Any], ...]]:
    """Merge the verified curated registries into per-dimension refs."""
    out: dict[str, list[dict[str, Any]]] = {dim: [] for dim in DIMENSIONS}
    try:
        from engine.knowledge.performance_engineering import get_citations_for_domain
    except Exception:  # pragma: no cover - import guard
        return {dim: () for dim in DIMENSIONS}

    for domain, dimensions in _DOMAIN_TO_DIMENSIONS.items():
        for key, entry in get_citations_for_domain(domain).items():
            url = str(entry.get("url") or "").strip()
            if not url.startswith("https://"):
                continue
            source = str(entry.get("source") or "")
            year_match = _YEAR_RE.search(source)
            ref = {
                "key": f"curated:{key}",
                "title": str(entry.get("title") or ""),
                "authors": str(entry.get("authors") or ""),
                "journal": source,
                "year": int(year_match.group(0)) if year_match else 0,
                "doi": url.split("doi.org/", 1)[1].lower() if "doi.org/" in url else "",
                "url": url,
                "category": f"curated_{domain}",
                "used_for": str(entry.get("used_for") or ""),
                "tier": str(entry.get("tier") or "A_peer_reviewed"),
            }
            for dim in dimensions:
                out[dim].append(ref)

    # Floral registry contributes to hedonics/chemistry depth of the floral family.
    try:
        from engine.knowledge.floral_hedonic_evidence import all_floral_evidence
    except Exception:  # pragma: no cover
        all_floral_evidence = None  # type: ignore[assignment]
    if all_floral_evidence is not None:
        for evidence in all_floral_evidence():
            for ref in evidence.refs:
                entry = {
                    "key": f"floral:{ref.url}",
                    "title": ref.title,
                    "authors": ref.authors,
                    "journal": ref.journal,
                    "year": ref.year,
                    "doi": ref.url.split("doi.org/", 1)[1].lower() if "doi.org/" in ref.url else "",
                    "url": ref.url,
                    "category": "floral_hedonic_evidence",
                    "used_for": ref.used_for,
                    "tier": ref.tier,
                }
                if ref.category in ("mixture_perception", "olfactory_white", "architecture"):
                    out["depth_stacking"].append(entry)
                    out["legibility_coherence"].append(entry)
                else:
                    out["temporal_layering"].append(entry)
                    out["function_balance"].append(entry)

    return {dim: tuple(refs) for dim, refs in out.items()}


def dimension_citations(dimension: str) -> tuple[dict[str, Any], ...]:
    if dimension not in DIMENSIONS:
        raise ValueError(f"unknown deep-architecture dimension: {dimension}")
    collected = load_collected_evidence().get("dimensions", {}).get(dimension, [])
    merged: dict[str, dict[str, Any]] = {}
    for ref in list(collected) + list(_curated_dimension_refs()[dimension]):
        merged.setdefault(_ref_key(ref), ref)
    return tuple(merged.values())


def family_citations(family: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_collected_evidence().get("families", {}).get(family, []))


def subfamily_citations(subfamily: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_collected_evidence().get("subfamilies", {}).get(subfamily, []))


def archetype_citations(archetype: str) -> tuple[dict[str, Any], ...]:
    return tuple(load_collected_evidence().get("archetypes", {}).get(archetype, []))


def evidence_coverage() -> dict[str, Any]:
    payload = load_collected_evidence()
    dimension_counts = {dim: len(dimension_citations(dim)) for dim in DIMENSIONS}
    return {
        "dimension_refs": dimension_counts,
        "families": {k: len(v) for k, v in payload.get("families", {}).items()},
        "subfamily_keys": len(payload.get("subfamilies", {})),
        "archetype_keys": len(payload.get("archetypes", {})),
        "gaps": payload.get("gaps", {}),
        "doi_verification": payload.get("doi_verification", {}),
    }


# ---------------------------------------------------------------------------
# Profiles
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DimensionTarget:
    target: float
    minimum: float
    maximum: float


@dataclass(frozen=True, slots=True)
class DeepArchitectureProfile:
    key: str
    level: str  # "archetype" | "subfamily" | "family" | "generic"
    family: str
    targets: Mapping[str, DimensionTarget]
    authority: Mapping[str, str]

    def target(self, dimension: str) -> DimensionTarget:
        return self.targets[dimension]

    def within(self, dimension: str, value: float) -> bool:
        spec = self.targets[dimension]
        return spec.minimum <= value <= spec.maximum

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "level": self.level,
            "family": self.family,
            "targets": {
                dim: {"target": t.target, "min": t.minimum, "max": t.maximum}
                for dim, t in self.targets.items()
            },
            "authority": dict(self.authority),
        }


@lru_cache(maxsize=1)
def _profiles_payload() -> dict[str, Any]:
    payload = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    if payload.get("schema_version") != PROFILES_SCHEMA_VERSION:
        raise ValueError("deep architecture profiles schema mismatch")
    return payload


def _family_to_subfamilies() -> dict[str, str]:
    mapping: dict[str, str] = {}
    try:
        from engine.knowledge.perfume_taxonomy import FAMILY_SUBFAMILY_MAP
    except Exception:  # pragma: no cover
        return mapping
    for family, subs in FAMILY_SUBFAMILY_MAP.items():
        family_value = getattr(family, "value", family)
        for sub in subs:
            mapping[str(getattr(sub, "value", sub))] = str(family_value)
    return mapping


def _make_targets(
    raw: Mapping[str, float],
    tolerance: Mapping[str, float],
    ranges: Mapping[str, list[float]] | None = None,
    override_dims: set[str] | None = None,
) -> dict[str, DimensionTarget]:
    minus = float(tolerance.get("minus", 25))
    plus = float(tolerance.get("plus", 15))
    targets: dict[str, DimensionTarget] = {}
    for dim in DIMENSIONS:
        value = float(raw.get(dim, 50.0))
        use_range = (
            ranges is not None
            and dim in ranges
            and (override_dims is None or dim not in override_dims)
        )
        if use_range:
            lo, hi = ranges[dim]
            targets[dim] = DimensionTarget(
                target=value, minimum=float(lo), maximum=float(hi)
            )
        else:
            targets[dim] = DimensionTarget(
                target=value,
                minimum=max(0.0, value - minus),
                maximum=min(100.0, value + plus),
            )
    return targets


def resolve_profile(key: str = "") -> DeepArchitectureProfile:
    """Resolve archetype override -> subfamily -> family -> generic."""
    payload = _profiles_payload()
    families = payload.get("families", {})
    overrides = payload.get("archetype_overrides", {})
    tolerance = payload.get("tolerance", {})
    family_ranges = payload.get("family_ranges", {})
    authority = {dim: dimension_authority(dim) for dim in DIMENSIONS}

    normalized = str(key or "").strip()
    if normalized in overrides:
        override = overrides[normalized]
        family = str(override.get("family", ""))
        raw = dict(families.get(family, {}))
        raw.update({k: v for k, v in override.items() if k != "family"})
        override_dims = {k for k in override if k != "family"}
        return DeepArchitectureProfile(
            key=normalized,
            level="archetype",
            family=family,
            targets=_make_targets(
                raw, tolerance, family_ranges.get(family, {}), override_dims
            ),
            authority=authority,
        )

    sub_to_family = _family_to_subfamilies()
    if normalized in sub_to_family:
        family = sub_to_family[normalized]
        raw = families.get(family, {})
        return DeepArchitectureProfile(
            key=normalized, level="subfamily", family=family,
            targets=_make_targets(raw, tolerance, family_ranges.get(family, {})),
            authority=authority,
        )

    if normalized in families:
        return DeepArchitectureProfile(
            key=normalized, level="family", family=normalized,
            targets=_make_targets(families[normalized], tolerance, family_ranges.get(normalized, {})),
            authority=authority,
        )

    return DeepArchitectureProfile(
        key=normalized or "generic", level="generic", family="",
        targets=_make_targets({dim: 60.0 for dim in DIMENSIONS}, tolerance),
        authority=authority,
    )


def validate_deep_architecture() -> dict[str, Any]:
    """Raise if evidence quotas / profile coverage are violated; return a report."""
    coverage = evidence_coverage()
    weak = {dim: n for dim, n in coverage["dimension_refs"].items() if n < MIN_DIMENSION_REFS}
    if weak:
        raise ValueError(f"dimensions below {MIN_DIMENSION_REFS} refs: {weak}")
    families = coverage["families"]
    if len(families) < 13:
        raise ValueError(f"expected 13 family evidence groups, found {len(families)}")

    payload = _profiles_payload()
    missing_families = [f for f in families if f not in payload.get("families", {})]
    if missing_families:
        raise ValueError(f"families without deep-architecture profile: {missing_families}")

    # Every profile must expose all dimensions with valid ranges.
    for family, raw in payload.get("families", {}).items():
        profile = resolve_profile(family)
        for dim in DIMENSIONS:
            spec = profile.targets[dim]
            if not (0 <= spec.minimum <= spec.target <= spec.maximum <= 100):
                raise ValueError(f"invalid target for {family}/{dim}: {spec}")

    collected = load_collected_evidence()
    verification = collected.get("doi_verification", {})
    failed = verification.get("failed_dois", []) if isinstance(verification, Mapping) else []
    if failed:
        raise ValueError(f"unresolved DOIs in registry: {failed[:5]}")
    return coverage


__all__ = [
    "DIMENSIONS",
    "DIMENSION_AUTHORITY",
    "AUTHORITY_STRUCTURAL",
    "AUTHORITY_PREDICTED_PHYSICAL",
    "MIN_DIMENSION_REFS",
    "DimensionTarget",
    "DeepArchitectureProfile",
    "dimension_authority",
    "dimension_citations",
    "family_citations",
    "subfamily_citations",
    "archetype_citations",
    "evidence_coverage",
    "resolve_profile",
    "validate_deep_architecture",
]
