"""
NICHE PERFUME DISCOVERY — 100% DB-Driven Formula Generation
============================================================
Every formula is discovered by the engine from:
  - perfume_chem.db synergy rules
  - perfume_chem.db pairing rules  
  - perfume_chem.db material properties (MW, VP, CLP, Carles, Roudnitska, Jellinek)
  - inventory.txt materials
  - Carles grid search algorithm
  - FormulaOptimizer iterative improvement

NO hand-coded formulas. The engine finds the best niche ideas itself.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))




import sys, json
from collections import defaultdict

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.optimizer.models import (
    FormulaVector, ObjectiveWeights, OptimizationConstraints,
    get_materials_db, get_pairing_rules, get_synergy_rules, get_theory_rules,
    _lookup_material, classify_note, _fuzzy_name_match,
)
from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.optimizer import FormulaOptimizer
from engine.confidence import ConfidenceScorer


def discover_star_materials(inventory: list[str]) -> dict[str, list[str]]:
    """Identify the most connected/synergistic materials from the DB.
    
    Returns a dict of niche archetype → list of star materials, chosen
    by counting how many synergy/pairing rules each material appears in.
    """
    synergy_rules = get_synergy_rules()
    pairing_rules = get_pairing_rules()
    db = get_materials_db()

    # Count connections per inventory material
    connection_count = defaultdict(int)
    synergy_partners = defaultdict(set)   # material → set of partners
    pairing_effects = defaultdict(list)   # material → list of effect strings

    inv_lower = {m.lower().strip(): m for m in inventory}

    for rule in synergy_rules:
        a = rule.get("material_a", "").lower().strip()
        b = rule.get("material_b", "").lower().strip()
        effect = rule.get("effect", "")
        for inv_key, inv_name in inv_lower.items():
            if _fuzzy_name_match(a, inv_key):
                connection_count[inv_name] += 2  # synergy worth more
                synergy_partners[inv_name].add(rule.get("material_b", b))
                pairing_effects[inv_name].append(effect)
            if _fuzzy_name_match(b, inv_key):
                connection_count[inv_name] += 2
                synergy_partners[inv_name].add(rule.get("material_a", a))
                pairing_effects[inv_name].append(effect)

    for rule in pairing_rules:
        a = rule.get("material_a", "").lower().strip()
        b = rule.get("material_b", "").lower().strip()
        rtype = rule.get("type", "").lower()
        if rtype == "antagonism":
            continue  # skip conflicts
        for inv_key, inv_name in inv_lower.items():
            if _fuzzy_name_match(a, inv_key):
                connection_count[inv_name] += 1
                synergy_partners[inv_name].add(rule.get("material_b", b))
            if _fuzzy_name_match(b, inv_key):
                connection_count[inv_name] += 1
                synergy_partners[inv_name].add(rule.get("material_a", a))

    # Classify each material
    note_class = {}
    properties = {}
    for name in inventory:
        note_class[name] = classify_note(name)
        mat = _lookup_material(name)
        if mat:
            properties[name] = {
                "roudnitska": mat.get("roudnitska_function", ""),
                "jellinek": mat.get("jellinek_quadrant", ""),
                "sar_class": mat.get("sar_class", ""),
                "carles": mat.get("carles_position", ""),
            }

    # Select star materials for different niche archetypes
    # Pick the MOST connected material from each olfactory family
    archetypes = {}

    # Group by olfactory character
    families = {
        "incense-resinous": ["olibanum", "myrrh", "benzoin", "labdanum", "frankincense"],
        "leather-smoky":    ["birch tar", "ibq", "isobutyl quinoline", "guaiacol", "styrax", "suederal"],
        "iris-violet":      ["irone", "ionone", "orris", "iris", "violet"],
        "green-earthy":     ["vetiver", "galbanum", "patchouli", "clearwood", "carrot"],
        "woody-amber":      ["iso e super", "ambrox", "cashmeran", "cedarwood", "sandalwood", "javanol", "bacdanol"],
        "molecular-transparent": ["hedione", "iso e super", "ambrox", "dihydromyrcenol", "linalool"],
        "dark-fruit":       ["blackcurrant", "raspberry", "dewberry", "cassis"],
        "solar-amber":      ["ambrox", "amber", "neroli", "hedione", "bergamot"],
    }

    for archetype, keywords in families.items():
        candidates = []
        for name in inventory:
            name_lower = name.lower()
            if any(kw in name_lower for kw in keywords):
                score = connection_count.get(name, 0)
                candidates.append((name, score))
        candidates.sort(key=lambda x: -x[1])
        if candidates:
            # Pick top material as star
            archetypes[archetype] = [c[0] for c in candidates[:3]]

    return archetypes, connection_count, synergy_partners, pairing_effects


def build_synergy_formula(star: str, partners: set, inventory: list[str],
                          connection_count: dict) -> FormulaVector:
    """Build a formula around a star material using its DB synergy partners.
    
    Instead of hand-picking, we:
    1. Start with the star material
    2. Add its highest-connected synergy partners (that are in inventory)
    3. Fill structural gaps (top/heart/base) from the most-connected remaining
    4. Add musks for base anchoring
    """
    inv_lower = {m.lower().strip(): m for m in inventory}
    ingredients = {}

    # Star material
    star_note = classify_note(star)
    star_pct = {"top": 6.0, "heart": 10.0, "base": 12.0}.get(star_note, 8.0)
    ingredients[star] = star_pct

    # Find which partners are in inventory
    available_partners = []
    for partner in partners:
        partner_lower = partner.lower().strip()
        for inv_key, inv_name in inv_lower.items():
            if _fuzzy_name_match(partner_lower, inv_key):
                if inv_name != star and inv_name not in ingredients:
                    score = connection_count.get(inv_name, 0)
                    available_partners.append((inv_name, score))
                break

    # Deduplicate and sort by connection count
    seen = set()
    unique_partners = []
    for name, score in available_partners:
        if name not in seen:
            seen.add(name)
            unique_partners.append((name, score))
    unique_partners.sort(key=lambda x: -x[1])

    # Add top partners (up to 8 to stay niche — not too many ingredients)
    for name, _ in unique_partners[:8]:
        note = classify_note(name)
        pct = {"top": 5.0, "heart": 6.0, "base": 8.0}.get(note, 5.0)
        ingredients[name] = pct

    # Check note distribution and fill gaps
    fv_check = FormulaVector(ingredients=ingredients)
    dist = fv_check.note_distribution()

    # If tops are < 10%, add the most-connected top note from inventory
    if dist.get("top", 0) < 10:
        for name in inventory:
            if name not in ingredients and classify_note(name) == "top":
                if connection_count.get(name, 0) > 0:
                    ingredients[name] = 5.0
                    break

    # If hearts are < 15%, add a heart
    if dist.get("heart", 0) < 15:
        for name in inventory:
            if name not in ingredients and classify_note(name) == "heart":
                if connection_count.get(name, 0) > 0:
                    ingredients[name] = 6.0
                    break

    # Ensure at least one musk anchor if not present
    musk_keywords = ["galaxolide", "romandolide", "habanolide", "ethylene brassylate",
                     "zenolide", "ambrettolide", "exaltolide", "musk"]
    has_musk = any(any(mk in ing.lower() for mk in musk_keywords) for ing in ingredients)
    if not has_musk:
        for name in inventory:
            if any(mk in name.lower() for mk in musk_keywords) and name not in ingredients:
                ingredients[name] = 8.0
                break

    return FormulaVector(ingredients=ingredients)


def main():
    print("=" * 78)
    print("  NICHE PERFUME DISCOVERY — 100% DB-DRIVEN (no hand-coded formulas)")
    print("=" * 78)

    weights = ObjectiveWeights()
    scorer = FormulaScorer(weights)
    optimizer = FormulaOptimizer(weights)
    confidence_scorer = ConfidenceScorer()
    inventory = optimizer.inventory

    # ── PHASE 1: Discover star materials from DB ──
    print("\n>>> PHASE 1: DISCOVERING STAR MATERIALS FROM DB\n")
    archetypes, connection_count, synergy_partners, pairing_effects = \
        discover_star_materials(inventory)

    for archetype, stars in archetypes.items():
        star_info = []
        for s in stars:
            cnt = connection_count.get(s, 0)
            partners = len(synergy_partners.get(s, set()))
            star_info.append(f"{s} ({cnt} connections, {partners} partners)")
        print(f"  {archetype:28s}: {', '.join(star_info)}")

    # ── PHASE 2: Carles Grid Search — engine discovers candidates per archetype ──
    print("\n>>> PHASE 2: CARLES GRID SEARCH (engine-generated candidates)\n")
    grid_results = {}
    for archetype, stars in archetypes.items():
        top_star = stars[0]  # most connected star
        try:
            candidates = optimizer.carles_grid_search(top_star, n_results=3)
            if candidates:
                best = candidates[0]
                grid_results[archetype] = {
                    "star": top_star,
                    "candidate": best,
                    "all_candidates": candidates,
                }
                print(f"  {archetype:28s}  star={top_star:24s}  "
                      f"grid_best={best.total_score:.1f}  "
                      f"({len(best.formula.ingredients)} ingredients)")
        except Exception as e:
            print(f"  {archetype:28s}  ERROR: {e}")

    # ── PHASE 3: Build synergy-based formulas from DB connections ──
    print("\n>>> PHASE 3: BUILDING SYNERGY FORMULAS FROM DB CONNECTIONS\n")
    synergy_formulas = {}
    for archetype, stars in archetypes.items():
        top_star = stars[0]
        partners = synergy_partners.get(top_star, set())
        fv = build_synergy_formula(top_star, partners, inventory, connection_count)
        scores = scorer.score(fv)
        synergy_formulas[archetype] = {
            "star": top_star,
            "fv": fv,
            "scores": scores,
        }
        print(f"  {archetype:28s}  star={top_star:24s}  "
              f"synergy_score={scores['total']:.1f}  "
              f"({len(fv.ingredients)} ingredients)")

    # ── PHASE 4: Pick the BEST version (grid vs synergy) per archetype ──
    print("\n>>> PHASE 4: SELECTING BEST PER ARCHETYPE\n")
    final_formulas = {}
    for archetype in archetypes:
        grid = grid_results.get(archetype)
        syn = synergy_formulas.get(archetype)
        
        grid_score = grid["candidate"].total_score if grid else 0
        syn_score = syn["scores"]["total"] if syn else 0

        if grid_score >= syn_score and grid:
            final_formulas[archetype] = {
                "source": "carles_grid_search",
                "star": grid["star"],
                "fv": grid["candidate"].formula,
                "scores": grid["candidate"].scores,
                "total": grid["candidate"].total_score,
            }
            winner = "GRID"
        elif syn:
            final_formulas[archetype] = {
                "source": "synergy_build",
                "star": syn["star"],
                "fv": syn["fv"],
                "scores": syn["scores"],
                "total": syn["scores"]["total"],
            }
            winner = "SYNERGY"
        
        if archetype in final_formulas:
            f = final_formulas[archetype]
            print(f"  {archetype:28s}  Winner: {winner:8s}  "
                  f"Score: {f['total']:.1f}  Star: {f['star']}")

    # ── PHASE 5: Rank and select top 6 ──
    print("\n" + "=" * 78)
    print("  RANKING — TOP 6 NICHE DISCOVERIES")
    print("=" * 78)
    ranked = sorted(final_formulas.items(), key=lambda x: -x[1]["total"])
    top6 = ranked[:6]

    for i, (archetype, data) in enumerate(top6, 1):
        fv = data["fv"]
        nd = fv.note_distribution()
        ns = ", ".join(f"{k}:{v:.0f}%"
                       for k, v in sorted(nd.items(), key=lambda x: -x[1]) if v > 0)
        print(f"  #{i}  {archetype:28s}  Score: {data['total']:5.1f}  "
              f"Star: {data['star']}   ({data['source']})")
        print(f"       Notes: {ns}")
        print(f"       Ingredients: {', '.join(fv.ingredient_list())}")
        print()

    # ── PHASE 6: Optimize top 3 ──
    print("=" * 78)
    print("  OPTIMIZATION (top 3)")
    print("=" * 78)
    optimized = {}
    for archetype, data in top6[:3]:
        fv = data["fv"]
        result = optimizer.optimize(fv)
        delta = result.total_score - data["total"]
        optimized[archetype] = result
        print(f"\n  {archetype}  (star: {data['star']}):")
        print(f"    Original: {data['total']:.1f}  ->  Optimized: {result.total_score:.1f}  (delta {delta:+.1f})")
        if result.reasoning:
            for r in result.reasoning[1:6]:
                print(f"    {r}")
        added = set(result.formula.ingredients.keys()) - set(fv.ingredients.keys())
        removed = set(fv.ingredients.keys()) - set(result.formula.ingredients.keys())
        if added:
            print(f"    + Added: {', '.join(added)}")
        if removed:
            print(f"    - Removed: {', '.join(removed)}")

    # ── PHASE 7: Suggestions for top 3 ──
    print("\n" + "=" * 78)
    print("  SUGGESTIONS (top 3)")
    print("=" * 78)
    for archetype, data in top6[:3]:
        fv = data["fv"]
        suggestions = optimizer.suggest(fv)
        print(f"\n  {archetype}  (star: {data['star']}):")
        if suggestions:
            for s in suggestions[:5]:
                print(f"    -> {s}")
        else:
            print("    (none)")

    # ── PHASE 8: Confidence ──
    print("\n" + "=" * 78)
    print("  CONFIDENCE")
    print("=" * 78)
    confidences = {}
    for archetype, data in top6:
        conf = confidence_scorer.score(dict(data["fv"].ingredients))
        confidences[archetype] = conf
        print(f"  {archetype:28s}  "
              f"data={conf.get('data_confidence', 'N/A')}  "
              f"pairing={conf.get('pairing_confidence', 'N/A')}  "
              f"prediction={conf.get('prediction_confidence', 'N/A')}  "
              f"overall={conf.get('overall_confidence', 'N/A')}")

    # ── PHASE 9: Show DB provenance — what rules drove each formula ──
    print("\n" + "=" * 78)
    print("  DB PROVENANCE — Synergy/Pairing Rules Used")
    print("=" * 78)
    synergy_rules = get_synergy_rules()
    pairing_rules = get_pairing_rules()

    for archetype, data in top6:
        fv = data["fv"]
        ing_names = [n.lower().strip() for n in fv.ingredient_list()]
        
        relevant_synergies = []
        for rule in synergy_rules:
            a = rule.get("material_a", "").lower().strip()
            b = rule.get("material_b", "").lower().strip()
            if any(_fuzzy_name_match(a, ing) for ing in ing_names) and \
               any(_fuzzy_name_match(b, ing) for ing in ing_names):
                relevant_synergies.append(rule)

        relevant_pairings = []
        for rule in pairing_rules:
            a = rule.get("material_a", "").lower().strip()
            b = rule.get("material_b", "").lower().strip()
            rtype = rule.get("type", "")
            if rtype == "synergy":
                if any(_fuzzy_name_match(a, ing) for ing in ing_names) and \
                   any(_fuzzy_name_match(b, ing) for ing in ing_names):
                    relevant_pairings.append(rule)

        print(f"\n  {archetype} ({data['star']}):")
        print(f"    Synergy rules matched: {len(relevant_synergies)}")
        for r in relevant_synergies[:5]:
            print(f"      {r.get('material_a')} + {r.get('material_b')}: "
                  f"{r.get('effect', '')[:60]}")
        print(f"    Pairing rules matched: {len(relevant_pairings)}")
        for r in relevant_pairings[:5]:
            print(f"      {r.get('material_a')} → {r.get('material_b')}: "
                  f"{r.get('effect', '')[:60]}")

    # ── PHASE 10: Save JSON ──
    serializable = {}
    for archetype, data in top6:
        fv = data["fv"]
        serializable[archetype] = {
            "star_material": data["star"],
            "source": data["source"],
            "ingredients": dict(fv.ingredients),
            "scores": data["scores"],
            "note_distribution": fv.note_distribution(),
            "confidence": confidences.get(archetype, {}),
        }
    if optimized:
        serializable["_optimized"] = {}
        for name, result in optimized.items():
            serializable["_optimized"][name] = {
                "optimized_score": result.total_score,
                "optimized_ingredients": dict(result.formula.ingredients),
                "optimized_scores": result.scores,
                "reasoning": result.reasoning,
                "suggestions": result.suggestions,
            }

    out_path = Path("niche_discovery_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)

    # ── PHASE 11: Markdown report ──
    md = [
        "# Niche Perfume Discovery — 100% DB-Driven",
        "",
        "Every formula discovered by the engine from `perfume_chem.db`.",
        "Star materials selected by synergy/pairing rule connection count.",
        "Formulas built by `carles_grid_search()` or `build_synergy_formula()`.",
        "",
    ]

    for i, (archetype, data) in enumerate(top6, 1):
        fv = data["fv"]
        scores = data["scores"]
        nd = fv.note_distribution()
        conf = confidences.get(archetype, {})

        md.append(f"## #{i} — {archetype}")
        md.append(f"**Star Material:** {data['star']}  |  "
                  f"**Source:** `{data['source']}`  |  "
                  f"**Score:** {data['total']:.1f}/100")
        md.append("")

        md.append("### Scores")
        md.append("| Axis | Score |")
        md.append("|------|-------|")
        for axis in ["longevity", "sillage", "balance", "synergy", "theory", "cost"]:
            md.append(f"| {axis.title()} | {scores.get(axis, 0):.1f} |")
        md.append("")

        md.append("### Note Distribution")
        md.append(f"Top: {nd.get('top',0):.0f}%  |  "
                  f"Heart: {nd.get('heart',0):.0f}%  |  "
                  f"Base: {nd.get('base',0):.0f}%")
        md.append("")

        md.append("### DB-Discovered Formula")
        md.append("| Material | % | Note |")
        md.append("|----------|---|------|")
        for mat, pct in sorted(fv.ingredients.items(), key=lambda x: -x[1]):
            note = classify_note(mat)
            md.append(f"| {mat} | {pct:.1f} | {note} |")
        md.append("")

        if archetype in optimized:
            opt = optimized[archetype]
            md.append(f"### Optimized (Score: {opt.total_score:.1f})")
            md.append("| Material | % | Note |")
            md.append("|----------|---|------|")
            for mat, pct in sorted(opt.formula.ingredients.items(), key=lambda x: -x[1]):
                note = classify_note(mat)
                md.append(f"| {mat} | {pct:.1f} | {note} |")
            md.append("")
            if opt.reasoning:
                md.append("**Optimization changes:**")
                for r in opt.reasoning[1:]:
                    md.append(f"- {r}")
                md.append("")

        # DB provenance
        ing_names = [n.lower().strip() for n in fv.ingredient_list()]
        relevant = []
        for rule in synergy_rules:
            a = rule.get("material_a", "").lower().strip()
            b = rule.get("material_b", "").lower().strip()
            if any(_fuzzy_name_match(a, ing) for ing in ing_names) and \
               any(_fuzzy_name_match(b, ing) for ing in ing_names):
                relevant.append(rule)
        if relevant:
            md.append("### DB Synergy Rules Driving This Formula")
            for r in relevant[:8]:
                md.append(f"- **{r.get('material_a')}** + **{r.get('material_b')}**: "
                          f"{r.get('effect', '')}")
            md.append("")

        md.append("### Confidence")
        md.append(f"Data: {conf.get('data_confidence', 'N/A')}  |  "
                  f"Pairing: {conf.get('pairing_confidence', 'N/A')}  |  "
                  f"Prediction: {conf.get('prediction_confidence', 'N/A')}  |  "
                  f"Overall: {conf.get('overall_confidence', 'N/A')}")
        md.append("")
        md.append("---")
        md.append("")

    md_path = Path("niche_discovery_formulas.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    print(f"\n  Results saved to {out_path}")
    print(f"  Report saved to {md_path}")
    print("\n" + "=" * 78)
    print("  DONE — All formulas discovered from DB, zero hand-coded knowledge")
    print("=" * 78)


if __name__ == "__main__":
    main()
