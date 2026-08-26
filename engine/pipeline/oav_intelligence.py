"""Secondary OAV intelligence bridge for future_modules integration.

This layer consumes the existing FormulaState + simulation frames and adds
family-target, shift-zone, balance, performance, and synergy interpretation
without replacing the engine's physical/OAV computation path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from engine.pipeline.formula_state import FormulaState, MaterialState
from engine.pipeline.simulator import SimulationFrame

_FUTURE_MODULES_AVAILABLE = False
try:
    from future_modules._shared_types import ConcentrationBracket, FragranceFamily
    from future_modules.balance_axes import (
        evaluate_diffusion_layers,
        evaluate_material_class_distribution,
        evaluate_oav_contrast,
        evaluate_volatility_balance,
    )
    from future_modules.character_shift_zones import (
        check_zone_boundaries,
        get_zone_by_oav,
    )
    from future_modules.family_hedonic_optimizer import (
        check_family_cliffs,
        get_cliff_oav,
        get_oav_targets,
        list_family_performance_tips,
        list_family_pitfalls,
    )
    from future_modules.performance_profiles import get_performance
    from future_modules.synergy_matrix import (
        get_all_antagonist_pairs,
        get_all_synergy_pairs,
        get_synergy_factor,
    )
    _FUTURE_MODULES_AVAILABLE = True
except ImportError:
    from enum import Enum
    class FragranceFamily(str, Enum):
        CITRUS = "citrus"
        AROMATIC_FOUGERE = "aromatic_fougere"
        FLORAL_ROSE = "floral_rose"
        FLORAL_JASMINE = "floral_jasmine"
        CHYPRE = "chypre"
        AMBER_ORIENTAL = "amber_oriental"
        WOODY_AMBER = "woody_amber"
        GOURMAND = "gourmand"
        MARINE_AQUATIC = "marine_aquatic"
        LEATHER = "leather"
        MUSK = "musk"

    class ConcentrationBracket(str, Enum):
        EDP = "EdP"
        EDT = "EdT"
        EDC = "EdC"
        EXTRAIT = "Extrait"

    def evaluate_diffusion_layers(*args, **kwargs):
        return {"axis_name": "diffusion_layers", "score": 0.0, "target_range": None, "status": "degraded", "details": "engine heuristic fallback active"}

    def evaluate_material_class_distribution(*args, **kwargs):
        return {"axis_name": "material_class_distribution", "score": 0.0, "target_range": None, "status": "degraded", "details": "engine heuristic fallback active"}

    def evaluate_oav_contrast(*args, **kwargs):
        return {"axis_name": "oav_contrast", "score": 0.0, "target_range": None, "status": "degraded", "details": "engine heuristic fallback active"}

    def evaluate_volatility_balance(*args, **kwargs):
        return {"axis_name": "volatility_balance", "score": 0.0, "target_range": None, "status": "degraded", "details": "engine heuristic fallback active"}

    def check_zone_boundaries(*args, **kwargs):
        return True, "engine heuristic fallback active"

    def get_zone_by_oav(*args, **kwargs):
        return None

    def check_family_cliffs(*args, **kwargs):
        return {}

    def get_cliff_oav(*args, **kwargs):
        return None

    def get_oav_targets(*args, **kwargs):
        return None

    def list_family_performance_tips(*args, **kwargs):
        return ()

    def list_family_pitfalls(*args, **kwargs):
        return ()

    def get_performance(*args, **kwargs):
        return None

    def get_all_synergy_pairs(*args, **kwargs):
        return ()

    def get_all_antagonist_pairs(*args, **kwargs):
        return ()

    def get_synergy_factor(*args, **kwargs):
        return 1.0


_FAMILY_ALIASES: dict[str, FragranceFamily] = {
    "citrus": FragranceFamily.CITRUS,
    "hesperidic": FragranceFamily.CITRUS,
    "citrus classical": FragranceFamily.CITRUS,
    "citrus_classical": FragranceFamily.CITRUS,
    "eau de cologne": FragranceFamily.CITRUS,
    "dior homme cologne": FragranceFamily.CITRUS,
    "dior_homme_cologne": FragranceFamily.CITRUS,
    "citrus aromatic": FragranceFamily.CITRUS,
    "citrus_aromatic": FragranceFamily.CITRUS,
    "aromatic_fougere": FragranceFamily.AROMATIC_FOUGERE,
    "fougere": FragranceFamily.AROMATIC_FOUGERE,
    "fougere classical": FragranceFamily.AROMATIC_FOUGERE,
    "fougere_classical": FragranceFamily.AROMATIC_FOUGERE,
    "floral_rose": FragranceFamily.FLORAL_ROSE,
    "rose": FragranceFamily.FLORAL_ROSE,
    "floral soliflore": FragranceFamily.FLORAL_ROSE,
    "floral_soliflore": FragranceFamily.FLORAL_ROSE,
    "floral_jasmine": FragranceFamily.FLORAL_JASMINE,
    "jasmine": FragranceFamily.FLORAL_JASMINE,
    "floral bouquet": FragranceFamily.FLORAL_JASMINE,
    "floral_bouquet": FragranceFamily.FLORAL_JASMINE,
    "floral white": FragranceFamily.FLORAL_JASMINE,
    "floral_white": FragranceFamily.FLORAL_JASMINE,
    "white floral": FragranceFamily.FLORAL_JASMINE,
    "floral muguet": FragranceFamily.FLORAL_JASMINE,
    "floral_muguet": FragranceFamily.FLORAL_JASMINE,
    "muguet floral": FragranceFamily.FLORAL_JASMINE,
    "floral carnation": FragranceFamily.FLORAL_JASMINE,
    "floral_carnation": FragranceFamily.FLORAL_JASMINE,
    "carnation floral": FragranceFamily.FLORAL_JASMINE,
    "floral powdery": FragranceFamily.FLORAL_JASMINE,
    "floral_powdery": FragranceFamily.FLORAL_JASMINE,
    "powdery floral": FragranceFamily.FLORAL_JASMINE,
    "floral green": FragranceFamily.FLORAL_JASMINE,
    "floral_green": FragranceFamily.FLORAL_JASMINE,
    "green floral": FragranceFamily.FLORAL_JASMINE,
    "floral aldehydic": FragranceFamily.FLORAL_JASMINE,
    "floral_aldehydic": FragranceFamily.FLORAL_JASMINE,
    "chypre": FragranceFamily.CHYPRE,
    "chypre classical": FragranceFamily.CHYPRE,
    "chypre_classical": FragranceFamily.CHYPRE,
    "floral chypre": FragranceFamily.CHYPRE,
    "chypre_floral": FragranceFamily.CHYPRE,
    "fruity chypre": FragranceFamily.CHYPRE,
    "chypre_fruity": FragranceFamily.CHYPRE,
    "green chypre": FragranceFamily.CHYPRE,
    "chypre_green": FragranceFamily.CHYPRE,
    "leather chypre": FragranceFamily.CHYPRE,
    "chypre_leathery": FragranceFamily.CHYPRE,
    "amber_oriental": FragranceFamily.AMBER_ORIENTAL,
    "oriental": FragranceFamily.AMBER_ORIENTAL,
    "oriental classical": FragranceFamily.AMBER_ORIENTAL,
    "oriental_classical": FragranceFamily.AMBER_ORIENTAL,
    "classic oriental": FragranceFamily.AMBER_ORIENTAL,
    "soft oriental": FragranceFamily.AMBER_ORIENTAL,
    "oriental_soft": FragranceFamily.AMBER_ORIENTAL,
    "soft amber": FragranceFamily.AMBER_ORIENTAL,
    "floral oriental": FragranceFamily.AMBER_ORIENTAL,
    "oriental_floral": FragranceFamily.AMBER_ORIENTAL,
    "floral amber": FragranceFamily.AMBER_ORIENTAL,
    "woody_amber": FragranceFamily.WOODY_AMBER,
    "woody amber": FragranceFamily.WOODY_AMBER,
    "woody floral musk": FragranceFamily.WOODY_AMBER,
    "woody": FragranceFamily.WOODY_AMBER,
    "gourmand": FragranceFamily.GOURMAND,
    "marine_aquatic": FragranceFamily.MARINE_AQUATIC,
    "aquatic": FragranceFamily.MARINE_AQUATIC,
    "marine": FragranceFamily.MARINE_AQUATIC,
    "leather": FragranceFamily.LEATHER,
    "musk": FragranceFamily.MUSK,
}

_MATERIAL_ALIASES: dict[str, str] = {
    "d-limonene": "Limonene",
    "ambrox super": "Ambroxan",
    "ambrofix": "Ambroxan",
    "damascenone": "Beta-Damascenone",
    "isobutyl quinoline": "Isobutyl Quinoline (IBQ)",
    "ibq": "Isobutyl Quinoline (IBQ)",
    "cis jasmone": "Cis-Jasmone",
    "phenethyl alcohol": "Phenethyl Alcohol",
    "phenyl ethyl alcohol": "Phenethyl Alcohol",
}

_BALANCE_NAME_ALIASES: dict[str, str] = {
    "d-limonene": "limonene",
    "phenethyl alcohol": "phenylethyl alcohol",
    "phenyl ethyl alcohol": "phenylethyl alcohol",
    "ambrox super": "ambroxan",
    "ambrofix": "ambroxan",
    "aldehyde c10": "c10 aldehyde",
    "aldehyde c11": "c11 aldehyde",
    "aldehyde c12 mna": "c12 mna",
    "isobutyl quinoline": "isobutyl quinoline",
    "bergamot fcf": "bergamot fcf",
    "lavender eo": "lavender eo",
}


def _normalize_token(value: str) -> str:
    return " ".join(
        value.lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
        .replace(".", " ")
        .split()
    )


def _map_family(archetype: str) -> FragranceFamily | None:
    token = _normalize_token(archetype)
    if token in _FAMILY_ALIASES:
        return _FAMILY_ALIASES[token]
    if "woody" in token and any(
        qualifier in token for qualifier in ("amber", "floral", "musk")
    ):
        return FragranceFamily.WOODY_AMBER
    if "oriental" in token or token.endswith("amber"):
        return FragranceFamily.AMBER_ORIENTAL
    if "fougere" in token:
        return FragranceFamily.AROMATIC_FOUGERE
    if "floral" in token or "muguet" in token or "carnation" in token:
        return FragranceFamily.FLORAL_JASMINE
    if "jasmine" in token:
        return FragranceFamily.FLORAL_JASMINE
    if "rose" in token:
        return FragranceFamily.FLORAL_ROSE
    if "chypre" in token:
        return FragranceFamily.CHYPRE
    if "gourmand" in token:
        return FragranceFamily.GOURMAND
    if "leather" in token:
        return FragranceFamily.LEATHER
    if "musk" in token:
        return FragranceFamily.MUSK
    if "marine" in token or "aquatic" in token:
        return FragranceFamily.MARINE_AQUATIC
    if "amber" in token and "woody" in token:
        return FragranceFamily.WOODY_AMBER
    if "woody" in token:
        return FragranceFamily.WOODY_AMBER
    if "cologne" in token:
        return FragranceFamily.CITRUS
    if "citrus" in token or "hesperidic" in token:
        return FragranceFamily.CITRUS
    return None


def _material_candidates(material: MaterialState) -> tuple[str, ...]:
    candidates: list[str] = []
    for value in (
        material.canonical_name,
        material.name,
        material.profile_name,
        material.registry_name,
    ):
        if not value:
            continue
        candidates.append(value)
        alias = _MATERIAL_ALIASES.get(_normalize_token(value))
        if alias:
            candidates.append(alias)
    deduped: list[str] = []
    seen: set[str] = set()
    for value in candidates:
        token = value.strip()
        if token and token not in seen:
            deduped.append(token)
            seen.add(token)
    return tuple(deduped)


def _balance_name(material: MaterialState) -> str:
    primary = material.canonical_name or material.name
    token = _normalize_token(primary)
    return _BALANCE_NAME_ALIASES.get(token, token)


def _serialize_balance(report: Any) -> dict[str, Any]:
    if isinstance(report, dict):
        return {
            "axis_name": report.get("axis_name", "unknown"),
            "score": round(float(report.get("score", 0.0)), 6),
            "target_range": list(report["target_range"]) if report.get("target_range") is not None else None,
            "status": report.get("status", "unavailable"),
            "details": report.get("details", ""),
        }
    return {
        "axis_name": report.axis_name,
        "score": round(float(report.score), 6),
        "target_range": list(report.target_range) if report.target_range is not None else None,
        "status": report.status,
        "details": report.details,
    }


def _severity_rank(severity: str) -> int:
    return {"error": 2, "warn": 1, "info": 0}.get(severity, 0)


def _top_oav_map(state: FormulaState) -> dict[str, float]:
    result: dict[str, float] = {}
    for material in state.materials:
        oav = float(material.oav or 0.0)
        for candidate in _material_candidates(material):
            result[candidate.lower()] = max(oav, result.get(candidate.lower(), 0.0))
    return result


@dataclass(frozen=True, slots=True)
class OAVIntelligenceResult:
    family_archetype: str
    mapped_family: str | None
    family_target_alignment: dict[str, Any]
    material_cliff_findings: tuple[dict[str, Any], ...]
    shift_zone_findings: tuple[dict[str, Any], ...]
    balance_reports: tuple[dict[str, Any], ...]
    performance_projection: dict[str, Any]
    synergy_findings: dict[str, Any]
    intelligence_status: str
    intelligence_blocking_reasons: tuple[str, ...]
    intelligence_warning_reasons: tuple[str, ...]
    unmapped_materials: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "family_archetype": self.family_archetype,
            "mapped_family": self.mapped_family,
            "family_target_alignment": dict(self.family_target_alignment),
            "material_cliff_findings": [dict(item) for item in self.material_cliff_findings],
            "shift_zone_findings": [dict(item) for item in self.shift_zone_findings],
            "balance_reports": [dict(item) for item in self.balance_reports],
            "performance_projection": dict(self.performance_projection),
            "synergy_findings": {
                key: [dict(item) for item in value] if isinstance(value, tuple) else value
                for key, value in self.synergy_findings.items()
            },
            "intelligence_status": self.intelligence_status,
            "intelligence_blocking_reasons": list(self.intelligence_blocking_reasons),
            "intelligence_warning_reasons": list(self.intelligence_warning_reasons),
            "unmapped_materials": list(self.unmapped_materials),
        }


def _minimal_intelligence_result(family_archetype: str) -> OAVIntelligenceResult:
    return OAVIntelligenceResult(
        family_archetype=family_archetype,
        mapped_family=None,
        family_target_alignment={"family": None, "pitfalls": (), "performance_tips": (), "materials": []},
        material_cliff_findings=(),
        shift_zone_findings=(),
        balance_reports=(),
        performance_projection={"materials": [], "warnings": ["engine heuristic fallback active"]},
        synergy_findings={"positive": (), "antagonists": ()},
        intelligence_status="WARN",
        intelligence_blocking_reasons=(),
        intelligence_warning_reasons=("engine heuristic fallback active; advanced OAV intelligence degraded",),
        unmapped_materials=(),
    )


def analyze_oav_intelligence(
    state: FormulaState,
    frames: Sequence[SimulationFrame],
    family_archetype: str,
) -> OAVIntelligenceResult:
    """Derive secondary OAV intelligence from future_modules without recomputing physics."""
    if not _FUTURE_MODULES_AVAILABLE:
        return _minimal_intelligence_result(family_archetype)
    family = _map_family(family_archetype)
    material_oavs = _top_oav_map(state)
    active_pct = state.active_percentages()

    blocking_reasons: list[str] = []
    warning_reasons: list[str] = []

    family_materials: list[dict[str, Any]] = []
    cliff_findings: list[dict[str, Any]] = []
    shift_findings: list[dict[str, Any]] = []
    performance_materials: list[dict[str, Any]] = []
    performance_warnings: list[str] = []
    unmapped_materials: list[str] = []

    mapped_presence: dict[str, MaterialState] = {}
    for material in state.materials:
        for candidate in _material_candidates(material):
            mapped_presence.setdefault(candidate.lower(), material)

    family_cliff_hits = (
        check_family_cliffs(family, material_oavs) if family is not None else {}
    )

    if family is None and family_archetype.strip():
        warning_reasons.append(
            f"Unmapped family archetype for future-module intelligence: {family_archetype}"
        )

    for material in sorted(state.materials, key=lambda row: ((row.oav or 0.0), row.name), reverse=True):
        oav = float(material.oav or 0.0)
        if oav <= 0.0:
            continue
        candidates = _material_candidates(material)

        mapped_target_name: str | None = None
        target_range: tuple[float, float] | None = None
        if family is not None:
            for candidate in candidates:
                target_range = get_oav_targets(family, candidate)
                if target_range is not None:
                    mapped_target_name = candidate
                    break

        if family is not None and target_range is None and oav >= 1.0:
            unmapped_materials.append(material.canonical_name)

        if target_range is not None:
            target_min, target_max = target_range
            if target_min <= oav <= target_max:
                target_status = "within_target"
                severity = "info"
            elif oav < target_min:
                target_status = "below_target"
                severity = "warn"
                warning_reasons.append(
                    f"{material.canonical_name} OAV {oav:.1f} is below {family.value} target {target_min:.1f}-{target_max:.1f}"
                )
            else:
                target_status = "above_target"
                severity = "warn"
                warning_reasons.append(
                    f"{material.canonical_name} OAV {oav:.1f} is above {family.value} target {target_min:.1f}-{target_max:.1f}"
                )
            family_materials.append(
                {
                    "material": material.canonical_name,
                    "mapped_material": mapped_target_name,
                    "oav": round(oav, 6),
                    "target_min": round(target_min, 6),
                    "target_max": round(target_max, 6),
                    "status": target_status,
                    "severity": severity,
                }
            )

        mapped_shift_name: str | None = None
        zone = None
        for candidate in candidates:
            zone = get_zone_by_oav(candidate, oav)
            if zone is not None:
                mapped_shift_name = candidate
                break
        if zone is not None and mapped_shift_name is not None:
            concentration_pct = float(active_pct.get(material.name, 0.0))
            boundary_safe, boundary_detail = check_zone_boundaries(
                mapped_shift_name,
                concentration_pct,
            )
            if zone.label in {"overdose", "danger"} or zone.hedonic <= -2.0:
                severity = "error"
                blocking_reasons.append(
                    f"{material.canonical_name} is in {zone.label} shift zone: {zone.character}"
                )
            elif not boundary_safe or zone.label in {"threshold", "dominant"}:
                severity = "warn"
                warning_reasons.append(
                    f"{material.canonical_name} is in {zone.label} shift zone: {zone.character}"
                )
            else:
                severity = "info"
            shift_findings.append(
                {
                    "material": material.canonical_name,
                    "mapped_material": mapped_shift_name,
                    "oav": round(oav, 6),
                    "concentration_pct": round(concentration_pct, 6),
                    "zone_label": zone.label,
                    "zone_character": zone.character,
                    "zone_hedonic": round(float(zone.hedonic), 6),
                    "boundary_safe": boundary_safe,
                    "boundary_detail": boundary_detail,
                    "severity": severity,
                }
            )

        if family is not None:
            mapped_cliff_name: str | None = None
            cliff_data: tuple[float, str] | None = None
            for candidate in candidates:
                cliff_data = get_cliff_oav(family, candidate)
                if cliff_data is not None:
                    mapped_cliff_name = candidate
                    break
            if mapped_cliff_name is not None and cliff_data is not None:
                cliff_oav, cliff_detail = cliff_data
                if oav > cliff_oav:
                    detail = family_cliff_hits.get(
                        mapped_cliff_name,
                        f"OAV {oav:.1f} exceeds cliff {cliff_oav:.1f}",
                    )
                    blocking_reasons.append(detail)
                    cliff_findings.append(
                        {
                            "material": material.canonical_name,
                            "mapped_material": mapped_cliff_name,
                            "oav": round(oav, 6),
                            "cliff_oav": round(float(cliff_oav), 6),
                            "detail": cliff_detail,
                            "severity": "error",
                        }
                    )

        perf = None
        mapped_perf_name: str | None = None
        for candidate in candidates:
            perf = get_performance(candidate)
            if perf is not None:
                mapped_perf_name = candidate
                break
        if perf is not None and mapped_perf_name is not None:
            note_mismatch = material.note != perf.note_tier.value
            temperature_factor = material.vp_temperature_factor
            temperature_shift = {
                "reference_temperature_K": 298.15,
                "formula_temperature_K": state.temperature_K,
                "vp_ratio": (
                    round(float(temperature_factor), 6)
                    if temperature_factor is not None
                    else None
                ),
                "formula_vp_pa": (
                    round(float(material.vp_pure_pa), 6)
                    if material.vp_pure_pa is not None
                    else None
                ),
                "temperature_model": material.sources.get(
                    "vp_temperature",
                    "missing",
                ),
                "half_life_projection": None,
                "limitation": (
                    "Profile half-life is an independent 32 C skin estimate; "
                    "it is not rescaled from vapor pressure."
                ),
            }
            performance_materials.append(
                {
                    "material": material.canonical_name,
                    "mapped_material": mapped_perf_name,
                    "oav": round(oav, 6),
                    "engine_note": material.note,
                    "future_note_tier": perf.note_tier.value,
                    "note_tier_mismatch": note_mismatch,
                    "profile_half_life_min_at_32c": round(
                        float(perf.half_life_min),
                        6,
                    ),
                    "profile_vp_25c_pa": round(float(perf.vp_pa), 6),
                    "formula_temperature_shift": temperature_shift,
                }
            )
            if note_mismatch and oav >= 10.0:
                performance_warnings.append(
                    f"{material.canonical_name} note-tier mismatch: engine={material.note}, future={perf.note_tier.value}"
                )

    top_oav = sum(float(m.oav or 0.0) for m in state.materials if m.note == "top")
    heart_oav = sum(float(m.oav or 0.0) for m in state.materials if m.note == "heart")
    base_oav = sum(float(m.oav or 0.0) for m in state.materials if m.note == "base")
    material_masses = {_balance_name(material): float(material.active_ul) for material in state.materials}
    oav_values = [float(m.oav or 0.0) for m in state.materials if (m.oav or 0.0) > 0.0]
    diffusion_inputs = {
        _balance_name(material): float(material.oav or 0.0)
        for material in state.materials
        if (material.oav or 0.0) > 0.0
    }

    balance_reports = [
        evaluate_volatility_balance(top_oav, heart_oav, base_oav, ConcentrationBracket.EDP),
        evaluate_oav_contrast(oav_values),
        evaluate_diffusion_layers(diffusion_inputs),
    ]
    if family is not None:
        balance_reports.append(evaluate_material_class_distribution(material_masses, family))

    serialized_balances = tuple(
        sorted(
            (_serialize_balance(report) for report in balance_reports),
            key=lambda row: (row["axis_name"], row["status"], row["details"]),
        )
    )
    for report in serialized_balances:
        if report["status"] == "critical":
            warning_reasons.append(f"{report['axis_name']}: {report['details']}")
        elif report["status"] == "needs_improvement":
            warning_reasons.append(f"{report['axis_name']}: {report['details']}")

    performance_warnings = sorted(set(performance_warnings))
    warning_reasons.extend(performance_warnings)
    performance_projection = {
        "materials": sorted(
            performance_materials,
            key=lambda row: (-row["oav"], row["material"]),
        ),
        "warnings": performance_warnings,
    }

    synergy_positive: list[dict[str, Any]] = []
    synergy_antagonists: list[dict[str, Any]] = []
    for pair in get_all_synergy_pairs():
        a_material = mapped_presence.get(pair.material_a.lower())
        b_material = mapped_presence.get(pair.material_b.lower())
        if a_material is None or b_material is None:
            continue
        oav_a = material_oavs.get(pair.material_a.lower(), 0.0)
        oav_b = material_oavs.get(pair.material_b.lower(), 0.0)
        factor = get_synergy_factor(pair.material_a, pair.material_b, oav_a, oav_b)
        synergy_positive.append(
            {
                "material_a": a_material.canonical_name,
                "material_b": b_material.canonical_name,
                "mapped_material_a": pair.material_a,
                "mapped_material_b": pair.material_b,
                "oav_a": round(oav_a, 6),
                "oav_b": round(oav_b, 6),
                "synergy_factor": round(float(factor), 6),
                "optimal_ratio": list(pair.optimal_ratio),
                "oav_range": list(pair.oav_range),
                "mechanism": pair.mechanism,
            }
        )
        if factor > 1.0:
            warning_reasons.append(
                f"Active synergy present: {a_material.canonical_name} + {b_material.canonical_name} ({factor:.2f}x)"
            )

    for pair in get_all_antagonist_pairs():
        token_a = pair.material_a.lower()
        token_b = pair.material_b.lower()
        a_material = mapped_presence.get(token_a)
        b_material = mapped_presence.get(token_b)

        matched = a_material is not None and b_material is not None
        if not matched and token_a == "aldehydes c10/c11":
            aldehyde = next(
                (m for m in state.materials if _normalize_token(m.canonical_name) in {"aldehyde c10", "aldehyde c11"}),
                None,
            )
            ma = mapped_presence.get("methyl anthranilate")
            if aldehyde is not None and ma is not None:
                a_material = aldehyde
                b_material = ma
                matched = True
        if not matched and token_b == "floral materials":
            ibq = mapped_presence.get("isobutyl quinoline (ibq)")
            floral = next(
                (m for m in state.materials if (m.family or "").lower() in {"floral", "rose", "muguet", "salicylate"}),
                None,
            )
            if ibq is not None and floral is not None:
                a_material = ibq
                b_material = floral
                matched = True
        if not matched and token_b == "citrus top notes":
            vanillin = mapped_presence.get("vanillin")
            citrus = next(
                (m for m in state.materials if (m.family or "").lower() == "citrus" or m.note == "top"),
                None,
            )
            if vanillin is not None and citrus is not None:
                a_material = vanillin
                b_material = citrus
                matched = True
        if not matched and token_b == "gourmand materials":
            calone = mapped_presence.get("calone")
            gourmand = next(
                (
                    m for m in state.materials
                    if _normalize_token(m.canonical_name) in {"vanillin", "coumarin", "ethyl maltol", "ethyl vanillin"}
                ),
                None,
            )
            if calone is not None and gourmand is not None:
                a_material = calone
                b_material = gourmand
                matched = True

        if not matched or a_material is None or b_material is None:
            continue

        synergy_antagonists.append(
            {
                "material_a": a_material.canonical_name,
                "material_b": b_material.canonical_name,
                "problem": pair.problem,
                "mechanism": pair.mechanism,
                "max_safe_ratio": pair.max_safe_ratio,
            }
        )
        warning_reasons.append(
            f"Antagonist pair present: {a_material.canonical_name} + {b_material.canonical_name}"
        )

    synergy_findings = {
        "positive": tuple(
            sorted(
                synergy_positive,
                key=lambda row: (-row["synergy_factor"], row["material_a"], row["material_b"]),
            )
        ),
        "antagonists": tuple(
            sorted(
                synergy_antagonists,
                key=lambda row: (row["material_a"], row["material_b"], row["problem"]),
            )
        ),
    }

    family_target_alignment = {
        "family": family.value if family is not None else None,
        "pitfalls": list_family_pitfalls(family) if family is not None else (),
        "performance_tips": list_family_performance_tips(family) if family is not None else (),
        "materials": sorted(
            family_materials,
            key=lambda row: (_severity_rank(row["severity"]), row["status"] != "within_target", row["material"]),
            reverse=True,
        ),
    }

    cliff_findings = sorted(
        cliff_findings,
        key=lambda row: (-row["oav"], row["material"]),
    )
    shift_findings = sorted(
        shift_findings,
        key=lambda row: (_severity_rank(row["severity"]), row["zone_label"], row["material"]),
        reverse=True,
    )

    deduped_blockers = tuple(dict.fromkeys(blocking_reasons))
    deduped_warnings = tuple(
        reason for reason in dict.fromkeys(warning_reasons) if reason not in deduped_blockers
    )

    if deduped_blockers:
        status = "FAIL"
    elif deduped_warnings:
        status = "WARN"
    else:
        status = "PASS"

    return OAVIntelligenceResult(
        family_archetype=family_archetype,
        mapped_family=family.value if family is not None else None,
        family_target_alignment=family_target_alignment,
        material_cliff_findings=tuple(cliff_findings),
        shift_zone_findings=tuple(shift_findings),
        balance_reports=serialized_balances,
        performance_projection=performance_projection,
        synergy_findings=synergy_findings,
        intelligence_status=status,
        intelligence_blocking_reasons=deduped_blockers,
        intelligence_warning_reasons=deduped_warnings,
        unmapped_materials=tuple(sorted(dict.fromkeys(unmapped_materials))),
    )
