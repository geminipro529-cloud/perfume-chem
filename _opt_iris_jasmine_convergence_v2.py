"""Multi-seed iterative convergence optimizer for the two 15 mL formulas.

V2 adds:
 - OAV guard check (check_proportional_scaling 15 -> 30 mL) AT EVERY MOVE.
   Any move that would introduce an OAV error (pipette-floor violation when
   the half is merged back into a 30 mL whole) is rejected before scoring.
 - 3 seeds per formula.
 - Full convergence: iterate until best-move delta <= EPSILON.
 - JSON + Markdown output per formula.

Axes: depth (stacking_depth), sillage, luxury, texture, longevity, photorealism,
plus perceptual_clarity / skin_performance as quality floors.
"""
from __future__ import annotations
import sys, math, random, io, time, json, os
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
# Force unbuffered UTF-8 stdout that actually reaches disk on every newline.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True, write_through=True)
except Exception:
    sys.stdout = io.TextIOWrapper(os.fdopen(sys.stdout.fileno(), "wb", 0),
                                   encoding="utf-8", errors="replace",
                                   line_buffering=True, write_through=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.optimizer.scoring import FormulaScorer
from engine.optimizer.oav_guard import (
    check_proportional_scaling, check_batch_scaling, summarize,
)
from engine.formula_analyzer import FormulaInfo, formula_to_vector
from engine.synergy_graph import SynergyGraph

BATCH_ML = 15.0
TARGET_MERGE_ML = 30.0     # splits will be merged into 30 mL wholes later
EPSILON = 0.02             # stop when best-move delta < this for a full pass
MAX_PASSES = 15
SEEDS = (1, 42, 2026)

AXIS_WEIGHTS = {
    "longevity": 1.0, "sillage": 1.0, "luxury": 1.0, "texture": 1.0,
    "stacking_depth": 1.0, "photorealism": 1.0,
    "perceptual_clarity": 0.6, "skin_performance": 0.6,
    "synergy": 0.5, "hedonic": 0.4,
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

# Candidate moves. Material → default dilution if added anew.
CANDIDATE_MATERIALS = [
    ("Alpha Irone", 0.30), ("Alpha Ionone", None), ("Beta Ionone", None),
    ("Alpha Isomethyl Ionone", None), ("Allyl Ionone", None),
    ("Dihydro Beta Ionone", None), ("Irotyl", None), ("Orivone", None),
    ("Ultralia", None), ("Koavone", None), ("Carrot Seed EO", None),
    ("Violet Fleuressence", None),
    ("Hedione", None), ("Hedione HC", None), ("Benzyl Acetate", None),
    ("Methyl Benzoate", None), ("Cis Jasmone", None), ("Indole", 0.10),
    ("Paradisamide", 0.10), ("Jasmine FO", None), ("Ylang Extra EO", None),
    ("Amyl Cinnamic Aldehyde", None), ("Farnesol", None),
    ("Bergamot FCF oil Sicilian", None), ("Grapefruit FCF", None),
    ("Methyl Pamplemousse", 0.10), ("Leafovert", None),
    ("Ethyl Linalool", None), ("Allyl Amyl Glycolate", None),
    ("Scentenal", 0.01), ("Dihydromyrcenol", None), ("Cyclamen Aldehyde", None),
    ("Heliotropal", None),
    ("Iso E Super", None), ("Azarbre", None), ("Ebanol", None),
    ("Cashmeran", 0.20),
    ("Ethylene Brassylate", None), ("Romandolide", None),
    ("Musk Ketone", 0.10), ("Exaltolide", 0.10), ("Ambrettolide", 0.10),
    ("Habanolide", None), ("Zenolide", None),
    ("Ambrox Super", 0.30), ("Amberwood F", None), ("Ambermax", 0.10),
    ("Benzyl Salicylate", None), ("Hexyl Salicylate", None),
    ("Benzyl Benzoate", None), ("IPM", None), ("Myristic Acid", 0.20),
]
STEPS = (+60, +30, +15, -15, -30, -60)


def oav_clean(ing: dict, dil: dict) -> bool:
    """Reject moves that introduce OAV errors when this 15 mL half is
    proportionally re-scaled into a 30 mL whole (1:2 doubling is always safe
    for pipette-floor; the real test is 15 mL → 7.5 mL halving in case we
    later want to re-split). Also check absolute-µL semantics at 15 mL.
    """
    # Proportional 15 -> 7.5 catches trace pipette-floor
    half_checks = check_proportional_scaling(ing, dil, 15.0, 7.5)
    if any(c.severity == "error" for c in half_checks):
        return False
    # Absolute-keep semantics (current 15 mL state) — catch ODT crossings
    # if this ever got re-contextualized into a different-volume bottle.
    same_checks = check_batch_scaling(ing, dil, 15.0, 15.0)
    if any(c.severity == "error" for c in same_checks):
        return False
    return True


def geo_score(ing: dict, dil: dict, scorer: FormulaScorer) -> tuple[float, dict]:
    total_ul = sum(ing.values())
    if total_ul <= 0:
        return 0.0, {a: 0.0 for a in AXIS_WEIGHTS}
    fi = FormulaInfo(number=0, name="X", ingredients=ing, dilutions=dil,
                     concentrate_ml=total_ul / 1000.0, description="")
    fv = formula_to_vector(fi)
    s = scorer.score(fv)
    log_sum = 0.0
    for a, w in AXIS_WEIGHTS.items():
        v = max(float(s.get(a, 5.0)), 5.0)
        log_sum += (w / WSUM) * math.log(v)
    return round(math.exp(log_sum), 3), s


def enumerate_moves(ing: dict, rng: random.Random):
    moves = []
    for name, material_dil in CANDIDATE_MATERIALS:
        current = ing.get(name, 0)
        for step in STEPS:
            new = current + step
            if new < 0:
                continue
            if 0 < new < 1:
                continue
            if new > 800:
                continue
            if new == current:
                continue
            moves.append((name, new, material_dil))
    rng.shuffle(moves)
    return moves


def hill_climb(seed_ing: dict, seed_dil: dict, scorer: FormulaScorer,
               seed_rng: int, label: str):
    rng = random.Random(seed_rng)
    ing = dict(seed_ing)
    dil = dict(seed_dil)
    geo, _ = geo_score(ing, dil, scorer)
    print(f"  [{label} seed={seed_rng}] baseline geo={geo}")
    prev = geo
    for p in range(1, MAX_PASSES + 1):
        moves = enumerate_moves(ing, rng)
        best = None   # (new_geo, name, new_ul, mat_dil)
        rejected_oav = 0
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
            tot = sum(trial_ing.values())
            if tot > 4500 or tot < 2250:
                continue
            if not oav_clean(trial_ing, trial_dil):
                rejected_oav += 1
                continue
            g, _ = geo_score(trial_ing, trial_dil, scorer)
            if best is None or g > best[0]:
                best = (g, name, new_ul, mat_dil)
        if best is None:
            print(f"    pass {p}: no valid moves ({rejected_oav} OAV-rejected)")
            break
        new_geo, name, new_ul, mat_dil = best
        delta = new_geo - prev
        if delta <= EPSILON:
            print(f"    pass {p}: best {name}->{new_ul} geo={new_geo} Δ={delta:+.3f} (<ε) STOP")
            break
        if new_ul == 0:
            ing.pop(name, None)
            dil.pop(name, None)
        else:
            ing[name] = new_ul
            if mat_dil is not None:
                dil[name] = mat_dil
        print(f"    pass {p}: {name} -> {new_ul} µL  geo={new_geo}  Δ={delta:+.3f}  "
              f"({rejected_oav} OAV-rejected)")
        prev = new_geo
    final_geo, final_detail = geo_score(ing, dil, scorer)
    return ing, dil, final_geo, final_detail


def run(label: str, seed_ing: dict, seed_dil: dict, scorer: FormulaScorer):
    print(f"\n═══ {label} ═══")
    best = None
    per_seed = []
    for s in SEEDS:
        ing, dil, geo, detail = hill_climb(seed_ing, seed_dil, scorer, s, label)
        per_seed.append((s, geo))
        if best is None or geo > best[2]:
            best = (ing, dil, geo, detail)
    ing, dil, geo, detail = best
    print(f"\n  >>> BEST {label}: geo={geo}  (seeds: {per_seed})")
    for a in AXIS_WEIGHTS:
        print(f"      {a:22s} {detail[a]:.1f}")
    print(f"      concentrate µL = {sum(ing.values())}")
    # Final OAV audit
    audit = check_proportional_scaling(ing, dil, 15.0, 7.5)
    print(f"      OAV audit (15 -> 7.5 mL):")
    errs = [c for c in audit if c.severity == "error"]
    warns = [c for c in audit if c.severity == "warn"]
    infos = [c for c in audit if c.severity == "info"]
    print(f"        {len(errs)} err, {len(warns)} warn, {len(infos)} info")
    for c in errs + warns:
        print(f"        {c.severity}: {c.message}")
    return best, audit, per_seed


def emit_markdown(label: str, ing: dict, dil: dict, detail: dict,
                  per_seed: list, audit, path: Path):
    total_ul = sum(ing.values())
    batch_ul = int(BATCH_ML * 1000)
    lines = [
        f"# {label} — optimized 15 mL half",
        "",
        "**Status:** converged (multi-seed hill-climb, 3 seeds, OAV-guarded).",
        f"**Per-seed best geometric composite:** {per_seed}",
        "",
        f"**Batch:** {BATCH_ML:.2f} mL · concentrate {total_ul} µL · "
        f"{total_ul/batch_ul*100:.1f}% concentrate",
        "",
        "## Axis scores (optimized composite)",
        "",
        "| Axis | Score |",
        "|---|---:|",
    ]
    for a in AXIS_WEIGHTS:
        lines.append(f"| {a} | {detail[a]:.1f} |")
    geo = sum((AXIS_WEIGHTS[a] / WSUM) * math.log(max(float(detail[a]), 5.0))
              for a in AXIS_WEIGHTS)
    lines.append(f"| **geometric composite** | **{math.exp(geo):.2f}** |")
    lines += ["", "## Formula", "",
              "| # | Material | Dilution | Amount (µL) | Amount (mL) |",
              "|--:|---|---|---:|---:|"]
    # Sort by amount descending
    for i, (name, ul) in enumerate(
        sorted(ing.items(), key=lambda kv: -kv[1]), start=1,
    ):
        d = dil.get(name, 1.0)
        d_str = "neat" if d >= 1.0 else f"{d*100:.0f}%"
        lines.append(f"| {i} | {name} | {d_str} | {ul:.0f} | {ul/1000:.3f} |")
    lines += [
        f"| — | Ethanol 96% | — | {batch_ul - total_ul} | {(batch_ul-total_ul)/1000:.3f} |",
        f"| — | **TOTAL** | — | **{batch_ul}** | **{BATCH_ML:.3f}** |",
        "",
        "## OAV audit (15 mL → 7.5 mL proportional — worst-case future re-split)",
        "",
    ]
    errs = [c for c in audit if c.severity == "error"]
    warns = [c for c in audit if c.severity == "warn"]
    infos = [c for c in audit if c.severity == "info"]
    lines.append(f"- errors: **{len(errs)}** · warnings: **{len(warns)}** · info: **{len(infos)}**")
    for c in errs + warns + infos:
        lines.append(f"  - `{c.severity}` {c.message}")
    if not errs and not warns:
        lines.append("  - ✓ all materials scale cleanly to 7.5 mL (and trivially to 30 mL merge)")
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"      wrote {path}")


if __name__ == "__main__":
    t0 = time.time()
    sg = SynergyGraph()
    scorer = FormulaScorer(synergy_graph=sg, batch_volume_ml=BATCH_ML)

    iris_best, iris_audit, iris_seeds = run("PHOTOREALISTIC IRIS 15mL",
                                            IRIS_SEED, IRIS_DIL, scorer)
    ij_best, ij_audit, ij_seeds = run("IRIS-JASMINE 15mL",
                                      IJ_SEED, IJ_DIL, scorer)

    out = {
        "iris": {
            "ingredients": iris_best[0], "dilutions": iris_best[1],
            "geo": iris_best[2], "seeds": iris_seeds,
            "detail": {k: iris_best[3][k] for k in AXIS_WEIGHTS},
        },
        "iris_jasmine": {
            "ingredients": ij_best[0], "dilutions": ij_best[1],
            "geo": ij_best[2], "seeds": ij_seeds,
            "detail": {k: ij_best[3][k] for k in AXIS_WEIGHTS},
        },
    }
    Path("_opt_convergence_v2_out.json").write_text(json.dumps(out, indent=2))
    Path("formulas/collections").mkdir(parents=True, exist_ok=True)
    emit_markdown("Photorealistic Iris", iris_best[0], iris_best[1], iris_best[3],
                  iris_seeds, iris_audit,
                  Path("formulas/collections/Photorealistic_Iris_15mL_optimized.md"))
    emit_markdown("Iris-Jasmine", ij_best[0], ij_best[1], ij_best[3],
                  ij_seeds, ij_audit,
                  Path("formulas/collections/Iris_Jasmine_15mL_optimized.md"))
    print(f"\n[elapsed {time.time()-t0:.1f}s]")
