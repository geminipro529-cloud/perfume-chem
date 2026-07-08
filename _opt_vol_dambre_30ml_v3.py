"""Vol d'Ambre v3 — Layton-inspired mass-appeal aromatic fougère, 30 mL EDP.

Third pass: perfumer stock-dilution correction + identity rebalance.

KEY FIXES vs v2
---------------
1.  STOCK-DILUTION CORRECTION  (root cause of the base weakness in v2)
    The v2 engine passed *stock* wt% directly to evaporate(), treating every
    material as neat.  Vanillin at 10% stock was credited with 10× its real
    headspace contribution; Ambrox Super at 30% stock was credited with 3×.
    v3 applies STOCK_DILUTION to convert stock wt% → neat-equivalent wt%
    before OAV scoring.  The optimizer still works in stock-volume wt% (which
    is what the mixing guide needs), but the fitness function sees reality.

2.  VANILLA ANCHOR  (Vanillin initial 5% → 15% stock-vol)
    With 10% stock, 5% stock-vol = 300 µL = only 30 µL neat → ~0.1% in
    finished EDP — far below Layton's rich vanilla base.  Raising to 15%
    stock-vol = 900 µL = 90 µL neat → 0.3% in EDP; the optimizer can push
    further within bounds.

3.  ISO E SUPER TRIM  (8% → 5% neat)
    Was dominating late dry-down and potentially masking Javanol/Sandalore
    creaminess.  Layton's woody facet is present but subordinate.

4.  APPLE CHORD BOOST  (Apritone 3.5% → 5.0% stock-vol)
    v2 fruity top OAV hit only 429 vs. target 650.  Apritone is the gentlest
    lever; raising its stock volume is the cleanest fix.

5.  DIHYDROMYRCENOL ADDED  (3.5% neat)
    The watery-woody-clean facet that defines Layton's contemporary freshness
    was absent in v2.  Adds the "just-showered" opening lift.

6.  AMBROX SUPER RAISED  (7% → 9% stock-vol)
    At 30% stock, 9% stock-vol = 540 µL = 162 µL neat in concentrate → 0.54%
    neat in finished EDP.  Meaningful skin-musk depth without overdose.

Batch spec:
    20% concentrate EDP — 6 mL fragrance concentrate + 24 mL ethanol 96%
    Volumes in the mixing guide are of the stock as-held in inventory
    (diluted or neat).  No conversion needed at the bench.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from engine.data_spine.loader import load_registry
from engine.odor_thresholds import ODT_DATA
from engine.thermo.trajectory import evaporate
from engine.optimizer.oav_objective import (
    OAVObjective,
    differential_evolution_oav,
    score_formula_oav,
)

# ── Stock dilution factors ────────────────────────────────────────────────────
# Maps *material name* → fraction of neat odorant in the stock-as-held.
# Materials not listed are assumed to be neat (factor = 1.0).
# The OAV/evaporate engine receives neat-equivalent wt%, not stock wt%.
STOCK_DILUTION: dict[str, float] = {
    "Vanillin":          0.10,   # 10% in ethanol
    "Coumarin":          0.20,   # 20% in ethanol
    "Apritone":          0.10,   # 10% in DPG
    "Hexyl Acetate":     0.10,   # 10% in ethanol
    "Cardamom FTEC":     0.10,   # 10% in ethanol
    "Benzoin Resinoid":  0.50,   # 50% in ethanol
    "Ambrox Super":      0.30,   # 30% in DPG/ethanol
}

# ── Material → olfactive family ───────────────────────────────────────────────
FAMILY: dict[str, str] = {
    # Citrus / top
    "Bergamot FCF":              "citrus",
    "Bergamot FCF oil Sicilian": "citrus",
    "Grapefruit FCF":            "citrus",
    "Red Mandarin EO":           "citrus",
    "Blood Orange oil Sicilian": "citrus",
    "D-Limonene":                "citrus",
    "Citral":                    "citrus",
    "Lemonile":                  "citrus",
    # Aromatic / lavender
    "Lavender EO":               "aromatic",
    "Linalool":                  "aromatic",
    "Linalyl Acetate":           "aromatic",
    "Ethyl Linalool":            "aromatic",
    "Clary Sage EO":             "aromatic",
    "Dihydromyrcenol":           "aromatic",   # watery-fresh aromatic facet
    # Fruity / apple
    "Apritone":                  "fruity",
    "Hexyl Acetate":             "fruity",
    "Ethyl 2-Methylbutyrate":    "fruity",
    "Dynascone":                 "fruity",
    "Raspberry Ketone":          "fruity",
    # Spice
    "Cardamom FTEC":             "spice",
    "Eugenol":                   "spice",
    "Isoeugenol":                "spice",
    "Ethyl Safranate":           "spice",
    "Black Pepper FTEC":         "spice",
    "Pink Pepper Base":          "spice",
    # Floral / jasmine
    "Benzyl Acetate":            "floral",
    "Dihydrojasmone":            "floral",
    "Cis Jasmone":               "floral",
    "Methyl Benzoate":           "floral",
    "Hedione":                   "radiance",
    "Hedione HC":                "radiance",
    # Powdery / violet / iris
    "Alpha Isomethyl Ionone":    "powdery",
    "Alpha Ionone":              "powdery",
    "Beta Ionone":               "powdery",
    "Allyl Ionone":              "powdery",
    # Geranium / rose
    "Geraniol":                  "geranium",
    "Citronellol":               "geranium",
    "Phenethyl Alcohol":         "geranium",
    # Wood / structure
    "Iso E Super":               "wood",
    "Javanol":                   "wood",
    "Sandalore":                 "wood",
    "Ebanol":                    "wood",
    "Bacdanol":                  "wood",
    "Cedarwood EO":              "wood",
    "Cedarwood oil Virginia":    "wood",
    "Vetiver EO":                "wood",
    "Patchouli EO":              "wood",
    "Clearwood":                 "wood",
    "Timberol":                  "wood",
    "Polysantol":                "wood",
    "Cashmeran":                 "wood",
    # Amber / ambrox
    "Ambrox Super":              "amber",
    "Ambrofix":                  "amber",
    "Ambermax":                  "amber",
    "Amberwood F":               "amber",
    "Cedramber":                 "amber",
    "Azarbre":                   "amber",
    # Gourmand / sweet
    "Vanillin":                  "gourmand",
    "Ethyl Vanillin":            "gourmand",
    "Ethyl Maltol":              "gourmand",
    "Maple Lactone":             "gourmand",
    "Anisaldehyde":              "gourmand",
    "Heliotropal":               "gourmand",
    # Coumarin / hay
    "Coumarin":                  "coumarin",
    # Balsamic / resinous
    "Benzoin Resinoid":          "balsamic",
    "Siam Benzoin":              "balsamic",
    "Benzoin Sumatra Resinoid":  "balsamic",
    # Musk
    "Galaxolide":                "musk",
    "Habanolide":                "musk",
    "Romandolide":               "musk",
    "Ethylene Brassylate":       "musk",
    "Exaltolide":                "musk",
    "Ambrettolide":              "musk",
    "Zenolide":                  "musk",
    "Macrolide":                 "musk",
    # Cushion / fixative
    "Hexyl Salicylate":          "cushion",
    "Benzyl Salicylate":         "cushion",
    "Benzyl Benzoate":           "cushion",
}

# IFRA caps at concentrate level (fine fragrance Category 4, conservative)
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF":           50.0,
    "Lavender EO":            15.0,
    "Linalool":               25.0,
    "Linalyl Acetate":        25.0,
    "Geraniol":               17.0,
    "Citronellol":            25.0,
    "Coumarin":                7.0,   # stock vol cap; ~1.4% neat in concentrate
    "Benzyl Acetate":          5.0,
    "Phenethyl Alcohol":      20.0,
    "Hedione":                50.0,
    "Hexyl Salicylate":       12.5,
    "Benzyl Salicylate":      25.0,
    "Iso E Super":            30.0,   # tighter perfumer ceiling vs regulatory 60%
    "Eugenol":                 2.5,
    "Isoeugenol":              1.0,
    "Citral":                  5.0,
    "Ethyl 2-Methylbutyrate":  0.30,  # odour-impact cap
    "Dihydromyrcenol":        50.0,
}

# ── Formula ───────────────────────────────────────────────────────────────────
CONCEPT: dict = {
    "key":     "LAYTON_V3",
    "name":    "Vol d'Ambre v3",
    "tagline": (
        "Layton-inspired mass-appeal aromatic fougere — "
        "stock-dilution corrected, vanilla-anchored third pass."
    ),
    "direction": (
        "A lush, sweet aromatic fougère in the Parfums de Marly Layton lineage. "
        "Bergamot + fruity-apple chord (Apritone / Hexyl Acetate / "
        "Ethyl 2-Methylbutyrate) opens bright and accessible; "
        "Dihydromyrcenol adds the watery-clean freshness of the original; "
        "Cardamom FTEC anchors the signature spice warmth; "
        "Lavender EO + Linalyl Acetate + Ethyl Linalool form a full, sweet lavender "
        "pillar. The heart blooms with Hedione HC radiance, Geraniol rose-warmth, "
        "and Alpha Isomethyl Ionone violet-powder softness. The drydown is the real "
        "strength: Ambrox Super skin-musk, Javanol + Sandalore creamy sandalwood, "
        "Vanillin + Ethyl Vanillin vanilla warmth, Benzoin Resinoid balsamic depth, "
        "Coumarin hay sweetness — rich, enveloping, intimate. "
        "Direction: mass appeal → maximise fruity-aromatic top energy; preserve "
        "obvious lavender-cardamom-apple-fresh recognition; keep the base plush and "
        "vanilla-forward; no oakmoss/moss bitterness; sandalwood must read as creamy/"
        "milky (Javanol-led). NOTE: Vanillin at 10% stock, Coumarin at 20% stock, "
        "Apritone/Hexyl Acetate/Cardamom at 10% stock, Benzoin Resinoid at 50% stock, "
        "Ambrox Super at 30% stock — OAV engine uses neat-equivalent concentrations."
    ),
    "recipe": {
        # ── Top — citrus / aromatic / fruity / spice ──────────────────────────
        "Bergamot FCF":              7.0,   # neat
        "Lavender EO":               9.0,   # neat
        "Linalyl Acetate":           3.0,   # neat
        "Ethyl Linalool":            2.0,   # neat
        "Dihydromyrcenol":           3.5,   # neat  ← NEW: watery Layton freshness
        "Apritone":                  5.0,   # 10% stock  ↑ from 3.5
        "Hexyl Acetate":             3.0,   # 10% stock  ↑ from 2.5
        "Ethyl 2-Methylbutyrate":    0.15,  # neat — extreme potency; keep tight
        "Cardamom FTEC":             4.0,   # 10% stock  ↑ from 3.0
        # ── Heart — radiance / floral / geranium / powdery ───────────────────
        "Hedione HC":                7.0,   # neat
        "Hedione":                   4.0,   # neat  ↓ from 5.0 (double-stack trim)
        "Benzyl Acetate":            2.0,   # neat
        "Dihydrojasmone":            0.8,   # neat
        "Geraniol":                  2.0,   # neat
        "Alpha Isomethyl Ionone":    2.5,   # neat
        "Phenethyl Alcohol":         1.5,   # neat
        # ── Base — wood / amber / gourmand / musk ─────────────────────────────
        "Iso E Super":               5.0,   # neat  ↓ from 8.0 (was over-dominating)
        "Javanol":                   4.0,   # neat
        "Sandalore":                 3.0,   # neat
        "Ambrox Super":              9.0,   # 30% stock  ↑ from 7.0
        "Vanillin":                 15.0,   # 10% stock  ★ KEY FIX: ↑ from 5.0
        "Ethyl Vanillin":            0.5,   # neat
        "Coumarin":                  4.0,   # 20% stock  ↑ from 3.5
        "Benzoin Resinoid":          3.0,   # 50% stock
        "Habanolide":                4.0,   # neat
        "Galaxolide":                3.5,   # neat
        "Romandolide":               2.0,   # neat
        "Ethylene Brassylate":       1.5,   # neat
    },
    # Target OAV envelope — mass-appeal aromatic fougère (stock-dilution corrected)
    # Targets are for NEAT-equivalent OAV contributions from the headspace engine.
    # Amber/gourmand base targets relaxed to realistic range given diluted stocks;
    # fruity top raised to 650 (close Apritone gap); aromatic top maintained.
    "envelope": {
        "top": {
            "citrus":    2400,
            "aromatic":  1150,   # maintained; Dihydromyrcenol adds aromatic OAV
            "fruity":     650,   # ↑ target — Apritone boost should reach this
            "spice":       90,
            "radiance":    30,
            "floral":      12,
        },
        "heart": {
            "aromatic":   900,
            "radiance":    70,
            "citrus":     500,
            "fruity":     260,
            "geranium":    55,
            "powdery":    160,
            "amber":      320,
            "spice":       55,
            "floral":      18,
        },
        "base": {
            "amber":      420,   # realistic with stock-corrected Ambrox Super
            "gourmand":   180,   # realistic with 10% Vanillin stock
            "balsamic":    95,
            "wood":        90,
            "coumarin":    55,
            "musk":        65,
            "powdery":    110,
        },
    },
}

# Perfumer-style identity floors
IDENTITY_FLOOR_PCT: dict[str, float] = {
    "Bergamot FCF":          6.5,
    "Lavender EO":           8.5,
    "Dihydromyrcenol":       2.5,   # watery freshness floor
    "Apritone":              4.0,
    "Hexyl Acetate":         2.2,
    "Cardamom FTEC":         3.0,
    "Hedione HC":            6.5,
    "Hedione":               3.5,
    "Alpha Isomethyl Ionone": 2.0,
    "Linalyl Acetate":       2.5,
    "Vanillin":             10.0,   # floor keeps vanilla meaningful at 10% stock
    "Ambrox Super":          7.0,   # floor keeps ambrox present at 30% stock
}

# Support-material ceilings: prevent the frame from swallowing the signature
IDENTITY_CEIL_PCT: dict[str, float] = {
    "Iso E Super":    8.0,    # hard ceiling — was over-dominating in v2
    "Habanolide":     6.0,
    "Romandolide":    3.0,
    "Galaxolide":     4.5,
    "Ambrox Super":  12.0,
    "Vanillin":      22.0,   # stock vol ceiling (= 2.2% neat in concentrate)
}


def enforce_identity_profile(wt_pct: dict[str, float]) -> dict[str, float]:
    """Project a normalized formula back into the perfumer floor/ceiling box."""
    mats = list(wt_pct.keys())
    floors = {m: IDENTITY_FLOOR_PCT.get(m, 0.0) for m in mats}
    ceils  = {m: IDENTITY_CEIL_PCT.get(m,  100.0) for m in mats}
    projected = {m: min(max(wt_pct[m], floors[m]), ceils[m]) for m in mats}
    target_total = 100.0

    for _ in range(12):
        total = sum(projected.values())
        delta = target_total - total
        if abs(delta) < 1e-6:
            break
        if delta > 0:
            free = [m for m in mats if projected[m] < ceils[m] - 1e-9]
            room = sum(ceils[m] - projected[m] for m in free)
            if not free or room <= 1e-9:
                break
            for m in free:
                projected[m] += delta * (ceils[m] - projected[m]) / room
        else:
            free = [m for m in mats if projected[m] > floors[m] + 1e-9]
            room = sum(projected[m] - floors[m] for m in free)
            if not free or room <= 1e-9:
                break
            for m in free:
                projected[m] += delta * (projected[m] - floors[m]) / room
        for m in mats:
            projected[m] = min(max(projected[m], floors[m]), ceils[m])

    total = sum(projected.values())
    delta = target_total - total
    if abs(delta) > 1e-6:
        if delta > 0:
            free = [m for m in mats if projected[m] < ceils[m] - 1e-9]
            room = sum(ceils[m] - projected[m] for m in free)
            if free and room > 1e-9:
                for m in free:
                    projected[m] += delta * (ceils[m] - projected[m]) / room
        else:
            free = [m for m in mats if projected[m] > floors[m] + 1e-9]
            room = sum(projected[m] - floors[m] for m in free)
            if free and room > 1e-9:
                for m in free:
                    projected[m] += delta * (projected[m] - floors[m]) / room
    return projected


# ── Batch parameters ──────────────────────────────────────────────────────────
BATCH_ML        = 30.0
CONCENTRATE_PCT = 0.20
CONCENTRATE_ML  = BATCH_ML * CONCENTRATE_PCT      # 6.0 mL
CONCENTRATE_UL  = CONCENTRATE_ML * 1000           # 6000 µL
ETHANOL_UL      = (BATCH_ML - CONCENTRATE_ML) * 1000  # 24000 µL
DROP_UL         = 20.0

# ── Engine helpers ────────────────────────────────────────────────────────────
REGISTRY = load_registry()


def _odt_air_ppm(name: str) -> float:
    n = name.casefold()
    if n in ODT_DATA:
        return ODT_DATA[n]["odt_air"] / 1000.0
    for key in ODT_DATA:
        if key in n or n in key:
            return ODT_DATA[key]["odt_air"] / 1000.0
    return 0.05


def build_tables(materials: list[str]) -> dict:
    mw_t, vp_t, hsp_t, odt_t, fam_t = {}, {}, {}, {}, {}
    missing = []
    for m in materials:
        rec = REGISTRY.get(m)
        if rec is None:
            missing.append(m)
            mw_t[m], vp_t[m] = 200.0, 1.0
        else:
            mw_t[m] = rec.mw_g_mol or 200.0
            vp_t[m] = rec.vp_25c_pa or 1.0
            if rec.hsp.delta_d is not None:
                hsp_t[m] = (rec.hsp.delta_d, rec.hsp.delta_p or 0.0, rec.hsp.delta_h or 0.0)
        odt_t[m] = _odt_air_ppm(m)
        fam_t[m] = FAMILY.get(m, "default")
    return dict(mw=mw_t, vp=vp_t, hsp=hsp_t, odt=odt_t, fam=fam_t, missing=missing)


def make_headspace_fn(tables: dict):
    """Build a headspace function that applies stock dilution before OAV scoring.

    The optimizer works in *stock wt%* (volume of stock-as-held).  Before
    passing to the thermodynamic evaporation engine, each material's wt% is
    multiplied by its STOCK_DILUTION factor so the engine sees the *neat
    equivalent* concentration.  This is the key fix vs. v2.
    """
    mw_t, vp_t, hsp_t, odt_t = tables["mw"], tables["vp"], tables["hsp"], tables["odt"]

    def headspace_fn(wt_pct: Mapping[str, float]) -> dict[str, dict[str, float]]:
        # Convert stock wt% → neat-equivalent wt% for thermodynamic accuracy
        neat_wt = {m: v * STOCK_DILUTION.get(m, 1.0) for m, v in wt_pct.items()}
        if not any(v > 0 for v in neat_wt.values()):
            return {"top": {}, "heart": {}, "base": {}}
        frames = evaporate(
            neat_wt, duration_s=14400.0, n_steps=12,
            mw_table=mw_t, vp_table=vp_t, hsp_table=hsp_t,
        )
        targets = {"top": 60.0, "heart": 1800.0, "base": 14400.0}
        out = {}
        for win, tgt in targets.items():
            best = min(frames, key=lambda f: abs(f.t_seconds - tgt))
            out[win] = {
                n: {"oav": c.vapor_ppm / max(odt_t.get(n, 0.05), 1e-6)}
                for n, c in best.headspace.items()
            }
        return out

    return headspace_fn


def family_summed(
    profile: dict[str, dict[str, float]], fam_t: dict[str, str]
) -> dict[str, float]:
    out: dict[str, float] = {}
    for m, p in profile.items():
        fam = fam_t.get(m, "default")
        out[fam] = out.get(fam, 0.0) + p.get("oav", 0.0)
    return out


def render_envelope(snap: dict[str, dict[str, float]], fam_t: dict[str, str]) -> str:
    lines = []
    for win in ("top", "heart", "base"):
        fams  = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"  {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items))
    return "\n".join(lines)


def run_one(
    concept: dict, *, maxiter: int = 60, popsize: int = 18, seed: int = 42
) -> dict:
    name, key = concept["name"], concept["key"]
    recipe    = {k: v for k, v in concept["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables    = build_tables(materials)

    bounds = []
    for m in materials:
        v  = recipe[m]
        lo = max(0.0, v * 0.55)
        hi = v * 1.60
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.5:
            hi = max(hi, v * 2.5)
        lo = max(lo, IDENTITY_FLOOR_PCT.get(m, 0.0))
        if m in IDENTITY_CEIL_PCT:
            hi = min(hi, IDENTITY_CEIL_PCT[m])
        bounds.append((lo, hi))

    headspace_fn = make_headspace_fn(tables)
    obj = OAVObjective(
        materials=materials,
        bounds=bounds,
        target_envelope=concept["envelope"],
        headspace_fn=headspace_fn,
        families=tables["fam"],
    )

    init_score = score_formula_oav(recipe, obj)
    init_snap  = headspace_fn(recipe)
    print(f"\n=== [{key}] {name} ===")
    print(f"  Tagline:  {concept['tagline']}")
    print(f"  Materials: {len(materials)}   missing-from-spine: {tables['missing']}")
    print(f"  INITIAL   score = {init_score:+.3f}  (stock-dilution corrected)")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, best_score = differential_evolution_oav(
        obj, maxiter=maxiter, popsize=popsize, seed=seed
    )
    total        = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_wt_norm = enforce_identity_profile(best_wt_norm)
    best_snap    = headspace_fn(best_wt_norm)
    final_score  = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final_score:+.3f}   (delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key":     key,
        "name":    name,
        "tagline": concept["tagline"],
        "direction": concept["direction"],
        "envelope_target": concept["envelope"],
        "stock_dilution":  STOCK_DILUTION,
        "initial": {
            "recipe_wt_pct": recipe,
            "score": init_score,
            "envelope": {
                w: family_summed(init_snap[w], tables["fam"])
                for w in ("top", "heart", "base")
            },
        },
        "optimized": {
            "recipe_wt_pct": {
                k: round(v, 3)
                for k, v in sorted(best_wt_norm.items(), key=lambda kv: -kv[1])
            },
            "score": final_score,
            "envelope": {
                w: family_summed(best_snap[w], tables["fam"])
                for w in ("top", "heart", "base")
            },
        },
        "delta_score": final_score - init_score,
        "missing_from_spine": tables["missing"],
    }


# ── Mixing-guide renderer ─────────────────────────────────────────────────────
def emit_markdown(result: dict) -> str:
    r    = result
    opt  = r["optimized"]["recipe_wt_pct"]
    init = r["initial"]["recipe_wt_pct"]
    sd   = r.get("stock_dilution", {})

    def neat_in_conc(m: str, wt: float) -> str:
        """Return human-readable neat-in-concentrate string for a material."""
        factor = sd.get(m, 1.0)
        neat_ul = (wt / 100.0) * CONCENTRATE_UL * factor
        neat_pct_conc = neat_ul / CONCENTRATE_UL * 100
        neat_pct_edp  = neat_pct_conc * CONCENTRATE_PCT
        if factor < 1.0:
            return f"≈{neat_ul:.0f} µL neat → {neat_pct_edp:.3f}% neat in EDP"
        return ""

    lines = [
        f"# {r['name']} — 30 mL EDP Mixing Guide",
        "",
        f"*{r['tagline']}*",
        "",
        "**Status:** OAV differential-evolution optimized (DE/rand/1/bin, "
        "60 generations, stock-dilution corrected).",
        f"**Score delta vs initial:** {r['delta_score']:+.3f}",
        "",
        "---",
        "",
        "## Concept Brief",
        "",
        r["direction"],
        "",
        "---",
        "",
        "## Stock Dilution Reference",
        "",
        "The OAV engine in v3 uses *neat-equivalent* concentrations.  "
        "The mixing guide volumes below are of the **stock as-held**.",
        "",
        "| Material | Stock | Dilution factor | Neat in concentrate |",
        "|---|---|---:|---|",
    ]

    for m, factor in sorted(sd.items(), key=lambda kv: kv[0]):
        wt_pct = opt.get(m, 0.0)
        neat_ul = (wt_pct / 100.0) * CONCENTRATE_UL * factor
        neat_pct_edp = neat_ul / CONCENTRATE_UL * 100 * CONCENTRATE_PCT
        pct_str = f"{int(factor*100)}%"
        lines.append(
            f"| {m} | {pct_str} | {factor:.2f} | "
            f"≈{neat_ul:.0f} µL neat → {neat_pct_edp:.3f}% in EDP |"
        )

    lines += [
        "",
        "---",
        "",
        "## Batch Parameters",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Total batch | {BATCH_ML:.0f} mL |",
        f"| EDP concentration | {CONCENTRATE_PCT*100:.0f}% |",
        f"| Fragrance concentrate | {CONCENTRATE_ML:.1f} mL ({CONCENTRATE_UL:.0f} µL) |",
        f"| Ethanol 96% (dilution) | {BATCH_ML - CONCENTRATE_ML:.1f} mL ({ETHANOL_UL:.0f} µL) |",
        f"| Drop reference | {DROP_UL:.0f} µL / drop |",
        "",
        "> All volumes below are for the stock **as-held in inventory** (diluted or neat).",
        "> Measure into the concentrate; top up concentrate with ethanol to exactly",
        f"> {CONCENTRATE_ML:.1f} mL before adding to the final bottle.",
        "",
        "---",
        "",
        "## Optimized Formula — 30 mL EDP",
        "",
        "| # | Material | Stock | wt% | µL | mL | ~Drops | Neat in EDP |",
        "|--:|---|---|---:|---:|---:|---:|---|",
    ]

    all_mats = sorted(opt.keys(), key=lambda k: -opt[k])
    for i, m in enumerate(all_mats, start=1):
        wt    = opt[m]
        ul    = wt / 100.0 * CONCENTRATE_UL
        drops = ul / DROP_UL
        factor = sd.get(m, 1.0)
        neat_ul  = ul * factor
        neat_edp = neat_ul / CONCENTRATE_UL * CONCENTRATE_PCT * 100
        stock_str = f"{int(factor*100)}%" if factor < 1.0 else "neat"
        neat_str  = f"{neat_edp:.3f}%" if factor < 1.0 else "—"
        lines.append(
            f"| {i} | {m} | {stock_str} | {wt:.2f} | {ul:.0f} | "
            f"{ul/1000:.3f} | {drops:.1f} | {neat_str} |"
        )

    total_wt  = sum(opt.values())
    total_ul  = total_wt / 100.0 * CONCENTRATE_UL
    eth_conc  = CONCENTRATE_UL - total_ul

    lines += [
        f"| — | **Fragrance sub-total** | — | **{total_wt:.2f}** | "
        f"**{total_ul:.0f}** | **{total_ul/1000:.3f}** | — | — |",
        f"| — | Ethanol 96% (in concentrate) | — | — | "
        f"{eth_conc:.0f} | {eth_conc/1000:.3f} | — | — |",
        f"| — | **Concentrate total** | — | — | "
        f"**{CONCENTRATE_UL:.0f}** | **{CONCENTRATE_ML:.3f}** | — | — |",
        f"| — | Ethanol 96% (bottle fill) | — | — | "
        f"**{ETHANOL_UL:.0f}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** | — | — |",
        f"| — | **Final bottle total** | — | — | "
        f"**{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** | — | — |",
        "",
        "---",
        "",
        "## wt% Comparison (v2 Initial → v3 Optimized)",
        "",
        "| Material | v2 Initial | v3 Optimized | Δ | Stock |",
        "|---|---:|---:|---:|---|",
    ]

    all_keys = sorted(set(init) | set(opt), key=lambda k: -opt.get(k, 0))
    for m in all_keys:
        iv     = init.get(m, 0.0)
        ov     = opt.get(m, 0.0)
        factor = sd.get(m, 1.0)
        stock_str = f"{int(factor*100)}%" if factor < 1.0 else "neat"
        lines.append(
            f"| {m} | {iv:.2f} | {ov:.2f} | {ov - iv:+.2f} | {stock_str} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Family OAV Envelope (neat-equivalent)",
        "",
        "| Window | Family axes (OAV) |",
        "|---|---|",
    ]
    for section, label in (("initial", "v3 Initial (corrected)"),
                            ("optimized", "v3 Optimized")):
        lines.append("")
        lines.append(f"### {label}")
        for win in ("top", "heart", "base"):
            fams = r[section]["envelope"][win]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            lines.append(
                f"- **{win}**: " + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
            )
    lines += ["", "### Target"]
    for win in ("top", "heart", "base"):
        tgt  = r["envelope_target"][win]
        top6 = sorted(tgt.items(), key=lambda kv: -kv[1])[:6]
        lines.append(
            f"- **{win}**: " + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
        )

    lines += [
        "",
        "---",
        "",
        "## Mixing Protocol",
        "",
        "1. Tare a clean 10 mL glass vial on a 0.001 g precision scale.",
        "2. **Base first:** add macrocyclic musks, amber, balsamic, and wood materials.",
        "3. **Heart:** add Hedione HC/Hedione radiance, geranium, powdery, floral.",
        "4. **Top:** add lavender, Dihydromyrcenol, fruity, citrus, and spice last.",
        "5. Add ethanol 96% inside the concentrate to reach exactly **6.00 mL**.",
        "6. Seal and macerate **48 h minimum** before first evaluation.",
        "7. Transfer to the 30 mL bottle; top up with remaining ethanol (**24.0 mL**).",
        "8. Macerate the finished EDP **2–4 weeks** for full accord integration.",
        "",
        "### Layering order (base → top)",
        "",
        "| Order | Material | Reason |",
        "|---|---|---|",
        "| 1 | Ethylene Brassylate, Habanolide, Romandolide | Slowest evaporators — add first |",
        "| 2 | Galaxolide | Musk anchor |",
        "| 3 | Ambrox Super (30%) | Amber fixative |",
        "| 4 | Benzoin Resinoid (50%) | Balsamic base |",
        "| 5 | Vanillin (10%), Ethyl Vanillin, Coumarin (20%) | Sweet-hay-vanilla structure |",
        "| 6 | Iso E Super, Javanol, Sandalore | Wood-sandalwood body |",
        "| 7 | Alpha Isomethyl Ionone | Powdery bridge |",
        "| 8 | Hedione HC, Hedione, Dihydrojasmone, Benzyl Acetate | Radiance + jasmine heart |",
        "| 9 | Geraniol, Phenethyl Alcohol | Rose-geranium warmth |",
        "| 10 | Linalyl Acetate, Ethyl Linalool, Lavender EO | Lavender pillar |",
        "| 11 | Dihydromyrcenol | Watery-fresh top facet |",
        "| 12 | Apritone (10%), Hexyl Acetate (10%), Ethyl 2-Methylbutyrate | Apple chord |",
        "| 13 | Cardamom FTEC (10%), Bergamot FCF | Top spice + citrus |",
        "",
        "---",
        "",
        "## Safety & Stock Notes",
        "",
        "- **Vanillin (10% stock):** At the optimized dose, you are dispensing a large",
        "  volume of diluted stock.  This is intentional — neat Vanillin is not soluble",
        "  at the required level in a cold concentrate.  Total neat Vanillin in finished",
        "  EDP will be ≈ 0.2–0.4%; perceivable but mild.  If you can prepare a 50%",
        "  Vanillin stock in warm ethanol, reduce the volume by 5× and redistribute.",
        "- **Ethyl 2-Methylbutyrate (neat):** extreme potency.  A 1 µL error at this",
        "  dose range materially changes the apple character.",
        "- **Ambrox Super (30% stock):** No IFRA cap in fine fragrance; keep neat",
        "  ambroxan ≤ 3% in finished EDP for skin comfort.  v3 is well within this.",
        "- **Benzyl Acetate:** skin sensitiser — IFRA Category 4 cap ~2.5% in finished",
        "  product; at 20% EDP this allows up to ~12.5% in concentrate.  v3 is safe.",
        "- **Cardamom FTEC (10% stock):** FTEC — registry uses default thermodynamic",
        "  values; optimized proportion is based on stock-dilution-corrected OAV.",
        "- **Dihydromyrcenol (neat):** citrus-watery-woody; use the measured volume",
        "  only — it can make the formula read soapy if overdosed above ~5% in conc.",
        "",
        "---",
        "",
        "## v3 vs v2 Key Differences",
        "",
        "| Change | v2 | v3 | Reason |",
        "|---|---|---|---|",
        "| OAV engine | Stock wt% (uncorrected) | Neat-equivalent (corrected) | Root-cause fix |",
        "| Vanillin | 5% of 10% stock | 15%+ of 10% stock | Actual vanilla presence |",
        "| Iso E Super | 6–8% neat | 5% neat (hard cap 8%) | Prevent cedar dominance |",
        "| Dihydromyrcenol | absent | 2.5–4% neat | Layton watery freshness |",
        "| Apritone | 3.5–4% of 10% stock | 5%+ of 10% stock | Close fruity OAV gap |",
        "| Ambrox Super | 7% of 30% stock | 9%+ of 30% stock | Deeper skin-musk base |",
    ]

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    result = run_one(CONCEPT, maxiter=60, popsize=18, seed=42)

    root     = Path(__file__).parent
    json_out = root / "_opt_vol_dambre_v3_out.json"
    json_out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/Vol_dAmbre_30mL_Layton_Inspired_v3.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
