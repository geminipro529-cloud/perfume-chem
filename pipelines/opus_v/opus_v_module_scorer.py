import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

"""Opus V Module Ratio Scorer — Score different module combinations through the 10-axis pipeline.

Defines 5 modules from the Opus V Pure EDP formula, lets you set ratios,
builds the blended ingredient dict, and scores through the full pipeline.

Usage:
    python opus_v_module_scorer.py                    # Score all preset ratios
    python opus_v_module_scorer.py 46 14 11 17 10     # Score a custom ratio
"""
import sys, io, csv
from itertools import product

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph

# ─────────────────────────────────────────────────────────────
# MODULE DEFINITIONS — ingredients grouped by functional role
# Values are the ORIGINAL parts from opus_v_pure_edp.csv
# ─────────────────────────────────────────────────────────────

MODULE_1_IRIS_CORE = {
    # The ionone stack + iris identity materials
    "Alpha Isomethyl Ionone": 16.3265,
    "Alpha Ionone": 8.1633,
    "Beta Ionone": 5.6122,
    "Dihydro Beta Ionone": 4.0816,
    "Ultralia": 5.1020,
    "Orivone": 4.0816,
    "Alpha Irone 30%": 1.5306,
    "Parmavert": 1.0204,
}

MODULE_2_WOODY_AMBER = {
    # Structural woods + amber warmth
    "Koavone": 3.0612,
    "Iso E Super": 2.5510,
    "Myristic Acid": 2.5510,
    "Amberwood F": 2.0408,
    "Javanol": 2.0408,
    "Ebanol": 1.0204,
    "Cashmeran": 1.0204,
}

MODULE_3_MUSK_BED = {
    # Musk architecture — depth, projection, character axes
    "Galaxolide 50%": 3.0612,
    "Habanolide": 2.5510,
    "Musk Ketone 10%": 2.0408,
    "Ethylene Brassylate": 1.5306,
    "Romandolide": 1.5306,
}

MODULE_4_FLORAL_RADIANCE = {
    # Radiance amplifiers + floral detail
    "Hedione HC": 3.0612,
    "Dihydromyrcenol": 3.0612,
    "Phenylethyl Alcohol": 2.5510,
    "Geraniol": 2.0408,
    "Linalool": 2.0408,
    "Hydroxycitronellal": 1.5306,
    "Citronellol": 1.5306,
    "Polysantol": 1.5306,
}

MODULE_5_TOP_LIFT_ACCENTS = {
    # Opening burst + finishing accents
    "Ambrox Super (30%)": 2.0408,
    "Bergamot FCF": 1.5306,
    "Terpinyl Acetate": 1.5306,
    "Coumarin": 1.5306,
    "Lavender EO": 1.0204,
    "Helional": 0.5102,
    "Limonene": 0.5102,
    "Petitgrain EO": 0.5102,
    "Cyclimal Aldehyde": 0.5102,
    "Paradiseamine (10%)": 0.5102,
}

MODULES = [
    ("Iris Core", MODULE_1_IRIS_CORE),
    ("Woody-Amber", MODULE_2_WOODY_AMBER),
    ("Musk Bed", MODULE_3_MUSK_BED),
    ("Floral-Radiance", MODULE_4_FLORAL_RADIANCE),
    ("Top/Lift/Accents", MODULE_5_TOP_LIFT_ACCENTS),
]

# Dilutions for materials that aren't neat
DILUTIONS = {
    "Alpha Irone 30%": 0.30,
    "Galaxolide 50%": 0.50,
    "Musk Ketone 10%": 0.10,
    "Ambrox Super (30%)": 0.30,
    "Coumarin": 0.20,
    "Cashmeran": 0.20,
    "Paradiseamine (10%)": 0.10,
}

# ─────────────────────────────────────────────────────────────
# PRESET MODULE RATIOS TO COMPARE
# Format: (name, [M1, M2, M3, M4, M5])
# ─────────────────────────────────────────────────────────────

PRESETS = [
    ("Original (balanced)",       [46, 14, 11, 17, 10]),
    ("Iris Heavy",                [55, 10, 11, 14, 10]),
    ("Darker (more wood/amber)",  [40, 20, 11, 17, 12]),
    ("Musk-Forward",              [40, 14, 18, 17, 11]),
    ("High Radiance",             [42, 12, 11, 22, 13]),
    ("Skin Scent (intimate)",     [48, 10, 16, 16,  8]),
    ("Powdery Iris (soft)",       [50, 10, 14, 16, 10]),
    ("Bold Projection",           [38, 16, 13, 20, 13]),
]


def compute_original_totals():
    """Return the sum of parts in each module (for ratio normalization)."""
    return [sum(mod.values()) for _, mod in MODULES]


def blend_modules(ratios: list[float]) -> dict[str, float]:
    """Build a single ingredient dict from module ratios.

    Each module's ingredients are scaled so that the module's total parts
    match the target ratio, then all modules are merged.
    """
    orig_totals = compute_original_totals()
    total_ratio = sum(ratios)
    blended = {}
    for i, (_, module) in enumerate(MODULES):
        if orig_totals[i] == 0:
            continue
        # Scale factor: target share / original share
        scale = (ratios[i] / total_ratio) / (orig_totals[i] / sum(orig_totals))
        for mat, parts in module.items():
            blended[mat] = blended.get(mat, 0) + parts * scale
    return blended


