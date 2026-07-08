"""Addition-only optimizer for Vol d'Ambre v3c -> Thai aromatic fougere.

This models the already-built v3c bottle, including the documented post-mix
amber/wood boosters, then searches only for add-on volumes. The objective is
not a pure Thai fougere from zero: it preserves Layton DNA while adding enough
lavender/coumarin/moss/fresh structure for an aromatic fougere read.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping

try:
    from scipy.optimize import differential_evolution
except Exception:  # pragma: no cover
    differential_evolution = None

from engine.data_spine.loader import load_registry
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA
from engine.thermo.trajectory import evaporate


ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "_opt_layton_fougere_addonly_out.json"

BOTTLE_UL = 30_000.0
BASE_NOTE = "Vol d'Ambre v3c plus documented Ambrox/Azarbre/Javanol/Norlimbanol/Timberol additions"

STOCK_DILUTION: dict[str, float] = {
    "Vanillin": 0.10,
    "Coumarin": 0.20,
    "Apritone": 0.10,
    "Hexyl Acetate": 0.10,
    "Cardamom FTEC": 0.10,
    "Benzoin Resinoid": 0.50,
    "Ambrox Super": 0.30,
}

FAMILY: dict[str, str] = {
    "Bergamot FCF": "citrus",
    "Lime Distilled EO": "citrus",
    "Grapefruit FCF": "citrus",
    "Red Mandarin EO": "citrus",
    "Lavender EO": "aromatic",
    "Spike Lavender EO": "aromatic",
    "Linalyl Acetate": "aromatic",
    "Ethyl Linalool": "aromatic",
    "Linalool": "aromatic",
    "Dihydromyrcenol": "fresh",
    "Juniper Berry EO": "aromatic",
    "Beta-Pinene": "aromatic",
    "Terpinyl Acetate": "aromatic",
    "Clary Sage EO": "aromatic",
    "Petitgrain EO": "aromatic",
    "Apritone": "fruity",
    "Hexyl Acetate": "fruity",
    "Ethyl 2-Methylbutyrate": "fruity",
    "Cardamom FTEC": "spice",
    "Eugenol": "spice",
    "Hedione": "radiance",
    "Benzyl Acetate": "floral",
    "Dihydrojasmone": "floral",
    "Geraniol": "floral",
    "Phenethyl Alcohol": "floral",
    "Alpha Isomethyl Ionone": "powdery",
    "Iso E Super": "wood",
    "Javanol": "wood",
    "Sandalore": "wood",
    "Cashmeran": "wood",
    "Timberol": "wood",
    "Clearwood": "wood",
    "Cedarwood oil Virginia": "wood",
    "Vetiver EO": "wood",
    "Patchouli EO": "wood",
    "Nagarmortha Oil": "wood",
    "Evernyl": "moss",
    "Ambrox Super": "amber",
    "Azarbre": "amber",
    "Norlimbanol Dextro": "wood",
    "Vanillin": "gourmand",
    "Ethyl Vanillin": "gourmand",
    "Coumarin": "coumarin",
    "Benzoin Resinoid": "balsamic",
    "Benzyl Salicylate": "cushion",
    "Galaxolide": "musk",
    "Habanolide": "musk",
    "Romandolide": "musk",
    "Ethylene Brassylate": "musk",
    "Frankincense EO": "resin",
}

PHYSICS_OVERRIDES: dict[str, tuple[float, float]] = {
    "Lime Distilled EO": (136.2, 170.0),
    "Juniper Berry EO": (136.2, 65.0),
    "Spike Lavender EO": (154.3, 24.0),
    "Beta-Pinene": (136.2, 390.0),
    "Frankincense EO": (136.2, 25.0),
    "Nagarmortha Oil": (220.0, 0.005),
    "Norlimbanol Dextro": (226.4, 0.001),
}

ODT_OVERRIDES_PPB: dict[str, float] = {
    "Lime Distilled EO": 8.0,
    "Juniper Berry EO": 10.0,
    "Spike Lavender EO": 20.0,
    "Beta-Pinene": 25.0,
    "Nagarmortha Oil": 5.0,
}


# Stock-as-held volumes already in the current bottle. This includes the v3c
# concentrate and the documented post-mix base + Timberol additions.
BASE_STOCK_UL: dict[str, float] = {
    "Vanillin": 658,
    "Hedione": 557,
    "Ambrox Super": 456 + 900,
    "Bergamot FCF": 390,
    "Lavender EO": 390,
    "Iso E Super": 289,
    "Apritone": 260,
    "Cardamom FTEC": 230,
    "Javanol": 225 + 100,
    "Benzoin Resinoid": 218,
    "Habanolide": 214,
    "Coumarin": 205,
    "Linalyl Acetate": 184,
    "Sandalore": 171,
    "Galaxolide": 165,
    "Alpha Isomethyl Ionone": 154,
    "Hexyl Acetate": 153,
    "Benzyl Acetate": 148,
    "Benzyl Salicylate": 123,
    "Dihydromyrcenol": 120,
    "Geraniol": 117,
    "Cashmeran": 93,
    "Ethyl Linalool": 93,
    "Phenethyl Alcohol": 87,
    "Ethyl Vanillin": 81,
    "Romandolide": 78,
    "Ethylene Brassylate": 71,
    "Dihydrojasmone": 58,
    "Azarbre": 150,
    "Timberol": 100,
    "Norlimbanol Dextro": 40,
    "Ethyl 2-Methylbutyrate": 9,
}

# Do not prioritize new materials: all useful existing inventory levers are in
# the same search space. Bounds are finished-bottle add-on microliters.
CANDIDATE_BOUNDS_UL: dict[str, tuple[float, float]] = {
    "Evernyl": (0, 24),  # 80% IFRA-headroom approximation for 30 mL Cat 4.
    "Dihydromyrcenol": (0, 130),
    "Linalyl Acetate": (0, 100),
    "Lavender EO": (0, 70),
    "Spike Lavender EO": (0, 90),
    "Lime Distilled EO": (0, 120),
    "Grapefruit FCF": (0, 80),
    "Juniper Berry EO": (0, 70),
    "Beta-Pinene": (0, 25),
    "Terpinyl Acetate": (0, 80),
    "Clary Sage EO": (0, 55),
    "Petitgrain EO": (0, 45),
    "Coumarin": (0, 80),
    "Cardamom FTEC": (0, 45),
    "Apritone": (0, 45),
    "Hexyl Acetate": (0, 30),
    "Ethyl 2-Methylbutyrate": (0, 5),
    "Vetiver EO": (0, 45),
    "Patchouli EO": (0, 22),
    "Clearwood": (0, 45),
    "Cedarwood oil Virginia": (0, 50),
    "Nagarmortha Oil": (0, 12),
    "Frankincense EO": (0, 45),
}

NEW_MATERIALS = {
    "Spike Lavender EO",
    "Lime Distilled EO",
    "Juniper Berry EO",
    "Beta-Pinene",
    "Nagarmortha Oil",
    "Frankincense EO",
}

FINAL_PASS_ADDITIONS_UL: dict[str, float] = {
    "Evernyl": 23,
    "Patchouli EO": 8,
    "Vetiver EO": 8,
    "Cedarwood oil Virginia": 45,
    "Coumarin": 70,
    "Linalyl Acetate": 80,
    "Terpinyl Acetate": 70,
    "Clary Sage EO": 35,
    "Petitgrain EO": 30,
    "Lavender EO": 20,
    "Spike Lavender EO": 15,
    "Dihydromyrcenol": 40,
    "Lime Distilled EO": 50,
    "Juniper Berry EO": 15,
    "Beta-Pinene": 12,
    "Cardamom FTEC": 20,
    "Apritone": 12,
}

# Priority-shifted pass requested 2026-04-30:
# 1) best Thai mass-market smell/performance, 2) masculine aromatic fougere read.
# This lowers gate-forcing moss/coumarin/herbal pressure and reallocates mass to
# clean diffusion, fresh impact, and musky/woody persistence.
PERFORMANCE_FIRST_ADDITIONS_UL: dict[str, float] = {
    "Evernyl": 16,
    "Patchouli EO": 5,
    "Vetiver EO": 6,
    "Cedarwood oil Virginia": 50,
    "Iso E Super": 90,
    "Habanolide": 45,
    "Coumarin": 45,
    "Linalyl Acetate": 70,
    "Terpinyl Acetate": 50,
    "Clary Sage EO": 25,
    "Petitgrain EO": 20,
    "Lavender EO": 15,
    "Spike Lavender EO": 8,
    "Dihydromyrcenol": 75,
    "Grapefruit FCF": 45,
    "Lime Distilled EO": 35,
    "Juniper Berry EO": 10,
    "Beta-Pinene": 5,
    "Cardamom FTEC": 15,
    "Apritone": 10,
}

REGISTRY = load_registry()
ODT_INDEX = {normalize_name(k): v for k, v in ODT_DATA.items()}


def stock_dilution(name: str) -> float:
    return STOCK_DILUTION.get(name, 1.0)


def _material_physics(name: str) -> tuple[float, float]:
    if name == "Ethanol":
        return 46.07, 7900.0
    if name == "Carrier":
        return 134.0, 0.01
    if name in PHYSICS_OVERRIDES:
        return PHYSICS_OVERRIDES[name]

    rec = REGISTRY.get(name)
    if rec is not None and rec.mw_g_mol and rec.vp_25c_pa:
        return float(rec.mw_g_mol), float(rec.vp_25c_pa)

    prof = get_profile(name)
    if prof is not None and prof.mw and prof.vp:
        return float(prof.mw), float(prof.vp)

    return 200.0, 1.0


def odt_air_ppm(name: str) -> float:
    if name in ODT_OVERRIDES_PPB:
        return ODT_OVERRIDES_PPB[name] / 1000.0
    data = ODT_INDEX.get(normalize_name(name))
    if data is not None and data.get("odt_air") is not None:
        return float(data["odt_air"]) / 1000.0
    if name == "Nagarmortha Oil":
        data = ODT_INDEX.get("cypriol eo")
        if data:
            return float(data["odt_air"]) / 1000.0
    return 0.05


def build_tables(materials: list[str]) -> dict[str, dict]:
    all_names = ["Ethanol", "Carrier", *materials]
    mw_t: dict[str, float] = {}
    vp_t: dict[str, float] = {}
    odt_t: dict[str, float] = {}
    missing: list[str] = []

    for name in all_names:
        mw, vp = _material_physics(name)
        mw_t[name] = mw
        vp_t[name] = vp
        if name not in ("Ethanol", "Carrier"):
            odt_t[name] = odt_air_ppm(name)
            if REGISTRY.get(name) is None and name not in PHYSICS_OVERRIDES and get_profile(name) is None:
                missing.append(name)
    return {"mw": mw_t, "vp": vp_t, "hsp": {}, "odt": odt_t, "missing": missing}


def combine(additions_ul: Mapping[str, float]) -> dict[str, float]:
    out = dict(BASE_STOCK_UL)
    for mat, ul in additions_ul.items():
        if ul <= 0:
            continue
        out[mat] = out.get(mat, 0.0) + float(ul)
    return out


def final_wt_pct(stock_ul: Mapping[str, float]) -> dict[str, float]:
    total_ul = BOTTLE_UL + sum(stock_ul.get(m, 0.0) for m in CANDIDATE_BOUNDS_UL)
    final: dict[str, float] = {}
    active_sum = 0.0
    carrier_sum = 0.0
    for mat, ul in stock_ul.items():
        dilution = stock_dilution(mat)
        active = ul * dilution / total_ul * 100.0
        carrier = ul * (1.0 - dilution) / total_ul * 100.0
        if active > 0:
            final[mat] = final.get(mat, 0.0) + active
            active_sum += active
        carrier_sum += carrier
    if carrier_sum > 0:
        final["Carrier"] = carrier_sum
    final["Ethanol"] = max(0.0, 100.0 - active_sum - carrier_sum)
    return final


def snapshots(stock_ul: Mapping[str, float], tables: dict[str, dict]) -> dict[str, dict[str, dict[str, float]]]:
    frames = evaporate(
        final_wt_pct(stock_ul),
        initial_mass_g=0.05,
        duration_s=14400.0,
        n_steps=10,
        mw_table=tables["mw"],
        vp_table=tables["vp"],
        hsp_table=tables["hsp"],
    )
    targets = {"top": 60.0, "heart": 1800.0, "base": 14400.0}
    out: dict[str, dict[str, dict[str, float]]] = {}
    for window, target_s in targets.items():
        frame = min(frames, key=lambda f: abs(f.t_seconds - target_s))
        rows: dict[str, dict[str, float]] = {}
        for mat, comp in frame.headspace.items():
            if mat in ("Ethanol", "Carrier"):
                continue
            odt = max(tables["odt"].get(mat, 0.05), 1e-9)
            rows[mat] = {
                "vapor_ppm": comp.vapor_ppm,
                "odt_ppm": odt,
                "oav": comp.vapor_ppm / odt,
            }
        out[window] = rows
    return out


def family_envelope(snap: Mapping[str, Mapping[str, Mapping[str, float]]]) -> dict[str, dict[str, float]]:
    env: dict[str, dict[str, float]] = {}
    for window, rows in snap.items():
        fams: dict[str, float] = {}
        for mat, payload in rows.items():
            fam = FAMILY.get(mat, "default")
            fams[fam] = fams.get(fam, 0.0) + payload["oav"]
        env[window] = fams
    return env


def log_fit(value: float, target: float) -> float:
    return (math.log1p(max(value, 0.0)) - math.log1p(target)) ** 2


def objective(additions_ul: Mapping[str, float], base_env: dict[str, dict[str, float]], tables: dict[str, dict]) -> float:
    total_add = sum(additions_ul.values())
    stock = combine(additions_ul)
    env = family_envelope(snapshots(stock, tables))

    # Fit deltas, not absolutes: the current bottle must keep its Layton body.
    target_delta = {
        "top": {"fresh": 360, "citrus": 300, "aromatic": 250},
        "heart": {"fresh": 260, "aromatic": 220, "moss": 8},
        "base": {"moss": 6, "wood": 14, "coumarin": 4, "aromatic": 45},
    }
    err = 0.0
    for window, targets in target_delta.items():
        for fam, target in targets.items():
            delta = env.get(window, {}).get(fam, 0.0) - base_env.get(window, {}).get(fam, 0.0)
            err += log_fit(delta, target)

    # Required aromatic fougere grammar. Evernyl is kept small for IFRA, so the
    # moss read may be trace-level, supported by dry woods and existing coumarin.
    grammar_penalty = 0.0
    base = env["base"]
    heart = env["heart"]
    top = env["top"]
    if (base.get("moss", 0.0) - base_env["base"].get("moss", 0.0)) < 3:
        grammar_penalty += 2.0
    if heart.get("aromatic", 0.0) < base_env["heart"].get("aromatic", 0.0) + 120:
        grammar_penalty += 1.0
    if top.get("fresh", 0.0) < base_env["top"].get("fresh", 0.0) + 180:
        grammar_penalty += 0.8
    if base.get("coumarin", 0.0) < base_env["base"].get("coumarin", 0.0) + 1.5:
        grammar_penalty += 0.5

    # Thai mass-market freshness, but no shower-gel marine and no extra amber.
    thai_penalty = 0.0
    if top.get("fresh", 0.0) > base_env["top"].get("fresh", 0.0) + 900:
        thai_penalty += 0.8
    if total_add < 260:
        thai_penalty += ((260 - total_add) / 120) ** 2
    if total_add > 620:
        thai_penalty += ((total_add - 620) / 120) ** 2

    # Layton retention: keep new material mass and dark-earth additions modest.
    new_total = sum(additions_ul.get(m, 0.0) for m in NEW_MATERIALS)
    retention_penalty = 0.0
    if new_total > total_add * 0.55:
        retention_penalty += ((new_total / max(total_add, 1.0) - 0.55) / 0.15) ** 2
    dark_earth = additions_ul.get("Patchouli EO", 0.0) + additions_ul.get("Nagarmortha Oil", 0.0)
    if dark_earth > 25:
        retention_penalty += ((dark_earth - 25) / 12) ** 2
    layton_hook_add = (
        additions_ul.get("Apritone", 0.0)
        + additions_ul.get("Cardamom FTEC", 0.0)
        + additions_ul.get("Hexyl Acetate", 0.0)
    )
    if layton_hook_add < 20:
        retention_penalty += 0.5

    return -(err + grammar_penalty + thai_penalty + retention_penalty)


def optimize() -> dict:
    materials = sorted(set(BASE_STOCK_UL) | set(CANDIDATE_BOUNDS_UL))
    tables = build_tables(materials)
    base_snap = snapshots(BASE_STOCK_UL, tables)
    base_env = family_envelope(base_snap)
    candidates = list(CANDIDATE_BOUNDS_UL)
    bounds = [CANDIDATE_BOUNDS_UL[m] for m in candidates]

    def neg(x):
        additions = {mat: max(0.0, float(value)) for mat, value in zip(candidates, x)}
        return -objective(additions, base_env, tables)

    if differential_evolution is None:
        best_x = [(lo + hi) / 2.0 for lo, hi in bounds]
        optimizer_fun = neg(best_x)
    else:
        result = differential_evolution(
            neg,
            bounds,
            maxiter=12,
            popsize=5,
            seed=729,
            polish=False,
            tol=1e-4,
            updating="immediate",
        )
        best_x = [float(v) for v in result.x]
        optimizer_fun = float(result.fun)

    additions = {
        mat: round(max(0.0, value), 1)
        for mat, value in zip(candidates, best_x)
        if value >= 2.0
    }
    final_stock = combine(additions)
    final_snap = snapshots(final_stock, tables)
    final_env = family_envelope(final_snap)
    pass_stock = combine(FINAL_PASS_ADDITIONS_UL)
    pass_snap = snapshots(pass_stock, tables)
    pass_env = family_envelope(pass_snap)
    performance_stock = combine(PERFORMANCE_FIRST_ADDITIONS_UL)
    performance_snap = snapshots(performance_stock, tables)
    performance_env = family_envelope(performance_snap)

    return {
        "input": BASE_NOTE,
        "missing_from_spine": tables["missing"],
        "optimizer_fun": optimizer_fun,
        "score": objective(additions, base_env, tables),
        "base_envelope": base_env,
        "optimized_additions_ul": dict(sorted(additions.items(), key=lambda item: -item[1])),
        "total_add_ul": round(sum(additions.values()), 1),
        "new_material_add_ul": round(sum(additions.get(m, 0.0) for m in NEW_MATERIALS), 1),
        "final_envelope": final_env,
        "base_windows": base_snap,
        "final_windows": final_snap,
        "chemist_perfumer_final_pass": {
            "additions_ul": FINAL_PASS_ADDITIONS_UL,
            "total_add_ul": round(sum(FINAL_PASS_ADDITIONS_UL.values()), 1),
            "new_material_add_ul": round(sum(FINAL_PASS_ADDITIONS_UL.get(m, 0.0) for m in NEW_MATERIALS), 1),
            "score": objective(FINAL_PASS_ADDITIONS_UL, base_env, tables),
            "envelope": pass_env,
            "windows": pass_snap,
            "rationale": (
                "Trim low-value trace clutter, keep new materials below 20% of the addition, "
                "cap Evernyl for conservative IFRA headroom, and retain Cardamom FTEC/Apritone "
                "so the fougere still smells Layton-derived."
            ),
        },
        "performance_first_final_pass": {
            "additions_ul": PERFORMANCE_FIRST_ADDITIONS_UL,
            "total_add_ul": round(sum(PERFORMANCE_FIRST_ADDITIONS_UL.values()), 1),
            "new_material_add_ul": round(
                sum(PERFORMANCE_FIRST_ADDITIONS_UL.get(m, 0.0) for m in NEW_MATERIALS),
                1,
            ),
            "score": objective(PERFORMANCE_FIRST_ADDITIONS_UL, base_env, tables),
            "envelope": performance_env,
            "windows": performance_snap,
            "rationale": (
                "Performance-first Thai mass-market pass: trade some strict family-gate moss/coumarin/herb "
                "pressure for Iso E Super/Habanolide diffusion, higher Dihydromyrcenol freshness, and a "
                "grapefruit-lime top while retaining enough lavender/coumarin/Evernyl to read masculine fougere."
            ),
        },
    }


def top_families(env: Mapping[str, float]) -> str:
    return ", ".join(f"{k}={v:.1f}" for k, v in sorted(env.items(), key=lambda item: -item[1])[:8])


def main() -> int:
    result = optimize()
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Input: {result['input']}")
    print(f"Missing/overridden from spine: {result['missing_from_spine']}")
    print(f"Score: {result['score']:.3f}; total add: {result['total_add_ul']} uL")
    print("Optimized additions:")
    for mat, ul in result["optimized_additions_ul"].items():
        print(f"  {mat}: {ul:.1f} uL")
    print("Final family OAV:")
    for window in ("top", "heart", "base"):
        print(f"  {window}: {top_families(result['final_envelope'][window])}")
    final_pass = result["chemist_perfumer_final_pass"]
    print(f"Chemist/perfumer final pass total: {final_pass['total_add_ul']} uL; score: {final_pass['score']:.3f}")
    for mat, ul in final_pass["additions_ul"].items():
        print(f"  {mat}: {ul:.1f} uL")
    performance_pass = result["performance_first_final_pass"]
    print(
        f"Performance-first final pass total: {performance_pass['total_add_ul']} uL; "
        f"score: {performance_pass['score']:.3f}"
    )
    for mat, ul in performance_pass["additions_ul"].items():
        print(f"  {mat}: {ul:.1f} uL")
    print(f"Wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
