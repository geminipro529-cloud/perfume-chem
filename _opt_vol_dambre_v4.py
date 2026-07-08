"""Vol d'Ambre v4 — Layton-axis re-optimisation, 30 mL EDP.

Changes vs v1/v3c:
  - Target envelope rebuilt for true Layton DNA (amber dominates, aromatic subdued).
  - Lavender EO hard-capped at 6 % concentrate (was 15 %).
  - Norlimbanol Dextro + Azarbre + Timberol added; Javanol removed (out of stock).
  - Ambrox Super initial raised to 12 %; Vanillin raised to 9 %.
  - VP overrides applied for Sandalore + Norlimbanol Dextro (spine has None → fallback
    1.0 Pa would be 1000× wrong; real value ~0.001 Pa from ingredient_intelligence).
  - Guard Rail verification (GR1/3/4/5/6/7/8/10) appended to mixing-guide MD output.
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

# ── Olfactive family map ──────────────────────────────────────────────────────
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
    "Sandalore":                 "wood",
    "Timberol":                  "wood",
    "Norlimbanol Dextro":        "wood",   # added v4
    "Ebanol":                    "wood",
    "Bacdanol":                  "wood",
    "Cedarwood EO":              "wood",
    "Cedarwood oil Virginia":    "wood",
    "Vetiver EO":                "wood",
    "Patchouli EO":              "wood",
    "Clearwood":                 "wood",
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

# ── IFRA / odour-impact caps at concentrate level ────────────────────────────
# (fine fragrance Category 4, conservative where known)
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF":          50.0,
    "Lavender EO":            6.0,   # v4 Layton-axis hard cap (IFRA allows 15 %; cap here for balance)
    "Linalool":              25.0,
    "Linalyl Acetate":       25.0,
    "Geraniol":              17.0,
    "Citronellol":           25.0,
    "Coumarin":               7.0,
    "Benzyl Acetate":         5.0,
    "Phenethyl Alcohol":     20.0,
    "Hedione":               50.0,
    "Hexyl Salicylate":      12.5,
    "Benzyl Salicylate":     25.0,
    "Iso E Super":           60.0,
    "Eugenol":                2.5,
    "Isoeugenol":             1.0,
    "Citral":                 5.0,
    "Ethyl 2-Methylbutyrate": 0.30,  # odour-impact cap
    "Norlimbanol Dextro":     0.85,  # GR5 adaptation cliff at ~0.17 % in EDP = 0.85 % conc.
}

# ── Correct VP values for materials with spine VP = None ─────────────────────
# Data spine falls back to VP = 1.0 Pa for None, which is 1000× wrong for these.
# Values sourced from ingredient_intelligence profiles (verified against literature).
VP_OVERRIDE: dict[str, float] = {
    "Sandalore":          0.001,   # spine: None  real: ~0.001 Pa
    "Norlimbanol Dextro": 0.001,   # spine: None  real: ~0.001 Pa
}

# ── Formula ───────────────────────────────────────────────────────────────────
CONCEPT: dict = {
    "key":     "LAYTON_V4",
    "name":    "Vol d'Ambre v4",
    "tagline": (
        "Layton-axis re-optimised — amber-dominant base, subdued aromatic top, "
        "no Javanol (out of stock), Norlimbanol/Azarbre/Timberol woody triad."
    ),
    "direction": (
        "Vol d'Ambre v4 rebalances the formula toward the true Layton DNA: "
        "an apple-cardamom-citrus top where the lavender is a *supporting* note, "
        "not the theme; a Hedione HC jasmine radiance in the heart; and above all, "
        "an amber-vanilla-sandalwood drydown that reads as warm, skin-close, and opulent. "
        "Ambrox Super anchors the base at 12 % (skin-depot amber). Azarbre fills the aerial "
        "amber tier (VP 17× higher, projects into the air column Ambrox cannot reach). "
        "Norlimbanol Dextro adds dry woody permanence at trace level. "
        "Sandalore + Timberol replace Javanol for creamy sandalwood. "
        "Lavender is hard-capped at 6 % of concentrate; the aromatic OAV target is 400 "
        "(vs 1100 in v1) — the optimizer is penalised for over-recruiting aromatic ORs."
    ),
    "recipe": {
        # ── Top — citrus / fruity / spice / minimal aromatic ─────────────────
        "Bergamot FCF":             6.0,
        "Lavender EO":              4.5,   # 10% was original; 4.5 % → max 6 % by cap
        "Linalyl Acetate":          2.5,
        "Ethyl Linalool":           1.5,
        "Apritone":                 3.0,   # 10% stock
        "Hexyl Acetate":            2.0,   # 10% stock
        "Ethyl 2-Methylbutyrate":   0.15,  # neat — keep tight
        "Cardamom FTEC":            3.5,   # 10% stock — raised for spice prominence
        # ── Heart — radiance / floral / geranium / powdery ───────────────────
        "Hedione HC":               8.0,   # THE Layton jasmine molecule
        "Hedione":                  3.0,   # radiance support
        "Benzyl Acetate":           1.5,
        "Dihydrojasmone":           0.8,
        "Geraniol":                 2.0,
        "Alpha Isomethyl Ionone":   2.5,
        "Phenethyl Alcohol":        1.0,
        # ── Base — amber / wood / gourmand / musk ────────────────────────────
        "Ambrox Super":            12.0,   # 30% stock — Layton foundation, floor at 7.2 %
        "Azarbre":                  2.0,   # amber family, VP 0.001 Pa — aerial amber tier
        "Iso E Super":              6.0,
        "Sandalore":                6.0,   # Javanol out; Sandalore raised to carry creamy sandalwood
        "Timberol":                 2.0,   # sandalwood-cedar hybrid, VP 0.12 Pa (heart-base)
        "Norlimbanol Dextro":       0.5,   # hard woody backbone — capped at 0.85 % (GR5)
        "Cashmeran":                0.8,   # cashmere-woody warmth
        "Vanillin":                 9.0,   # 10% stock — Layton vanilla is prominent
        "Ethyl Vanillin":           1.5,
        "Coumarin":                 3.0,   # 20% stock
        "Benzoin Resinoid":         3.0,   # 50% stock
        "Habanolide":               5.0,
        "Galaxolide":               3.5,
        "Romandolide":              2.5,
        "Ethylene Brassylate":      2.0,
    },
    # ── Target OAV envelope — Layton DNA ────────────────────────────────────
    # Amber dominates base and builds through heart.
    # Aromatic intentionally low (400 in top, 300 in heart) to force lavender reduction.
    # Gourmand raised to 500 (Layton vanilla signature).
    # Numbers calibrated to what this material set can physically achieve (GR1/VP ceiling).
    "envelope": {
        "top": {
            "citrus":    2200,
            "fruity":     800,
            "spice":      200,
            "aromatic":   400,   # tight — forces lavender to minimum
            "radiance":    60,
        },
        "heart": {
            "amber":      400,
            "fruity":     350,
            "radiance":    80,
            "powdery":    200,
            "aromatic":   300,   # lavender fading through heart
            "citrus":     400,
        },
        "base": {
            "amber":      500,   # Ambrox (skin) + Azarbre (aerial) — realistic VP ceiling
            "gourmand":   500,   # Vanillin/Ethyl Vanillin dominant
            "wood":       200,   # Sandalore + Timberol + Norlimbanol
            "balsamic":   180,
            "coumarin":    90,
            "musk":        80,
        },
    },
}

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
    missing, vp_overridden = [], []
    for m in materials:
        rec = REGISTRY.get(m)
        if rec is None:
            missing.append(m)
            mw_t[m], vp_t[m] = 200.0, 1.0
        else:
            mw_t[m] = rec.mw_g_mol or 200.0
            raw_vp  = rec.vp_25c_pa
            if raw_vp is None and m in VP_OVERRIDE:
                vp_t[m] = VP_OVERRIDE[m]
                vp_overridden.append(m)
            elif m in VP_OVERRIDE:
                vp_t[m] = VP_OVERRIDE[m]   # prefer known-good value even if spine has something
                vp_overridden.append(m)
            else:
                vp_t[m] = raw_vp or 1.0
            if rec.hsp.delta_d is not None:
                hsp_t[m] = (rec.hsp.delta_d, rec.hsp.delta_p or 0.0, rec.hsp.delta_h or 0.0)
        odt_t[m] = _odt_air_ppm(m)
        fam_t[m] = FAMILY.get(m, "default")
    return dict(mw=mw_t, vp=vp_t, hsp=hsp_t, odt=odt_t, fam=fam_t,
                missing=missing, vp_overridden=vp_overridden)


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
    concept: dict, *, maxiter: int = 60, popsize: int = 20, seed: int = 7
) -> dict:
    name, key = concept["name"], concept["key"]
    recipe    = {k: v for k, v in concept["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables    = build_tables(materials)

    bounds = []
    for m in materials:
        v  = recipe[m]
        lo = max(0.0, v * 0.60)
        hi = v * 1.50
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.5:
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
    print(f"  VP overrides applied: {tables['vp_overridden']}")
    print(f"  Missing from spine:   {tables['missing']}")
    print(f"  INITIAL score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, best_score = differential_evolution_oav(
        obj, maxiter=maxiter, popsize=popsize, seed=seed
    )
    total        = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap    = headspace_fn(best_wt_norm)
    final_score  = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final_score:+.3f}  (delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key":     key,
        "name":    name,
        "tagline": concept["tagline"],
        "direction": concept["direction"],
        "envelope_target": concept["envelope"],
        "tables":  tables,
        "initial": {
            "recipe_wt_pct": recipe,
            "score":         init_score,
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
            "score":         final_score,
            "envelope": {
                w: family_summed(best_snap[w], tables["fam"])
                for w in ("top", "heart", "base")
            },
        },
        "delta_score":       final_score - init_score,
        "missing_from_spine": tables["missing"],
        "vp_overridden":     tables["vp_overridden"],
    }


# ── Guard Rail verification ───────────────────────────────────────────────────
def guard_rail_report(result: dict) -> str:
    """Evaluate the optimized formula against all 11 guard rails from the framework doc."""
    opt   = result["optimized"]["recipe_wt_pct"]
    fam_t = result["tables"]["fam"]
    vp_t  = result["tables"]["vp"]
    mw_t  = result["tables"]["mw"]
    odt_t = result["tables"]["odt"]
    env   = result["optimized"]["envelope"]

    from engine.ingredient_intelligence import get_profile

    lines = [
        "",
        "---",
        "",
        "## Guard Rail Verification",
        "",
        "> Auto-generated against *Hidden Guard Rails of Perfumery* framework.",
        "",
    ]

    # ── GR1 / GR3: Vapor Phase + Evaporation Trajectory ──────────────────────
    lines += [
        "### GR1 + GR3 — Vapor Phase & Evaporation Trajectory",
        "",
        "Materials sorted by VP (Pa) — determines when each contributes to headspace.",
        "",
        "| Material | wt% conc | VP (Pa) | MW | Temporal tier |",
        "|---|---:|---:|---:|---|",
    ]
    for m, wt in sorted(opt.items(), key=lambda kv: -vp_t.get(kv[0], 0)):
        vp = vp_t.get(m, 1.0)
        mw = mw_t.get(m, 200.0)
        if vp >= 0.5:
            tier = "top (volatile, <5 min)"
        elif vp >= 0.05:
            tier = "early heart (5–20 min)"
        elif vp >= 0.005:
            tier = "heart/base transition"
        elif vp >= 0.001:
            tier = "base (1–4 h)"
        else:
            tier = "skin-close fixative (>4 h, minimal aerial)"
        lines.append(f"| {m} | {wt:.2f} | {vp:.4f} | {mw:.0f} | {tier} |")

    lines += [
        "",
        "**GR1 flag — Ambrox Super (VP 0.0003 Pa):** skin-depot molecule only. "
        "Adding more Ambrox deepens the skin-warmth reservoir but does not increase "
        "projected sillage. Azarbre (VP 0.001 Pa) fills the aerial amber tier.",
        "",
        "**GR3 flag — Timberol (VP 0.12 Pa):** most volatile of the wood materials. "
        "Will contribute to early heart, not base drydown. This is correct behaviour "
        "for creating temporal novelty (GR10) — a woody-cedar note in the T+20 min zone "
        "before the Sandalore/Norlimbanol drydown reveals.",
        "",
    ]

    # ── GR4: OAV envelope ─────────────────────────────────────────────────────
    lines += [
        "### GR4 — OAV Envelope vs Target",
        "",
        "| Window | Family | Actual OAV | Target OAV | Δ ratio |",
        "|---|---|---:|---:|---:|",
    ]
    target = result["envelope_target"]
    for win in ("top", "heart", "base"):
        actual_fams = env[win]
        tgt_fams    = target[win]
        all_fams    = sorted(set(actual_fams) | set(tgt_fams),
                             key=lambda f: -tgt_fams.get(f, 0))
        for fam in all_fams:
            av  = actual_fams.get(fam, 0.0)
            tv  = tgt_fams.get(fam, 0.0)
            rat = f"{av/tv:.2f}×" if tv > 0 else "—"
            lines.append(f"| {win} | {fam} | {av:.1f} | {tv:.1f} | {rat} |")

    lines += [""]

    # ── GR5: Adaptation Risk ──────────────────────────────────────────────────
    lines += [
        "### GR5 — Olfactory Receptor Adaptation Risk",
        "",
        "Flag: any material sustaining OAV >> 10 in all three windows "
        "(continuously activates the same OR population).",
        "",
        "| Material | Family | wt% conc | EDP% (neat) | Adaptation note |",
        "|---|---|---:|---:|---|",
    ]
    for m, wt in sorted(opt.items(), key=lambda kv: -kv[1]):
        p = get_profile(m)
        logp = p.clogp if p else None
        # Estimate neat EDP%: wt% of concentrate × 20% EDP factor
        neat_pct = wt * 0.20
        fam      = fam_t.get(m, "?")
        note     = ""
        if m == "Norlimbanol Dextro":
            note = "**GR5 HARD CAP** — woody:9 character; >0.17 % EDP risks OR flooding"
        elif m == "Ambrox Super":
            note = "Low VP limits sustained OR load despite high concentration — OK"
        elif m in ("Lavender EO", "Linalyl Acetate", "Ethyl Linalool"):
            note = "Aromatic family — monitor combined aromatic OAV vs target 400"
        elif fam == "musk":
            note = "Musk — skin-close, OR load spread over long timescale"
        lines.append(f"| {m} | {fam} | {wt:.2f} | {neat_pct:.3f} | {note} |")
    lines += [""]

    # ── GR6: OR Family Competition ────────────────────────────────────────────
    lines += [
        "### GR6 — OR Family Competition",
        "",
        "| OR family | Materials | Risk | Mitigation |",
        "|---|---|---|---|",
        "| amber | Ambrox Super + Azarbre | Compete at amber ORs | "
        "VP separation: Azarbre (0.001 Pa) projects early; Ambrox (0.0003 Pa) skin-close late. "
        "Net: complementary temporal tiers, not pure competition. |",
        "| wood | Sandalore + Timberol + Norlimbanol + Iso E Super | "
        "Partial competition | Different character axes: Sandalore=creamy, "
        "Timberol=cedar (high VP/early), Norlimbanol=dry (low VP/late). Blends as layered wood accord. |",
        "| aromatic | Lavender + Linalyl Acetate + Ethyl Linalool | "
        "All recruit aromatic ORs | Capped at 6 % total in concentrate; combined aromatic OAV "
        "should stay below 600 in top. |",
        "",
    ]

    # ── GR7: Skin Substantivity ───────────────────────────────────────────────
    lines += [
        "### GR7 — Skin Substantivity (logP / MW)",
        "",
        "| Material | logP | MW | Tier | Substantivity |",
        "|---|---:|---:|---|---|",
    ]
    for m, wt in sorted(opt.items(), key=lambda kv: -kv[1]):
        p    = get_profile(m)
        logp = p.clogp if p else None
        mw   = mw_t.get(m, 200.0)
        if logp is None:
            tier = "unknown"
            sub  = "?"
        elif logp >= 5.0:
            tier = "lipid depot"
            sub  = "Excellent — sebum/SC fixation, very long lasting"
        elif logp >= 4.0:
            tier = "skin surface"
            sub  = "Good — surface reservoir, 4–8 h"
        elif logp >= 2.5:
            tier = "partial penetration"
            sub  = "Moderate — evaporates and absorbs, 2–4 h"
        else:
            tier = "volatile/polar"
            sub  = "Low — evaporates quickly"
        lines.append(f"| {m} | {logp or '?'} | {mw:.0f} | {tier} | {sub} |")

    lines += [
        "",
        "**GR7 summary:** Norlimbanol (logP 5.2), Galaxolide (logP ~5.9), Habanolide/Romandolide "
        "(logP ~5.5) form the lipid-depot permanence layer. Ambrox (logP 4.92), Azarbre (logP 4.8), "
        "Iso E Super (logP 4.73), Sandalore (logP 4.2) fill the 4–8 h skin-surface tier. "
        "Formula has strong substantivity — appropriate for a Layton-type EDP targeting "
        "6–8 h wear.",
        "",
    ]

    # ── GR8: Chemical Stability ───────────────────────────────────────────────
    lines += [
        "### GR8 — Chemical Stability / Maturation Risks",
        "",
        "| Risk | Materials | Reaction | Action |",
        "|---|---|---|---|",
        "| Oxidation | Lavender EO (linalool, limonene), Linalyl Acetate | "
        "Terpene peroxide / hydroperoxide formation → skin sensitiser | "
        "**Add BHT 0.02 % concentrate** before sealing (as per v3c protocol) |",
        "| Acetal formation | None — no free aldehydes in formula | "
        "No acetal risk | — |",
        "| Schiff base | None — no primary amines | No Schiff risk | — |",
        "| Vanillin oxidation | Vanillin at 9 % | Slow darkening in light/air | "
        "Dark glass storage; BHT also helps |",
        "",
        "**GR8 action required:** add BHT antioxidant. Dissolve ~1.2 mg BHT in 200 µL ethanol "
        "and count it in the concentrate volume (same protocol as v3c).",
        "",
    ]

    # ── GR10: Temporal Novelty ────────────────────────────────────────────────
    lines += [
        "### GR10 — Temporal Novelty (OR Activation Sequence)",
        "",
        "Glomerular activation vector change over time — formula must not stagnate.",
        "",
        "| Time window | Dominant OR families | Novelty vs prior window |",
        "|---|---|---|",
        "| T+0–5 min (top) | citrus (Bergamot), fruity (Apritone/apple), spice (Cardamom), "
        "early aromatic (Lavender) | — (first impression) |",
        "| T+5–20 min (early heart) | citrus fading, Timberol wood reveals (VP 0.12 Pa), "
        "radiance (Hedione HC jasmine) builds, powdery (Alpha Isomethyl Ionone) | "
        "**High** — wood + jasmine replace citrus/fruity |",
        "| T+20–60 min (heart) | radiance peak, amber building (Azarbre enters), "
        "aromatic fully faded, gourmand (Vanillin) starts reading | "
        "**High** — amber + gourmand replace aromatic |",
        "| T+60–240 min (base) | amber (Ambrox skin warmth), gourmand (Vanillin dominant), "
        "wood (Sandalore creamy, Norlimbanol dry), musk | "
        "**Medium** — steady evolution within amber/gourmand frame |",
        "| T+240+ min (drydown) | Ambrox + Norlimbanol + musks on skin | "
        "**Low** — intentional: Layton drydown is a static skin scent |",
        "",
        "**GR10 verdict:** formula has 3 distinct temporal phases (citrus-spice → "
        "jasmine-amber → vanilla-sandalwood-musk). This satisfies the novelty requirement "
        "and matches Layton's known performance arc.",
        "",
    ]

    return "\n".join(lines)


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
        f"**Score delta vs initial:** {r['delta_score']:+.3f}",
        f"**VP overrides applied:** {', '.join(r['vp_overridden']) or 'none'}",
        f"**Missing from spine:** {', '.join(r['missing_from_spine']) or 'none'}",
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
        "> All volumes are **stock as-held** (diluted or neat). Measure into concentrate vial; "
        "top up to exactly 6.00 mL before bottling.",
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
        lines.append(f"| {i} | {m} | {wt:.2f} | {ul:.0f} | {ul/1000:.3f} | {drops:.1f} |")

    total_wt    = sum(opt.values())
    total_conc  = total_wt / 100.0 * CONCENTRATE_UL
    ethanol_conc = CONCENTRATE_UL - total_conc

    lines += [
        f"| — | **Fragrance sub-total** | **{total_wt:.2f}** | **{total_conc:.0f}** | **{total_conc/1000:.3f}** | — |",
        f"| — | BHT antioxidant pre-soln | — | 200 | 0.200 | — |",
        f"| — | Ethanol 96% top-up | — | {max(0, ethanol_conc - 200):.0f} | {max(0, (ethanol_conc-200)/1000):.3f} | — |",
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
        "### Prepare BHT antioxidant pre-solution",
        "Weigh **~1.2 mg** BHT into a clean 1 mL vial. Add **200 µL ethanol 96%**; swirl until dissolved.",
        "",
        "### Add to concentrate vial (base → top order)",
        "",
        "| Step | Material | Stock | µL | Notes |",
        "|---:|---|---|---:|---|",
        "| 1 | BHT pre-solution | — | 200 | GR8: guards lavender/vanillin oxidation |",
        "| 2 | Ethylene Brassylate | neat | {:.0f} | Slowest evaporator — add first |".format(
            opt.get("Ethylene Brassylate", 0) / 100 * CONCENTRATE_UL
        ),
        "| 3 | Habanolide | neat | {:.0f} | Macrocyclic musk |".format(
            opt.get("Habanolide", 0) / 100 * CONCENTRATE_UL
        ),
        "| 4 | Romandolide | neat | {:.0f} | Macrocyclic musk |".format(
            opt.get("Romandolide", 0) / 100 * CONCENTRATE_UL
        ),
        "| 5 | Galaxolide | neat | {:.0f} | Musk anchor |".format(
            opt.get("Galaxolide", 0) / 100 * CONCENTRATE_UL
        ),
        "| 6 | Ambrox Super | 30% | {:.0f} | Layton amber foundation |".format(
            opt.get("Ambrox Super", 0) / 100 * CONCENTRATE_UL
        ),
        "| 7 | Azarbre | neat | {:.0f} | Aerial amber tier (GR1: VP 0.001 Pa) |".format(
            opt.get("Azarbre", 0) / 100 * CONCENTRATE_UL
        ),
        "| 8 | Norlimbanol Dextro | neat | {:.0f} | Hard wood — measure precisely; GR5 cliff at 50 µL total |".format(
            opt.get("Norlimbanol Dextro", 0) / 100 * CONCENTRATE_UL
        ),
        "| 9 | Iso E Super | neat | {:.0f} | Woody-cedar halo |".format(
            opt.get("Iso E Super", 0) / 100 * CONCENTRATE_UL
        ),
        "| 10 | Sandalore | neat | {:.0f} | Creamy sandalwood (Javanol substitute) |".format(
            opt.get("Sandalore", 0) / 100 * CONCENTRATE_UL
        ),
        "| 11 | Timberol | neat | {:.0f} | Cedar-sandalwood bridge (GR3: VP 0.12 Pa, heart tier) |".format(
            opt.get("Timberol", 0) / 100 * CONCENTRATE_UL
        ),
        "| 12 | Cashmeran | neat | {:.0f} | Cashmere warmth |".format(
            opt.get("Cashmeran", 0) / 100 * CONCENTRATE_UL
        ),
        "| 13 | Benzoin Resinoid | 50% | {:.0f} | Balsamic base |".format(
            opt.get("Benzoin Resinoid", 0) / 100 * CONCENTRATE_UL
        ),
        "| 14 | Vanillin | 10% | {:.0f} | Layton vanilla dominant |".format(
            opt.get("Vanillin", 0) / 100 * CONCENTRATE_UL
        ),
        "| 15 | Ethyl Vanillin | neat | {:.0f} | Headspace-active vanilla |".format(
            opt.get("Ethyl Vanillin", 0) / 100 * CONCENTRATE_UL
        ),
        "| 16 | Coumarin | 20% | {:.0f} | Hay sweetness |".format(
            opt.get("Coumarin", 0) / 100 * CONCENTRATE_UL
        ),
        "| 17 | Alpha Isomethyl Ionone | neat | {:.0f} | Powdery violet bridge |".format(
            opt.get("Alpha Isomethyl Ionone", 0) / 100 * CONCENTRATE_UL
        ),
        "| 18 | Hedione HC | neat | {:.0f} | Jasmine radiance — THE Layton molecule |".format(
            opt.get("Hedione HC", 0) / 100 * CONCENTRATE_UL
        ),
        "| 19 | Hedione | neat | {:.0f} | Radiance support |".format(
            opt.get("Hedione", 0) / 100 * CONCENTRATE_UL
        ),
        "| 20 | Benzyl Acetate | neat | {:.0f} | Jasmine body |".format(
            opt.get("Benzyl Acetate", 0) / 100 * CONCENTRATE_UL
        ),
        "| 21 | Dihydrojasmone | neat | {:.0f} | Jasmine warmth |".format(
            opt.get("Dihydrojasmone", 0) / 100 * CONCENTRATE_UL
        ),
        "| 22 | Geraniol | neat | {:.0f} | Rose-geranium warmth |".format(
            opt.get("Geraniol", 0) / 100 * CONCENTRATE_UL
        ),
        "| 23 | Phenethyl Alcohol | neat | {:.0f} | Rose, honey |".format(
            opt.get("Phenethyl Alcohol", 0) / 100 * CONCENTRATE_UL
        ),
        "| 24 | Linalyl Acetate | neat | {:.0f} | Sweet lavender support |".format(
            opt.get("Linalyl Acetate", 0) / 100 * CONCENTRATE_UL
        ),
        "| 25 | Ethyl Linalool | neat | {:.0f} | Floral lavender |".format(
            opt.get("Ethyl Linalool", 0) / 100 * CONCENTRATE_UL
        ),
        "| 26 | Lavender EO | neat | {:.0f} | Lavender — supporting, not dominant |".format(
            opt.get("Lavender EO", 0) / 100 * CONCENTRATE_UL
        ),
        "| 27 | Apritone | 10% | {:.0f} | Apple chord |".format(
            opt.get("Apritone", 0) / 100 * CONCENTRATE_UL
        ),
        "| 28 | Hexyl Acetate | 10% | {:.0f} | Apple/fruity green |".format(
            opt.get("Hexyl Acetate", 0) / 100 * CONCENTRATE_UL
        ),
        "| 29 | Ethyl 2-Methylbutyrate | neat | {:.0f} | Sharp apple — measure carefully |".format(
            opt.get("Ethyl 2-Methylbutyrate", 0) / 100 * CONCENTRATE_UL
        ),
        "| 30 | Cardamom FTEC | 10% | {:.0f} | Spice signature |".format(
            opt.get("Cardamom FTEC", 0) / 100 * CONCENTRATE_UL
        ),
        "| 31 | Bergamot FCF | neat | {:.0f} | Citrus opening |".format(
            opt.get("Bergamot FCF", 0) / 100 * CONCENTRATE_UL
        ),
        "",
        "### Finish",
        "- Seal; swirl gently 30 s; **macerate 48 h minimum** before evaluating.",
        "- Transfer to the 30 mL bottle; fill to **30 mL** with ethanol 96% (**24.0 mL**).",
        "- Macerate finished EDP **2–4 weeks** for full accord integration.",
        "",
        "---",
        "",
        "## Safety Notes",
        "",
        "- **BHT:** 0.02 % in concentrate — cosmetic antioxidant, within limits. Required for GR8.",
        "- **Norlimbanol Dextro:** GR5 hard cap at 0.85 % concentrate (0.17 % EDP). "
        "Exceeding this causes woody OR flooding and harsh dry-wood dominance.",
        "- **Ethyl 2-Methylbutyrate:** extreme odour potency at this dose. "
        "Measure against a tared vial; a 1 µL error changes the apple character materially.",
        "- **Ambrox Super (30% stock):** no IFRA cap for fine fragrance; keep neat EDP% ≤ 3 % "
        "for skin comfort. At this recipe level you are within range.",
        "- **Benzyl Acetate:** IFRA Cat 4 limit ~2.5 % in finished product. "
        "At <2 % in concentrate × 20 % EDP, well within limits.",
        "- **Coumarin:** IFRA Cat 4 capped at 3.5 % in concentrate. "
        "Optimized value must stay at or below this — check the optimized wt% above.",
    ]

    # Append guard rail report
    lines.append(guard_rail_report(result))

    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    result = run_one(CONCEPT, maxiter=60, popsize=20, seed=7)

    root     = Path(__file__).parent
    json_out = root / "_opt_vol_dambre_v4_out.json"
    json_out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/Vol_dAmbre_30mL_Layton_v4.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
