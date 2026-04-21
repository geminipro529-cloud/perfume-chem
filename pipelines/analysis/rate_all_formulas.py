"""Comprehensive formula rating script — generates 10-star ratings + 0-100 scores for all formulas.

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
Usage:
    python rate_all_formulas.py
    
Generates:
    - Individual rating reports for each formula (detailed)
    - Comparison table (all formulas, all characteristics)
    - Insights document (strengths/weaknesses analysis)
"""

import sys
import re
from typing import List, Dict, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except OSError:
        pass

from engine.optimizer.scoring import FormulaScorer, FormulaVector
from engine.chemical_life_graph import build_chemical_life_graph
from engine.formula_rating import (
    compute_star_ratings,
    format_comprehensive_report,
    compare_rating_systems,
    StarRatings,
)
from engine.formula_recommendations import (
    load_inventory,
    generate_recommendations,
    format_recommendations,
)
from engine.synergy_graph import SynergyGraph


def _parse_dilution(raw: str) -> float:
    """Convert dilution string to factor: 'neat' → 1.0, '10%' → 0.1, '50% DPG' → 0.5."""
    raw = raw.strip().lower()
    if raw in ("neat", "pure", ""):
        return 1.0
    m = re.match(r'(\d+(?:\.\d+)?)\s*%', raw)
    if m:
        return float(m.group(1)) / 100.0
    return 1.0  # default to neat if unparseable


def parse_formula_amounts_from_text(text: str) -> tuple[dict[str, float], dict[str, float], float]:
    """Parse formula from markdown text, return (ingredient_uL, dilutions, ethanol_mL)."""
    ingredients = {}
    dilutions = {}
    ethanol_ul = 0.0
    
    # Parse ingredient table rows
    # Format: | N | Ingredient | Dilution | Amount (µL) | Amount (mL) |
    for line in text.split('\n'):
        # Skip section-header rows like | **— MINERAL CITRUS TOP —** |
        if '**—' in line or '---' in line:
            continue
        # Match ingredient rows
        m = re.match(
            r'\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|',
            line
        )
        if m:
            ing_name = m.group(2).strip()
            dilution_raw = m.group(3).strip()
            amount_ul = float(m.group(4))
            # Skip total row
            if 'total' in ing_name.lower():
                continue
            # Clean up name (remove bold markers)
            ing_name = ing_name.replace('**', '').strip()
            if 'ethanol' in ing_name.lower():
                ethanol_ul = amount_ul
                continue
            ingredients[ing_name] = amount_ul
            dilutions[ing_name] = _parse_dilution(dilution_raw)
    return ingredients, dilutions, ethanol_ul / 1000.0


def parse_formula_from_text(text: str) -> tuple[dict[str, float], dict[str, float], dict[str, float], float]:
    """Parse formula from markdown text, return (ingredient_pcts, dilutions, ingredient_uL, ethanol_mL)."""
    ingredients, dilutions, ethanol_ml = parse_formula_amounts_from_text(text)
    
    # Convert to percentages
    total_ul = sum(ingredients.values())
    if total_ul == 0:
        return {}, {}, {}, ethanol_ml
    
    pcts = {name: (ul / total_ul) * 100 for name, ul in ingredients.items()}
    return pcts, dilutions, ingredients, ethanol_ml


def rate_formula(name: str, formula_text: str) -> Tuple[Dict[str, float], StarRatings, Dict[str, float], FormulaVector, object]:
    """Rate a single formula using both star ratings and scores."""
    # Parse formula (now returns dilutions too)
    ingredients_pct, dilutions, ingredient_amounts, ethanol_ml = parse_formula_from_text(formula_text)
    if not ingredients_pct:
        raise ValueError(f"Failed to parse formula: {name}")
    
    # Create formula vector with dilution data
    fv = FormulaVector(ingredients=ingredients_pct, dilutions=dilutions)
    
    # Compute 0-100 scores (technical)
    scorer = FormulaScorer()
    scores = scorer.score(fv)
    
    # Compute character radar (for star rating inputs)
    character_radar = scorer.formula_character_radar(fv)
    
    # Compute 10-star ratings (consumer)
    stars = compute_star_ratings(fv, scores, character_radar)

    synergy_graph = SynergyGraph()
    synergy_graph.build()
    life_graph = build_chemical_life_graph(
        name,
        ingredient_amounts,
        ethanol_ml=ethanol_ml,
        style="classical",
        synergy_graph=synergy_graph,
    )
    
    return scores, stars, character_radar, fv, life_graph


