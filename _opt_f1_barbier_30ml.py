"""F1 — Le Barbier de Grasse, 30 mL EDP.

OAV differential-evolution optimizer derived from `_opt_vol_dambre_30ml.py`.
This version targets a more classical fougere envelope:

- lavender-aromatic lift
- bergamot freshness
- coumarin-led hay warmth
- mossy cedar / vetiver shadow
- restrained amber-musk support

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


FAMILY: dict[str, str] = {
    # Citrus / top
    "Bergamot FCF": "citrus",
    "Bergamot FCF oil Sicilian": "citrus",
    "Red Mandarin EO": "citrus",
    "Grapefruit FCF": "citrus",
    # Aromatic / fougere
    "Lavender EO": "aromatic",
    "Linalool": "aromatic",
    "Linalyl Acetate": "aromatic",
    "Ethyl Linalool": "aromatic",
    "Clary Sage EO": "aromatic",
    # Heart support
    "Hedione": "radiance",
    "Hedione HC": "radiance",
    "Geraniol": "geranium",
    "Phenethyl Alcohol": "geranium",
    "Eugenol": "spice",
    # Woods / moss / amber
    "Iso E Super": "wood",
    "Cedarwood EO": "wood",
    "Cedarwood oil Virginia": "wood",
    "Patchouli EO": "wood",
    "Vetiver EO": "wood",
    "Evernyl": "moss",
    "Ambrox Super": "amber",
    "Ambrofix": "amber",
    # Sweet / fougere base
    "Coumarin": "coumarin",
    "Vanillin": "gourmand",
    "Ethyl Vanillin": "gourmand",
    # Musks / cushion
    "Ethylene Brassylate": "musk",
    "Galaxolide": "musk",
    "Habanolide": "musk",
    "Romandolide": "musk",
    "Hexyl Salicylate": "cushion",
}


# Conservative caps on the as-held stock percentage inside the fragrance concentrate.
IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Bergamot FCF": 50.0,
    "Lavender EO": 15.0,
    "Linalool": 25.0,
    "Linalyl Acetate": 25.0,
    "Geraniol": 17.0,
    "Coumarin": 40.0,         # 20% stock, keeps active coumarin comfortably inside Cat. 4
    "Vanillin": 20.0,         # 10% stock
    "Hexyl Salicylate": 12.5,
    "Iso E Super": 60.0,
    "Eugenol": 2.5,
    "Hedione": 50.0,
    "Hedione HC": 25.0,
}


def load_recipe_wt_pct() -> dict[str, float]:
    src = json.loads(Path("_F1_30mL_EDP_recipe.json").read_text(encoding="utf-8"))
    rows = src["rows"]
    total_ul = sum(row["uL"] for row in rows)
    return {
        row["mat"]: row["uL"] * 100.0 / total_ul
        for row in rows
    }


CONCEPT: dict = {
    "key": "F1_BARBIER",
    "name": "F1 — Le Barbier de Grasse",
    "tagline": "Classical fougere — bergamot, lavender, coumarin, mossy cedar, amber-musk restraint.",
    "direction": (
        "A classical French barbershop fougere built around a lavender-coumarin axis, "
        "with bergamot lift, mossy cedar shadow, and a soft amber-musk bed. "
        "The brief is not modern sweet mass-appeal and not dense gourmand amber. "
        "Keep the structure recognisably fougere: aromatic top and heart must stay legible, "
        "coumarin must remain the warm hay signature, Evernyl must read as moss-shadow rather "
        "than bitterness, and the amber-musks should support rather than dominate. "
        "Vanilla warmth is welcome only as polish. Preserve elegance, dryness, and grooming-soap "
        "clarity over syrup or loud projection."
    ),
    "recipe": load_recipe_wt_pct(),
    "envelope": {
        "top": {
            "citrus": 900,
            "aromatic": 700,
            "spice": 35,
            "radiance": 20,
        },
        "heart": {
            "aromatic": 850,
            "citrus": 180,
            "radiance": 70,
            "geranium": 95,
            "spice": 50,
            "wood": 260,
            "coumarin": 120,
            "moss": 50,
        },
        "base": {
            "coumarin": 180,
            "moss": 120,
            "wood": 300,
            "amber": 650,
            "musk": 90,
            "gourmand": 120,
            "cushion": 40,
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
            out[win] = {
                n: {"oav": c.vapor_ppm / max(odt_t.get(n, 0.05), 1e-6)}
                for n, c in best.headspace.items()
            }
        return out

    return headspace_fn


def family_summed(profile: dict[str, dict[str, float]], fam_t: dict[str, str]) -> dict[str, float]:
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


def run_one(concept: dict, *, maxiter: int = 50, popsize: int = 16, seed: int = 42) -> dict:
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
    init_snap = headspace_fn(recipe)
    print(f"\n=== [{key}] {name} ===")
    print(f"  Tagline:  {concept['tagline']}")
    print(f"  Materials: {len(materials)}   missing-from-spine: {tables['missing']}")
    print(f"  INITIAL   score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, _ = differential_evolution_oav(obj, maxiter=maxiter, popsize=popsize, seed=seed)
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap = headspace_fn(best_wt_norm)
    final_score = score_formula_oav(best_wt_norm, obj)

    print(f"  OPTIMIZED score = {final_score:+.3f}   (delta = {final_score - init_score:+.3f})")
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


def emit_markdown(result: dict) -> str:
    r = result
    opt = r["optimized"]["recipe_wt_pct"]
    init = r["initial"]["recipe_wt_pct"]

    lines = [
        f"# {r['name']} — Optimized 30 mL EDP",
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
        "## Mixing Intent",
        "",
        "Base first, then aromatic heart, then bergamot top. This formula should stay recognisably fougere:",
        "dry-aromatic in the opening, lavender-coumarin in the heart, mossy-woody in the base, with the amber-musk layer behaving as support rather than as the main theme.",
    ]
    return "\n".join(lines)


def main() -> None:
    result = run_one(CONCEPT, maxiter=50, popsize=16, seed=42)

    root = Path(__file__).parent
    json_out = root / "_opt_f1_barbier_out.json"
    json_out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {json_out}")

    md_out = root / "formulas/collections/F1_Le_Barbier_de_Grasse_30mL_EDP_Optimized.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(emit_markdown(result), encoding="utf-8")
    print(f"Wrote {md_out}")


if __name__ == "__main__":
    main()
