"""Opus V — Top / Heart / Base Modular Scorer

Reorganises the 40 Opus V ingredients into a classical perfumery
pyramid (Top, Heart, Base) based on volatility and functional role,
then scores various pyramid ratio combinations through the 10-axis pipeline.

Material placement rationale:
  TOP  — VP > 0.1 mmHg or perception window < 2 hr: citrus EOs,
         dihydromyrcenol, linalool, lavender, helional, terpinyl acetate
  HEART — Core identity / ionone stack, radiance florals, green-violet
  BASE  — VP < 0.001 mmHg: musks, woods, ambers, fixatives, coumarin

Usage:
    python opus_v_thb_scorer.py                 # Score all preset ratios
    python opus_v_thb_scorer.py 12 58 30        # Score a custom T:H:B ratio
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys, io, csv

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.optimizer.models import FormulaVector
from engine.optimizer.scoring import FormulaScorer
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph

# ═════════════════════════════════════════════════════════════════
# TOP — Opening burst, fresh lift, citrus sparkle, herbal aromatics
# Original total: ~11.73 parts (12.0% of formula)
# ═════════════════════════════════════════════════════════════════

TOP = {
    # Fresh-citrus lift
    "Dihydromyrcenol":      3.0612,   # Dihydromyrcenol freshness, drives projection in first 30 min
    "Linalool":             2.0408,   # Floral-citrus bridge, linear top-to-heart transition
    "Bergamot FCF":         1.5306,   # Classical bergamot sparkle — opening signature
    "Terpinyl Acetate":     1.5306,   # Pine-citrus herbal, coniferous lift pairing lavender
    # Herbal / aromatic
    "Lavender EO":          1.0204,   # Aromatic crown, fougère element grounding florals
    # Green / ozone accents
    "Helional":             0.5102,   # Metallic-green ozone, melon facet, transparent lift
    "Limonene":             0.5102,   # Raw orange-peel burst, fleeting terpenic sparkle
    "Petitgrain EO":        0.5102,   # Bitter-green neroli bridge, citrus-leaf
    # Aldehyde / specialty
    "Cyclimal Aldehyde":    0.5102,   # Muguet-crisp, clean aldehyde lift into iris heart
    "Paradiseamine (10%)":  0.5102,   # Fruity sparkle — guava, passion fruit, cassis flash
}

# ═════════════════════════════════════════════════════════════════
# HEART — Iris monument: ionone stack, violet-green architecture,
#          radiance amplifiers, floral detail
# Original total: ~56.63 parts (57.5% of formula)
# ═════════════════════════════════════════════════════════════════

HEART = {
    # ── Ionone stack (the iris identity) ──
    "Alpha Isomethyl Ionone": 16.3265,  # Iris backbone — orris-violet, massive dose = the character
    "Alpha Ionone":            8.1633,  # Violet facet of iris, fruity-floral, woody
    "Beta Ionone":             5.6122,  # Deeper violet, cedarwood-like dryness
    "Dihydro Beta Ionone":     4.0816,  # Suede-iris, powdery, extends ionone depth
    "Ultralia":                5.1020,  # Ghost iris at trace — transparent powdery halo
    "Orivone":                 4.0816,  # Buttery orris, warm iris base note
    "Alpha Irone 30%":         1.5306,  # True orris root character — the authenticator
    # ── Green-violet modifier ──
    "Parmavert":               1.0204,  # Green violet-leaf, grounds ionones in nature
    # ── Radiance / floral detail ──
    "Hedione HC":              3.0612,  # Radiance amplifier, jasmine transparency, volume expander
    "Phenylethyl Alcohol":     2.5510,  # Rose body, natural roundness, floral anchor
    "Geraniol":                2.0408,  # Rose-geranium facet, citrus-floral bridge
    "Citronellol":             1.5306,  # Rosy-citrusy, pairs with geraniol for rose accord
    "Hydroxycitronellal":      1.5306,  # Muguet-lily, dewy, the watery-floral element
}

# ═════════════════════════════════════════════════════════════════
# BASE — Structural foundation: woods, amber, musk chord, fixatives
# Original total: ~30.10 parts (30.6% of formula)
# ═════════════════════════════════════════════════════════════════

BASE = {
    # ── Woody structure ──
    "Koavone":             3.0612,  # Warm woody, cedar support, slightly balsamic
    "Iso E Super":         2.5510,  # Molecular-skin cocoon, abstract cedar halo
    "Javanol":             2.0408,  # Dry mineral sandalwood, skin-scent intimacy
    "Amberwood F":         2.0408,  # Transparent amber-wood, invisible warmth
    "Ebanol":              1.0204,  # Creamy sandalwood, silk complement to Javanol's dryness
    "Cashmeran":           1.0204,  # Textile-warm, spicy-musky, cashmere wrap
    "Polysantol":          1.5306,  # Creamy sandalwood, pairs Javanol + Ebanol for chord
    # ── Musk chord (depth + projection + character) ──
    "Galaxolide 50%":      3.0612,  # Polycyclic musk, fruity-floral, projection driver
    "Habanolide":          2.5510,  # Warm macrocyclic, skin-intimate depth
    "Musk Ketone 10%":     2.0408,  # Powdery nitro musk, iris-powder character-echo
    "Ethylene Brassylate":  1.5306,  # Creamy-lactonic, oriental depth
    "Romandolide":          1.5306,  # Clean-diffusive projection musk, extends sillage
    # ── Amber / fixative ──
    "Ambrox Super (30%)":  2.0408,  # Crystalline mineral amber, transparent depth
    "Coumarin":            1.5306,  # Hay-tonka, powdery drydown, bridges iris-musk
    "Myristic Acid":       2.5510,  # Waxy carrier/fixative, molecular weight anchor
}

MODULES = [
    ("Top",   TOP),
    ("Heart", HEART),
    ("Base",  BASE),
]

# ── Dilutions ──
DILUTIONS = {
    "Alpha Irone 30%":       0.30,
    "Galaxolide 50%":        0.50,
    "Musk Ketone 10%":       0.10,
    "Ambrox Super (30%)":    0.30,
    "Coumarin":              0.20,
    "Cashmeran":             0.20,
    "Paradiseamine (10%)":   0.10,
}

# ═════════════════════════════════════════════════════════════════
# PRESET PYRAMID RATIOS  [Top, Heart, Base]
# Original formula = 12:58:30
# ═════════════════════════════════════════════════════════════════

PRESETS = [
    ("Original (12:58:30)",       [12, 58, 30]),
    ("Fresh Opening",             [18, 52, 30]),
    ("Iris Dominant",             [10, 65, 25]),
    ("Long Trail",                [ 8, 50, 42]),
    ("Powdery Intimate",          [10, 55, 35]),
    ("Radiant Iris",              [14, 56, 30]),
    ("Deep Iris (dark wood)",     [10, 52, 38]),
    ("Classic Pyramid",           [15, 50, 35]),
    ("Skin Scent",                [ 8, 58, 34]),
    ("Maximum Projection",        [16, 46, 38]),
]


# ─────────────────────────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────────────────────────

def compute_original_totals():
    return [sum(mod.values()) for _, mod in MODULES]


def blend_modules(ratios: list[float]) -> dict[str, float]:
    """Scale each module so its share matches the target ratio, then merge."""
    orig_totals = compute_original_totals()
    total_ratio = sum(ratios)
    grand_orig = sum(orig_totals)
    blended = {}
    for i, (_, module) in enumerate(MODULES):
        if orig_totals[i] == 0:
            continue
        scale = (ratios[i] / total_ratio) / (orig_totals[i] / grand_orig)
        for mat, parts in module.items():
            blended[mat] = blended.get(mat, 0) + parts * scale
    return blended


def score_blend(ingredients: dict[str, float], name: str = "Blend") -> dict:
    """Score a blended formula through the 10-axis pipeline."""
    total_parts = sum(ingredients.values())
    scale = 5000.0 / total_parts if total_parts > 0 else 1.0
    ul_dict = {mat: parts * scale for mat, parts in ingredients.items()}

    info = FormulaInfo(
        number=0,
        name=name,
        ingredients=ul_dict,
        dilutions=DILUTIONS,
        concentrate_ml=total_parts * scale / 1000,
        description=f"Opus V pyramid blend: {name}",
    )
    fv = formula_to_vector(info)
    sg = SynergyGraph()
    sg.build(material_names=list(ul_dict.keys()))
    scorer = FormulaScorer(synergy_graph=sg)
    return scorer.score(fv)


# ─────────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────────

AXES = [
    "longevity", "sillage", "synergy", "luxury", "texture",
    "stacking_depth", "hedonic", "skin_performance",
    "perceptual_clarity", "safety",
]


def print_scores(name: str, ratios: list[int], scores: dict):
    geo = scores.get("geometric_total", 0)
    ratio_str = ":".join(str(r) for r in ratios)

    print(f"\n{'=' * 70}")
    print(f"  {name}  [T:H:B = {ratio_str}]")
    print(f"  COMPOSITE (geometric): {geo:.1f}")
    print(f"{'─' * 70}")

    for ax in AXES:
        v = scores.get(ax, 0)
        bar = "█" * int(v / 2) + "░" * (50 - int(v / 2))
        flag = " ⚠" if v < 40 else ""
        print(f"  {ax:>22s}: {v:5.1f}  {bar}{flag}")

    style = scores.get("detected_style", "?")
    print(f"  {'detected_style':>22s}: {style}")

    diags = scores.get("_diagnostics", [])
    if diags:
        print(f"  {'─' * 66}")
        for d in diags[:5]:
            print(f"    {d}")


def print_comparison_table(results: list[tuple[str, list[int], dict]]):
    print(f"\n{'=' * 110}")
    print(f"  TOP / HEART / BASE  — COMPARISON TABLE")
    print(f"{'=' * 110}")

    display_axes = [a for a in AXES if a != "safety"]

    header = f"{'Blend':>28s} | {'T:H:B':>10s} | {'Geo':>6s}"
    for ax in display_axes:
        header += f" | {ax[:7]:>7s}"
    print(header)
    print("─" * len(header))

    sorted_results = sorted(results, key=lambda x: x[2].get("geometric_total", 0), reverse=True)
    best_geo = sorted_results[0][2].get("geometric_total", 0) if sorted_results else 0

    for name, ratios, scores in sorted_results:
        geo = scores.get("geometric_total", 0)
        ratio_str = ":".join(str(r) for r in ratios)
        marker = " ★" if geo == best_geo else ""
        row = f"{name:>28s} | {ratio_str:>10s} | {geo:>5.1f}{marker}"
        for ax in display_axes:
            v = scores.get(ax, 0)
            row += f" | {v:>7.1f}"
        print(row)

    print(f"\n  ★ = highest geometric composite\n")

    print(f"  Best per axis:")
    for ax in display_axes:
        best = max(sorted_results, key=lambda x: x[2].get(ax, 0))
        print(f"    {ax:>22s}: {best[0]} ({best[2].get(ax, 0):.1f})")

    # Print ingredient count per module
    print(f"\n  Module sizes: Top={len(TOP)} materials, Heart={len(HEART)} materials, Base={len(BASE)} materials")
    print(f"  Total unique materials: {len(set(list(TOP) + list(HEART) + list(BASE)))}")


def export_csv(results: list[tuple[str, list[int], dict]], path: str = "opus_v_thb_comparison.csv"):
    export_axes = ["geometric_total"] + AXES
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Blend", "Top", "Heart", "Base"] + export_axes)
        for name, ratios, scores in results:
            row = [name] + ratios + [round(scores.get(ax, 0), 1) for ax in export_axes]
            w.writerow(row)
    print(f"\n  Exported to {path}")


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if len(args) == 3:
        ratios = [int(a) for a in args]
        name = f"Custom ({':'.join(args)})"
        presets = [(name, ratios)]
    else:
        presets = PRESETS

    # Show pyramid composition
    orig_totals = compute_original_totals()
    grand_total = sum(orig_totals)
    print("OPUS V — TOP / HEART / BASE PYRAMID")
    print("─" * 60)
    for i, (mname, mod) in enumerate(MODULES):
        pct = orig_totals[i] / grand_total * 100
        print(f"\n  {mname.upper()} — {orig_totals[i]:.1f} parts ({pct:.1f}%)")
        for mat, parts in sorted(mod.items(), key=lambda x: -x[1]):
            dil = DILUTIONS.get(mat)
            dil_str = f" [{int(dil*100)}%]" if dil else ""
            print(f"    {mat:>30s}: {parts:6.2f}{dil_str}")
    print(f"\n  {'GRAND TOTAL':>30s}: {grand_total:.1f} parts")
    print(f"  Original ratio: T {orig_totals[0]/grand_total*100:.0f}% : "
          f"H {orig_totals[1]/grand_total*100:.0f}% : "
          f"B {orig_totals[2]/grand_total*100:.0f}%")

    # Score each preset
    print(f"\n\nScoring {len(presets)} blend(s)...")
    results = []
    for name, ratios in presets:
        print(f"  → {name}...", end=" ", flush=True)
        ingredients = blend_modules(ratios)
        scores = score_blend(ingredients, name)
        results.append((name, ratios, scores))
        print(f"done ({scores.get('geometric_total', 0):.1f})")

    # Output
    for name, ratios, scores in results:
        print_scores(name, ratios, scores)

    if len(results) > 1:
        print_comparison_table(results)
        export_csv(results)


if __name__ == "__main__":
    main()