def score_blend(ingredients: dict[str, float], name: str = "Blend") -> dict:
    """Score a blended formula through the full 10-axis pipeline."""
    total_parts = sum(ingredients.values())
    # Convert parts to µL (scale to ~5000 µL total for realistic scoring)
    scale = 5000.0 / total_parts if total_parts > 0 else 1.0
    ul_dict = {mat: parts * scale for mat, parts in ingredients.items()}

    info = FormulaInfo(
        number=0,
        name=name,
        ingredients=ul_dict,
        dilutions=DILUTIONS,
        concentrate_ml=total_parts * scale / 1000,
        description=f"Opus V module blend: {name}",
    )
    fv = formula_to_vector(info)
    sg = SynergyGraph()
    sg.build(material_names=list(ul_dict.keys()))
    scorer = FormulaScorer(synergy_graph=sg)
    return scorer.score(fv)


def print_scores(name: str, ratios: list[int], scores: dict):
    """Pretty-print a single blend's scores."""
    geo = scores.get("geometric_total", 0)
    ratio_str = ":".join(str(r) for r in ratios)

    print(f"\n{'=' * 70}")
    print(f"  {name}  [{ratio_str}]")
    print(f"  COMPOSITE (geometric): {geo:.1f}")
    print(f"{'─' * 70}")

    AXES = [
        "longevity", "sillage", "synergy", "luxury", "texture",
        "stacking_depth", "hedonic", "skin_performance",
        "perceptual_clarity", "safety",
    ]
    for ax in AXES:
        v = scores.get(ax, 0)
        bar = "█" * int(v / 2) + "░" * (50 - int(v / 2))
        flag = " ⚠" if v < 40 else ""
        print(f"  {ax:>22s}: {v:5.1f}  {bar}{flag}")

    # Show detected style
    style = scores.get("detected_style", "?")
    print(f"  {'detected_style':>22s}: {style}")

    # Show diagnostics (first 5)
    diags = scores.get("_diagnostics", [])
    if diags:
        print(f"  {'─' * 66}")
        for d in diags[:5]:
            print(f"    {d}")


def print_comparison_table(results: list[tuple[str, list[int], dict]]):
    """Print a compact comparison table of all blends."""
    AXES = [
        "longevity", "sillage", "synergy", "luxury", "texture",
        "stacking_depth", "hedonic", "skin_performance",
        "perceptual_clarity",
    ]

    print(f"\n{'=' * 100}")
    print(f"  COMPARISON TABLE")
    print(f"{'=' * 100}")

    # Header
    header = f"{'Blend':>30s} | {'Ratio':>15s} | {'GeoTotal':>8s}"
    for ax in AXES:
        header += f" | {ax[:6]:>6s}"
    print(header)
    print("─" * len(header))

    # Sort by geometric total descending
    sorted_results = sorted(results, key=lambda x: x[2].get("geometric_total", 0), reverse=True)
    best_geo = sorted_results[0][2].get("geometric_total", 0) if sorted_results else 0

    for name, ratios, scores in sorted_results:
        geo = scores.get("geometric_total", 0)
        ratio_str = ":".join(str(r) for r in ratios)
        marker = " ★" if geo == best_geo else ""
        row = f"{name:>30s} | {ratio_str:>15s} | {geo:>7.1f}{marker}"
        for ax in AXES:
            v = scores.get(ax, 0)
            row += f" | {v:>6.1f}"
        print(row)

    print(f"\n  ★ = highest geometric composite")

    # Find best per axis
    print(f"\n  Best per axis:")
    for ax in AXES:
        best = max(sorted_results, key=lambda x: x[2].get(ax, 0))
        print(f"    {ax:>22s}: {best[0]} ({best[2].get(ax, 0):.1f})")


def export_csv(results: list[tuple[str, list[int], dict]], path: str = "opus_v_module_comparison.csv"):
    """Export results to CSV for further analysis."""
    AXES = [
        "geometric_total", "longevity", "sillage", "synergy", "luxury",
        "texture", "stacking_depth", "hedonic", "skin_performance",
        "perceptual_clarity", "safety",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Blend", "M1_Iris", "M2_Wood", "M3_Musk", "M4_Floral", "M5_Top"] + AXES)
        for name, ratios, scores in results:
            row = [name] + ratios + [round(scores.get(ax, 0), 1) for ax in AXES]
            w.writerow(row)
    print(f"\n  Exported to {path}")


def main():
    args = sys.argv[1:]

    if len(args) == 5:
        # Custom ratio from command line
        ratios = [int(a) for a in args]
        name = f"Custom ({':'.join(args)})"
        presets = [(name, ratios)]
    else:
        presets = PRESETS

    # Show module composition
    orig_totals = compute_original_totals()
    grand_total = sum(orig_totals)
    print("MODULE COMPOSITION (original parts)")
    print("─" * 50)
    for i, (mname, mod) in enumerate(MODULES):
        pct = orig_totals[i] / grand_total * 100
        print(f"  M{i+1} {mname:>20s}: {orig_totals[i]:6.1f} parts ({pct:4.1f}%)")
        for mat, parts in sorted(mod.items(), key=lambda x: -x[1]):
            print(f"      {mat:>35s}: {parts:.2f}")
    print(f"  {'TOTAL':>23s}: {grand_total:6.1f} parts")

    # Score each preset
    print(f"\n\nSCORING {len(presets)} MODULE RATIOS...")
    print("(Building synergy graph per blend — this takes ~2-4s each)\n")

    results = []
    for name, ratios in presets:
        print(f"  Scoring: {name} [{':'.join(str(r) for r in ratios)}]...", end=" ", flush=True)
        ingredients = blend_modules(ratios)
        scores = score_blend(ingredients, name)
        geo = scores.get("geometric_total", 0)
        print(f"→ {geo:.1f}")
        results.append((name, ratios, scores))

    # Detailed output per blend
    for name, ratios, scores in results:
        print_scores(name, ratios, scores)

    # Comparison table
    print_comparison_table(results)

    # Export
    export_csv(results)


if __name__ == "__main__":
    main()
