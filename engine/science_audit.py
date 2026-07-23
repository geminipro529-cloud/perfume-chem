"""science_audit — print known weaknesses, missing data, validation status.

Run:
    python -m engine.science_audit
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "materials"


def _gather_data_coverage() -> dict[str, float]:
    """Mirror engine.data_spine.audit using the live Material schema."""
    try:
        from engine.data_spine.loader import load_materials
    except Exception:
        return {}

    materials = load_materials(DATA)
    if not materials:
        return {}

    fields = [
        "mw", "logp", "vp_25c", "antoine", "dhvap", "hsp",
        "odt_air", "or_targets", "ifra", "hedonic", "trp", "smiles", "cas",
    ]
    counts = {field: 0 for field in fields}
    for material in materials:
        completeness = material.completeness()
        for field in fields:
            if completeness.get(field):
                counts[field] += 1

    total = len(materials)
    return {field: 100.0 * count / total for field, count in counts.items()}


def _positive_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0.0 else None


def _looks_like_natural_mixture(material_name: str) -> bool:
    """Identify materials for which a single MW/VP is only a bulk proxy."""
    normalized = " ".join(str(material_name).lower().replace("-", " ").split())
    markers = (
        " eo",
        " oil",
        " absolute",
        " resinoid",
        " balsam",
        " oleoresin",
        " co2 extract",
    )
    return any(normalized.endswith(marker) or marker + " " in normalized for marker in markers)


def build_material_consistency_audit(
    material_names: Iterable[str] | None = None,
    *,
    physical_ratio_threshold: float = 1.5,
    mw_ratio_threshold: float = 1.02,
) -> dict:
    """Compare runtime profile, data-spine, and ODT records without choosing a winner."""
    from engine.ingredient_intelligence import get_profile
    from engine.inventory_parser import parse_inventory
    from engine.material_resolver import resolve_material
    from engine.odor_thresholds import lookup_odt_entry
    from engine.pipeline.natural_absolute_decomposition import get_composite_metadata

    if material_names is None:
        names = tuple(
            item.name for item in parse_inventory(include_unavailable=False)
        )
        scope = "live_inventory"
    else:
        names = tuple(dict.fromkeys(str(name) for name in material_names if str(name)))
        scope = "requested_materials"

    conflicts: list[dict[str, object]] = []
    for name in names:
        resolved = resolve_material(name)
        natural_mixture = _looks_like_natural_mixture(name)
        natural_metadata = get_composite_metadata(name) if natural_mixture else None
        profile = get_profile(name)
        registry = resolved.registry_material
        odt = lookup_odt_entry(name) or {}
        fields = {
            "mw_g_mol": {
                "profile": getattr(profile, "mw", None),
                "data_spine": getattr(registry, "mw_g_mol", None),
            },
            "vp_25c_pa": {
                "profile": getattr(profile, "vp", None),
                "data_spine": getattr(registry, "vp_25c_pa", None),
            },
            "odt_air_ppb": {
                "profile": getattr(profile, "odt", None),
                "data_spine": getattr(registry, "odt_air_ppb", None),
                "odt_data": odt.get("odt_air"),
            },
            "odt_eth_ppm": {
                "profile": getattr(profile, "odt_ppm", None),
                "data_spine": getattr(registry, "odt_eth_ppm", None),
                "odt_data": odt.get("odt_eth"),
            },
        }
        for field_name, raw_values in fields.items():
            values = {
                source: number
                for source, value in raw_values.items()
                if (number := _positive_float(value)) is not None
            }
            if len(values) < 2:
                continue
            ratio = max(values.values()) / min(values.values())
            threshold = (
                mw_ratio_threshold
                if field_name == "mw_g_mol"
                else physical_ratio_threshold
            )
            if ratio <= threshold:
                continue
            conflicts.append(
                {
                    "material": name,
                    "canonical_name": resolved.canonical_name,
                    "field": field_name,
                    "ratio": round(ratio, 6),
                    "values": values,
                    "runtime_precedence": (
                        "natural_composite_constituents"
                        if natural_metadata is not None
                        else "odt_data"
                        if field_name.startswith("odt_") and "odt_data" in values
                        else "data_spine"
                        if "data_spine" in values
                        else "profile"
                    ),
                    "evidence_class": (
                        "NATURAL_MIXTURE_BULK_PROXY"
                        if natural_mixture
                        else "MONOMOLECULAR_PROPERTY"
                    ),
                    "composite_oav_coverage": (
                        natural_metadata is not None if natural_mixture else None
                    ),
                    "status": (
                        "UNRESOLVED_NATURAL_MIXTURE_PROXY_CONFLICT"
                        if natural_mixture
                        else "UNRESOLVED_SOURCE_CONFLICT"
                    ),
                }
            )

    conflicts.sort(
        key=lambda row: (
            -float(row["ratio"]),
            str(row["material"]),
            str(row["field"]),
        )
    )
    return {
        "scope": scope,
        "material_count": len(names),
        "conflict_count": len(conflicts),
        "material_conflict_count": len(
            {str(row["material"]) for row in conflicts}
        ),
        "thresholds": {
            "physical_ratio": physical_ratio_threshold,
            "mw_ratio": mw_ratio_threshold,
        },
        "conflicts": conflicts,
        "release_authority": False,
    }


@lru_cache(maxsize=8)
def _build_inventory_oav_coverage_audit_cached(
    inventory_fingerprint: tuple[int, int],
) -> dict:
    """Build one formula-state screen for the current live inventory.

    The fingerprint is part of the cache key so inventory edits invalidate the
    result without making every release gate rebuild a 200+ material state.
    """
    del inventory_fingerprint
    from engine.inventory_parser import parse_inventory
    from engine.pipeline.formula_state import build_formula_state

    records = parse_inventory(
        include_solvents=False,
        include_unavailable=False,
    )
    ingredients = {record.name: 1.0 for record in records}
    dilutions = {record.name: record.dilution for record in records}
    stock_specs = {
        record.name: {
            "fraction": record.dilution,
            "fraction_basis": record.fraction_basis,
            "carrier": record.carrier,
            "approximate": record.approximate,
            "declared": True,
        }
        for record in records
    }
    state = build_formula_state(
        ingredients,
        dilutions,
        stock_specs=stock_specs,
    )

    available: list[str] = []
    opaque_unknown: list[str] = []
    natural_missing: list[str] = []
    identity_unknown: list[str] = []
    other_unknown: list[str] = []
    composite_profiles: list[str] = []
    literature_proxies: list[str] = []

    for material in state.materials:
        natural_source = material.sources.get("natural_composite", "")
        if natural_source:
            composite_profiles.append(material.name)
            if "LITERATURE_PARTIAL_PROXY" in natural_source:
                literature_proxies.append(material.name)
        if material.oav is not None:
            available.append(material.name)
        elif not material.is_known:
            identity_unknown.append(material.name)
        elif material.is_opaque_preblend:
            opaque_unknown.append(material.name)
        elif material.sources.get("oav_model") == (
            "unknown:composite_decomposition_missing"
        ):
            natural_missing.append(material.name)
        else:
            other_unknown.append(material.name)

    categories = {
        "opaque_preblends_without_disclosed_composition": sorted(opaque_unknown),
        "naturals_missing_composite_evidence": sorted(natural_missing),
        "unknown_material_identities": sorted(identity_unknown),
        "other_oav_unknowns": sorted(other_unknown),
    }
    unknown_count = sum(len(rows) for rows in categories.values())
    if natural_missing or identity_unknown or other_unknown:
        status = "FAIL_CLOSED_GAPS"
    elif opaque_unknown:
        status = "PASS_WITH_OPAQUE_BLEND_LIMITS"
    else:
        status = "PASS"

    return {
        "scope": "live_owned_non_solvent_inventory",
        "status": status,
        "material_count": len(state.materials),
        "oav_available_count": len(available),
        "oav_unknown_count": unknown_count,
        "oav_coverage_pct": round(
            100.0 * len(available) / max(len(state.materials), 1),
            3,
        ),
        "categories": categories,
        "natural_composite_profile_count": len(composite_profiles),
        "natural_literature_proxy_count": len(literature_proxies),
        "natural_literature_proxies": sorted(literature_proxies),
        "limitations": [
            "Available means a modeled OAV exists; it is not measured headspace.",
            "Opaque fragrance oils remain unknown until supplier composition is disclosed.",
            "Natural profiles are literature fingerprints, not supplier-batch GC-MS/GC-O certificates.",
        ],
        "release_authority": False,
    }


def build_inventory_oav_coverage_audit() -> dict:
    """Return fail-closed OAV coverage for the current owned inventory."""
    from engine.inventory_parser import INVENTORY_PATH

    stat = INVENTORY_PATH.stat()
    return _build_inventory_oav_coverage_audit_cached(
        (int(stat.st_mtime_ns), int(stat.st_size))
    )


def build_science_audit_contract() -> dict:
    """Return the machine-readable science audit contract."""
    cov = _gather_data_coverage()
    return {
        "data_coverage_pct": cov,
        "material_consistency": build_material_consistency_audit(),
        "inventory_oav_coverage": build_inventory_oav_coverage_audit(),
        "weaknesses": [{"title": t, "body": b} for t, b in KNOWN_WEAKNESSES],
        "open_questions": OPEN_QUESTIONS,
    }


def coverage_confidence_penalty(contract: dict | None = None) -> float:
    """Convert sparse science coverage into a bounded confidence penalty.

    This is intentionally conservative. It should lower trust, not fabricate
    a hard-fail from incomplete auxiliary science fields.
    """
    contract = contract or build_science_audit_contract()
    coverage = contract.get("data_coverage_pct", {}) or {}
    penalty = 0.0
    targets = {
        "antoine": 20.0,
        "hsp": 40.0,
        "ifra": 50.0,
        "or_targets": 10.0,
    }
    for field, target in targets.items():
        actual = float(coverage.get(field, 0.0) or 0.0)
        if actual < target:
            penalty += min(3.0, (target - actual) / max(target, 1.0) * 3.0)
    return round(min(12.0, penalty), 3)


KNOWN_WEAKNESSES = [
    ("Cross-source material truth",
     "Profile, data-spine, and ODT records can disagree. Runtime precedence is explicit, "
     "but every unresolved ratio conflict remains advisory and blocks exact scientific claims."),
    ("Antoine constants",
     "0% of materials have Antoine A/B/C. Phase 1 falls back to single-point VP_25 → "
     "VP(T) extrapolation is wrong above 40 °C and at the cold-tail."),
    ("UNIFAC γ",
     "thermo.unifac integration is stubbed. Activity coefficients use a Hansen-distance "
     "regular-solution heuristic calibrated only to limonene-in-EtOH."),
    ("OR targets",
     "0% of materials have published EC50/Hill coefficients. Receptor occupancy uses a "
     "family→OR-affinity prior. Mainland 2014 dataset not yet ingested."),
    ("Hedonic / TRP / IFRA",
     "Coverage <10%. Ferreira mixture-shift β=0.3 is hard-coded, not fitted."),
    ("Adaptation timescales",
     "τ_fast / τ_med / τ_slow values from rat single-cell studies. Human bulb-level "
     "feedback may differ by 2-3×."),
    ("Maturation kinetics",
     "Arrhenius A/Ea per reaction class are order-of-magnitude calibrated to one Blakeway "
     "1987 reference. Per-aldehyde overrides not yet supplied."),
    ("Spray atomisation",
     "Log-normal Dv50=30 µm σ_g=1.5 is the typical perfume-atomiser literature value, "
     "not measured for any specific bottle."),
    ("OR polymorphism coverage",
     "Only OR7D4 / OR5A1 / OR11H7 SNPs encoded. ~400 ORs × 3 variants = ~1200 alleles "
     "remain unmodeled."),
]

OPEN_QUESTIONS = [
    "Should mixture-shift β be material-pair-specific?",
    "Is Stevens' law (per-OR exponent) or Weber–Fechner (log) the better default for "
    "supra-threshold perception?",
    "How to weight retronasal vs orthonasal in the optimizer when the brief is for skin "
    "fragrance, not flavour?",
    "Lateral-inhibition kernel: ring-uniform vs structural-similarity-weighted?",
    "Granularity of OR families: 8 abstract groups (current) vs full 396-locus model?",
]


def main():
    cov = _gather_data_coverage()
    print("=" * 60)
    print("perfume-chem science audit")
    print("=" * 60)
    print("\nData coverage (% of materials with field filled):")
    for k, v in sorted(cov.items()):
        print(f"  {k:14s} {v:6.1f}%")
    print("\nKnown weaknesses:")
    for title, body in KNOWN_WEAKNESSES:
        print(f"\n  • {title}")
        print(f"    {body}")
    print("\nOpen questions:")
    for q in OPEN_QUESTIONS:
        print(f"  ? {q}")
    print()
    # External-AI feedback contract
    contract = build_science_audit_contract()
    out_path = ROOT / "verification_runs" / "science_audit.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    print(f"Wrote machine-readable contract → {out_path}")


if __name__ == "__main__":
    main()
