"""Vol d'Ambre v3b — Layton-inspired, NO HEDIONE HC (OUT OF STOCK).

Inherits all v3 fixes (stock-dilution-corrected OAV, vanilla anchor,
Iso E Super trim, Dihydromyrcenol freshness).

Change vs v3
------------
- Hedione HC removed  ← OUT OF STOCK
- Hedione raised 4.0 → 12.0 %  (sole radiance/bloom carrier)
  Hedione HC OAV impact is ~3–5× per unit weight vs plain Hedione,
  so adding ~8% extra Hedione partially closes the bloom gap.
  The heart will read slightly softer / rounder; the opening stays intact.
- Hedione identity floor raised to 10.0 %
- Benzyl Acetate nudged to 2.5 %  (extra jasmine body to compensate)
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

# ── Stock dilution factors (identical to v3) ──────────────────────────────────
STOCK_DILUTION: dict[str, float] = {
    "Vanillin":          0.10,
    "Coumarin":          0.20,
    "Apritone":          0.10,
    "Hexyl Acetate":     0.10,
    "Cardamom FTEC":     0.10,
    "Benzoin Resinoid":  0.50,
    "Ambrox Super":      0.30,
}

# ── Material → olfactive family (identical to v3) ─────────────────────────────
FAMILY: dict[str, str] = {
    "Bergamot FCF":              "citrus",
    "Bergamot FCF oil Sicilian": "citrus",
    "Grapefruit FCF":            "citrus",
    "Red Mandarin EO":           "citrus",
    "Blood Orange oil Sicilian": "citrus",
    "D-Limonene":                "citrus",
    "Citral":                    "citrus",
    "Lemonile":                  "citrus",
    "Lavender EO":               "aromatic",
    "Linalool":                  "aromatic",
    "Linalyl Acetate":           "aromatic",
    "Ethyl Linalool":            "aromatic",
    "Clary Sage EO":             "aromatic",
    "Dihydromyrcenol":           "aromatic",
    "Apritone":                  "fruity",
    "Hexyl Acetate":             "fruity",
    "Ethyl 2-Methylbutyrate":    "fruity",
    "Dynascone":                 "fruity",
    "Raspberry Ketone":          "fruity",
    "Cardamom FTEC":             "spice",
    "Eugenol":                   "spice",
    "Isoeugenol":                "spice",
    "Ethyl Safranate":           "spice",
    "Black Pepper FTEC":         "spice",
    "Pink Pepper Base":          "spice",
    "Benzyl Acetate":            "floral",
    "Dihydrojasmone":            "floral",
    "Cis Jasmone":               "floral",
    "Methyl Benzoate":           "floral",
    "Hedione":                   "radiance",
    # Hedione HC intentionally absent — OUT OF STOCK
    "Alpha Isomethyl Ionone":    "powdery",
    "Alpha Ionone":              "powdery",
    "Beta Ionone":               "powdery",
    "Allyl Ionone":              "powdery",
    "Geraniol":                  "geranium",
    "Citronellol":               "geranium",
    "Phenethyl Alcohol":         "geranium",
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
    "Ambrox Super":              "amber",
    "Ambrofix":                  "amber",
    "Ambermax":                  "amber",
    "Amberwood F":               "amber",
    "Cedramber":                 "amber",
    "Azarbre":                   "amber",
    "Vanillin":                  "gourmand",
    "Ethyl Vanillin":            "gourmand",
    "Ethyl Maltol":              "gourmand",
    "Maple Lactone":             "gourmand",
    "Anisaldehyde":              "gourmand",
    "Heliotropal":               "gourmand",
    "Coumarin":                  "coumarin",
    "Benzoin Resinoid":          "balsamic",
    "Siam Benzoin":              "balsamic",
    "Benzoin Sumatra Resinoid":  "balsamic",
    "Galaxolide":                "musk",
    "Habanolide":                "musk",
    "Romandolide":               "musk",
    "Ethylene Brassylate":       "musk",
    "Exaltolide":                "musk",
    "Ambrettolide":              "musk",
    "Zenolide":                  "musk",
    "Macrolide":                 "musk",
    "Hexyl Salicylate":          "cushion",
    "Benzyl Salicylate":         "cushion",
    "Benzyl Benzoate":           "cushion",
}

IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF":           50.0,
    "Lavender EO":            15.0,
    "Linalool":               25.0,
    "Linalyl Acetate":        25.0,
    "Geraniol":               17.0,
    "Citronellol":            25.0,
    "Coumarin":                7.0,
    "Benzyl Acetate":          5.0,
    "Phenethyl Alcohol":      20.0,
    "Hedione":                50.0,
    "Hexyl Salicylate":       12.5,
    "Benzyl Salicylate":      25.0,
    "Iso E Super":            30.0,
    "Eugenol":                 2.5,
    "Isoeugenol":              1.0,
    "Citral":                  5.0,
    "Ethyl 2-Methylbutyrate":  0.30,
    "Dihydromyrcenol":        50.0,
}

# ── Formula (no Hedione HC) ───────────────────────────────────────────────────
CONCEPT: dict = {
    "key":     "LAYTON_V3B",
    "name":    "Vol d'Ambre v3b",
    "tagline": (
        "Layton-inspired aromatic fougere — "
        "Hedione HC OUT OF STOCK build, stock-dilution corrected."
    ),
    "direction": (
        "Vol d'Ambre v3b: identical structure to v3 but built without Hedione HC "
        "(currently out of stock).  Hedione (plain) is raised to 12% to carry the "
        "jasmine-radiance bloom alone; Benzyl Acetate is slightly boosted for "
        "jasmine body.  Expect a softer, rounder heart vs v3 — the diffusive "
        "glossy lift of HC is partially compensated but not fully replicated. "
        "All other v3 improvements are preserved: stock-dilution-corrected OAV, "
        "Dihydromyrcenol watery freshness, Vanillin vanilla anchor at 10% stock, "
        "Iso E Super trimmed to prevent cedar dominance. "
        "STOCK NOTE — Hedione HC: OUT OF STOCK. "
        "Vanillin at 10% stock, Coumarin at 20% stock, "
        "Apritone/Hexyl Acetate/Cardamom FTEC at 10% stock, "
        "Benzoin Resinoid at 50% stock, Ambrox Super at 30% stock."
    ),
    "recipe": {
        # ── Top ───────────────────────────────────────────────────────────────
        "Bergamot FCF":              7.0,   # neat
        "Lavender EO":               9.0,   # neat
        "Linalyl Acetate":           3.0,   # neat
        "Ethyl Linalool":            2.0,   # neat
        "Dihydromyrcenol":           3.5,   # neat
        "Apritone":                  5.0,   # 10% stock
        "Hexyl Acetate":             3.0,   # 10% stock
        "Ethyl 2-Methylbutyrate":    0.15,  # neat
        "Cardamom FTEC":             4.0,   # 10% stock
        # ── Heart (Hedione HC removed; Hedione raised) ────────────────────────
        # "Hedione HC":             OOS — do not add
        "Hedione":                  12.0,   # neat  ↑ from 4.0 — sole radiance
        "Benzyl Acetate":            2.5,   # neat  ↑ from 2.0 — jasmine body
        "Dihydrojasmone":            1.0,   # neat  ↑ from 0.8
        "Geraniol":                  2.0,   # neat
        "Alpha Isomethyl Ionone":    2.5,   # neat
        "Phenethyl Alcohol":         1.5,   # neat
        # ── Base ──────────────────────────────────────────────────────────────
        "Iso E Super":               5.0,   # neat
        "Javanol":                   4.0,   # neat
        "Sandalore":                 3.0,   # neat
        "Ambrox Super":              9.0,   # 30% stock
        "Vanillin":                 15.0,   # 10% stock
        "Ethyl Vanillin":            0.5,   # neat
        "Coumarin":                  4.0,   # 20% stock
        "Benzoin Resinoid":          3.0,   # 50% stock
        "Habanolide":                4.0,   # neat
        "Galaxolide":                3.5,   # neat
        "Romandolide":               2.0,   # neat
        "Ethylene Brassylate":       1.5,   # neat
    },
    "envelope": {
        "top": {
            "citrus":    2400,
            "aromatic":  1150,
            "fruity":     650,
            "spice":       90,
            "radiance":    18,   # lower — no HC, radiance bloom is reduced
            "floral":      12,
        },
        "heart": {
            "aromatic":   900,
            "radiance":    55,   # lower than v3 target; HC absence felt here
            "citrus":     500,
            "fruity":     260,
            "geranium":    55,
            "powdery":    160,
            "amber":      320,
            "spice":       55,
            "floral":      22,   # slightly raised; Benzyl Acetate carries more
        },
        "base": {
            "amber":      420,
            "gourmand":   180,
            "balsamic":    95,
            "wood":        90,
            "coumarin":    55,
            "musk":        65,
            "powdery":    110,
        },
    },
}

# Identity floors
IDENTITY_FLOOR_PCT: dict[str, float] = {
    "Bergamot FCF":           6.5,
    "Lavender EO":            8.5,
    "Dihydromyrcenol":        2.5,
    "Apritone":               4.0,
    "Hexyl Acetate":          2.2,
    "Cardamom FTEC":          3.0,
    "Hedione":               10.0,   # sole radiance carrier — hard floor
    "Alpha Isomethyl Ionone": 2.0,
    "Linalyl Acetate":        2.5,
    "Vanillin":              10.0,
    "Ambrox Super":           7.0,
}

# Support ceilings
IDENTITY_CEIL_PCT: dict[str, float] = {
    "Iso E Super":    8.0,
    "Habanolide":     6.0,
    "Romandolide":    3.0,
    "Galaxolide":     4.5,
    "Ambrox Super":  12.0,
    "Vanillin":      22.0,
    "Hedione":       20.0,   # allow optimizer to push Hedione high if needed
}


def enforce_identity_profile(wt_pct: dict[str, float]) -> dict[str, float]:
    mats   = list(wt_pct.keys())
    floors = {m: IDENTITY_FLOOR_PCT.get(m, 0.0) for m in mats}
    ceils  = {m: IDENTITY_CEIL_PCT.get(m, 100.0) for m in mats}
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
CONCENTRATE_ML  = BATCH_ML * CONCENTRATE_PCT
CONCENTRATE_UL  = CONCENTRATE_ML * 1000
ETHANOL_UL      = (BATCH_ML - CONCENTRATE_ML) * 1000
DROP_UL         = 20.0

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
                hsp_t[m] = (
                    rec.hsp.delta_d,
                    rec.hsp.delta_p or 0.0,
                    rec.hsp.delta_h or 0.0,
                )
        odt_t[m] = _odt_air_ppm(m)
        fam_t[m] = FAMILY.get(m, "default")
    return dict(mw=mw_t, vp=vp_t, hsp=hsp_t, odt=odt_t, fam=fam_t, missing=missing)


def make_headspace_fn(tables: dict):
    """Stock-dilution-corrected headspace (same as v3)."""
    mw_t  = tables["mw"]
    vp_t  = tables["vp"]
    hsp_t = tables["hsp"]
    odt_t = tables["odt"]

    def headspace_fn(
        wt_pct: Mapping[str, float],
    ) -> dict[str, dict[str, float]]:
        neat_wt = {
            m: v * STOCK_DILUTION.get(m, 1.0) for m, v in wt_pct.items()
        }
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


def family_summed(profile, fam_t: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for m, p in profile.items():
        fam = fam_t.get(m, "default")
        out[fam] = out.get(fam, 0.0) + p.get("oav", 0.0)
    return out


def render_envelope(snap: dict, fam_t: dict[str, str]) -> str:
    lines = []
    for win in ("top", "heart", "base"):
        fams  = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(
            f"  {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items)
        )
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
    print(f"  Hedione HC: OUT OF STOCK — excluded from formula")
    print(f"  Materials: {len(materials)}   missing: {tables['missing']}")
    print(f"  INITIAL  score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, best_score = differential_evolution_oav(
        obj, maxiter=maxiter, popsize=popsize, seed=seed
    )
    total        = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_wt_norm = enforce_identity_profile(best_wt_norm)
    best_snap    = headspace_fn(best_wt_norm)
    final_score  = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final_score:+.3f}  "
          f"(delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key":     key,
        "name":    name,
        "tagline": concept["tagline"],
        "direction": concept["direction"],
        "oos_materials": ["Hedione HC"],
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
                for k, v in sorted(
                    best_wt_norm.items(), key=lambda kv: -kv[1]
                )
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
    r   = result
    opt = r["optimized"]["recipe_wt_pct"]
    sd  = r.get("stock_dilution", {})

    lines = [
        f"# {r['name']} — 30 mL EDP Mixing Guide",
        "",
        f"*{r['tagline']}*",
        "",
        "> **⚠️ HEDIONE HC — OUT OF STOCK**  ",
        "> This formula is the official OOS fallback for Vol d'Ambre v3.  ",
        "> Hedione (plain) replaces Hedione HC as the sole radiance carrier.  ",
        "> Expect a softer, rounder heart; all other v3 improvements intact.",
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
        "| Material | Stock | Neat µL in conc. | Neat % in EDP |",
        "|---|---|---:|---:|",
    ]

    for m, factor in sorted(sd.items()):
        wt = opt.get(m, 0.0)
        ul     = wt / 100.0 * CONCENTRATE_UL
        neat_u = ul * factor
        neat_e = neat_u / CONCENTRATE_UL * CONCENTRATE_PCT * 100
        lines.append(
            f"| {m} | {int(factor*100)}% | "
            f"≈{neat_u:.0f} µL | {neat_e:.3f}% |"
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
        f"| Fragrance concentrate | {CONCENTRATE_ML:.1f} mL "
        f"({CONCENTRATE_UL:.0f} µL) |",
        f"| Ethanol 96% (dilution) | "
        f"{BATCH_ML - CONCENTRATE_ML:.1f} mL ({ETHANOL_UL:.0f} µL) |",
        f"| Drop reference | {DROP_UL:.0f} µL / drop |",
        "",
        "> All volumes below are for the stock **as-held** (diluted or neat).",
        "",
        "---",
        "",
        "## Optimized Formula — 30 mL EDP  (No Hedione HC)",
        "",
        "| # | Material | Stock | wt% | µL | mL | ~Drops | Neat in EDP |",
        "|--:|---|---|---:|---:|---:|---:|---|",
    ]

    for i, m in enumerate(
        sorted(opt.keys(), key=lambda k: -opt[k]), start=1
    ):
        wt     = opt[m]
        ul     = wt / 100.0 * CONCENTRATE_UL
        drops  = ul / DROP_UL
        factor = sd.get(m, 1.0)
        neat_u = ul * factor
        neat_e = neat_u / CONCENTRATE_UL * CONCENTRATE_PCT * 100
        s_str  = f"{int(factor*100)}%" if factor < 1.0 else "neat"
        n_str  = f"{neat_e:.3f}%" if factor < 1.0 else "—"
        lines.append(
            f"| {i} | {m} | {s_str} | {wt:.2f} | {ul:.0f} | "
            f"{ul/1000:.3f} | {drops:.1f} | {n_str} |"
        )

    total_ul = sum(opt[m] / 100.0 * CONCENTRATE_UL for m in opt)
    eth_conc = CONCENTRATE_UL - total_ul
    lines += [
        f"| — | **Fragrance sub-total** | — | "
        f"**{sum(opt.values()):.2f}** | **{total_ul:.0f}** | "
        f"**{total_ul/1000:.3f}** | — | — |",
        f"| — | Ethanol 96% (in concentrate) | — | — | "
        f"{eth_conc:.0f} | {eth_conc/1000:.3f} | — | — |",
        f"| — | **Concentrate total** | — | — | "
        f"**{CONCENTRATE_UL:.0f}** | **{CONCENTRATE_ML:.3f}** | — | — |",
        f"| — | Ethanol 96% (bottle fill) | — | — | "
        f"**{ETHANOL_UL:.0f}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** "
        f"| — | — |",
        f"| — | **Final bottle total** | — | — | "
        f"**{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** | — | — |",
        "",
        "---",
        "",
        "## Family OAV Envelope (neat-equivalent, stock-dilution corrected)",
        "",
    ]

    for section, label in (
        ("initial",   "v3b Initial (corrected)"),
        ("optimized", "v3b Optimized"),
    ):
        lines.append(f"### {label}")
        for win in ("top", "heart", "base"):
            fams = r[section]["envelope"][win]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            lines.append(
                "- **" + win + "**: "
                + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
            )
        lines.append("")

    lines += [
        "### Target",
    ]
    for win in ("top", "heart", "base"):
        tgt  = r["envelope_target"][win]
        top6 = sorted(tgt.items(), key=lambda kv: -kv[1])[:6]
        lines.append(
            "- **" + win + "**: "
            + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
        )

    lines += [
        "",
        "---",
        "",
        "## Mixing Protocol",
        "",
        "1. Tare a clean 10 mL glass vial on a 0.001 g precision scale.",
        "2. **Base first:** musks, amber, balsamic, wood.",
        "3. **Heart:** Hedione (radiance), geranium, powdery, floral.",
        "4. **Top:** lavender, Dihydromyrcenol, fruity, citrus, spice.",
        "5. Top up concentrate with ethanol 96% to exactly **6.00 mL**.",
        "6. Seal; macerate **48 h minimum** before first evaluation.",
        "7. Transfer to 30 mL bottle; fill with **24.0 mL** ethanol 96%.",
        "8. Macerate finished EDP **2–4 weeks**.",
        "",
        "### Layering order (base → top)",
        "",
        "| Order | Material | Reason |",
        "|---|---|---|",
        "| 1 | Ethylene Brassylate, Habanolide, Romandolide "
        "| Slowest evaporators |",
        "| 2 | Galaxolide | Musk anchor |",
        "| 3 | Ambrox Super (30%) | Amber fixative |",
        "| 4 | Benzoin Resinoid (50%) | Balsamic base |",
        "| 5 | Vanillin (10%), Ethyl Vanillin, Coumarin (20%) "
        "| Sweet-hay-vanilla |",
        "| 6 | Iso E Super, Javanol, Sandalore | Wood-sandalwood body |",
        "| 7 | Alpha Isomethyl Ionone | Powdery bridge |",
        "| 8 | **Hedione** (sole radiance), Dihydrojasmone, Benzyl Acetate "
        "| Heart bloom |",
        "| 9 | Geraniol, Phenethyl Alcohol | Rose-geranium warmth |",
        "| 10 | Linalyl Acetate, Ethyl Linalool, Lavender EO | Lavender pillar |",
        "| 11 | Dihydromyrcenol | Watery-fresh facet |",
        "| 12 | Apritone (10%), Hexyl Acetate (10%), "
        "Ethyl 2-Methylbutyrate | Apple chord |",
        "| 13 | Cardamom FTEC (10%), Bergamot FCF | Top spice + citrus |",
        "",
        "---",
        "",
        "## Safety & Stock Notes",
        "",
        "- **Hedione HC — OUT OF STOCK.**  "
        "When restocked, rebuild from v3 recipe.",
        "- **Hedione (plain):** at the optimized dose this is the highest-volume "
        "  material in the concentrate.  Weigh carefully; it is a large but "
        "  benign addition.",
        "- **Vanillin (10% stock):** large volume by design — see v3 notes on "
        "  preparing a 50% stock for easier handling.",
        "- **Ethyl 2-Methylbutyrate (neat):** extreme potency; "
        "  1 µL error matters.",
        "- **Benzyl Acetate:** IFRA cap ~12.5% in concentrate; v3b is well under.",
        "- **Ambrox Super (30% stock):** keep neat ambroxan ≤ 3% in EDP.",
        "- **Cardamom FTEC (10% stock):** OAV weight uses "
        "  stock-corrected neat concentration.",
    ]

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    result = run_one(CONCEPT, maxiter=60, popsize=18, seed=42)

    root     = Path(__file__).parent
    json_out = root / "_opt_vol_dambre_v3b_out.json"
    json_out.write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/Vol_dAmbre_30mL_Layton_Inspired_v3b.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
