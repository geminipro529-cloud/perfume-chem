"""Diagnose the texture axis: why didn't v7i (cushion 720 µL) move texture vs v7h (cushion 270 µL)?

Reads v7h and v7i snapshots, replays the score_texture pipeline component-by-component:
  dims (weighted character) → derived axes (round/crisp/dry/silky/harsh)
  → coherence(35) + richness(25) + fit(20) + balance(20)
  → detected style (drives `fit`)

Prints a side-by-side table so we can see exactly which sub-component is flat / wrong.
"""

from __future__ import annotations
import json
import sys

sys.path.insert(0, ".")

from engine.optimizer.scoring import FormulaScorer, DIMENSIONS
from engine.optimizer.models import ObjectiveWeights
from engine.synergy_graph import SynergyGraph
from engine.ingredient_intelligence import get_profile
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from _scale_30mL_verify_nonlinear import score_formula

scorer = FormulaScorer(synergy_graph=SynergyGraph(), weights=ObjectiveWeights())


def replay_texture(ing, dil, label):
    """Recompute texture sub-components verbatim from scoring.py:1317."""
    geo, detail = score_formula(ing, dil, scorer)

    # We need a FormulaVector to call detect_style + effective_ingredients.
    # Build it the same way score_formula does internally.
    total_ul = sum(ing.values())
    fi = FormulaInfo(number=0, name=label, ingredients=ing, dilutions=dil,
                     concentrate_ml=total_ul / 1000.0, description="")
    fv = formula_to_vector(fi)

    eff = fv.effective_ingredients()
    dim_sums = {d: 0.0 for d in DIMENSIONS}
    total_pct = 0.0
    contrib_by_dim: dict[str, list[tuple[str, float]]] = {d: [] for d in DIMENSIONS}
    for name, pct in eff.items():
        prof = get_profile(name)
        if not prof:
            continue
        for d in DIMENSIONS:
            v = prof.character.get(d, 0) * pct
            dim_sums[d] += v
            if v > 0.001:
                contrib_by_dim[d].append((name, v))
        total_pct += pct
    dims = {d: v / total_pct for d, v in dim_sums.items()} if total_pct else {d: 0 for d in DIMENSIONS}

    roundness = (dims.get("creamy", 0) + dims.get("warmth", 0) + dims.get("sweetness", 0) * 0.5) / 2.5
    crispness = (dims.get("freshness", 0) + dims.get("transparency", 0) + dims.get("green", 0) * 0.5) / 2.5
    dryness   = (dims.get("woody", 0) + dims.get("smoky", 0) * 0.7 - dims.get("creamy", 0) * 0.3)
    silkiness = (dims.get("floral", 0) * 0.6 + dims.get("creamy", 0) * 0.4 + dims.get("transparency", 0) * 0.3)
    harshness = (dims.get("spicy", 0) * 0.5 + dims.get("animalic", 0) * 0.5 + dims.get("smoky", 0) * 0.3)

    roundness = max(0, min(roundness, 10))
    crispness = max(0, min(crispness, 10))
    dryness   = max(0, min(dryness, 10))
    silkiness = max(0, min(silkiness, 10))
    harshness = max(0, min(harshness, 10))

    rc_tension = abs(roundness - crispness)
    sh_tension = abs(silkiness - harshness)
    coherence = 35.0
    if rc_tension > 5: coherence -= (rc_tension - 5) * 3
    if sh_tension > 4: coherence -= (sh_tension - 4) * 3
    coherence = max(0, coherence)

    tactile = [roundness, crispness, dryness, silkiness]
    active_facets = sum(1 for f in tactile if f > 2.0)
    richness = min(active_facets * 7, 25)

    style = scorer.detect_style(fv)
    fit = 10.0
    if style in ("oriental", "gourmand"):
        fit = min(20, roundness * 2.5) if roundness > 2 else 5
    elif style in ("fresh", "citrus", "aquatic", "cologne"):
        fit = min(20, crispness * 2.5) if crispness > 2 else 5
    elif style in ("woody", "leather", "chypre"):
        fit = min(20, max(dryness, 0) * 2.5) if dryness > 1 else 5
    elif style == "iris_crystalline":
        fit = min(20, crispness * 2.5) if crispness > 2 else 5
    elif style in ("floral", "white_floral", "rose_oud", "soliflore", "iris_powdery"):
        fit = min(20, silkiness * 2.5) if silkiness > 2 else 5
    elif style in ("skin_scent", "linear"):
        smoothness = (roundness + silkiness - harshness) / 2
        fit = min(20, smoothness * 3.0) if smoothness > 1.5 else 5

    balance = 15.0
    if style in ("floral", "white_floral", "fresh", "skin_scent",
                 "soliflore", "iris_powdery", "iris_crystalline"):
        if harshness > 3: balance -= (harshness - 3) * 3
    elif style in ("leather", "woody", "chypre"):
        if 1.5 < harshness < 4: balance = 20
    if harshness > 6: balance -= (harshness - 6) * 4
    balance = max(0, min(balance, 20))

    score = coherence + richness + fit + balance

    print(f"\n========== {label} ==========")
    print(f"  geo (overall)     : {geo:.3f}")
    print(f"  texture (engine)  : {detail.get('texture', '?')}")
    print(f"  texture (replay)  : {round(score,1)}")
    print(f"  detected style    : {style}")
    print(f"  -- character dims (weighted by effective %) --")
    for d in DIMENSIONS:
        print(f"    {d:18s} {dims.get(d,0):6.3f}")
    print(f"  -- derived tactile axes (clamped 0..10) --")
    print(f"    roundness  {roundness:5.2f}   crispness  {crispness:5.2f}   dryness    {dryness:5.2f}")
    print(f"    silkiness  {silkiness:5.2f}   harshness  {harshness:5.2f}")
    print(f"  -- sub-components --")
    print(f"    coherence  {coherence:5.1f} / 35   (rc_tension {rc_tension:.2f}, sh_tension {sh_tension:.2f})")
    print(f"    richness   {richness:5.1f} / 25   (active facets > 2.0: {active_facets})")
    print(f"    fit        {fit:5.1f} / 20   (style→{style})")
    print(f"    balance    {balance:5.1f} / 20")
    print(f"    TOTAL      {score:5.1f} / 100")

    # Top contributors to the silkiness-feeding dims
    print(f"  -- top contributors to silkiness ingredients (floral/creamy/transparency) --")
    for d in ("floral", "creamy", "transparency"):
        rows = sorted(contrib_by_dim[d], key=lambda x: -x[1])[:6]
        if rows:
            print(f"    [{d}]")
            for name, v in rows:
                print(f"      {name:35s}  {v:6.3f}")

    return {
        "label": label, "geo": geo, "texture_engine": detail.get("texture"),
        "style": style, "dims": dims,
        "roundness": roundness, "crispness": crispness, "dryness": dryness,
        "silkiness": silkiness, "harshness": harshness,
        "coherence": coherence, "richness": richness, "fit": fit, "balance": balance,
    }


def main():
    with open("_opt_v7h_ifra_iris.json", encoding="utf-8") as f:
        h = json.load(f)["v7h"]
    with open("_opt_v7i_cushion_floor.json", encoding="utf-8") as f:
        i = json.load(f)["v7i"]

    rh = replay_texture(h["ing"], h["dil"], "v7h")
    ri = replay_texture(i["ing"], i["dil"], "v7i")

    print("\n========== SIDE-BY-SIDE Δ ==========")
    print(f"  {'metric':22s}  {'v7h':>8s}  {'v7i':>8s}  {'Δ':>8s}")
    for k in ("texture_engine", "roundness", "crispness", "dryness", "silkiness", "harshness",
              "coherence", "richness", "fit", "balance"):
        a, b = rh[k], ri[k]
        if a is None or b is None: continue
        print(f"  {k:22s}  {a:8.2f}  {b:8.2f}  {b-a:+8.2f}")
    print(f"  style v7h={rh['style']}   style v7i={ri['style']}")


if __name__ == "__main__":
    main()
