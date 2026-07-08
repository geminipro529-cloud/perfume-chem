"""Multi-seed iterative convergence optimizer for the two 15 mL formulas.

Runs hill-climbing from each seed formula, using 3 different random shuffles
of the candidate/move order per formula. Iterates until geometric-mean delta
between passes drops below EPSILON.

Axes optimized (user-requested): depth (stacking_depth), sillage, luxury,
texture, longevity, photorealism, plus perceptual_clarity and skin_performance
as quality floors.
"""
from __future__ import annotations
import sys, math, random, io, time, copy
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.optimizer.scoring import FormulaScorer
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph

BATCH_ML = 15.0
EPSILON = 0.03          # stop when geo delta < 0.03 for a full pass
MAX_PASSES = 12

AXIS_WEIGHTS = {
    "longevity": 1.0,
    "sillage": 1.0,
    "luxury": 1.0,
    "texture": 1.0,
    "stacking_depth": 1.0,   # user's "depth"
    "photorealism": 1.0,
    "perceptual_clarity": 0.6,
    "skin_performance": 0.6,
    "synergy": 0.5,
    "hedonic": 0.4,
}
WSUM = sum(AXIS_WEIGHTS.values())


# ═══════════════════════════════════════════════════════════════════
# SEED 1: Photorealistic Iris 15 mL half
# ═══════════════════════════════════════════════════════════════════
IRIS_SEED = {
    "Bergamot FCF oil Sicilian": 100, "Grapefruit FCF": 30, "Leafovert": 4,
    "Ethyl Linalool": 70, "Dihydromyrcenol": 50, "Allyl Amyl Glycolate": 10,
    "Scentenal": 12,
    "Alpha Irone": 250, "Myristic Acid": 750, "Alpha Ionone": 40, "Beta Ionone": 25,
    "Allyl Ionone": 15, "Alpha Isomethyl Ionone": 90, "Dihydro Beta Ionone": 20,
    "Irotyl": 30, "Orivone": 60, "Hedione": 325, "Hedione HC": 40, "Cis Jasmone": 10,
    "Carrot Seed EO": 30, "Ultralia": 40, "Cyclamen Aldehyde": 15, "Farnesol": 5,
    "Violet Fleuressence": 15, "Heliotropal": 40, "Musk Ketone": 100,
    "Koavone": 100, "Azarbre": 50, "Ebanol": 115, "Iso E Super": 140,
    "Habanolide": 275, "Ethylene Brassylate": 190, "Exaltolide": 150,
    "Ambrettolide": 125, "Romandolide": 60, "Ambrox Super": 50, "IPM": 250,
}
IRIS_DIL = {
    "Alpha Irone": 0.30, "Scentenal": 0.01, "Myristic Acid": 0.20,
    "Musk Ketone": 0.10, "Exaltolide": 0.10, "Ambrettolide": 0.10,
    "Ambrox Super": 0.30,
}

# ═══════════════════════════════════════════════════════════════════
# SEED 2: Iris-Jasmine 15 mL
# ═══════════════════════════════════════════════════════════════════
IJ_SEED = {
    "Bergamot FCF oil Sicilian": 140, "Methyl Pamplemousse": 30, "Leafovert": 4,
    "Allyl Amyl Glycolate": 8, "Ethyl Linalool": 48, "Alpha Irone": 280,
    "Alpha Ionone": 35, "Beta Ionone": 15, "Alpha Isomethyl Ionone": 120,
    "Irotyl": 35, "Orivone": 55, "Ultralia": 35, "Myristic Acid": 500,
    "Hedione": 620, "Hedione HC": 95, "Indole": 8, "Methyl Benzoate": 25,
    "Benzyl Acetate": 80, "Amyl Cinnamic Aldehyde": 15, "Cis Jasmone": 15,
    "Paradisamide": 5, "Jasmine FO": 35, "Ylang Extra EO": 35,
    "Carrot Seed EO": 20, "Farnesol": 6, "Violet Fleuressence": 15,
    "Benzyl Salicylate": 220, "Hexyl Salicylate": 90, "Ebanol": 115,
    "Koavone": 80, "Azarbre": 60, "Iso E Super": 130,
    "Ethylene Brassylate": 260, "Romandolide": 95, "Musk Ketone": 150,
    "Exaltolide": 180, "Ambrettolide": 140, "Ambrox Super": 40, "IPM": 250,
    "Benzyl Benzoate": 80,
}
IJ_DIL = {
    "Alpha Irone": 0.30, "Myristic Acid": 0.20, "Methyl Pamplemousse": 0.10,
    "Indole": 0.10, "Paradisamide": 0.10, "Musk Ketone": 0.10,
    "Exaltolide": 0.10, "Ambrettolide": 0.10, "Ambrox Super": 0.30,
}