def format_comparison_table(ratings: List[Dict]) -> str:
    """Generate comparison table for all formulas (both stars and scores)."""
    lines = []
    lines.append("=" * 120)
    lines.append("  COMPREHENSIVE FORMULA COMPARISON — All Ratings")
    lines.append("=" * 120)
    lines.append("")
    
    # Table header
    lines.append("  10-STAR RATINGS (Consumer/Wearability)")
    lines.append("  " + "-" * 116)
    header = f"{'Formula':<30s} {'Wear':>5s} {'Vers':>5s} {'Orig':>5s} {'Soph':>5s} {'Sig':>5s} {'Mass':>5s} {'Gend':>5s} {'Age':>5s} {'Val':>5s} {'⭐AVG':>6s}"
    lines.append(header)
    lines.append("  " + "-" * 116)
    
    for r in ratings:
        stars = r["stars"].as_dict()
        row = f"{r['name']:<30s} "
        row += f"{stars['wearability']:5.1f} "
        row += f"{stars['versatility']:5.1f} "
        row += f"{stars['originality']:5.1f} "
        row += f"{stars['sophistication']:5.1f} "
        row += f"{stars['signature_potential']:5.1f} "
        row += f"{stars['mass_appeal']:5.1f} "
        row += f"{stars['gender_versatility']:5.1f} "
        row += f"{stars['age_range']:5.1f} "
        row += f"{stars['value_for_money']:5.1f} "
        row += f"{r['stars'].average():6.2f}"
        lines.append(row)
    
    lines.append("")
    lines.append("  0-100 SCORES (Technical/Compositional)")
    lines.append("  " + "-" * 124)
    header = f"{'Formula':<30s} {'Long':>5s} {'Sill':>5s} {'Bal':>5s} {'Theo':>5s} {'Rad':>5s} {'Text':>5s} {'Cplx':>5s} {'ChrB':>5s} {'Syn':>5s} {'Hlt':>5s} {'Cost':>5s} {'▣GEO':>6s}"
    lines.append(header)
    lines.append("  " + "-" * 124)
    
    for r in ratings:
        scores = r["scores"]
        row = f"{r['name']:<30s} "
        row += f"{scores['longevity']:5.1f} "
        row += f"{scores['sillage']:5.1f} "
        row += f"{scores['balance']:5.1f} "
        row += f"{scores['theory']:5.1f} "
        row += f"{scores['radiance']:5.1f} "
        row += f"{scores['texture']:5.1f} "
        row += f"{scores['complexity']:5.1f} "
        row += f"{scores['character_balance']:5.1f} "
        row += f"{scores['synergy']:5.1f} "
        row += f"{r['life_graph'].health_score:5.1f} "
        row += f"{scores['cost']:5.1f} "
        row += f"{scores['geometric_total']:6.1f}"
        lines.append(row)
    
    return "\n".join(lines)


