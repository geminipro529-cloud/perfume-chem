"""Vol d'Ambre — Layton-inspired mass-appeal aromatic fougère, 30 mL EDP.

OAV differential-evolution optimizer (same engine as _fougere_5_named_v2.py).
Outputs a 30 mL mixing guide with µL / mL / drop counts.

Batch spec:
  20% concentrate EDP — 6 mL fragrance concentrate + 24 mL ethanol 96%
  Volumes in the mixing guide are of the stock as-held in inventory
  (diluted or neat). No conversion needed.
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

# ── Material → olfactive family ───────────────────────────────────────────────
FAMILY: dict[str, str] = {
    # Citrus / top
    "Bergamot FCF":             "citrus",
    "Bergamot FCF oil Sicilian": "citrus",
    "Grapefruit FCF":           "citrus",
    "Red Mandarin EO":          "citrus",
    "Blood Orange oil Sicilian": "citrus",
    "D-Limonene":               "citrus",
    "Citral":                   "citrus",
    "Lemonile":                 "citrus",
    # Aromatic / lavender
    "Lavender EO":              "aromatic",
    "Linalool":                 "aromatic",
    "Linalyl Acetate":          "aromatic",
    "Ethyl Linalool":           "aromatic",
    "Clary Sage EO":            "aromatic",
    # Fruity / apple
    "Apritone":                 "fruity",
    "Hexyl Acetate":            "fruity",
    "Ethyl 2-Methylbutyrate":   "fruity",
    "Dynascone":                "fruity",
    "Raspberry Ketone":         "fruity",
    # Spice
    "Cardamom FTEC":            "spice",
    "Eugenol":                  "spice",
    "Isoeugenol":               "spice",
    "Ethyl Safranate":          "spice",
    "Black Pepper FTEC":        "spice",
    "Pink Pepper Base":         "spice",
    # Floral / jasmine
    "Benzyl Acetate":           "floral",
    "Dihydrojasmone":           "floral",
    "Cis Jasmone":              "floral",
    "Methyl Benzoate":          "floral",
    "Hedione":                  "radiance",
    "Hedione HC":               "radiance",
    # Powdery / violet / iris
    "Alpha Isomethyl Ionone":   "powdery",
    "Alpha Ionone":             "powdery",
    "Beta Ionone":              "powdery",
    "Allyl Ionone":             "powdery",
    # Geranium / rose
    "Geraniol":                 "geranium",
    "Citronellol":              "geranium",
    "Phenethyl Alcohol":        "geranium",
    # Wood / structure
    "Iso E Super":              "wood",
    "Javanol":                  "wood",
    "Sandalore":                "wood",
    "Ebanol":                   "wood",
    "Bacdanol":                 "wood",
    "Cedarwood EO":             "wood",
    "Cedarwood oil Virginia":   "wood",
    "Vetiver EO":               "wood",
    "Patchouli EO":             "wood",
    "Clearwood":                "wood",
    "Timberol":                 "wood",
    "Polysantol":               "wood",
    "Cashmeran":                "wood",
    # Amber / ambrox
    "Ambrox Super":             "amber",
    "Ambrofix":                 "amber",
    "Ambermax":                 "amber",
    "Amberwood F":              "amber",
    "Cedramber":                "amber",
    "Azarbre":                  "amber",
    # Gourmand / sweet
    "Vanillin":                 "gourmand",
    "Ethyl Vanillin":           "gourmand",
    "Ethyl Maltol":             "gourmand",
    "Maple Lactone":            "gourmand",
    "Anisaldehyde":             "gourmand",
    "Heliotropal":              "gourmand",
    # Coumarin / hay
    "Coumarin":                 "coumarin",
    # Balsamic / resinous
    "Benzoin Resinoid":         "balsamic",
    "Siam Benzoin":             "balsamic",
    "Benzoin Sumatra Resinoid": "balsamic",
    # Musk
    "Galaxolide":               "musk",
    "Habanolide":               "musk",
    "Romandolide":              "musk",
    "Ethylene Brassylate":      "musk",
    "Exaltolide":               "musk",
    "Ambrettolide":             "musk",
    "Zenolide":                 "musk",
    "Macrolide":                "musk",
    # Cushion / fixative
    "Hexyl Salicylate":         "cushion",
    "Benzyl Salicylate":        "cushion",
    "Benzyl Benzoate":          "cushion",
}

# IFRA caps at concentrate level (fine fragrance Category 4, conservative)
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF":           50.0,
    "Lavender EO":            15.0,
    "Linalool":               25.0,
    "Linalyl Acetate":        25.0,
    "Geraniol":               17.0,
    "Citronellol":            25.0,
    "Coumarin":                7.0,
    "Benzyl Acetate":          5.0,   # skin sensitiser
    "Phenethyl Alcohol":      20.0,
    "Hedione":                50.0,
    "Hexyl Salicylate":       12.5,
    "Benzyl Salicylate":      25.0,
    "Iso E Super":            60.0,
    "Eugenol":                 2.5,
    "Isoeugenol":              1.0,
    "Citral":                  5.0,
    "Ethyl 2-Methylbutyrate":  0.30,  # odour-impact cap
}

# ── Formula ───────────────────────────────────────────────────────────────────
# wt% of fragrance concentrate; volumes scale directly from stock as-held.
CONCEPT: dict = {
    "key":     "LAYTON",
    "name":    "Vol d'Ambre",
    "tagline": "Layton-inspired mass-appeal aromatic fougère — sweet apple, lavender, cardamom, vanilla-sandalwood.",
    "direction": (
        "A lush, sweet aromatic fougère in the Parfums de Marly Layton lineage. "
        "Bergamot + fruity-apple chord (Apritone / Hexyl Acetate / Ethyl 2-Methylbutyrate) "
        "opens bright and accessible; Cardamom FTEC adds the signature spice warmth; "
        "Lavender EO + Linalyl Acetate + Ethyl Linalool form a full, sweet lavender pillar. "
        "The heart blooms with Hedione HC radiance, Geraniol rose-warmth, and Alpha "
        "Isomethyl Ionone violet-powder softness. The drydown is the real strength: "
        "Ambrox Super skin-musk, Javanol + Sandalore creamy sandalwood, Vanillin + "
        "Ethyl Vanillin vanilla warmth, Benzoin Resinoid balsamic depth, Coumarin hay "
        "sweetness — rich, enveloping, intimate. "
        "Direction: mass appeal → maximise fruity-aromatic top energy; drive amber in "
        "drydown; keep sweet without going gourmand-dark; no oakmoss/moss bitterness; "
        "sandalwood must read as creamy/milky (Javanol-led)."
    ),
    "recipe": {
        # ── Top — citrus / aromatic / fruity / spice ──────────────────────
        "Bergamot FCF":             8.0,
        "Lavender EO":             10.0,
        "Linalyl Acetate":          3.0,
        "Ethyl Linalool":           2.0,
        "Apritone":                 3.5,   # 10% stock
        "Hexyl Acetate":            2.5,   # 10% stock
        "Ethyl 2-Methylbutyrate":   0.15,  # neat — very powerful, keep tight
        "Cardamom FTEC":            3.0,   # 10% stock
        # ── Heart — radiance / floral / geranium / powdery ───────────────
        "Hedione HC":               7.0,
        "Hedione":                  5.0,
        "Benzyl Acetate":           2.0,
        "Dihydrojasmone":           1.0,
        "Geraniol":                 2.5,
        "Alpha Isomethyl Ionone":   2.5,
        "Phenethyl Alcohol":        1.5,
        # ── Base — wood / amber / gourmand / musk ────────────────────────
        "Iso E Super":              8.0,
        "Javanol":                  4.0,
        "Sandalore":                3.0,
        "Ambrox Super":             7.0,   # 30% stock
        "Vanillin":                 5.0,   # 10% stock
        "Ethyl Vanillin":           0.5,
        "Coumarin":                 3.5,   # 20% stock
        "Benzoin Resinoid":         3.0,   # 50% stock
        "Habanolide":               5.0,
        "Galaxolide":               4.0,   # 100% neat
        "Romandolide":              2.5,
        "Ethylene Brassylate":      1.5,
    },
    # Target OAV envelope — mass-appeal aromatic fougère
    # Calibrated to realistic per-window magnitudes for this material set.
    "envelope": {
        "top": {
            "citrus":    2600,
            "aromatic":  1100,
            "fruity":     700,
            "spice":      110,
            "radiance":    40,
        },
        "heart": {
            "aromatic":   850,
            "radiance":    80,
            "citrus":     650,
            "fruity":     250,
            "geranium":    70,
            "powdery":    180,
            "amber":      700,
            "spice":       75,
        },
        "base": {
            "amber":     1600,
            "gourmand":   380,
            "balsamic":   150,
            "wood":       100,
            "coumarin":    70,
            "musk":        55,
            "powdery":    120,
        },
    },
}

# ── Batch parameters ──────────────────────────────────────────────────────────
BATCH_ML        = 30.0
CONCENTRATE_PCT = 0.20                           # 20% EDP
CONCENTRATE_ML  = BATCH_ML * CONCENTRATE_PCT     # 6.0 mL
CONCENTRATE_UL  = CONCENTRATE_ML * 1000          # 6000 µL
ETHANOL_UL      = (BATCH_ML - CONCENTRATE_ML) * 1000   # 24000 µL
DROP_UL         = 20.0                           # 1 drop ≈ 20 µL

# ── Engine helpers (identical to _fougere_5_named_v2.py) ─────────────────────
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
    mw_t, vp_t, hsp_t, odt_t = tables["mw"], tables["vp"], tables["hsp"], tables["odt"]

    def headspace_fn(wt_pct: Mapping[str, float]) -> dict[str, dict[str, float]]:
        if not any(v > 0 for v in wt_pct.values()):
            return {"top": {}, "heart": {}, "base": {}}
        frames = evaporate(
            wt_pct, duration_s=14400.0, n_steps=12,
            mw_table=mw_t, vp_table=vp_t, hsp_table=hsp_t,
        )
        targets = {"top": 60.0, "heart": 1800.0, "base": 14400.0}
        out = {}
        for win, tgt in targets.items():
            best = min(frames, key=lambda f: abs(f.t_seconds - tgt))
            out[win] = {n: {"oav": c.vapor_ppm / max(odt_t.get(n, 0.05), 1e-6)}
                        for n, c in best.headspace.items()}
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
        fams = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"  {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items))
    return "\n".join(lines)


def run_one(
    concept: dict, *, maxiter: int = 50, popsize: int = 16, seed: int = 42
) -> dict:
    name, key = concept["name"], concept["key"]
    recipe = {k: v for k, v in concept["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables = build_tables(materials)

    bounds = []
    for m in materials:
        v = recipe[m]
        lo = max(0.0, v * 0.60)
        hi = v * 1.50
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.5:                    # trace materials — allow 2.5× headroom
            hi = max(hi, v * 2.5)
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
    print(f"  INITIAL   score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, best_score = differential_evolution_oav(
        obj, maxiter=maxiter, popsize=popsize, seed=seed
    )
    total         = sum(best_wt.values()) or 1.0
    best_wt_norm  = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap     = headspace_fn(best_wt_norm)
    final_score   = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final_score:+.3f}   (delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key":     key,
        "name":    name,
        "tagline": concept["tagline"],
        "direction": concept["direction"],
        "envelope_target": concept["envelope"],
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
    r   = result
    opt  = r["optimized"]["recipe_wt_pct"]
    init = r["initial"]["recipe_wt_pct"]

    lines = [
        f"# {r['name']} — 30 mL EDP Mixing Guide",
        "",
        f"*{r['tagline']}*",
        "",
        "**Status:** OAV differential-evolution optimized (DE/rand/1/bin, 50 generations).",
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
        "| # | Material | wt% | µL | mL | ~Drops |",
        "|--:|---|---:|---:|---:|---:|",
    ]

    all_mats = sorted(opt.keys(), key=lambda k: -opt[k])
    for i, m in enumerate(all_mats, start=1):
        wt    = opt[m]
        ul    = wt / 100.0 * CONCENTRATE_UL
        drops = ul / DROP_UL
        lines.append(
            f"| {i} | {m} | {wt:.2f} | {ul:.0f} | {ul/1000:.3f} | {drops:.1f} |"
        )

    total_wt   = sum(opt.values())
    total_conc = total_wt / 100.0 * CONCENTRATE_UL
    ethanol_conc = CONCENTRATE_UL - total_conc

    lines += [
        f"| — | **Fragrance sub-total** | **{total_wt:.2f}** | **{total_conc:.0f}** | **{total_conc/1000:.3f}** | — |",
        f"| — | Ethanol 96% (in concentrate) | — | {ethanol_conc:.0f} | {ethanol_conc/1000:.3f} | — |",
        f"| — | **Concentrate total** | — | **{CONCENTRATE_UL:.0f}** | **{CONCENTRATE_ML:.3f}** | — |",
        f"| — | Ethanol 96% (bottle fill) | — | **{ETHANOL_UL:.0f}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** | — |",
        f"| — | **Final bottle total** | — | **{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** | — |",
        "",
        "---",
        "",
        "## wt% Comparison (Initial → Optimized)",
        "",
        "| Material | Initial | Optimized | Δ |",
        "|---|---:|---:|---:|",
    ]
    all_keys = sorted(set(init) | set(opt), key=lambda k: -opt.get(k, 0))
    for m in all_keys:
        iv = init.get(m, 0.0)
        ov = opt.get(m, 0.0)
        lines.append(f"| {m} | {iv:.2f} | {ov:.2f} | {ov - iv:+.2f} |")

    lines += [
        "",
        "---",
        "",
        "## Family OAV Envelope",
        "",
        "| Window | Family axes (OAV) |",
        "|---|---|",
    ]
    for section, label in (("initial", "Initial"), ("optimized", "Optimized")):
        lines.append(f"", )
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
        "2. **Base first:** add ambers, musks, balsamic, and wood materials.",
        "3. **Heart:** add radiance (Hedione), geranium, powdery, and floral materials.",
        "4. **Top:** add lavender, fruity, citrus, and spice materials last.",
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
        "| 3 | Ambrox Super | Amber fixative |",
        "| 4 | Benzoin Resinoid | Balsamic base |",
        "| 5 | Vanillin, Ethyl Vanillin, Coumarin | Sweet-hay structure |",
        "| 6 | Iso E Super, Javanol, Sandalore | Wood-sandalwood body |",
        "| 7 | Alpha Isomethyl Ionone | Powdery bridge |",
        "| 8 | Hedione HC, Hedione, Dihydrojasmone, Benzyl Acetate | Radiance + jasmine heart |",
        "| 9 | Geraniol, Phenethyl Alcohol | Rose-geranium warmth |",
        "| 10 | Linalyl Acetate, Ethyl Linalool, Lavender EO | Lavender pillar |",
        "| 11 | Apritone, Hexyl Acetate, Ethyl 2-Methylbutyrate | Apple chord |",
        "| 12 | Cardamom FTEC, Bergamot FCF | Top spice + citrus |",
        "",
        "---",
        "",
        "## Safety Notes",
        "",
        "- **Ethyl 2-Methylbutyrate** (neat): extreme odour potency. Measure carefully;",
        "  a 1 µL error at this dose range changes the apple character materially.",
        "- **Benzyl Acetate**: skin sensitiser — stay within IFRA Category 4 limits",
        "  (~2.5% in finished product; at 20% EDP this permits up to ~12.5% in concentrate).",
        "- **Ambrox Super** (30% stock): IFRA has no concentration cap for ambroxan in",
        "  fine fragrance but keep finished product ≤ 3% neat for skin comfort.",
        "- **Cardamom FTEC** (10% stock): FTEC — registry uses default thermodynamic",
        "  values; optimized proportion is based on OAV weighting, not evaporation curve.",
    ]
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    result = run_one(CONCEPT, maxiter=50, popsize=16, seed=42)

    root     = Path(__file__).parent
    json_out = root / "_opt_vol_dambre_out.json"
    json_out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/Vol_dAmbre_30mL_Layton_Inspired.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