# ═══════════════════════════════════════════════════════════════════
# MOVE SET — additions/deletions/adjustments (µL)
# Each move = (material_name, delta_ul, dilution_or_None)
# Positive delta = add/increase. Negative = decrease.
# ═══════════════════════════════════════════════════════════════════
# Axis-relevant candidates only (iris / jasmine / musk / fixative / structure)
CANDIDATE_MATERIALS = [
    # Iris-axis
    ("Alpha Irone", 0.30), ("Alpha Ionone", None), ("Beta Ionone", None),
    ("Alpha Isomethyl Ionone", None), ("Allyl Ionone", None),
    ("Dihydro Beta Ionone", None), ("Irotyl", None), ("Orivone", None),
    ("Ultralia", None), ("Koavone", None), ("Carrot Seed EO", None),
    ("Violet Fleuressence", None),
    # Jasmine / white-floral
    ("Hedione", None), ("Hedione HC", None), ("Benzyl Acetate", None),
    ("Methyl Benzoate", None), ("Cis Jasmone", None), ("Indole", 0.10),
    ("Paradisamide", 0.10), ("Jasmine FO", None), ("Ylang Extra EO", None),
    ("Amyl Cinnamic Aldehyde", None), ("Farnesol", None),
    # Lift / freshness
    ("Bergamot FCF oil Sicilian", None), ("Grapefruit FCF", None),
    ("Methyl Pamplemousse", 0.10), ("Leafovert", None),
    ("Ethyl Linalool", None), ("Allyl Amyl Glycolate", None),
    ("Scentenal", 0.01), ("Dihydromyrcenol", None), ("Cyclamen Aldehyde", None),
    ("Heliotropal", None),
    # Structure / skin
    ("Iso E Super", None), ("Azarbre", None), ("Ebanol", None),
    ("Cashmeran", 0.20),
    # Musk chord (depth/projection/echo axes)
    ("Ethylene Brassylate", None), ("Romandolide", None),
    ("Musk Ketone", 0.10), ("Exaltolide", 0.10), ("Ambrettolide", 0.10),
    ("Habanolide", None), ("Zenolide", None),
    # Amber / fixative
    ("Ambrox Super", 0.30), ("Amberwood F", None), ("Ambermax", 0.10),
    # Fixative / cushion
    ("Benzyl Salicylate", None), ("Hexyl Salicylate", None),
    ("Benzyl Benzoate", None), ("IPM", None), ("Myristic Acid", 0.20),
]

# Step sizes tried per move
STEPS = (+60, +30, +15, -15, -30, -60)


def geo_score(ing: dict, dil: dict, scorer: FormulaScorer) -> tuple[float, dict]:
    total_ul = sum(ing.values())
    fi = FormulaInfo(number=0, name="X", ingredients=ing, dilutions=dil,
                     concentrate_ml=total_ul / 1000, description="")
    fv = formula_to_vector(fi)
    s = scorer.score(fv)
    log_sum = 0.0
    for a, w in AXIS_WEIGHTS.items():
        v = max(float(s.get(a, 5.0)), 5.0)
        log_sum += (w / WSUM) * math.log(v)
    return round(math.exp(log_sum), 3), s


