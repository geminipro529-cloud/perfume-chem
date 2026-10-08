"""ifra_checker.py — IFRA Cat4 compliance checker with graceful degradation.

**RULE 1: All perfume calculations must use ppm, ODT, and OAV.**

This module provides a quick check of a formula against IFRA Cat 4 (Fine Fragrance)
limits from the sourced IFRA 51st Amendment table
(data/regulatory/ifra_cat4_51.json, read through engine.ifra_standards).

Unlike the full safety_ifra_allergen gate in the pipeline, this is a lightweight
standalone checker suitable for quick pre-formulation safety validation.

Usage:
    from engine.ifra_checker import check_formula_ifra

    materials = [
        ("Linalool", 150, 1.0),       # name, raw_uL, dilution
        ("Hedione", 620, 1.0),
        ("Geraniol", 100, 0.1),
    ]
    total_volume_ul = 6000
    concentration_pct = 20.0

    report = check_formula_ifra(materials, total_volume_ul, concentration_pct)
    print(report["summary"])
    for v in report["violations"]:
        print(f"  VIOLATION: {v}")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def check_formula_ifra(
    materials: "list[tuple[str, float, float]] | list[tuple[str, int, float]]",
    total_volume_ul: float,
    concentration_pct: float = 20.0,
    product_type: str = "EdP",
) -> dict:
    """Check a formula against IFRA Cat4 limits.

    Args:
        materials: list of (name, raw_volume_uL, dilution_fraction) tuples
        total_volume_ul: total formula volume in microliters
        concentration_pct: oil concentration in finished product (default 20%)
        product_type: product type for limit category (default "EdP" = Cat 4)

    Returns:
        dict with:
          - violations: list of (material, actual_pct, limit_pct, exceedance)
          - warnings: list of materials without IFRA limits
          - ok_materials: list of materials within limits
          - summary: human-readable summary string
    """
    try:
        from engine.ifra_standards import load_ifra_table
    except ImportError:
        return {
            "violations": [],
            "warnings": ["IFRA limits not available — module not found"],
            "ok_materials": [],
            "summary": "IFRA data unavailable (graceful degradation)",
        }
    table = load_ifra_table()

    violations = []
    warnings = []
    ok_materials = []

    # Calculate finished product volume: concentrate + ethanol
    # 20% concentration means 20% concentrate, 80% ethanol
    concentrate_pct = concentration_pct / 100.0

    for name, raw_ul, dilution in materials:
        active_ul = raw_ul * dilution
        # In finished product: active_uL / total_formula_volume × concentration_pct
        # For a 30mL EdP at 20%: concentrate = 6mL, ethanol = 24mL
        pct_in_finished = (active_ul / total_volume_ul) * concentrate_pct * 100

        # Look up limit: name and aliases in the sourced table. Prohibited
        # materials have a 0.0 limit; any other status has no numeric limit.
        record = table.lookup(name)
        if record is not None and record.status == "prohibited":
            limit: Optional[float] = 0.0
        elif record is not None and record.status == "restricted":
            limit = record.cat4_limit_pct
        else:
            limit = None
        if limit is None:
            warnings.append(name)
            continue

        if pct_in_finished > limit:
            exceedance_pct = (
                (pct_in_finished / limit - 1) * 100 if limit > 0 else float("inf")
            )
            violations.append(
                {
                    "material": name,
                    "actual_pct": round(pct_in_finished, 4),
                    "limit_pct": limit,
                    "exceedance_pct": round(exceedance_pct, 1),
                }
            )
        else:
            ok_materials.append(
                {
                    "material": name,
                    "actual_pct": round(pct_in_finished, 4),
                    "limit_pct": limit,
                    "headroom_pct": (
                        round((1 - pct_in_finished / limit) * 100, 1) if limit > 0 else 0.0
                    ),
                }
            )

    # Build summary
    summary_lines = [
        f"IFRA Cat4 Check ({product_type}, {concentration_pct}% concentration):",
        f"  Materials checked: {len(materials)}",
        f"  ✓ Within limits: {len(ok_materials)}",
        f"  ⚠️  Without limits: {len(warnings)}",
        f"  ❌ VIOLATIONS: {len(violations)}",
    ]
    if violations:
        summary_lines.append("\n  VIOLATIONS (must reduce dose or remove):")
        for v in violations:
            summary_lines.append(
                f"    {v['material']}: {v['actual_pct']:.3f}% / {v['limit_pct']}% "
                f"limit (exceedance: {v['exceedance_pct']}%)"
            )
    if warnings:
        summary_lines.append(
            "\n  MATERIALS WITHOUT IFRA LIMITS (acceptable for non-restricted materials):"
        )
        for w in warnings:
            summary_lines.append(f"    {w}")

    return {
        "violations": violations,
        "warnings": warnings,
        "ok_materials": ok_materials,
        "summary": "\n".join(summary_lines),
    }


# ══════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quick IFRA Cat4 check")
    parser.add_argument("--formula", help="Path to formula markdown (auto-parse)")
    parser.add_argument(
        "--total-volume",
        type=float,
        default=30000,
        help="Total formula volume in µL (default 30000 for 30mL)",
    )
    parser.add_argument(
        "--concentration",
        type=float,
        default=20.0,
        help="Oil concentration %% (default 20)",
    )
    args = parser.parse_args()

    if args.formula:
        # Auto-parse the formula markdown
        import re
        import sys
        from pathlib import Path

        sys.stdout.reconfigure(encoding="utf-8")
        content = Path(args.formula).read_text(encoding="utf-8")
        materials = []
        for line in content.split("\n"):
            if "|" not in line:
                continue
            if "Ingredient" in line or "Dilution" in line or "Amount" in line:
                continue
            if "---" in line or "===" in line:
                continue
            if line.strip().startswith("**") or line.strip().startswith("##"):
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < 4:
                continue
            dil = None
            amount = None
            name = None
            for i, p in enumerate(parts):
                if p.lower() == "neat":
                    dil = 1.0
                elif re.match(r"^\d+%$", p):
                    dil = int(p.rstrip("%")) / 100
                elif re.match(r"^\d+\s*µL$", p):
                    amt_match = re.match(r"^(\d+)", p)
                    if amt_match:
                        amount = int(amt_match.group(1))
                elif p.isdigit() and amount is None and dil is not None:
                    amount = int(p)
                elif name is None and not p.isdigit() and dil is None and amount is None:
                    if not any(
                        kw in p.lower() for kw in ["role", "chemical", "amount", "ingredient"]
                    ):
                        name = p
            if name and dil is not None and amount is not None:
                materials.append((name, amount, dil))
        total = sum(m[1] for m in materials)
        print(f"Parsed {len(materials)} materials, total raw: {total} µL")
        if materials:
            report = check_formula_ifra(materials, total, args.concentration)
            print()
            print(report["summary"])
    else:
        # Demo with Reflection Man Luxe materials
        demo = [
            ("Linalool", 150, 1.0),
            ("Hedione", 620, 1.0),
            ("Geraniol", 100, 0.1),
            ("Alpha Irone", 450, 0.3),
            ("Javanol", 250, 1.0),
            ("Iso E Super", 700, 1.0),
            ("Benzyl Salicylate", 220, 1.0),
        ]
        import sys

        sys.stdout.reconfigure(encoding="utf-8")
        report = check_formula_ifra(demo, 6000, 20.0)
        print(report["summary"])
