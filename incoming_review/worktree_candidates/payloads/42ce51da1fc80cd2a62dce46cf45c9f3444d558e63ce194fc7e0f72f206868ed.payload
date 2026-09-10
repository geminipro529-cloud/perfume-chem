"""Shared material resolver for gate and legacy scoring paths.

Unknown materials must remain unknown. This resolver intentionally does not
invent a generic profile when a label is absent from both the profile spine and
the structured registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import MaterialProfile, get_profile
from engine.name_utils import normalize_name


@dataclass(frozen=True, slots=True)
class ResolvedMaterial:
    requested_name: str
    canonical_name: str
    profile_name: str | None
    registry_name: str | None
    profile: MaterialProfile | None
    registry_material: Any | None
    is_known: bool


@lru_cache(maxsize=1)
def _registry():
    try:
        return load_registry()
    except Exception:
        return None


@lru_cache(maxsize=4096)
def resolve_material(name: str) -> ResolvedMaterial:
    """Resolve one label without manufacturing fallback material identity."""
    requested = str(name or "").strip()
    profile = get_profile(requested)
    registry = _registry()
    reg_mat = registry.get(requested) if registry is not None else None

    profile_name = getattr(profile, "name", None)
    registry_name = getattr(reg_mat, "canonical_name", None)
    canonical_source = profile_name or registry_name or requested
    canonical = normalize_name(canonical_source)

    return ResolvedMaterial(
        requested_name=requested,
        canonical_name=canonical,
        profile_name=profile_name,
        registry_name=registry_name,
        profile=profile,
        registry_material=reg_mat,
        is_known=bool(profile or reg_mat),
    )


def clear_material_resolver_cache() -> None:
    """Invalidate registry-backed resolution after an in-process data edit."""
    resolve_material.cache_clear()
    _registry.cache_clear()


def unknown_materials(names: Iterable[str]) -> list[str]:
    """Return material labels absent from both known material data sources."""
    return sorted(str(name) for name in names if not resolve_material(str(name)).is_known)
