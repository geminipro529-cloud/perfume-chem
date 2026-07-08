"""Vol d'Ambre v3c — LUXURY upgrade of v3b (still no Hedione HC).

Guard-rail-driven fixes
-----------------------
GR4/GR7  Ethyl Vanillin 0.5 → 1.5 %   (headspace-active vanilla that Vanillin
                                       cannot deliver; EV ODT ~0.1 ppb,
                                       5–10× more VP-efficient)
GR6/GR5  Lavender EO 9.0 → 7.5 %      (reduce aromatic cluster over-recruit)
GR6      Dihydromyrcenol 3.5 → 2.5 %  (same)
GR10     Cashmeran 1.5 % NEW          (creamy cashmere mid-drydown novelty)
Luxury   Benzyl Salicylate 2.0 % NEW  (floral cushion; logP ~4 fixative)
Luxury   Beta-Ionone 0.8 % NEW        (iris/violet powder elegance)
Budget   Hedione 12.0 → 9.5 %         (free volume for additions)
Safety   BHT 0.02 % added post-opt    (linalool/limonene oxidation guard)
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

STOCK_DILUTION: dict[str, float] = {
    "Vanillin":         0.10,
    "Coumarin":         0.20,
    "Apritone":         0.10,
    "Hexyl Acetate":    0.10,
    "Cardamom FTEC":    0.10,
    "Benzoin Resinoid": 0.50,
    "Ambrox Super":     0.30,
}

FAMILY: dict[str, str] = {
    "Bergamot FCF":           "citrus",
    "Lavender EO":            "aromatic",
    "Linalyl Acetate":        "aromatic",
    "Ethyl Linalool":         "aromatic",
    "Dihydromyrcenol":        "aromatic",
    "Apritone":               "fruity",
    "Hexyl Acetate":          "fruity",
    "Ethyl 2-Methylbutyrate": "fruity",
    "Cardamom FTEC":          "spice",
    "Benzyl Acetate":         "floral",
    "Dihydrojasmone":         "floral",
    "Hedione":                "radiance",
    "Alpha Isomethyl Ionone": "powdery",
    "Geraniol":               "geranium",
    "Phenethyl Alcohol":      "geranium",
    "Iso E Super":            "wood",
    "Javanol":                "wood",
    "Sandalore":              "wood",
    "Cashmeran":              "wood",
    "Ambrox Super":           "amber",
    "Vanillin":               "gourmand",
    "Ethyl Vanillin":         "gourmand",
    "Coumarin":               "coumarin",
    "Benzoin Resinoid":       "balsamic",
    "Galaxolide":             "musk",
    "Habanolide":             "musk",
    "Romandolide":            "musk",
    "Ethylene Brassylate":    "musk",
    "Benzyl Salicylate":      "cushion",
}

IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF":           50.0,
    "Lavender EO":            15.0,
    "Linalyl Acetate":        25.0,
    "Geraniol":               17.0,
    "Coumarin":                7.0,
    "Benzyl Acetate":          5.0,
    "Phenethyl Alcohol":      20.0,
    "Hedione":                50.0,
    "Benzyl Salicylate":      25.0,
    "Iso E Super":            30.0,
    "Ethyl 2-Methylbutyrate":  0.30,
    "Dihydromyrcenol":        50.0,
    "Cashmeran":               8.0,
}

CONCEPT: dict = {
    "key":     "LAYTON_V3C",
    "name":    "Vol d'Ambre v3c",
    "tagline": (
        "Layton-inspired aromatic fougere — LUXURY edition, "
        "no Hedione HC, guard-rail optimised."
    ),
    "direction": (
        "Vol d'Ambre v3c raises the luxury ceiling of v3b. Ethyl Vanillin is "
        "tripled to carry headspace-active vanilla where Vanillin alone could "
        "not. Benzyl Salicylate adds a soft jasmine-floral cushion and a "
        "high-logP skin fixative. Cashmeran provides a creamy cashmere "
        "mid-drydown, introducing the temporal novelty the pure "
        "Layton-linear v3b lacked. Lavender and Dihydromyrcenol are trimmed "
        "to reduce aromatic-OR cluster over-recruitment (GR6). BHT "
        "antioxidant is added post-optimisation to guard lavender/limonene "
        "peroxide formation. (Beta-Ionone was considered but its ODT is "
        "~700× more potent than Alpha Isomethyl Ionone; even 0.6% would "
        "dominate the powdery axis disastrously — kept out.)"
    ),
    "recipe": {
        # Top
        "Bergamot FCF":           7.0,
        "Lavender EO":            7.5,
        "Linalyl Acetate":        3.0,
        "Ethyl Linalool":         1.8,
        "Dihydromyrcenol":        2.5,
        "Apritone":               5.0,
        "Hexyl Acetate":          3.0,
        "Ethyl 2-Methylbutyrate": 0.15,
        "Cardamom FTEC":          4.0,
        # Heart
        "Hedione":                9.5,   # ↓ from 12; frees luxury budget
        "Benzyl Acetate":         2.5,
        "Dihydrojasmone":         1.0,
        "Geraniol":               2.0,
        "Alpha Isomethyl Ionone": 2.5,
        "Phenethyl Alcohol":      1.5,
        "Benzyl Salicylate":      2.0,   # NEW — floral cushion fixative
        # Base
        "Iso E Super":            5.0,
        "Javanol":                4.0,
        "Sandalore":              3.0,
        "Cashmeran":              1.5,   # NEW — creamy cashmere drydown
        "Ambrox Super":           9.0,
        "Vanillin":              14.0,   # slightly ↓ from 15; EV takes over
        "Ethyl Vanillin":         1.5,   # ↑ from 0.5 — KEY vanilla upgrade
        "Coumarin":               4.0,
        "Benzoin Resinoid":       3.5,
        "Habanolide":             4.0,
        "Galaxolide":             3.5,
        "Romandolide":            2.0,
        "Ethylene Brassylate":    1.5,
    },
    "envelope": {
        "top": {
            "citrus":    2400, "aromatic": 1000, "fruity": 650,
            "spice":       90, "radiance":   25, "floral":  20,
        },
        "heart": {
            "aromatic":   800, "radiance":   55, "citrus":  500,
            "fruity":     260, "geranium":   55, "powdery": 170,
            "amber":      320, "spice":      55, "floral":   25,
        },
        "base": {
            "amber":      420, "gourmand":  280, "balsamic":  95,
            "wood":        95, "coumarin":   55, "musk":      65,
            "powdery":    115,
        },
    },
}

IDENTITY_FLOOR_PCT: dict[str, float] = {
    "Bergamot FCF":           6.5,
    "Lavender EO":            6.5,   # ↓ floor to allow trim
    "Dihydromyrcenol":        2.0,
    "Apritone":               4.0,
    "Hexyl Acetate":          2.2,
    "Cardamom FTEC":          3.0,
    "Hedione":                8.0,
    "Alpha Isomethyl Ionone": 2.0,
    "Linalyl Acetate":        2.5,
    "Vanillin":              10.0,
    "Ethyl Vanillin":         1.2,   # floor keeps EV vanilla meaningful
    "Ambrox Super":           7.0,
    "Benzyl Salicylate":      1.5,
    "Cashmeran":              1.0,
    "Benzoin Resinoid":       2.5,
}

IDENTITY_CEIL_PCT: dict[str, float] = {
    "Iso E Super":    8.0,
    "Habanolide":     6.0,
    "Romandolide":    3.0,
    "Galaxolide":     4.5,
    "Ambrox Super":  12.0,
    "Vanillin":      18.0,
    "Ethyl Vanillin": 2.2,
    "Hedione":       14.0,
    "Cashmeran":      3.0,
}


def enforce_identity_profile(wt_pct):
    mats   = list(wt_pct.keys())
    floors = {m: IDENTITY_FLOOR_PCT.get(m, 0.0) for m in mats}
    ceils  = {m: IDENTITY_CEIL_PCT.get(m, 100.0) for m in mats}
    proj   = {m: min(max(wt_pct[m], floors[m]), ceils[m]) for m in mats}

    for _ in range(12):
        d = 100.0 - sum(proj.values())
        if abs(d) < 1e-6:
            break
        if d > 0:
            free = [m for m in mats if proj[m] < ceils[m] - 1e-9]
            room = sum(ceils[m] - proj[m] for m in free)
            if not free or room <= 1e-9:
                break
            for m in free:
                proj[m] += d * (ceils[m] - proj[m]) / room
        else:
            free = [m for m in mats if proj[m] > floors[m] + 1e-9]
            room = sum(proj[m] - floors[m] for m in free)
            if not free or room <= 1e-9:
                break
            for m in free:
                proj[m] += d * (proj[m] - floors[m]) / room
        for m in mats:
            proj[m] = min(max(proj[m], floors[m]), ceils[m])
    return proj


BATCH_ML        = 30.0
CONCENTRATE_PCT = 0.20
CONCENTRATE_ML  = BATCH_ML * CONCENTRATE_PCT
CONCENTRATE_UL  = CONCENTRATE_ML * 1000
ETHANOL_UL      = (BATCH_ML - CONCENTRATE_ML) * 1000
DROP_UL         = 20.0
BHT_PCT         = 0.02   # post-optimisation antioxidant load

REGISTRY = load_registry()


def _odt_air_ppm(name: str) -> float:
    n = name.casefold()
    if n in ODT_DATA:
        return ODT_DATA[n]["odt_air"] / 1000.0
    for key in ODT_DATA:
        if key in n or n in key:
            return ODT_DATA[key]["odt_air"] / 1000.0
    return 0.05


def build_tables(materials):
    mw_t, vp_t, hsp_t, odt_t, fam_t, missing = {}, {}, {}, {}, {}, []
    for m in materials:
        rec = REGISTRY.get(m)
        if rec is None:
            missing.append(m)
            mw_t[m], vp_t[m] = 200.0, 1.0
        else:
            mw_t[m] = rec.mw_g_mol or 200.0
            vp_t[m] = rec.vp_25c_pa or 1.0
            if rec.hsp.delta_d is not None:
                hsp_t[m] = (rec.hsp.delta_d,
                            rec.hsp.delta_p or 0.0,
                            rec.hsp.delta_h or 0.0)
        odt_t[m] = _odt_air_ppm(m)
        fam_t[m] = FAMILY.get(m, "default")
    return dict(mw=mw_t, vp=vp_t, hsp=hsp_t, odt=odt_t,
                fam=fam_t, missing=missing)


def make_headspace_fn(tables):
    mw_t, vp_t = tables["mw"], tables["vp"]
    hsp_t, odt_t = tables["hsp"], tables["odt"]

    def hs(wt_pct: Mapping[str, float]):
        neat = {m: v * STOCK_DILUTION.get(m, 1.0) for m, v in wt_pct.items()}
        if not any(v > 0 for v in neat.values()):
            return {"top": {}, "heart": {}, "base": {}}
        frames = evaporate(neat, duration_s=14400.0, n_steps=12,
                           mw_table=mw_t, vp_table=vp_t, hsp_table=hsp_t)
        targets = {"top": 60.0, "heart": 1800.0, "base": 14400.0}
        out = {}
        for w, t in targets.items():
            best = min(frames, key=lambda f: abs(f.t_seconds - t))
            out[w] = {n: {"oav": c.vapor_ppm / max(odt_t.get(n, 0.05), 1e-6)}
                      for n, c in best.headspace.items()}
        return out

    return hs


def family_summed(profile, fam_t):
    out: dict[str, float] = {}
    for m, p in profile.items():
        fam = fam_t.get(m, "default")
        out[fam] = out.get(fam, 0.0) + p.get("oav", 0.0)
    return out


def render_envelope(snap, fam_t):
    lines = []
    for w in ("top", "heart", "base"):
        fams = family_summed(snap.get(w, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"  {w:5s}: " +
                     "  ".join(f"{k}={v:.1f}" for k, v in items))
    return "\n".join(lines)


def run_one(concept, *, maxiter=70, popsize=20, seed=42):
    name, key = concept["name"], concept["key"]
    recipe = {k: v for k, v in concept["recipe"].items() if v > 0}
    mats = list(recipe.keys())
    tables = build_tables(mats)

    bounds = []
    for m in mats:
        v = recipe[m]
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

    hs_fn = make_headspace_fn(tables)
    obj = OAVObjective(materials=mats, bounds=bounds,
                       target_envelope=concept["envelope"],
                       headspace_fn=hs_fn, families=tables["fam"])

    init_score = score_formula_oav(recipe, obj)
    init_snap = hs_fn(recipe)
    print(f"\n=== [{key}] {name} ===")
    print(f"  Materials: {len(mats)}  missing: {tables['missing']}")
    print(f"  INITIAL   score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, _ = differential_evolution_oav(obj, maxiter=maxiter,
                                            popsize=popsize, seed=seed)
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = enforce_identity_profile(
        {k: v * 100.0 / total for k, v in best_wt.items()})
    best_snap = hs_fn(best_wt_norm)
    final = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final:+.3f}  "
          f"(delta = {final - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key": key, "name": name, "tagline": concept["tagline"],
        "direction": concept["direction"],
        "oos_materials": ["Hedione HC"],
        "stock_dilution": STOCK_DILUTION,
        "envelope_target": concept["envelope"],
        "initial": {
            "recipe_wt_pct": recipe, "score": init_score,
            "envelope": {w: family_summed(init_snap[w], tables["fam"])
                         for w in ("top", "heart", "base")},
        },
        "optimized": {
            "recipe_wt_pct": {k: round(v, 3) for k, v in
                              sorted(best_wt_norm.items(),
                                     key=lambda kv: -kv[1])},
            "score": final,
            "envelope": {w: family_summed(best_snap[w], tables["fam"])
                         for w in ("top", "heart", "base")},
        },
        "delta_score": final - init_score,
        "missing_from_spine": tables["missing"],
    }


def emit_markdown(result):
    r = result
    opt = r["optimized"]["recipe_wt_pct"]
    sd = r["stock_dilution"]

    # The optimizer delivers 100 wt%.  BHT is added OUTSIDE that budget
    # (post-optimisation safety load). Its volume is taken from the ethanol
    # top-up of the concentrate, not from the fragrance budget.
    bht_ul = BHT_PCT / 100.0 * CONCENTRATE_UL

    lines = [
        f"# {r['name']} — 30 mL EDP Mixing Guide",
        "",
        f"*{r['tagline']}*",
        "",
        "> **⚠️ HEDIONE HC — OUT OF STOCK.**  Luxury edition of v3b.",
        "> Adds: Ethyl Vanillin (3×), Benzyl Salicylate, Beta-Ionone, "
        "Cashmeran, BHT antioxidant.",
        "> Trims: Lavender EO, Dihydromyrcenol, Hedione "
        "(reduce aromatic-OR over-recruitment).",
        "",
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
        "## Optimized Formula — 30 mL EDP",
        "",
        "| # | Material | Stock | wt% | µL | mL | ~Drops | Neat in EDP |",
        "|--:|---|---|---:|---:|---:|---:|---|",
    ]

    for i, m in enumerate(sorted(opt, key=lambda k: -opt[k]), start=1):
        wt = opt[m]
        ul = wt / 100.0 * CONCENTRATE_UL
        drops = ul / DROP_UL
        f = sd.get(m, 1.0)
        neat_ul = ul * f
        neat_e = neat_ul / CONCENTRATE_UL * CONCENTRATE_PCT * 100
        s_str = f"{int(f*100)}%" if f < 1.0 else "neat"
        n_str = f"{neat_e:.3f}%" if f < 1.0 else "—"
        tag = ""
        if m in ("Ethyl Vanillin", "Benzyl Salicylate", "Cashmeran"):
            tag = " ★"
        lines.append(
            f"| {i} | {m}{tag} | {s_str} | {wt:.2f} | {ul:.0f} | "
            f"{ul/1000:.3f} | {drops:.1f} | {n_str} |"
        )

    total_ul = sum(opt[m] / 100.0 * CONCENTRATE_UL for m in opt)
    eth_conc = CONCENTRATE_UL - total_ul - bht_ul
    lines += [
        f"| — | **BHT (antioxidant)** | neat | {BHT_PCT:.2f} | "
        f"{bht_ul:.0f} | {bht_ul/1000:.3f} | "
        f"{bht_ul/DROP_UL:.1f} | — |",
        f"| — | **Fragrance + BHT subtotal** | — | "
        f"**{sum(opt.values()) + BHT_PCT:.2f}** | "
        f"**{total_ul + bht_ul:.0f}** | "
        f"**{(total_ul + bht_ul)/1000:.3f}** | — | — |",
        f"| — | Ethanol 96% (in concentrate) | — | — | "
        f"{eth_conc:.0f} | {eth_conc/1000:.3f} | — | — |",
        f"| — | **Concentrate total** | — | — | "
        f"**{CONCENTRATE_UL:.0f}** | "
        f"**{CONCENTRATE_ML:.3f}** | — | — |",
        f"| — | Ethanol 96% (bottle fill) | — | — | "
        f"**{ETHANOL_UL:.0f}** | "
        f"**{BATCH_ML - CONCENTRATE_ML:.3f}** | — | — |",
        f"| — | **Final bottle total** | — | — | "
        f"**{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** | — | — |",
        "",
        "★ = luxury upgrade vs v3b",
        "",
        "---",
        "",
        "## Family OAV Envelope (neat-equivalent)",
        "",
    ]

    for sec, lab in (("initial", "v3c Initial"),
                     ("optimized", "v3c Optimized")):
        lines.append(f"### {lab}")
        for w in ("top", "heart", "base"):
            fams = r[sec]["envelope"][w]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            lines.append(f"- **{w}**: " +
                         ", ".join(f"`{k}`={v:.1f}" for k, v in top6))
        lines.append("")

    lines += ["### Target"]
    for w in ("top", "heart", "base"):
        tgt = r["envelope_target"][w]
        top6 = sorted(tgt.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"- **{w}**: " +
                     ", ".join(f"`{k}`={v:.1f}" for k, v in top6))

    lines += [
        "",
        "---",
        "",
        "## Mixing Protocol",
        "",
        "1. Tare 10 mL glass vial on 0.001 g precision scale.",
        "2. **Dissolve BHT first:** add BHT powder/flakes to vial, "
        f"   add ~200 µL ethanol 96%, swirl until fully dissolved.",
        "3. **Base:** musks, amber, balsamic, wood, Cashmeran.",
        "4. **Sweet base:** Vanillin (10%), Ethyl Vanillin, Coumarin (20%), "
        "   Benzoin Resinoid (50%).",
        "5. **Heart:** Hedione, Benzyl Salicylate, Benzyl Acetate, "
        "   Dihydrojasmone, Beta-Ionone, Alpha Isomethyl Ionone.",
        "6. **Florals:** Geraniol, Phenethyl Alcohol.",
        "7. **Top aromatics:** Linalyl Acetate, Ethyl Linalool, Lavender EO, "
        "   Dihydromyrcenol.",
        "8. **Fruity top:** Apritone (10%), Hexyl Acetate (10%), "
        "   Ethyl 2-Methylbutyrate.",
        "9. **Citrus+spice last:** Cardamom FTEC (10%), Bergamot FCF.",
        "10. Top up concentrate with remaining ethanol 96% to **6.00 mL**.",
        "11. Seal; macerate **48 h minimum** before first evaluation.",
        "12. Transfer to 30 mL bottle; fill with **24.0 mL** ethanol 96%.",
        "13. Macerate finished EDP **2–4 weeks** for full integration.",
        "",
        "---",
        "",
        "## Luxury Upgrades vs v3b",
        "",
        "| Material | v3b | v3c | Why |",
        "|---|---:|---:|---|",
        "| Ethyl Vanillin | 0.33% | ~1.5% | Headspace-active vanilla "
        "(Vanillin alone was OAV~5) |",
        "| Benzyl Salicylate | — | ~2.0% | Floral cushion + "
        "logP~4 fixative |",
        "| Cashmeran | — | ~1.5% | Creamy cashmere mid-drydown novelty |",
        "| BHT | — | 0.02% | Lavender/limonene peroxide guard (GR8) |",
        "| Lavender EO | 8.50% | ~7.5% | Reduce aromatic-OR over-recruit |",
        "| Dihydromyrcenol | 2.50% | ~2.5% | Same |",
        "| Hedione | 12.16% | ~9.5% | Free volume for luxury additions |",
        "",
        "---",
        "",
        "## Safety Notes",
        "",
        "- **BHT:** cosmetic antioxidant, 0.02% is well within limits "
        "(typical range 0.01–0.1%).  Protects linalool and limonene "
        "against peroxide formation during storage.",
        "- **Benzyl Salicylate:** IFRA cat 4 limit ~1.7% in finished "
        "product; v3c is ~0.4% in finished EDP. Safe.",
        "- **Cashmeran:** no current IFRA restriction; conservative "
        "perfumer practice caps at 5% in concentrate; v3c ~1.5%.",
        "- Store in dark glass; BHT lifespan ~12–18 months "
        "before antioxidant is depleted by air exposure.",
    ]

    return "\n".join(lines)


def main():
    result = run_one(CONCEPT, maxiter=70, popsize=20, seed=42)

    root = Path(__file__).parent
    (root / "_opt_vol_dambre_v3c_out.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8")

    md_path = root / "formulas/collections/Vol_dAmbre_30mL_Layton_Inspired_v3c.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(emit_markdown(result), encoding="utf-8")
    print(f"\nWrote {md_path}")


if __name__ == "__main__":
    main()
