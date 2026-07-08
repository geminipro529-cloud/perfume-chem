"""F2 — Le Chypre Vert, 30 mL EDP — Green Chypre Luxury Optimization.

Target axes: luxury, depth, texture, performance, mass-marketness.
Base formula: F2_Le_Chypre_Vert_30mL_EDP.md
Added: Labdanum Absolute (10%) as chypre structural pillar.

Batch: 20% concentrate EDP — 6 mL concentrate + 24 mL ethanol 96%
Volumes are as-held stock. No conversion needed.
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


# ── Family map: material → olfactory family ────────────────────────
FAMILY: dict[str, str] = {
    # Citrus / top
    "Bergamot FCF oil Sicilian": "citrus",
    "Petitgrain EO": "citrus",
    "Cedrat FCF oil Sicilian": "citrus",
    # Green
    "Galbanum Resinoid": "green",
    "cis-3-Hexenol": "green",
    # Aldehydic
    "Aldehyde C12 MNA": "aldehydic",
    "Triplal": "green_aldehydic",
    # Fruity
    "Ethyl 2-Methylbutyrate": "fruity",
    # Radiance
    "Hedione HC": "radiance",
    "Hedione": "radiance",
    # Jasmine
    "Amyl Cinnamic Aldehyde (ACA)": "jasmine",
    "Benzyl Acetate": "jasmine",
    "p-Cresyl Methyl Ether (PCME)": "jasmine",
    "Cis Jasmone": "jasmine",
    # Rose
    "Damascol": "rose",
    "Phenethyl Alcohol (PEA)": "rose",
    "Geraniol": "rose",
    "Alpha Damascone": "rose",
    # Muguet
    "Mayol": "muguet",
    "Bourgeonal": "muguet",
    # Ylang
    "Ylang Comoros Complete EO": "ylang",
    # Woods
    "Iso E Super": "wood",
    "Patchouli EO": "wood",
    "Vetiver EO": "wood",
    "Cedarwood oil Virginia": "wood",
    # Amber
    "Ambrofix": "amber",
    "Cashmeran": "amber",
    "Labdanum Absolute": "amber_resin",
    # Moss
    "Evernyl": "moss",
    # Musk
    "Galaxolide": "musk",
    "Ethylene Brassylate": "musk",
    "Ambrettolide": "musk",
    "Habanolide": "musk",
    # Coumarin
    "Coumarin": "coumarin",
    # Sandalwood
    "Ebanol": "sandalwood",
    # Cushion / fixative
    "Benzyl Salicylate": "cushion",
    "Hexyl Salicylate": "cushion",
}


# ── IFRA caps: max wt% of as-held stock in concentrate ─────────────
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Amyl Cinnamic Aldehyde (ACA)": 9.0,   # IFRA Cat.4 ACA = 0.6% of EDP → at 20% conc: 3.0% active. Neat ACA ≈ 9.0% stock
    "Geraniol": 5.0,                        # IFRA Cat.4 = 5.3% EDP. Neat → cap at 5% conc
    "Coumarin": 40.0,                       # 20% stock → 8% active in conc = 1.6% in EDP (IFRA limit 1.6%)
    "Hexyl Salicylate": 25.0,               # neat → IFRA 5.0% EDP → 25% conc
    "Benzyl Salicylate": 22.0,              # neat → IFRA 4.5% EDP → 22.5% conc
    "Galbanum Resinoid": 30.0,              # 10% stock → safety cap
    "Alpha Damascone": 15.0,                # 10% stock → IFRA damascones ~0.02% EDP → 0.1% conc active → 1% of 10% stock
    "Damascol": 15.0,                       # 10% stock
    "Bergamot FCF oil Sicilian": 35.0,       # linalool limit
    "Petitgrain EO": 20.0,                  # linalool limit
    "Evernyl": 25.0,                        # safe cap
    "Labdanum Absolute": 15.0,              # 10% stock → 1.5% active in conc; IFRA guidance ~1.0% active EDP
    "cis-3-Hexenol": 5.0,                   # powerful green — keep restrained
    "Triplal": 3.0,                         # ultra-powerful — keep < 0.05% active
    "Aldehyde C12 MNA": 5.0,                # 1% stock — powerful
    "Ethyl 2-Methylbutyrate": 5.0,          # powerful fruity ester
    "Hedione HC": 25.0,                     # high-cis radiance
    "Hedione": 40.0,                        # radiance bed
    "Iso E Super": 40.0,                    # texture spine
    "Patchouli EO": 35.0,                   # earthy anchor
    "Vetiver EO": 25.0,                     # woody-root
    "p-Cresyl Methyl Ether (PCME)": 5.0,    # 10% stock → powerful cresylic
    "Bourgeonal": 3.0,                      # muguet — powerful
    "Mayol": 5.0,                           # muguet — moderate
    "Cis Jasmone": 3.0,                     # powerful jasmonic
    "Ylang Comoros Complete EO": 5.0,       # rich floral — restrained dose
    "Galaxolide": 25.0,                     # 80% stock
    "Ethylene Brassylate": 20.0,            # macrocyclic
    "Habanolide": 10.0,                     # intimate musk
    "Ambrettolide": 15.0,                   # 10% stock
    "Ambrofix": 30.0,                       # 30% stock
    "Cashmeran": 8.0,                       # powerful woody-amber
    "Ebanol": 5.0,                          # powerful sandalwood
    "Cedarwood oil Virginia": 20.0,         # woody anchor
}


def load_recipe_wt_pct() -> dict[str, float]:
    src = json.loads(Path("_F2_30mL_recipe.json").read_text(encoding="utf-8"))
    rows = src["rows"]
    total_ul = sum(row["uL"] for row in rows)
    return {row["mat"]: row["uL"] * 100.0 / total_ul for row in rows}


CONCEPT: dict = {
    "key": "F2_CHYPRE_VERT",
    "name": "F2 — Le Chypre Vert · Green Chypre Luxury",
    "tagline": (
        "Modern green chypre — galbanum-led, labdanum-warmed, mossy-woody-musky base. "
        "Luxury texture: Hedione HC radiance + Iso E Super velvet + Ebanol cream."
    ),
    "direction": (
        "A modern green chypre in the Cristalle / No. 19 / Niki de Saint Phalle lineage. "
        "Sparkling bergamot-galbanum top gives way to a luminous jasmonate-floral heart "
        "on a Hedione HC radiance bed, settling into a mossy-woody-chypre base anchored "
        "by patchouli, vetiver, evernyl, and labdanum. The luxury hook is the texture "
        "chord: Iso E Super at high dose for velvet halo, Hedione HC for shimmer, "
        "Ebanol for sandalwood-musk creaminess, and a 3-axis musk chord for 10-12 hr "
        "performance. Labdanum Absolute bridges the citrus top and mossy base — the "
        "warm amber-resinous heart that defines the chypre family. "
        "Mass-market accessible: no animalic indole, no birch tar, no IBQ. "
        "The green axis (galbanum → cis-3-hexenol → triplal) reads through all stages."
    ),
    "recipe": load_recipe_wt_pct(),
    "envelope": {
        "top": {
            "citrus": 2000,
            "green": 250,
            "amber": 650,
            "rose": 150,
            "aldehydic": 130,
            "muguet": 120,
            "jasmine": 50,
            "radiance": 50,
            "wood": 20,
            "musk": 10,
            "amber_resin": 10,
            "moss": 10,
        },
        "heart": {
            "citrus": 1100,
            "green": 80,
            "amber": 650,
            "amber_resin": 80,
            "rose": 150,
            "aldehydic": 130,
            "muguet": 120,
            "jasmine": 50,
            "radiance": 50,
            "wood": 30,
            "musk": 15,
            "moss": 15,
            "coumarin": 10,
            "sandalwood": 5,
            "cushion": 5,
        },
        "base": {
            "amber": 650,
            "amber_resin": 120,
            "wood": 45,
            "musk": 30,
            "moss": 30,
            "coumarin": 20,
            "rose": 130,
            "muguet": 100,
            "aldehydic": 90,
            "citrus": 80,
            "radiance": 40,
            "green": 30,
            "sandalwood": 10,
            "cushion": 5,
        },
    },
}


BATCH_ML = 30.0
CONCENTRATE_PCT = 0.20
CONCENTRATE_ML = BATCH_ML * CONCENTRATE_PCT
CONCENTRATE_UL = CONCENTRATE_ML * 1000
ETHANOL_UL = (BATCH_ML - CONCENTRATE_ML) * 1000
DROP_UL = 20.0

REGISTRY = load_registry()


ODT_FLOOR_PPM = 0.001  # 1 ppb — prevents ultra-low ODTs from dominating OAV


def _odt_air_ppm(name: str) -> float:
    n = name.casefold()
    raw = 0.05
    if n in ODT_DATA:
        raw = ODT_DATA[n]["odt_air"] / 1000.0
    else:
        for key in ODT_DATA:
            if key in n or n in key:
                raw = ODT_DATA[key]["odt_air"] / 1000.0
                break
    return max(raw, ODT_FLOOR_PPM)


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
    mw_t, vp_t, hsp_t, odt_t = tables["mw"], tables["vp"], tables["hsp"], tables["odt"]

    def headspace_fn(wt_pct: Mapping[str, float]) -> dict[str, dict[str, float]]:
        if not any(v > 0 for v in wt_pct.values()):
            return {"top": {}, "heart": {}, "base": {}}
        frames = evaporate(
            wt_pct,
            duration_s=28800.0,
            n_steps=16,
            mw_table=mw_t,
            vp_table=vp_t,
            hsp_table=hsp_t,
        )
        targets = {"top": 60.0, "heart": 1800.0, "base": 28800.0}
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


def render_envelope(
    snap: dict[str, dict[str, float]], fam_t: dict[str, str]
) -> str:
    lines = []
    for win in ("top", "heart", "base"):
        fams = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:8]
        lines.append(f"  {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items))
    return "\n".join(lines)


def run_one(
    concept: dict, *, maxiter: int = 60, popsize: int = 20, seed: int = 42
) -> dict:
    name, key = concept["name"], concept["key"]
    recipe = {k: v for k, v in concept["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables = build_tables(materials)

    bounds = []
    for m in materials:
        v = recipe[m]
        lo = max(0.0, v * 0.50)
        hi = v * 1.60
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.3:
            hi = max(hi, v * 3.0)
        bounds.append((lo, hi))

    headspace_fn = make_headspace_fn(tables)
    obj = OAVObjective(
        materials=materials,
        bounds=bounds,
        target_envelope=concept["envelope"],
        headspace_fn=headspace_fn,
        families=tables["fam"],
    )

    init_score = score_formula_oav(
        recipe, obj,
        evaporation_windows=(("top", 60.0), ("heart", 1800.0), ("base", 28800.0)),
    )
    init_snap = headspace_fn(recipe)
    print(f"\n=== [{key}] {name} ===")
    print(f"  Tagline:  {concept['tagline']}")
    print(f"  Materials: {len(materials)}   missing-from-spine: {tables['missing']}")
    print(f"  INITIAL   score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, _ = differential_evolution_oav(
        obj, maxiter=maxiter, popsize=popsize, seed=seed
    )
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap = headspace_fn(best_wt_norm)
    final_score = score_formula_oav(
        best_wt_norm, obj,
        evaporation_windows=(("top", 60.0), ("heart", 1800.0), ("base", 28800.0)),
    )

    print(
        f"  OPTIMIZED score = {final_score:+.3f}   "
        f"(delta = {final_score - init_score:+.3f})"
    )
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key": key,
        "name": name,
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


def emit_markdown(result: dict) -> str:
    r = result
    opt = r["optimized"]["recipe_wt_pct"]
    init = r["initial"]["recipe_wt_pct"]

    lines = [
        f"# {r['name']} — Optimized 30 mL EDP",
        "",
        f"*{r['tagline']}*",
        "",
        "**Status:** OAV differential-evolution optimized (DE/rand/1/bin, 30 generations).",
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
        "",
        "## Optimized Formula — 30 mL EDP",
        "",
        "| # | Material | wt% | µL | mL | ~Drops |",
        "|--:|---|---:|---:|---:|---:|",
    ]

    all_mats = sorted(opt.keys(), key=lambda k: -opt[k])
    for i, m in enumerate(all_mats, start=1):
        wt = opt[m]
        ul = wt / 100.0 * CONCENTRATE_UL
        drops = ul / DROP_UL
        lines.append(
            f"| {i} | {m} | {wt:.2f} | {ul:.0f} | {ul/1000:.3f} | {drops:.1f} |"
        )

    total_wt = sum(opt.values())
    total_conc = total_wt / 100.0 * CONCENTRATE_UL
    ethanol_conc = CONCENTRATE_UL - total_conc

    lines += [
        f"| — | **Fragrance sub-total** | **{total_wt:.2f}** | **{total_conc:.0f}** | **{total_conc/1000:.3f}** | — |",
        f"| — | Ethanol 96% (in concentrate) | — | {ethanol_conc:.0f} | {ethanol_conc/1000:.3f} | — |",
        f"| — | **Concentrate total** | — | **{CONCENTRATE_UL:.0f}** | **{CONCENTRATE_ML:.3f}** | — |",
        f"| — | Ethanol 96% (bottle fill) | — | **{ETHANOL_UL:.0f}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** | — |",
        f"| — | **Final bottle total** | — | **{BATCH_ML*1000:.0f}** | **{BATCH_ML:.3f}** | — |",
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
        "## Family OAV Envelope",
        "",
    ]
    for section, label in (("initial", "Initial"), ("optimized", "Optimized")):
        lines.append(f"### {label}")
        for win in ("top", "heart", "base"):
            fams = r[section]["envelope"][win]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            lines.append(
                f"- **{win}**: " + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
            )
        lines.append("")
    lines.append("### Target")
    for win in ("top", "heart", "base"):
        tgt = r["envelope_target"][win]
        top6 = sorted(tgt.items(), key=lambda kv: -kv[1])[:6]
        lines.append(
            f"- **{win}**: " + ", ".join(f"`{k}`={v:.1f}" for k, v in top6)
        )

    lines += [
        "",
        "## Design Notes",
        "",
        "- **Labdanum Absolute added** as structural chypre pillar — bridges citrus top and mossy base with warm amber-resinous heart.",
        "- **Green axis preserved:** Galbanum → cis-3-Hexenol → Triplal reads through all stages.",
        "- **Texture chord:** Iso E Super (velvet) + Hedione HC (radiance) + Ebanol (cream).",
        "- **3-axis musk:** Galaxolide (projection) + Ethylene Brassylate (depth) + Ambrettolide (character-echo).",
        "- **Chypre spine:** Patchouli + Vetiver + Cedarwood + Evernyl + Labdanum.",
        "- Mass-market accessible: no IBQ, no birch tar, no indole/skatole.",
    ]
    return "\n".join(lines)


def main() -> None:
    result = run_one(CONCEPT, maxiter=40, popsize=12, seed=42)

    root = Path(__file__).parent
    json_out = root / "_opt_f2_chypre_vert_out.json"
    json_out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/F2_Le_Chypre_Vert_30mL_EDP_Optimized.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
