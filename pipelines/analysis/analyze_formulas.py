"""Test runner — Score all 9 luxury formulas on 10 axes + character radar.

Validates the ingredient intelligence + multi-axis scoring pipeline.
Prints multi-axis scores, character radars, comparative rankings,
and (optionally) targeted improvement suggestions.

Usage:
    python analyze_formulas.py               # Score all 9 formulas
    python analyze_formulas.py --suggest radiance   # Suggestions for radiance
    python analyze_formulas.py -f 6          # Score F6 only
    python analyze_formulas.py -f 4 -s smoky # F4 smoky suggestions
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import sys

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from engine.formula_analyzer import (
    parse_formulas, formula_to_vector, run_analysis,
    suggest_changes, format_scores, format_suggestions,
    _CHANGE_TARGETS,
)
from engine.formula_recommendations import (
    format_recommendations,
    generate_intervention_recommendations,
    load_inventory,
)
from engine.optimizer.scoring import FormulaScorer
from engine.ingredient_intelligence import get_profile, get_all_profiles, DIMENSIONS


def diagnostics():
    """Run diagnostic checks on the ingredient intelligence database."""
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  INGREDIENT INTELLIGENCE DIAGNOSTICS                     ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    all_profiles = get_all_profiles()
    print(f"  Materials in intelligence DB: {len(all_profiles)}")

    # Check formula coverage
    formulas = parse_formulas()
    unmatched = set()
    matched = 0
    total = 0
    for f in formulas:
        for name in f.ingredients:
            total += 1
            prof = get_profile(name)
            if prof:
                matched += 1
            else:
                unmatched.add(name)

    coverage = matched / total * 100 if total else 0
    print(f"  Formula ingredients matched: {matched}/{total} ({coverage:.1f}%)")
    if unmatched:
        print(f"  Unmatched ingredients ({len(unmatched)}):")
        for u in sorted(unmatched):
            print(f"    - {u}")

    # Dimension distribution
    print(f"\n  Character dimensions: {len(DIMENSIONS)}")
    for dim in DIMENSIONS:
        vals = [p.character.get(dim, 0) for p in all_profiles.values()]
        avg = sum(vals) / len(vals) if vals else 0
        print(f"    {dim:>12s}: avg={avg:.1f}  min={min(vals):.0f}  max={max(vals):.0f}")

    print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-axis formula analysis test runner")
    parser.add_argument("--formula", "-f", type=int, help="Formula number (1-9)")
    parser.add_argument("--suggest", "-s", type=str,
                        help=f"Target: {', '.join(_CHANGE_TARGETS.keys())}")
    parser.add_argument("--diagnostics", "-d", action="store_true",
                        help="Run ingredient DB diagnostics")
    parser.add_argument("--file", type=str,
                        help="Path to formulas markdown file (defaults to luxury_formulas_2026-03-26.md)")
    parser.add_argument(
        "--mode",
        choices=["pre_mix", "post_mix", "between_mix"],
        help="Emit mode-aware intervention recommendations through the shared pipeline",
    )
    parser.add_argument(
        "--observation",
        action="append",
        default=[],
        help="Free-text observation for between-mix or post-mix recommendation bias",
    )
    parser.add_argument(
        "--intent-tag",
        action="append",
        default=[],
        help="Intent tag used to bias intervention recommendations",
    )
    parser.add_argument(
        "--batch-ml",
        type=float,
        default=30.0,
        help="Bottle size used to translate post-mix additions into approximate microliters",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Maximum intervention recommendations to show per formula",
    )
    args = parser.parse_args()

    if args.diagnostics:
        diagnostics()

    # Always run diagnostics summary first (brief)
    all_profiles = get_all_profiles()
    formula_path = Path(args.file) if args.file else None
    formulas = parse_formulas(formula_path)
    print(f"\n  Loaded {len(all_profiles)} material profiles, {len(formulas)} formulas.\n")

    # Run the analysis
    run_analysis(formula_num=args.formula, suggest_target=args.suggest, formula_path=formula_path)

    if args.mode:
        print("\n" + "=" * 70)
        print(f"  INTERVENTION RECOMMENDATIONS [{args.mode.upper()}]")
        print("=" * 70)
        scorer = FormulaScorer()
        inventory = load_inventory()
        target_formulas = formulas
        if args.formula:
            target_formulas = [f for f in formulas if f.number == args.formula]

        for info in target_formulas:
            fv = formula_to_vector(info)
            scores = scorer.score(fv)
            recs = generate_intervention_recommendations(
                fv,
                scores,
                inventory=inventory,
                top_n=args.top_n,
                mode=args.mode,
                observations=list(args.observation or []),
                intent_tags=list(args.intent_tag or []),
                batch_volume_ml=args.batch_ml,
            )
            print(format_recommendations(f"F{info.number}. {info.name}", recs, scores, mode=args.mode))

    # If no specific suggestion requested and showing all,
    # also print weakest axes for each formula
    if not args.formula and not args.suggest:
        print("\n" + "=" * 70)
        print("  WEAKEST AXES PER FORMULA (top improvement opportunities)")
        print("=" * 70)
        scorer = FormulaScorer()
        for info in formulas:
            fv = formula_to_vector(info)
            scores = scorer.score(fv)
            # Find 3 weakest non-meta axes
            axes = ["longevity", "sillage", "balance", "theory", "radiance",
                    "texture", "complexity", "character_balance"]
            ranked = sorted(axes, key=lambda a: scores.get(a, 0))
            weakest = ranked[:3]
            weak_str = ", ".join(f"{a}={scores.get(a, 0):.0f}" for a in weakest)
            print(f"  F{info.number}. {info.name:<28s} → {weak_str}")
        print()


if __name__ == "__main__":
    main()
