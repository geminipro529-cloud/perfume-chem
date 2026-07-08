"""Five mass-appeal fougères — NAMED, with directional briefs, then optimized
to each concept's specific olfactive arc.

v2 changes vs _fougere_5_mass_appeal.py:
  * Each formula has a name, tagline, and detailed directional description.
  * Target OAV envelopes are now scaled to *realistic* per-window magnitudes
    (informed by the v1 initial-run observations), so the optimizer chases
    the concept's intended shape rather than collapsing everything to zero.
  * Per-concept envelope shapes embody a distinct fougère direction
    (classical bracing, marine sport, gourmet boulangerie, polar-amber
    minimalism, urban cashmere wood).
  * Tightened bounds (±35% instead of ±50%) so we stay inside each concept.
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


# ─────────────────────────────────────────────────────────────────────────────
# Family map (same axes as v1; copied for self-containment)
# ─────────────────────────────────────────────────────────────────────────────
FAMILY: dict[str, str] = {
    "Lavender EO": "aromatic", "Linalool": "aromatic", "Linalyl Acetate": "aromatic",
    "Ethyl Linalool": "aromatic", "Clary Sage EO": "aromatic", "Eucalyptol": "aromatic",
    "Bergamot FCF": "citrus", "Bergamot FCF oil Sicilian": "citrus",
    "Grapefruit FCF": "citrus", "Red Mandarin EO": "citrus",
    "Blood Orange oil Sicilian": "citrus", "D-Limonene": "citrus", "Citral": "citrus",
    "Geraniol": "geranium", "Citronellol": "geranium", "Phenethyl Alcohol": "geranium",
    "Coumarin": "coumarin",
    "Calone": "marine", "Floralozone": "marine", "Dihydromyrcenol": "marine",
    "Eugenol": "spice",
    "Iso E Super": "wood", "Cedarwood EO": "wood", "Cedarwood oil Virginia": "wood",
    "Vetiver EO": "wood", "Patchouli EO": "wood", "Sandalore": "wood",
    "Ebanol": "wood", "Bacdanol": "wood", "Javanol": "wood", "Vetival": "wood",
    "Timberol": "wood", "Koavone": "wood", "Clearwood": "wood",
    "Ambrox Super": "amber", "Ambrofix": "amber", "Ambermax": "amber",
    "Amberwood F": "amber", "Cedramber": "amber", "Azarbre": "amber",
    "Evernyl": "moss",
    "Galaxolide": "musk", "Habanolide": "musk", "Romandolide": "musk",
    "Ethylene Brassylate": "musk", "Exaltolide": "musk", "Ambrettolide": "musk",
    "Zenolide": "musk",
    "Vanillin": "gourmand", "Ethyl Vanillin": "gourmand", "Heliotropal": "gourmand",
    "Anisaldehyde": "gourmand", "Ethyl Maltol": "gourmand", "Maple Lactone": "gourmand",
    "Hexyl Salicylate": "cushion", "Benzyl Salicylate": "cushion",
    "Hedione": "radiance", "Hedione HC": "radiance",
    "Cashmeran": "wood",  # textile-warm wood, mapped to wood for fougère grammar
}

IFRA_CAP_PCT_CONC: dict[str, float] = {
    "Eugenol": 2.5, "Citral": 5.0, "Coumarin": 7.0,
    "Linalool": 25.0, "Geraniol": 17.0, "Citronellol": 25.0,
    "Bergamot FCF": 50.0, "Lavender EO": 15.0,
    "Hexyl Salicylate": 12.5, "Benzyl Salicylate": 25.0,
    "Hedione": 50.0, "Iso E Super": 60.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Five named fougères with directional briefs
# ─────────────────────────────────────────────────────────────────────────────

CONCEPTS: list[dict] = [
    {
        "key": "F1",
        "name": "Le Barbier de Grasse",
        "tagline": "The classical aromatic fougère — boulevard, leather glove, hot shave-shop towel.",
        "direction": (
            "A bracing 1970s-architecture fougère. Cold-pressed bergamot rind hits "
            "first, then a clean lavandin-and-clary-sage bracket opens onto a "
            "geranium-rose accent. The drydown is the signature fougère triangle: "
            "coumarin-hay sweetness against oakmoss bitterness against a smoky "
            "vetiver-patchouli base, knit by polycyclic musks. Diffusive but "
            "intimate; a barbershop classic, not a sport-deo. "
            "Direction: emphasise aromatic + coumarin + moss; restrain citrus to a "
            "*bright but brief* opening; let the wood/moss/musk drydown carry."
        ),
        "recipe": {
            "Bergamot FCF": 12.0, "Lavender EO": 10.0, "Linalyl Acetate": 5.0,
            "Geraniol": 3.0, "Coumarin": 6.0, "Eugenol": 1.5,
            "Hedione": 15.0, "Iso E Super": 12.0, "Cedarwood EO": 6.0,
            "Patchouli EO": 5.0, "Vetiver EO": 3.0, "Evernyl": 2.0,
            "Habanolide": 8.0, "Galaxolide": 6.5, "Ambrox Super": 2.0,
            "Vanillin": 1.0, "Hexyl Salicylate": 2.0,
        },
        # Targets in OAV-magnitude (informed by v1 initial: top citrus≈4000, heart aromatic≈1200, base wood≈40)
        "envelope": {
            "top":   {"citrus": 2200, "aromatic": 1000, "geranium": 80,  "radiance": 60},
            "heart": {"aromatic": 1100, "coumarin": 90, "geranium": 90, "radiance": 80, "spice": 90, "citrus": 1500},
            "base":  {"aromatic": 350, "moss": 30, "wood": 80, "musk": 40, "coumarin": 60, "amber": 50},
        },
    },
    {
        "key": "F2",
        "name": "Côte Sauvage",
        "tagline": "Salt-cured marine fougère — wet rock, sea-pine, sun-bleached driftwood.",
        "direction": (
            "A modern aquatic fougère in the Cool-Water / Acqua-di-Giò lineage but "
            "skewed toward MINERAL rather than ozonic. Dihydromyrcenol gives the "
            "metallic-green sport opening; Calone trace adds the iodine-melon "
            "marine signature WITHOUT going synthetic-laundry. Hedione carries a "
            "ghost-floral radiance, and the drydown is dry cedar + transparent "
            "Romandolide musk — never sweet, never powdery. "
            "Direction: lift the marine and citrus axes hard; suppress gourmand "
            "and coumarin entirely; keep wood transparent (Iso E + cedar, not "
            "creamy sandal); musk is projection-only (Romandolide-led, not "
            "Habanolide-warm)."
        ),
        "recipe": {
            "Bergamot FCF": 10.0, "Grapefruit FCF": 4.0, "Dihydromyrcenol": 15.0,
            "Lavender EO": 6.0, "Calone": 0.4, "Floralozone": 3.0,
            "Hedione": 14.0, "Coumarin": 3.0, "Geraniol": 1.5,
            "Iso E Super": 12.0, "Cedarwood EO": 5.0, "Vetiver EO": 2.0,
            "Habanolide": 7.0, "Romandolide": 6.0, "Ambrox Super": 2.5,
            "Amberwood F": 3.0, "Hexyl Salicylate": 5.6,
        },
        "envelope": {
            "top":   {"marine": 35000, "citrus": 18000, "aromatic": 700, "radiance": 25},
            "heart": {"marine": 30000, "aromatic": 750, "radiance": 30, "citrus": 6000, "geranium": 25},
            "base":  {"marine": 18000, "amber": 90, "wood": 45, "musk": 40, "aromatic": 270, "cushion": 25},
        },
    },
    {
        "key": "F3",
        "name": "Boulanger de Minuit",
        "tagline": "Lavender pâtisserie at midnight — warm tonka, vanilla cream, hot oven sugar.",
        "direction": (
            "A gourmand fougère in the Le Mâle / A*Men lineage but pulled toward "
            "BAKERY-warm rather than chocolate-dark. The lavender is real EO (not "
            "synthetic), so the herb edge cuts through the sugar. Coumarin-tonka "
            "and vanillin form a hay-and-custard duet; ethyl maltol adds caramel "
            "lift; heliotropal and anisaldehyde push almond-pâtisserie. "
            "Drydown is creamy ebanol sandalwood + ethylene-brassylate musk — "
            "milky, soft, intimate. "
            "Direction: maximise gourmand + coumarin in heart and base; keep "
            "aromatic strong (lavender must read); marine and moss banished; "
            "wood pulled toward creamy (Sandalore/Ebanol) not dry."
        ),
        "recipe": {
            "Bergamot FCF": 8.0, "Lavender EO": 12.0, "Linalyl Acetate": 4.0,
            "Hedione": 12.0, "Coumarin": 7.0, "Vanillin": 4.0,
            "Ethyl Maltol": 0.6, "Heliotropal": 2.0, "Anisaldehyde": 1.5,
            "Eugenol": 1.0, "Cedarwood EO": 5.0, "Sandalore": 4.0,
            "Iso E Super": 10.0, "Ambrox Super": 2.5, "Ambermax": 3.0,
            "Habanolide": 5.0, "Ethylene Brassylate": 7.0, "Galaxolide": 4.4,
            "Patchouli EO": 5.0, "Hexyl Salicylate": 2.0,
        },
        "envelope": {
            "top":   {"citrus": 1500, "aromatic": 1300, "amber": 450, "gourmand": 120, "radiance": 40},
            "heart": {"aromatic": 1300, "coumarin": 90, "gourmand": 130, "amber": 450, "radiance": 50, "spice": 50},
            "base":  {"aromatic": 450, "amber": 550, "gourmand": 170, "wood": 80, "coumarin": 70, "musk": 50},
        },
    },
    {
        "key": "F4",
        "name": "Ambre Polaire",
        "tagline": "Polar-amber minimalism — bergamot ozone, ambroxan crystal, pink-pepper bite.",
        "direction": (
            "A modern Sauvage-lineage fougère stripped to three structural pillars: "
            "(a) a brilliant citrus-aromatic top — bergamot + mandarin + a thread "
            "of lavender — (b) a Hedione-led floral radiance with a single eugenol-"
            "geraniol spice prick, and (c) a Maximum-Ambrox base with cedar/iso-E "
            "transparency. No moss, no gourmand, no animalic warmth — the brief is "
            "*cold, mineral, infinite*. The musk is Romandolide-projection plus a "
            "thread of Habanolide for skin-adhesion. "
            "Direction: drive amber to dominance in heart and base; maximise "
            "radiance; keep wood transparent (no sandalwood, no patchouli mass); "
            "remove all gourmand, marine, moss; allow trace spice."
        ),
        "recipe": {
            "Bergamot FCF": 14.0, "Red Mandarin EO": 3.0, "Lavender EO": 5.0,
            "Linalool": 3.0, "Hedione": 15.0, "Eugenol": 0.8, "Geraniol": 1.5,
            "Iso E Super": 18.0, "Cedarwood EO": 4.0, "Patchouli EO": 3.0,
            "Vetiver EO": 1.5, "Ambrox Super": 6.0, "Ambrofix": 3.0,
            "Amberwood F": 4.0, "Habanolide": 6.0, "Romandolide": 5.0,
            "Galaxolide": 2.7, "Hexyl Salicylate": 1.5, "Citral": 0.6,
        },
        "envelope": {
            "top":   {"citrus": 12000, "aromatic": 1800, "amber": 1100, "radiance": 30},
            "heart": {"citrus": 5500, "aromatic": 2000, "amber": 1300, "radiance": 35, "spice": 50, "geranium": 25},
            "base":  {"amber": 1700, "aromatic": 550, "wood": 55, "musk": 50, "radiance": 45, "spice": 55},
        },
    },
    {
        "key": "F5",
        "name": "Velours de Cèdre",
        "tagline": "Urban cashmere wood — Virginian cedar, suede vetiver, soft ambrox velvet.",
        "direction": (
            "A woody-aromatic fougère in the Boss-Bottled / Bleu-de-Chanel lineage "
            "but pushed toward TEXTILE-warm rather than sport-cool. The opening is "
            "bergamot + grapefruit pith + a quiet lavender; the heart is Hedione-"
            "radiant with a small geranium-coumarin thread; the drydown is the "
            "star — Virginian cedar + dry vetiver + Iso-E molecular halo + a "
            "Cashmeran wrap, anchored by a soft Ambrox-Amberwood pair and a "
            "Romandolide+Habanolide musk chord. "
            "Direction: maximise wood density in base; keep amber present but "
            "subordinate to wood; allow a small coumarin warmth (not a gourmand "
            "axis); restrain citrus to a clean opening; no moss, no marine, no "
            "gourmand."
        ),
        "recipe": {
            "Bergamot FCF": 11.0, "Grapefruit FCF": 3.0, "Lavender EO": 7.0,
            "Linalyl Acetate": 3.0, "Geraniol": 2.0, "Hedione": 14.0,
            "Coumarin": 3.0, "Cedarwood oil Virginia": 6.0, "Cedarwood EO": 3.0,
            "Iso E Super": 16.0, "Vetiver EO": 4.0, "Patchouli EO": 3.0,
            "Sandalore": 3.0, "Ebanol": 2.0, "Ambrox Super": 3.0,
            "Amberwood F": 2.5, "Cashmeran": 0.4, "Habanolide": 7.0,
            "Romandolide": 4.5, "Hexyl Salicylate": 1.0,
        },
        "envelope": {
            "top":   {"citrus": 16000, "aromatic": 850, "wood": 80, "amber": 65, "radiance": 25},
            "heart": {"citrus": 5500, "aromatic": 900, "wood": 90, "amber": 75, "radiance": 30, "geranium": 25, "coumarin": 40},
            "base":  {"wood": 130, "amber": 90, "aromatic": 290, "musk": 50, "radiance": 35, "coumarin": 45},
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Engine glue (same as v1)
# ─────────────────────────────────────────────────────────────────────────────
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


def family_summed(profile: dict[str, dict[str, float]], fam_t: dict[str, str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for m, p in profile.items():
        out[fam_t.get(m, "default")] = out.get(fam_t.get(m, "default"), 0.0) + p.get("oav", 0.0)
    return out


def render_envelope(snap: dict[str, dict[str, float]], fam_t: dict[str, str]) -> str:
    lines = []
    for win in ("top", "heart", "base"):
        fams = family_summed(snap.get(win, {}), fam_t)
        items = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
        lines.append(f"  {win:5s}: " + "  ".join(f"{k}={v:.1f}" for k, v in items))
    return "\n".join(lines)


def run_one(concept: dict, *, maxiter: int = 40, popsize: int = 14, seed: int = 42) -> dict:
    name, key = concept["name"], concept["key"]
    recipe = {k: v for k, v in concept["recipe"].items() if v > 0}
    materials = list(recipe.keys())
    tables = build_tables(materials)

    bounds = []
    for m in materials:
        v = recipe[m]
        lo = max(0.0, v * 0.65)
        hi = v * 1.45
        cap = IFRA_CAP_PCT_CONC.get(m)
        if cap is not None:
            hi = min(hi, cap)
        if v < 0.5:
            hi = max(hi, v * 2.0)
        bounds.append((lo, hi))

    headspace_fn = make_headspace_fn(tables)
    obj = OAVObjective(
        materials=materials, bounds=bounds,
        target_envelope=concept["envelope"],
        headspace_fn=headspace_fn, families=tables["fam"],
    )

    init_score = score_formula_oav(recipe, obj)
    init_snap = headspace_fn(recipe)
    print(f"\n=== [{key}] {name} ===")
    print(f"  Tagline: {concept['tagline']}")
    print(f"  Materials: {len(materials)}   missing-from-spine: {tables['missing']}")
    print(f"  INITIAL  score = {init_score:+.3f}")
    print(render_envelope(init_snap, tables["fam"]))

    best_wt, best_score = differential_evolution_oav(obj, maxiter=maxiter, popsize=popsize, seed=seed)
    total = sum(best_wt.values()) or 1.0
    best_wt_norm = {k: v * 100.0 / total for k, v in best_wt.items()}
    best_snap = headspace_fn(best_wt_norm)
    final_score = score_formula_oav(best_wt_norm, obj)
    print(f"  OPTIMIZED score = {final_score:+.3f}   (delta = {final_score - init_score:+.3f})")
    print(render_envelope(best_snap, tables["fam"]))

    return {
        "key": key, "name": name, "tagline": concept["tagline"],
        "direction": concept["direction"],
        "envelope_target": concept["envelope"],
        "initial": {
            "recipe_wt_pct": recipe,
            "score": init_score,
            "envelope": {w: family_summed(init_snap[w], tables["fam"]) for w in ("top", "heart", "base")},
        },
        "optimized": {
            "recipe_wt_pct": {k: round(v, 3) for k, v in sorted(best_wt_norm.items(), key=lambda kv: -kv[1])},
            "score": final_score,
            "envelope": {w: family_summed(best_snap[w], tables["fam"]) for w in ("top", "heart", "base")},
        },
        "delta_score": final_score - init_score,
        "missing_from_spine": tables["missing"],
    }


def main():
    out = {c["key"]: run_one(c) for c in CONCEPTS}

    out_path = Path(__file__).parent / "_fougere_5_named_v2_out.json"
    out_path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")

    # Markdown
    md = ["# Five Named Fougeres — Direction-Optimized\n",
          "Each formula has a stated *direction* (concept brief). The optimizer "
          "tunes wt% to match a per-window OAV envelope shaped to that direction.\n",
          "All values are **wt% of fragrance concentrate** (no batch volumes; scales "
          "by mass to any size). Single molecules + EOs only — no FOs/FTECs/Cores.\n"]
    for key, r in out.items():
        md.append(f"\n---\n\n## {r['name']}\n")
        md.append(f"*{r['tagline']}*\n")
        md.append(f"\n**Direction.** {r['direction']}\n")
        md.append(f"\n**Score delta:** {r['delta_score']:+.3f}\n")
        md.append("\n### Recipe (wt% of concentrate)\n")
        md.append("| Material | Initial | Optimized | Δ |")
        md.append("|---|---:|---:|---:|")
        all_mats = sorted(set(r["initial"]["recipe_wt_pct"]) | set(r["optimized"]["recipe_wt_pct"]),
                          key=lambda k: -r["optimized"]["recipe_wt_pct"].get(k, 0))
        for m in all_mats:
            i = r["initial"]["recipe_wt_pct"].get(m, 0)
            o = r["optimized"]["recipe_wt_pct"].get(m, 0)
            md.append(f"| {m} | {i:.2f} | {o:.2f} | {o - i:+.2f} |")
        md.append("\n### Family OAV envelope (optimized)\n")
        for w in ("top", "heart", "base"):
            fams = r["optimized"]["envelope"][w]
            top6 = sorted(fams.items(), key=lambda kv: -kv[1])[:6]
            md.append(f"- **{w}**: " + ", ".join(f"`{k}`={v:.1f}" for k, v in top6))
    md_path = Path(__file__).parent / "_fougere_5_named_v2_out.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    main()