def format_insights(ratings: List[Dict]) -> str:
    """Generate insights document analyzing strengths/weaknesses."""
    lines = []
    lines.append("=" * 80)
    lines.append("  FORMULA INSIGHTS — Strengths & Weaknesses Analysis")
    lines.append("=" * 80)
    lines.append("")
    
    # Find best/worst in each star category
    star_categories = ["wearability", "versatility", "originality", "sophistication",
                       "signature_potential", "mass_appeal", "gender_versatility",
                       "age_range", "value_for_money"]
    
    lines.append("  ★ HIGHEST STAR RATINGS (Consumer Appeal)")
    lines.append("  " + "-" * 76)
    for cat in star_categories:
        best = max(ratings, key=lambda r: r["stars"].as_dict()[cat])
        best_val = best["stars"].as_dict()[cat]
        cat_display = cat.replace("_", " ").title()
        lines.append(f"    {cat_display:<25s} {best['name']:<35s} {best_val:.1f}★")
    
    lines.append("")
    lines.append("  ▣ HIGHEST SCORES (Technical Excellence)")
    lines.append("  " + "-" * 76)
    score_categories = ["longevity", "sillage", "balance", "theory", "radiance",
                        "texture", "complexity", "character_balance", "synergy"]
    for cat in score_categories:
        best = max(ratings, key=lambda r: r["scores"][cat])
        best_val = best["scores"][cat]
        lines.append(f"    {cat.title():<25s} {best['name']:<35s} {best_val:.1f}/100")
    best_health = max(ratings, key=lambda r: r["life_graph"].health_score)
    lines.append(f"    {'Health':<25s} {best_health['name']:<35s} {best_health['life_graph'].health_score:.1f}/100")
    
    lines.append("")
    lines.append("  ⚠️ LOWEST STAR RATINGS (Improvement Opportunities)")
    lines.append("  " + "-" * 76)
    for cat in star_categories:
        worst = min(ratings, key=lambda r: r["stars"].as_dict()[cat])
        worst_val = worst["stars"].as_dict()[cat]
        cat_display = cat.replace("_", " ").title()
        lines.append(f"    {cat_display:<25s} {worst['name']:<35s} {worst_val:.1f}★")
    
    lines.append("")
    lines.append("  ⚠️ LOWEST SCORES (Technical Weaknesses)")
    lines.append("  " + "-" * 76)
    for cat in score_categories:
        worst = min(ratings, key=lambda r: r["scores"][cat])
        worst_val = worst["scores"][cat]
        lines.append(f"    {cat.title():<25s} {worst['name']:<35s} {worst_val:.1f}/100")
    worst_health = min(ratings, key=lambda r: r["life_graph"].health_score)
    lines.append(f"    {'Health':<25s} {worst_health['name']:<35s} {worst_health['life_graph'].health_score:.1f}/100")
    
    # Overall champions
    lines.append("")
    lines.append("  🏆 OVERALL CHAMPIONS")
    lines.append("  " + "-" * 76)
    best_star_overall = max(ratings, key=lambda r: r["stars"].average())
    best_score_overall = max(ratings, key=lambda r: r["scores"]["geometric_total"])
    lines.append(f"    Highest Star Rating (Consumer):  {best_star_overall['name']:<35s} {best_star_overall['stars'].average():.2f}★")
    lines.append(f"    Highest Score (Technical):        {best_score_overall['name']:<35s} {best_score_overall['scores']['geometric_total']:.1f}/100")
    
    # Perfect balance (high in both)
    combined_scores = [(r["name"], r["stars"].average() * 10 + r["scores"]["geometric_total"]) for r in ratings]
    best_overall = max(combined_scores, key=lambda x: x[1])
    lines.append(f"    Best Overall (Combined):          {best_overall[0]:<35s} {best_overall[1]:.1f}")
    
    return "\n".join(lines)


