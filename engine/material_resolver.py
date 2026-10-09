"""Shared material resolver for gate and legacy scoring paths.

Unknown materials must remain unknown. This resolver intentionally does not
invent a generic profile when a label is absent from both the profile spine and
the structured registry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import MaterialProfile, get_profile
from engine.name_utils import normalize_name

# Provenance label for a registry VP tagged ``vp_source: placeholder``. It avoids
# the "registry"/"data_spine" tokens that preflight and the uncertainty bands read
# as authoritative registry data.
PLACEHOLDER_VP_SOURCE = "estimated:unsourced_placeholder.vp_25c"


@dataclass(frozen=True, slots=True)
class ResolvedMaterial:
    requested_name: str
    canonical_name: str
    profile_name: str | None
    registry_name: str | None
    profile: MaterialProfile | None
    registry_material: Any | None
    is_known: bool
    # The label every name-keyed physics lookup should use: the requested label,
    # or that label minus a trailing stock-strength suffix when only the bare
    # material name resolves.
    matched_name: str


# A trailing stock strength such as "10%", "7.7%", "1% v/v in ethanol" or
# "10% w/w in DPG". Only this suffix is removable; identity text never is.
_STOCK_STRENGTH_SUFFIX = re.compile(
    r"\s+\d+(?:\.\d+)?\s*%"
    r"(?:\s*(?:w/w|w/v|v/v))?"
    r"(?:\s+in\s+(?:dpg|dep|tec|ipm|ethanol))?\s*$",
    re.IGNORECASE,
)


def strip_stock_strength_suffix(name: str) -> str:
    """Return ``name`` without a trailing stock-strength suffix, if it has one."""
    text = str(name or "").strip()
    stripped = _STOCK_STRENGTH_SUFFIX.sub("", text).strip()
    return stripped or text


@lru_cache(maxsize=1)
def _registry():
    try:
        return load_registry()
    except Exception:
        return None


@lru_cache(maxsize=4096)
def resolve_material(name: str) -> ResolvedMaterial:
    """Resolve one label without manufacturing fallback material identity.

    A label carrying a trailing stock-strength suffix ("Eugenol 10%") resolves
    as the bare material when the full label adds no identity of its own: it is
    unknown, or it only hits the same registry record as the bare name. A label
    with its own distinct record (a registered pre-diluted stock) keeps it.
    """
    requested = str(name or "").strip()
    resolved = _resolve_exact(requested)
    bare = strip_stock_strength_suffix(requested)
    if bare == requested:
        return resolved
    bare_resolved = _resolve_exact(bare)
    if not bare_resolved.is_known:
        return resolved
    if resolved.profile is not None and resolved.profile_name != bare_resolved.profile_name:
        return resolved
    if (
        resolved.registry_material is not None
        and resolved.registry_name != bare_resolved.registry_name
    ):
        return resolved
    return ResolvedMaterial(
        requested_name=requested,
        canonical_name=bare_resolved.canonical_name,
        profile_name=bare_resolved.profile_name,
        registry_name=bare_resolved.registry_name,
        profile=bare_resolved.profile,
        registry_material=bare_resolved.registry_material,
        is_known=True,
        matched_name=bare,
    )


def _resolve_exact(requested: str) -> ResolvedMaterial:
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
        matched_name=requested,
    )


def resolved_vp_25c_pa(resolved: ResolvedMaterial) -> tuple[float | None, str]:
    """Return the 25 C reference vapour pressure the release gate uses.

    The YAML data spine is the canonical VP store; the ingredient-intelligence
    profile is the fallback. Formula state and the scoring/optimizer paths both
    call this so the two cannot drift apart.
    """
    reg_vp = getattr(resolved.registry_material, "vp_25c_pa", None)
    if reg_vp is not None:
        reg_vp_source = str(getattr(resolved.registry_material, "vp_source", None) or "")
        if reg_vp_source.strip().lower() == "placeholder":
            # An unsourced round number must not read as registry data.
            return float(reg_vp), PLACEHOLDER_VP_SOURCE
        return float(reg_vp), "registry:data_spine.vp_25c"
    profile_vp = getattr(resolved.profile, "vp", None)
    if profile_vp is not None:
        return float(profile_vp), "profile:ingredient_intelligence.vp"
    return None, "missing"


def resolved_mw_g_mol(resolved: ResolvedMaterial) -> tuple[float | None, str]:
    """Return the molecular weight the release gate uses: data spine, then profile."""
    reg_mw = getattr(resolved.registry_material, "mw_g_mol", None)
    if reg_mw is not None:
        return reg_mw, "registry:data_spine.mw"
    profile_mw = getattr(resolved.profile, "mw", None)
    if profile_mw is not None:
        return profile_mw, "profile:ingredient_intelligence.mw"
    return None, "missing"


def resolved_logp(resolved: ResolvedMaterial) -> tuple[float | None, str]:
    """Return the logP the release gate uses: data spine, then profile cLogP."""
    reg_logp = getattr(resolved.registry_material, "logp", None)
    if reg_logp is not None:
        return reg_logp, "registry:data_spine.logp"
    profile_logp = getattr(resolved.profile, "clogp", None)
    if profile_logp is not None:
        return profile_logp, "profile:ingredient_intelligence.clogp"
    return None, "missing"


def gate_vp_25c_pa(name: str) -> float | None:
    """Reference VP (Pa, 25 C) for a material label, as the release gate sees it."""
    return resolved_vp_25c_pa(resolve_material(str(name or "")))[0]


def clear_material_resolver_cache() -> None:
    """Invalidate registry-backed resolution after an in-process data edit."""
    resolve_material.cache_clear()
    _registry.cache_clear()


def unknown_materials(names: Iterable[str]) -> list[str]:
    """Return material labels absent from both known material data sources."""
    return sorted(str(name) for name in names if not resolve_material(str(name)).is_known)