def enumerate_moves(ing: dict, dil: dict, rng: random.Random):
    """Yield candidate (material, new_ul, dilution_or_None) moves."""
    moves = []
    for name, material_dil in CANDIDATE_MATERIALS:
        current = ing.get(name, 0)
        for step in STEPS:
            new = current + step
            if new < 0:
                continue
            if 0 < new < 1:   # pipette floor
                continue
            if new > 800:     # cap any single material at 800 µL (5.3%)
                continue
            if new == current:
                continue
            moves.append((name, new, material_dil))
    rng.shuffle(moves)
    return moves


def hill_climb(seed_ing: dict, seed_dil: dict, scorer: FormulaScorer,
               seed_rng: int, label: str) -> tuple[dict, dict, float, dict]:
    rng = random.Random(seed_rng)
    ing = dict(seed_ing)
    dil = dict(seed_dil)
    geo, detail = geo_score(ing, dil, scorer)
    print(f"  [{label} seed={seed_rng}] baseline geo={geo}")
    prev = geo
    for p in range(1, MAX_PASSES + 1):
        moves = enumerate_moves(ing, dil, rng)
        best = None  # (new_geo, name, new_ul, mat_dil)
        for name, new_ul, mat_dil in moves:
            trial_ing = dict(ing)
            trial_dil = dict(dil)
            if new_ul == 0:
                trial_ing.pop(name, None)
                trial_dil.pop(name, None)
            else:
                trial_ing[name] = new_ul
                if mat_dil is not None:
                    trial_dil[name] = mat_dil
            # Concentrate budget: 15–30% of 15 mL = 2250–4500 µL
            tot = sum(trial_ing.values())
            if tot > 4500 or tot < 2250:
                continue
            g, _ = geo_score(trial_ing, trial_dil, scorer)
            if best is None or g > best[0]:
                best = (g, name, new_ul, mat_dil)
        if best is None:
            print(f"    pass {p}: no valid moves")
            break
        new_geo, name, new_ul, mat_dil = best
        delta = new_geo - prev
        if delta <= EPSILON:
            print(f"    pass {p}: best move {name}->{new_ul} geo={new_geo} Δ={delta:+.3f} (below ε) STOP")
            break
        if new_ul == 0:
            ing.pop(name, None)
            dil.pop(name, None)
        else:
            ing[name] = new_ul
            if mat_dil is not None:
                dil[name] = mat_dil
        print(f"    pass {p}: {name} -> {new_ul} µL  geo={new_geo}  Δ={delta:+.3f}")
        prev = new_geo
    final_geo, final_detail = geo_score(ing, dil, scorer)
    return ing, dil, final_geo, final_detail


def run(label: str, seed_ing: dict, seed_dil: dict, scorer: FormulaScorer,
        seeds=(1, 42, 2026)):
    print(f"\n═══ {label} ═══")
    best = None
    for s in seeds:
        ing, dil, geo, detail = hill_climb(seed_ing, seed_dil, scorer, s, label)
        if best is None or geo > best[2]:
            best = (ing, dil, geo, detail)
    ing, dil, geo, detail = best
    print(f"\n  >>> BEST {label}: geo={geo}")
    for a in AXIS_WEIGHTS:
        print(f"      {a:22s} {detail[a]:.1f}")
    print(f"      concentrate µL = {sum(ing.values())}")
    return best


if __name__ == "__main__":
    t0 = time.time()
    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    iris_best = run("PHOTOREALISTIC IRIS 15mL", IRIS_SEED, IRIS_DIL, scorer)
    ij_best = run("IRIS-JASMINE 15mL", IJ_SEED, IJ_DIL, scorer)

    import json
    out = {
        "iris": {"ingredients": iris_best[0], "dilutions": iris_best[1],
                 "geo": iris_best[2], "detail": {k: iris_best[3][k] for k in AXIS_WEIGHTS}},
        "iris_jasmine": {"ingredients": ij_best[0], "dilutions": ij_best[1],
                         "geo": ij_best[2], "detail": {k: ij_best[3][k] for k in AXIS_WEIGHTS}},
    }
    Path("_opt_convergence_out.json").write_text(json.dumps(out, indent=2))
    print(f"\n[elapsed {time.time()-t0:.1f}s]  wrote _opt_convergence_out.json")
