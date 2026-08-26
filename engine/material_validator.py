"""material_validator.py — Unified material data validation.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

This module provides the "unified material data path" that:
  1. Queries local sources first (ingredient_intelligence, data_spine)
  2. Cross-validates against PubChem MCP (when available)
  3. Returns a unified record with provenance metadata
  4. Gracefully degrades to local-only if PubChem is unavailable

Architecture:
  Local sources (always available) → PubChem MCP (best-effort) → Report

Usage:
    from engine.material_validator import validate_material

    record = validate_material("Hedione", fields=["mw", "vp", "odt"])
    record["mw"]            # float
    record["mw_source"]     # "local" or "pubchem"
    record["conflicts"]     # list of field conflicts
    record["mcp_fresh"]     # bool
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine.pubchem_client import cache_stats, lookup_material  # noqa: E402  # sys.path

# Tier-1 confidence source → Tier-3 fallback
CONFIDENCE_RANK = {
    "local_yaml": 3,  # data/materials/<L>.yaml
    "local_profile": 2,  # ingredient_intelligence._PROFILES
    "pubchem_live": 1,  # PubChem API
    "derived": 0,  # computed/estimated
}


def validate_material(
    name: str,
    fields: Optional[list[str]] = None,
    include_pubchem: bool = True,
) -> dict:
    """Validate a material against all available sources.

    Args:
        name: canonical or common material name
        fields: list of fields to validate (e.g., ["mw", "vp", "odt"]).
                If None, returns all available fields.
        include_pubchem: whether to attempt PubChem cross-check (default True)

    Returns:
        dict with:
          - <field>: validated value (float, str, etc.)
          - <field>_source: provenance string ("local_yaml", "local_profile",
            "pubchem_live", "derived", or "missing")
          - <field>_confidence: int from CONFIDENCE_RANK
          - pubchem_data: raw PubChem response (or None)
          - pubchem_fresh: bool — whether PubChem data is from live API
          - conflicts: list of (field, local_val, pubchem_val)
          - source_summary: "local_only" or "local+pubchem" or "pubchem_only" or "missing"
    """
    if fields is None:
        fields = ["mw", "vp", "logp", "odt", "cas"]

    result = {}
    conflicts = []
    local_sources_used = set()

    # ── Step 1: Local sources (always available) ──
    local_data = _query_local(name, fields)
    for f in fields:
        val, source = local_data.get(f, (None, "missing"))
        if val is not None:
            result[f] = val
            result[f"{f}_source"] = source
            result[f"{f}_confidence"] = CONFIDENCE_RANK.get(source, 0)
            local_sources_used.add(source)
        else:
            result[f] = None
            result[f"{f}_source"] = "missing"
            result[f"{f}_confidence"] = 0

    # ── Step 2: PubChem cross-check (best-effort) ──
    pubchem_data = None
    pubchem_fresh = False
    if include_pubchem:
        try:
            pubchem_data = lookup_material(name)
            if pubchem_data:
                pubchem_fresh = pubchem_data.get("source") == "pubchem_live"
                # Compare MW
                if "mw" in fields and pubchem_data.get("molecular_weight"):
                    pub_mw = float(pubchem_data["molecular_weight"])
                    local_mw = result.get("mw")
                    if local_mw is not None and abs(pub_mw - local_mw) / pub_mw > 0.01:
                        conflicts.append(
                            {
                                "field": "mw",
                                "local": local_mw,
                                "pubchem": pub_mw,
                                "pct_diff": round(abs(pub_mw - local_mw) / pub_mw * 100, 2),
                            }
                        )
                # Compare logP
                if "logp" in fields and pubchem_data.get("xlogp") is not None:
                    pub_lp = float(pubchem_data["xlogp"])
                    local_lp = result.get("logp")
                    if local_lp is not None and abs(pub_lp - local_lp) > 0.5:
                        conflicts.append(
                            {
                                "field": "logp",
                                "local": local_lp,
                                "pubchem": pub_lp,
                                "pct_diff": round(
                                    abs(pub_lp - local_lp) / max(abs(pub_lp), 0.01) * 100,
                                    2,
                                ),
                            }
                        )
                # Fill missing CAS
                if "cas" in fields and pubchem_data.get("inchikey") and not result.get("cas"):
                    # InChIKey encodes structure but isn't CAS. We only use it as a hint.
                    pass
        except Exception:
            # Graceful degradation: network error, etc. — fall through.
            pubchem_data = None
            pubchem_fresh = False

    # ── Step 3: Build summary ──
    if result and any(result.get(f) is not None for f in fields):
        if pubchem_data is not None:
            source_summary = "local+pubchem"
        else:
            source_summary = "local_only"
    elif pubchem_data is not None:
        source_summary = "pubchem_only"
    else:
        source_summary = "missing"

    result["pubchem_data"] = pubchem_data
    result["pubchem_fresh"] = pubchem_fresh
    result["conflicts"] = conflicts
    result["source_summary"] = source_summary
    result["local_sources"] = sorted(local_sources_used)
    return result


def _query_local(name: str, fields: list[str]) -> dict:
    """Query local data sources for a material.

    Returns dict of {field: (value, source)}.
    """
    out = {}
    name_lower = name.lower().strip()

    # Source 1: ingredient_intelligence._PROFILES
    try:
        from engine.ingredient_intelligence import _PROFILES

        for prof_name, prof in _PROFILES.items():
            if prof_name.lower() == name_lower:
                if "mw" in fields and prof.get("mw"):
                    out["mw"] = (float(prof["mw"]), "local_profile")
                if "vp" in fields and prof.get("vp"):
                    out["vp"] = (float(prof["vp"]), "local_profile")
                if "logp" in fields and prof.get("clogp"):
                    out["logp"] = (float(prof["clogp"]), "local_profile")
                if "odt" in fields and prof.get("odt"):
                    out["odt"] = (float(prof["odt"]), "local_profile")
                if "cas" in fields and prof.get("cas"):
                    out["cas"] = (prof["cas"], "local_profile")
                break
    except Exception:
        pass

    # Source 2: data/materials/<L>.yaml (data_spine)
    try:
        from engine.data_spine.loader import load_registry

        registry = load_registry()
        mat = registry.get(name)
        if mat:
            if "mw" in fields and mat.mw_g_mol and "mw" not in out:
                out["mw"] = (float(mat.mw_g_mol), "local_yaml")
            if "vp" in fields and mat.vp_25c_pa and "vp" not in out:
                out["vp"] = (float(mat.vp_25c_pa), "local_yaml")
            if "logp" in fields and mat.logp and "logp" not in out:
                out["logp"] = (float(mat.logp), "local_yaml")
            if "odt" in fields:
                if mat.odt_air_ppb and "odt" not in out:
                    out["odt"] = (float(mat.odt_air_ppb), "local_yaml")
                elif mat.odt_eth_ppm and "odt" not in out:
                    out["odt"] = (float(mat.odt_eth_ppm), "local_yaml")
            if "cas" in fields and mat.cas and "cas" not in out:
                out["cas"] = (mat.cas, "local_yaml")
    except Exception:
        pass

    # Source 3: material_properties.json (knowledge_graph)
    try:
        import json

        props_path = REPO_ROOT / "data" / "knowledge_graph" / "material_properties.json"
        if props_path.exists():
            with open(props_path, "r", encoding="utf-8") as f:
                all_props = json.load(f)
            for entry in all_props:
                if entry.get("name", "").lower() == name_lower:
                    if "mw" in fields and entry.get("mw") and "mw" not in out:
                        out["mw"] = (float(entry["mw"]), "local_yaml")
                    if "vp" in fields and entry.get("vp") and "vp" not in out:
                        out["vp"] = (float(entry["vp"]), "local_yaml")
                    if "logp" in fields and entry.get("clp") and "logp" not in out:
                        out["logp"] = (float(entry["clp"]), "local_yaml")
                    if "odt" in fields and entry.get("odt") and "odt" not in out:
                        out["odt"] = (float(entry["odt"]), "local_yaml")
                    if "cas" in fields and entry.get("cas") and "cas" not in out:
                        out["cas"] = (entry["cas"], "local_yaml")
                    break
    except Exception:
        pass

    # Source 4: odor_thresholds.py ODT_DATA (ODT-specific fallback)
    if "odt" in fields and "odt" not in out:
        try:
            from engine.odor_thresholds import ODT_DATA

            for key, val in ODT_DATA.items():
                if key.lower() == name_lower:
                    odt_val = val.get("odt_air") or val.get("odt_eth")
                    if odt_val:
                        out["odt"] = (float(odt_val), "local_yaml")
                        break
        except Exception:
            pass

    return out


def batch_validate(materials: list[str], fields: Optional[list[str]] = None) -> list[dict]:
    """Validate a batch of materials. Returns list of validate_material() results."""
    return [validate_material(m, fields=fields) for m in materials]


def generate_audit_report(materials: list[str], output_file: Optional[str] = None) -> str:
    """Generate a material audit report for a list of materials.

    Args:
        materials: list of material names
        output_file: optional path to write the report

    Returns:
        Markdown-formatted report string
    """
    lines = ["# Material Audit Report", ""]
    lines.append(f"Materials audited: {len(materials)}")
    lines.append("")

    all_results = batch_validate(materials)

    # Summary
    fresh = sum(1 for r in all_results if r.get("pubchem_fresh"))
    cached = sum(1 for r in all_results if r.get("pubchem_data") and not r.get("pubchem_fresh"))
    no_pubchem = sum(1 for r in all_results if not r.get("pubchem_data"))
    with_conflicts = sum(1 for r in all_results if r.get("conflicts"))
    local_only = sum(1 for r in all_results if r.get("source_summary") == "local_only")
    local_plus_pubchem = sum(1 for r in all_results if r.get("source_summary") == "local+pubchem")

    lines.append("## Summary")
    lines.append(f"- **Local data present**: {local_only + local_plus_pubchem}/{len(materials)}")
    lines.append(f"- **PubChem fresh (live API)**: {fresh}")
    lines.append(f"- **PubChem cached**: {cached}")
    lines.append(f"- **No PubChem data**: {no_pubchem}")
    lines.append(f"- **With MW/logP conflicts**: {with_conflicts}")
    lines.append(
        f"- **Source breakdown**: {local_only} local-only, {local_plus_pubchem} local+pubchem"
    )
    lines.append("")

    # Cache stats
    stats = cache_stats()
    lines.append(
        f"Cache: {stats['fresh']} fresh entries / {stats['stale']} stale / TTL {stats['ttl_days']} days"
    )
    lines.append("")

    # Per-material detail
    lines.append("## Per-Material Detail")
    lines.append("")
    for mat, r in zip(materials, all_results):
        lines.append(f"### {mat}")
        lines.append(f"  Source: **{r['source_summary']}**")
        if r.get("conflicts"):
            lines.append(f"  ⚠️ **Conflicts**: {len(r['conflicts'])}")
            for c in r["conflicts"]:
                lines.append(
                    f"    - {c['field']}: local={c['local']} pubchem={c['pubchem']} diff={c['pct_diff']}%"
                )
        else:
            lines.append("  ✓ No conflicts")
        if r.get("pubchem_fresh"):
            lines.append("  🔄 PubChem: live API")
        elif r.get("pubchem_data"):
            lines.append("  💾 PubChem: from cache")
        else:
            lines.append("  ❌ PubChem: not available")
        lines.append("")

    report = "\n".join(lines)
    if output_file:
        Path(output_file).write_text(report, encoding="utf-8")
    return report


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Material validator with PubChem MCP cross-check")
    parser.add_argument("--name", help="Single material name to validate")
    parser.add_argument("--report", help="File path to write audit report")
    parser.add_argument("--materials", nargs="+", help="List of material names for batch audit")
    args = parser.parse_args()

    if args.name:
        r = validate_material(args.name)
        print(f"\n=== {args.name} ===")
        print(f"Source: {r['source_summary']}")
        print(f"Local sources: {r['local_sources']}")
        for k in ["mw", "vp", "logp", "odt", "cas"]:
            if r.get(k) is not None:
                print(f"  {k}: {r[k]} (source: {r.get(k + '_source')})")
        if r["conflicts"]:
            print(f"  CONFLICTS: {r['conflicts']}")
    elif args.materials:
        report = generate_audit_report(args.materials, args.report)
        if not args.report:
            print(report)
        else:
            print(f"Report written to {args.report}")
    else:
        # Default: audit Reflection Man Luxe materials
        default = [
            "Linalool",
            "Hedione",
            "Iso E Super",
            "Geraniol",
            "Phenethyl alcohol",
            "alpha-Ionone",
            "beta-Ionone",
            "alpha-Irone",
            "Methyl ionone",
            "Orivone",
            "Javanol",
            "Ebanol",
            "Acetyl cedrene",
            "Ambroxide",
            "Galaxolide",
            "Habanolide",
            "Benzyl salicylate",
        ]
        report = generate_audit_report(default, args.report or "output/material_audit.md")
        print(report)
        print(f"\nReport written to {args.report or 'output/material_audit.md'}")
