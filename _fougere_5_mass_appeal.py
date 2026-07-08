"""Five mass-appeal fougère recipes — VP/OAV-relative formulation, then DE optimization.

Per user rules (2026-04-23):
  * No batch-volume formulas — express as wt% of fragrance concentrate.
  * No FTECs / Fleuressences / FOs / Cores / Accord-bases — single molecules + EOs only.

Pipeline:
  1. Define 5 fougère starting recipes (wt% concentrate, sums to 100).
  2. Pull MW / VP / HSP from data spine; ODT from engine.odor_thresholds.
  3. Family-classify each material (lavender/aromatic, citrus, geranium-rose,
     coumarinic, woody, mossy, amber, musk, gourmand, marine/aquatic, …).
  4. Use engine.thermo.trajectory.evaporate to get top (60 s) / heart (30 min) /
     base (4 h) headspace snapshots; convert vapor ppm to OAV via ODT.
  5. Score against per-fougère target envelope (family-summed OAV per window).
  6. DE-optimize wt% within ±50 % per-material bounds, IFRA caps applied as
     hard upper bounds.
  7. Print before/after envelopes + score deltas; write JSON + Markdown files.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping

from engine.data_spine.loader import load_registry
from engine.odor_thresholds import ODT_DATA
from engine.thermo.trajectory import evaporate
from engine.optimizer.oav_objective import OAVObjective, differential_evolution_oav


# ─────────────────────────────────────────────────────────────────────────────
# 1. Family map for fougère grammar (axes the brief targets)
# ─────────────────────────────────────────────────────────────────────────────

FAMILY: dict[str, str] = {
    # Lavender / aromatic (the fougère core)
    "Lavender EO":                "aromatic",
    "Linalool":                   "aromatic",
    "Linalyl Acetate":            "aromatic",
    "Ethyl Linalool":             "aromatic",
    "Clary Sage EO":              "aromatic",
    "Eucalyptol":                 "aromatic",
    # Citrus / hesperidic top
    "Bergamot FCF":               "citrus",
    "Bergamot FCF oil Sicilian":  "citrus",
    "Grapefruit FCF":             "citrus",
    "Red Mandarin EO":            "citrus",
    "Blood Orange oil Sicilian":  "citrus",
    "D-Limonene":                 "citrus",
    "Citral":                     "citrus",
    # Geranium-rose accent
    "Geraniol":                   "geranium",
    "Citronellol":                "geranium",
    "Phenethyl Alcohol":          "geranium",
    # Coumarinic / hay (the fougère drydown signature)
    "Coumarin":                   "coumarin",
    "Tonka Bean FO":              "coumarin",  # only if user adds; we avoid
    # Aquatic / marine (modern fresh fougère)
    "Calone":                     "marine",
    "Floralozone":                "marine",
    "Dihydromyrcenol":            "marine",
    # Spice (pink pepper, eugenol — often in modern fougères)
    "Eugenol":                    "spice",
    "Pink Pepper Base":           "spice",
    "Cardamom FTEC":              "spice",  # avoid
    "Black Pepper FTEC":          "spice",  # avoid
    # Woody structure
    "Iso E Super":                "wood",
    "Cedarwood EO":               "wood",
    "Cedarwood oil Virginia":     "wood",
    "Vetiver EO":                 "wood",
    "Patchouli EO":               "wood",
    "Sandalore":                  "wood",
    "Ebanol":                     "wood",
    "Bacdanol":                   "wood",
    "Javanol":                    "wood",
    "Vetival":                    "wood",
    "Timberol":                   "wood",
    "Koavone":                    "wood",
    "Clearwood":                  "wood",
    # Amber / ambergris
    "Ambrox Super":               "amber",
    "Ambrofix":                   "amber",
    "Ambermax":                   "amber",
    "Amberwood F":                "amber",
    "Cedramber":                  "amber",
    "Azarbre":                    "amber",
    # Mossy / chypre (oakmoss replacement)
    "Evernyl":                    "moss",
    # Musk
    "Galaxolide":                 "musk",
    "Habanolide":                 "musk",
    "Romandolide":                "musk",
    "Ethylene Brassylate":        "musk",
    "Exaltolide":                 "musk",
    "Ambrettolide":               "musk",
    "Zenolide":                   "musk",
    # Gourmand / balsamic
    "Vanillin":                   "gourmand",
    "Ethyl Vanillin":             "gourmand",
    "Heliotropal":                "gourmand",
    "Anisaldehyde":               "gourmand",
    "Ethyl Maltol":               "gourmand",
    "Maple Lactone":              "gourmand",
    # Salicylate cushion (often in fougère heart)
    "Hexyl Salicylate":           "cushion",
    "Benzyl Salicylate":          "cushion",
    # Fresh radiance
    "Hedione":                    "radiance",
    "Hedione HC":                 "radiance",
}

# Approximate IFRA Cat 4 (EDP) caps — soft hard bounds on wt% of EDP concentrate
# (we apply at ~5x because concentrate is ~20% of EDP).
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Eugenol": 2.5,
    "Citral": 5.0,
    "Coumarin": 7.0,
    "Linalool": 25.0,
    "Geraniol": 17.0,
    "Citronellol": 25.0,
    "Bergamot FCF": 50.0,            # furocoumarin-free → not restricted by 5MOP
    "Lavender EO": 15.0,             # bound by linalool content
    "Hexyl Salicylate": 12.5,
    "Benzyl Salicylate": 25.0,
    "Hedione": 50.0,
    "Iso E Super": 60.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Five fougère starting recipes (wt% of concentrate)
# ─────────────────────────────────────────────────────────────────────────────

# Concept 1 — Classic Aromatic Fougère (Drakkar-noir / Azzaro PH lineage)
F1_CLASSIC = {
    "Bergamot FCF":           12.0,
    "Lavender EO":            10.0,
    "Linalyl Acetate":         5.0,
    "Geraniol":                3.0,
    "Coumarin":                6.0,
    "Eugenol":                 1.5,
    "Hedione":                15.0,
    "Iso E Super":            12.0,
    "Cedarwood EO":            6.0,
    "Patchouli EO":            5.0,
    "Vetiver EO":              3.0,
    "Evernyl":                 2.0,
    "Habanolide":              8.0,
    "Galaxolide":              6.5,
    "Ambrox Super":            2.0,
    "Vanillin":                1.0,
    "Hexyl Salicylate":        2.0,
}

# Concept 2 — Fresh Aquatic Fougère (Cool Water / Acqua di Giò men lineage)
F2_AQUATIC = {
    "Bergamot FCF":           10.0,
    "Grapefruit FCF":          4.0,
    "Dihydromyrcenol":        15.0,
    "Lavender EO":             6.0,
    "Calone":                  0.4,   # 1% dilution; very potent
    "Floralozone":             3.0,
    "Hedione":                14.0,
    "Coumarin":                3.0,
    "Geraniol":                1.5,
    "Iso E Super":            12.0,
    "Cedarwood EO":            5.0,
    "Vetiver EO":              2.0,
    "Habanolide":              7.0,
    "Romandolide":             6.0,
    "Ambrox Super":            2.5,
    "Amberwood F":             3.0,
    "Hexyl Salicylate":        5.6,
}

# Concept 3 — Sweet Gourmand Fougère (Le Mâle / A*Men lineage, lavender + tonka)
F3_GOURMAND = {
    "Bergamot FCF":            8.0,
    "Lavender EO":            12.0,
    "Linalyl Acetate":         4.0,
    "Hedione":                12.0,
    "Coumarin":                7.0,
    "Vanillin":                4.0,
    "Ethyl Maltol":            0.6,   # 10% dilution; very potent
    "Heliotropal":             2.0,
    "Anisaldehyde":            1.5,
    "Eugenol":                 1.0,
    "Cedarwood EO":            5.0,
    "Sandalore":               4.0,
    "Iso E Super":            10.0,
    "Ambrox Super":            2.5,
    "Ambermax":                3.0,
    "Habanolide":              5.0,
    "Ethylene Brassylate":     7.0,
    "Galaxolide":              4.4,
    "Patchouli EO":            5.0,
    "Hexyl Salicylate":        2.0,
}

# Concept 4 — Modern Spicy Ambrox Fougère (Sauvage / Bleu lineage)
F4_AMBROX = {
    "Bergamot FCF":           14.0,
    "Red Mandarin EO":         3.0,
    "Lavender EO":             5.0,
    "Linalool":                3.0,
    "Hedione":                15.0,
    "Pink Pepper Base":        3.0,   # avoid → swap to single molecules
    "Eugenol":                 0.8,
    "Geraniol":                1.5,
    "Iso E Super":            18.0,
    "Cedarwood EO":            4.0,
    "Patchouli EO":            3.0,
    "Vetiver EO":              1.5,
    "Ambrox Super":            6.0,    # the signature
    "Ambrofix":                3.0,
    "Amberwood F":             4.0,
    "Habanolide":              6.0,
    "Romandolide":             5.0,
    "Galaxolide":              2.7,
    "Hexyl Salicylate":        1.5,
}

# Concept 5 — Woody Aromatic Fougère (Boss Bottled / Bleu de Chanel lineage)
F5_WOODY = {
    "Bergamot FCF":           11.0,
    "Grapefruit FCF":          3.0,
    "Lavender EO":             7.0,
    "Linalyl Acetate":         3.0,
    "Geraniol":                2.0,
    "Hedione":                14.0,
    "Coumarin":                3.0,
    "Cedarwood oil Virginia":  6.0,
    "Cedarwood EO":            3.0,
    "Iso E Super":            16.0,
    "Vetiver EO":              4.0,
    "Patchouli EO":            3.0,
    "Sandalore":               3.0,
    "Ebanol":                  2.0,
    "Ambrox Super":            3.0,
    "Amberwood F":             2.5,
    "Cashmeran (20%)":         2.0,   # 20% in DPG, weak per-µL
    "Habanolide":              7.0,
    "Romandolide":             4.5,
    "Hexyl Salicylate":        1.0,
}

# Drop materials we deliberately ban (FOs, FTECs, Pre-blends).
# Concept 4 Pink Pepper Base must be replaced with single-molecules.
# Replace with Methyl Pamplemousse + Eugenol + a green note.
F4_AMBROX.pop("Pink Pepper Base", None)
F4_AMBROX["Citral"] = 0.6      # rind-bright lift
F4_AMBROX["Cedrat FCF oil Sicilian"] = 0.0  # placeholder, leave 0
F4_AMBROX.pop("Cedrat FCF oil Sicilian")
# Cashmeran 20% in F5 — convert to "Cashmeran" (we'll model neat for thermo; user accounts for dilution at compounding)
F5_WOODY["Cashmeran"] = F5_WOODY.pop("Cashmeran (20%)") * 0.20

RECIPES: dict[str, dict[str, float]] = {
    "F1_Classic_Aromatic":   F1_CLASSIC,
    "F2_Fresh_Aquatic":      F2_AQUATIC,
    "F3_Sweet_Gourmand":     F3_GOURMAND,
    "F4_Modern_Ambrox":      F4_AMBROX,
    "F5_Woody_Aromatic":     F5_WOODY,
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Target OAV envelopes per concept (family → relative OAV target per window)
#    Numbers are dimensionless OAV-share targets — the optimizer matches *shape*.
# ─────────────────────────────────────────────────────────────────────────────

TARGETS: dict[str, dict[str, dict[str, float]]] = {
    "F1_Classic_Aromatic": {
        "top":   {"citrus": 80, "aromatic": 60, "radiance": 30},
        "heart": {"aromatic": 50, "geranium": 25, "coumarin": 35, "radiance": 40, "spice": 15},
        "base":  {"wood": 40, "moss": 25, "musk": 35, "amber": 15, "coumarin": 20},
    },
    "F2_Fresh_Aquatic": {
        "top":   {"citrus": 90, "aromatic": 50, "marine": 35},
        "heart": {"marine": 30, "aromatic": 35, "radiance": 50, "geranium": 15},
        "base":  {"musk": 50, "amber": 30, "wood": 30, "cushion": 20},
    },
    "F3_Sweet_Gourmand": {
        "top":   {"citrus": 60, "aromatic": 70, "radiance": 25},
        "heart": {"aromatic": 45, "coumarin": 60, "gourmand": 50, "radiance": 30, "spice": 10},
        "base":  {"gourmand": 40, "amber": 30, "wood": 30, "musk": 50, "coumarin": 25},
    },
    "F4_Modern_Ambrox": {
        "top":   {"citrus": 100, "aromatic": 30, "radiance": 30},
        "heart": {"radiance": 60, "aromatic": 25, "geranium": 15, "spice": 15},
        "base":  {"amber": 70, "wood": 60, "musk": 40},
    },
    "F5_Woody_Aromatic": {
        "top":   {"citrus": 75, "aromatic": 50, "radiance": 30},
        "heart": {"aromatic": 35, "radiance": 50, "geranium": 15, "coumarin": 20},
        "base":  {"wood": 80, "amber": 30, "musk": 40, "cushion": 15},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Material data tables (MW, VP, ODT) from data spine + odor_thresholds
# ─────────────────────────────────────────────────────────────────────────────

REGISTRY = load_registry()


def _odt_air_ppm(name: str) -> float:
    """ODT_air in ppm (volumetric).  Default 50 ppm if unknown."""
    n = name.casefold()
    if n in ODT_DATA:
        return ODT_DATA[n]["odt_air"] / 1000.0  # ppb → ppm
    # try a couple of common normalizations
    for key in ODT_DATA:
        if key in n or n in key:
            return ODT_DATA[key]["odt_air"] / 1000.0
    return 0.05  # 50 ppb default — middle of fragrance ODT range


def build_tables(materials: list[str]) -> dict:
    """Pull MW / VP / HSP / ODT tables for the given materials."""
    mw_t: dict[str, float] = {}
    vp_t: dict[str, float] = {}
    hsp_t: dict[str, tuple[float, float, float]] = {}
    odt_t: dict[str, float] = {}
    fam_t: dict[str, str] = {}
    missing: list[str] = []
    for m in materials:
        rec = REGISTRY.get(m)
        if rec is None:
            missing.append(m)
            mw_t[m] = 200.0
            vp_t[m] = 1.0
        else:
            mw_t[m] = rec.mw_g_mol or 200.0
            vp_t[m] = rec.vp_25c_pa or 1.0
            if rec.hsp.delta_d is not None:
                hsp_t[m] = (rec.hsp.delta_d, rec.hsp.delta_p or 0.0, rec.hsp.delta_h or 0.0)
        odt_t[m] = _odt_air_ppm(m)
        fam_t[m] = FAMILY.get(m, "default")
    return dict(mw=mw_t, vp=vp_t, hsp=hsp_t, odt=odt_t, fam=fam_t, missing=missing)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Build a per-window headspace function from `evaporate(...)`
# ─────────────────────────────────────────────────────────────────────────────

def _frame_oav(frame, odt_t: dict[str, float]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for name, c in frame.headspace.items():
        odt = odt_t.get(name, 0.05)
        out[name] = {"oav": c.vapor_ppm / max(odt, 1e-6)}
    return out


def make_headspace_fn(materials: list[str], tables: dict):
    """Closure that runs a 4-frame trajectory and returns top/heart/base OAV."""
    mw_t = tables["mw"]; vp_t = tables["vp"]; hsp_t = tables["hsp"]; odt_t = tables["odt"]

    def headspace_fn(wt_pct: Mapping[str, float]) -> dict[str, dict[str, float]]:
        # Skip the trajectory if all wts are zero
        if not any(v > 0 for v in wt_pct.values()):
            return {"top": {}, "heart": {}, "base": {}}
        frames = evaporate(
            wt_pct,
            duration_s=14400.0,
            n_steps=12,
            mw_table=mw_t, vp_table=vp_t, hsp_table=hsp_t,
        )
        # Pick representative frames near 60s, 1800s, 14400s
        pick = {"top": frames[1], "heart": frames[2], "base": frames[-1]}
        # frames are at t = 1200s steps (14400/12), so frames[1]≈1200s, frames[2]≈2400s
        # Better: use index lookup by closest time
        targets = {"top": 60.0, "heart": 1800.0, "base": 14400.0}
        for win, tgt in targets.items():
            best = min(frames, key=lambda f: abs(f.t_seconds - tgt))
            pick[win] = best
        return {win: _frame_oav(fr, odt_t) for win, fr in pick.items()}

    return headspace_fn


# ─────────────────────────────────────────────────────────────────────────────
# 6. Reporting helpers
# ─────────────────────────────────────────────────────────────────────────────

def family_summed(profile: dict[str, dict[str, float]], fam_t: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for m, p in profile.items():
        f = fam_t.get(m, "default")
        out[f] = out.get(f, 0.0) + p.get("oav", 0.0)
    return out


def render_envelope(snap: dict[str, dict[str, float]], fam_t: dict[str, str]) -> str:
    lines = []
    for win in ("top", "heart", "base"):
        fams = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"  {win:5s}: " + "  ".join(f"{k}={v:.2f}" for k, v in items))
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Main
# ─────────────────────────────────────────────────────────────────────────────

def run_one(name: str, recipe: dict[str, float], target: dict[str, dict[str, float]],
            *, maxiter: int = 30, popsize: int = 12, seed: int = 42) -> dict:
    # Strip zeros, normalise
    recipe = {k: v for k, v in recipe.items() if v > 0}
    materials = list(recipe.keys())
    tables = build_tables(materials)

    # Bounds: ±50% per material, capped by IFRA where known. Min always ≥ 0.
    bounds: list[tuple[float, float]] = []
    for m in materials:
        v = recipe[m]
        lo = max(0.0, v * 0.5)
        hi = v * 1.6
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        # very-trace materials must keep some headroom
        if v < 0.5:
            hi = max(hi, v * 2.0)
        bounds.append((lo, hi))

    headspace_fn = make_headspace_fn(materials, tables)

    obj = OAVObjective(
        materials=materials,
        bounds=bounds,
        target_envelope=target,
        headspace_fn=headspace_fn,
        families=tables["fam"],
    )

    # Initial score
    from engine.optimizer.oav_objective import score_formula_oav
    init_score = score_formula_oav(recipe, obj)
    init_snap = headspace_fn(recipe)

    print(f"\n=== {name} ===")
    print(f"materials: {len(materials)}   missing-from-spine: {tables['missing']}")
    print(f"INITIAL  score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    # Optimize
    best_wt, best_score = differential_evolution_oav(obj, maxiter=maxiter, popsize=popsize, seed=seed)
    # Normalise the optimum to sum=100
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap = headspace_fn(best_wt_norm)
    final_score = score_formula_oav(best_wt_norm, obj)

    print(f"OPTIMIZED score = {final_score:+.3f}   (delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "name": name,
        "initial": {"recipe_wt_pct": recipe, "score": init_score,
                    "envelope": {w: family_summed(init_snap[w], tables["fam"]) for w in ("top", "heart", "base")}},
        "optimized": {"recipe_wt_pct": {k: round(v, 3) for k, v in sorted(best_wt_norm.items(), key=lambda kv: -kv[1])},
                      "score": final_score,
                      "envelope": {w: family_summed(best_snap[w], tables["fam"]) for w in ("top", "heart", "base")}},
        "delta_score": final_score - init_score,
        "missing_from_spine": tables["missing"],
    }


def main():
    out = {}
    for name, recipe in RECIPES.items():
        out[name] = run_one(name, recipe, TARGETS[name])

    out_path = Path(__file__).parent / "_fougere_5_mass_appeal_out.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")

    # Markdown summary
    md = ["# Five Mass-Appeal Fougères — VP/OAV-Optimized\n"]
    md.append("All recipes expressed as **wt% of fragrance concentrate**. Scale to any "
              "batch size by mass (no µL conversions encoded).\n")
    md.append("Optimization: differential evolution against per-window OAV target envelopes "
              "computed from `engine.thermo.trajectory.evaporate` headspace snapshots at "
              "60 s (top), 30 min (heart), 4 h (base).\n")
    for name, r in out.items():
        md.append(f"\n## {name.replace('_', ' ')}\n")
        md.append(f"Score delta: **{r['delta_score']:+.3f}**\n")
        md.append("| Material | Initial wt% | Optimized wt% |")
        md.append("|---|---:|---:|")
        all_mats = sorted(set(r["initial"]["recipe_wt_pct"]) | set(r["optimized"]["recipe_wt_pct"]))
        for m in sorted(all_mats, key=lambda k: -r["optimized"]["recipe_wt_pct"].get(k, 0)):
            i = r["initial"]["recipe_wt_pct"].get(m, 0)
            o = r["optimized"]["recipe_wt_pct"].get(m, 0)
            md.append(f"| {m} | {i:.2f} | {o:.2f} |")
        md.append("\n**Family OAV envelope (optimized)**\n")
        for w in ("top", "heart", "base"):
            fams = r["optimized"]["envelope"][w]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            md.append(f"- *{w}*: " + ", ".join(f"{k}={v:.2f}" for k, v in top6))
    md_path = Path(__file__).parent / "_fougere_5_mass_appeal_out.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