def main():
    # Read original formulas
    formulas_file = Path("luxury_formulas_2026-03-26.md")
    if not formulas_file.exists():
        print(f"❌ Formula file not found: {formulas_file}")
        sys.exit(1)
    
    content = formulas_file.read_text(encoding="utf-8")
    
    # Split into individual formulas
    formula_blocks = content.split("##")[1:]  # Skip intro
    
    ratings = []
    individual_reports = []
    
    print("=" * 80)
    print("  COMPREHENSIVE FORMULA RATING — 9 Luxury Perfumes")
    print("=" * 80)
    print("")
    print("  Rating system:")
    print("    ★ 10-star ratings (wearability, versatility, originality, etc.)")
    print("    ▣ 0-100 scores (longevity, sillage, balance, complexity, etc.)")
    print("")
    print("  Loading inventory for optimization recommendations...")
    inventory = load_inventory()
    print(f"  ✅ {len(inventory)} materials loaded")
    print("")
    print("  Processing formulas...")
    print("")
    
    for i, block in enumerate(formula_blocks, 1):
        if not block.strip():
            continue
        
        # Extract formula name
        lines_in_block = block.strip().split("\n")
        name = lines_in_block[0].strip()
        
        # Skip non-formula sections (no ingredient table)
        if "| #" not in block or "µL" not in block:
            continue
        
        print(f"  [{i}/9] {name}...", end=" ")
        
        try:
            # Rate formula
            scores, stars, character_radar, fv, life_graph = rate_formula(name, block)
            
            # Store results
            ratings.append({
                "name": name,
                "scores": scores,
                "stars": stars,
                "character_radar": character_radar,
                "fv": fv,
                "life_graph": life_graph,
            })
            
            # Generate individual report
            report = format_comprehensive_report(name, fv, scores, stars, character_radar)
            report += "\n\n## Chemical Life Graph\n\n"
            report += f"- Health score: {life_graph.health_score:.1f}/100\n"
            report += f"- Overall synergy: {life_graph.synergy_report.overall_synergy:+.3f}\n"
            if life_graph.weight_diagnosis.overweight:
                dim, excess = life_graph.weight_diagnosis.overweight[0]
                report += f"- Main overweight dimension: {dim} (+{excess:.1f})\n"
            if life_graph.weight_diagnosis.underweight:
                dim, deficit = life_graph.weight_diagnosis.underweight[0]
                report += f"- Main underweight dimension: {dim} (-{deficit:.1f})\n"
            if life_graph.musk_analysis.recommended:
                musk, score, reason = life_graph.musk_analysis.recommended[0]
                report += f"- Best recommended musk: {musk} ({score:+.3f}) - {reason}\n"
            
            # Generate optimization recommendations
            recs = generate_recommendations(fv, scores, inventory)
            rec_text = format_recommendations(name, recs, scores)
            report += "\n\n" + rec_text
            
            individual_reports.append(report)
            
            print(
                f"✅ {stars.average():.1f}★ / {scores['geometric_total']:.1f}/100 / "
                f"H{life_graph.health_score:.0f}"
            )
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    # Generate comparison table
    print("")
    print("  Generating comparison table...")
    comparison = format_comparison_table(ratings)
    
    # Generate insights
    print("  Generating insights...")
    insights = format_insights(ratings)
    
    # Generate system comparison doc
    print("  Generating rating system comparison...")
    system_comparison = compare_rating_systems()
    
    # Write outputs
    output_dir = Path(".")
    
    # Individual reports
    reports_file = output_dir / "formula_ratings_detailed.md"
    with open(reports_file, "w", encoding="utf-8") as f:
        f.write("# Comprehensive Formula Ratings — Detailed Reports\n\n")
        f.write("**Generated:** March 28, 2026  \n")
        f.write("**System:** Dual rating (10-star + 0-100 scores)  \n")
        f.write("**Formulas:** 9 luxury perfumes\n\n")
        f.write("---\n\n")
        for report in individual_reports:
            f.write(report + "\n\n")
    
    # Comparison table
    comparison_file = output_dir / "formula_ratings_comparison.md"
    with open(comparison_file, "w", encoding="utf-8") as f:
        f.write("# Formula Ratings Comparison Table\n\n")
        f.write("**Generated:** March 28, 2026  \n")
        f.write("**System:** Dual rating (10-star + 0-100 scores)  \n\n")
        f.write("**Legend:**\n")
        f.write("- **Wear** = Wearability, **Vers** = Versatility, **Orig** = Originality\n")
        f.write("- **Soph** = Sophistication, **Sig** = Signature Potential, **Mass** = Mass Appeal\n")
        f.write("- **Gend** = Gender Versatility, **Age** = Age Range, **Val** = Value for Money\n")
        f.write("- **⭐AVG** = Overall star rating (mean of all 10 characteristics)\n")
        f.write("- **Long** = Longevity, **Sill** = Sillage, **Bal** = Balance, **Theo** = Theory\n")
        f.write("- **Rad** = Radiance, **Text** = Texture, **Cplx** = Complexity, **ChrB** = Character Balance\n")
        f.write("- **Syn** = Synergy, **Hlt** = Chemical life health, **Cost** = Cost (inverted), **▣GEO** = Geometric mean composite\n\n")
        f.write("---\n\n")
        f.write(comparison + "\n")
    
    # Insights
    insights_file = output_dir / "formula_ratings_insights.md"
    with open(insights_file, "w", encoding="utf-8") as f:
        f.write("# Formula Ratings Insights\n\n")
        f.write("**Generated:** March 28, 2026  \n")
        f.write("**Analysis:** Strengths & weaknesses across all formulas\n\n")
        f.write("---\n\n")
        f.write(insights + "\n")
    
    # System comparison
    system_file = output_dir / "rating_system_comparison.md"
    with open(system_file, "w", encoding="utf-8") as f:
        f.write(system_comparison)
    
    print("")
    print("=" * 80)
    print("  ✅ COMPLETE")
    print("=" * 80)
    print("")
    print(f"  Generated files:")
    print(f"    📄 {reports_file.name} — Detailed individual reports")
    print(f"    📊 {comparison_file.name} — Comparison table")
    print(f"    💡 {insights_file.name} — Strengths/weaknesses analysis")
    print(f"    📖 {system_file.name} — Rating system methodology")
    print("")


if __name__ == "__main__":
    main()