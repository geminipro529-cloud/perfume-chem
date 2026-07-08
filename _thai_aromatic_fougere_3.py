"""Thai-market aromatic fougere optimizer.

Builds three 30 mL EDP aromatic fougeres from current inventory, optimized
against time-windowed OAV envelopes in a final 20% EDP ethanol solution.

The objective uses the project's physical model:
modified Raoult headspace -> Fick-style evaporation trajectory -> vapor ppm
-> ODT-normalized OAV -> family envelope fit.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Mapping

try:
    from scipy.optimize import differential_evolution
except Exception:  # pragma: no cover
    differential_evolution = None

from engine.data_spine.loader import load_registry
from engine.families.registry import archetype_penalty
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name
from engine.odor_thresholds import ODT_DATA
from engine.optimizer.gate_aware import optimize_until_release_ready, render_gate_audit_markdown
from engine.pipeline.gates import ReleaseGateConfig
from engine.thermo.trajectory import evaporate


ROOT = Path(__file__).resolve().parent
OUT_JSON = ROOT / "_thai_aromatic_fougere_3_out.json"
OUT_MD = ROOT / "formulas" / "collections" / "Thai_Aromatic_Fougere_3_Optimized.md"
BATCH_ML = 30.0
CONCENTRATE_ML = 6.0
EDP_CONCENTRATION = 0.20


def build_gate_config(
    *,
    commercial_ready: bool = False,
    commercial_trial: bool = False,
    ifra_headroom: float | None = None,
    scaling_targets_ml: tuple[float, ...] = (),
    audit_enabled: bool = True,
) -> ReleaseGateConfig:
    commercial_mode = commercial_ready or commercial_trial
    return ReleaseGateConfig(
        expected_concentrate_ul=CONCENTRATE_ML * 1000.0,
        batch_volume_ml=BATCH_ML,
        brief="aromatic_fougere",
        allow_preblends=False,
        min_confidence_score=25.0,
        ifra_headroom=ifra_headroom if ifra_headroom is not None else (0.8 if commercial_mode else 1.0),
        commercial_mode=commercial_mode,
        commercial_confidence_policy="warn" if commercial_trial else "block",
        batch_scaling_targets_ml=scaling_targets_ml,
        audit_enabled=audit_enabled,
        audit_source="_thai_aromatic_fougere_3.py",
    )


GATE_CONFIG = build_gate_config()


@dataclass(frozen=True)
class Stock:
    label: str
    dilution: float = 1.0


STOCKS: dict[str, Stock] = {
    "Aldehyde C12 MNA": Stock("1%", 0.01),
    "Ambrox Super": Stock("30%", 0.30),
    "Apritone": Stock("10%", 0.10),
    "Calone": Stock("1%", 0.01),
    "Coumarin": Stock("20%", 0.20),
    "Ethyl Maltol": Stock("10%", 0.10),
    "Ethyl Vanillin": Stock("10%", 0.10),
    "Floralozone": Stock("10%", 0.10),
    "Galaxolide": Stock("80%", 0.80),
    "Hexyl Acetate": Stock("10%", 0.10),
    "Methyl Pamplemousse": Stock("10%", 0.10),
    "Scentenal": Stock("1%", 0.01),
    "Vanillin": Stock("10%", 0.10),
}


FAMILY: dict[str, str] = {
    "Bergamot FCF": "citrus",
    "Bergamot FCF oil Sicilian": "citrus",
    "Cedrat FCF oil Sicilian": "citrus",
    "Grapefruit FCF": "citrus",
    "Red Mandarin EO": "citrus",
    "Lemonile": "citrus",
    "Lavender EO": "aromatic",
    "Clary Sage EO": "aromatic",
    "Linalool": "aromatic",
    "Linalyl Acetate": "aromatic",
    "Ethyl Linalool": "aromatic",
    "Dihydromyrcenol": "fresh",
    "Cyclamen Aldehyde": "fresh",
    "Floralozone": "marine",
    "Calone": "marine",
    "Scentenal": "marine",
    "Aldehyde C12 MNA": "sparkle",
    "cis-3-Hexenol": "green",
    "Cyclamen Aldehyde": "green",
    "Hedione": "radiance",
    "Hedione HC": "radiance",
    "Hydroxycitronellal": "floral",
    "Phenethyl Alcohol": "floral",
    "Nympheal": "floral",
    "Geraniol": "geranium",
    "Citronellol": "geranium",
    "Coumarin": "coumarin",
    "Evernyl": "moss",
    "Iso E Super": "wood",
    "Cedarwood EO": "wood",
    "Cedarwood oil Virginia": "wood",
    "Vetiver EO": "wood",
    "Patchouli EO": "wood",
    "Clearwood": "wood",
    "Sandalore": "wood",
    "Cashmeran": "wood",
    "Ambrox Super": "amber",
    "Azarbre": "amber",
    "Amberwood F": "amber",
    "Habanolide": "musk",
    "Romandolide": "musk",
    "Galaxolide": "musk",
    "Ethylene Brassylate": "musk",
    "Hexyl Salicylate": "cushion",
    "Benzyl Salicylate": "cushion",
    "Apritone": "fruity",
    "Hexyl Acetate": "fruity",
    "Ethyl 2-Methylbutyrate": "fruity",
    "Methyl Pamplemousse": "fruity",
    "Citral": "citrus",
    "Vanillin": "gourmand",
    "Ethyl Vanillin": "gourmand",
    "Ethyl Maltol": "gourmand",
    "Anisaldehyde": "gourmand",
    "Eugenol": "spice",
}


IFRA_CAP_RAW_PCT: dict[str, float] = {
    "Bergamot FCF": 35.0,
    "Bergamot FCF oil Sicilian": 35.0,
    "Cedrat FCF oil Sicilian": 18.0,
    "Grapefruit FCF": 18.0,
    "Lavender EO": 12.0,
    "Linalool": 18.0,
    "Linalyl Acetate": 18.0,
    "Coumarin": 8.0,
    "Citral": 1.0,
    "Eugenol": 2.0,
    "Geraniol": 10.0,
    "Citronellol": 10.0,
    "Hexyl Salicylate": 10.0,
    "Benzyl Salicylate": 15.0,
    "Calone": 4.0,
    "Scentenal": 3.0,
    "Evernyl": 0.40,
}


THAI_GATE_REPAIR_POOL: dict[str, float] = {
    "Iso E Super": 2.0,
    "Vetiver EO": 1.5,
    "Patchouli EO": 1.2,
    "Cedarwood EO": 1.0,
    "Cedarwood oil Virginia": 1.0,
    "Clearwood": 1.0,
    "Habanolide": 0.8,
    "Hexyl Salicylate": 0.6,
    "Ambrox Super": 0.5,
    "Sandalore": 0.5,
}


CONCEPTS: list[dict] = [
    {
        "name": "Siam Barber Citrus",
        "family_archetype": "aromatic_fougere.classic_reference",
        "tagline": "Bright office-safe aromatic fougere: bergamot rind, lavender-clary foam, dry vetiver moss.",
        "market_logic": (
            "Reference/control build for a classical barbershop fougere: fast freshness, low sticky sweetness, "
            "clean musks, and a recognizable lavender-coumarin-moss fougere frame."
        ),
        "initial": {
            "Bergamot FCF": 11.0,
            "Cedrat FCF oil Sicilian": 4.5,
            "Grapefruit FCF": 4.0,
            "Lavender EO": 8.0,
            "Clary Sage EO": 3.0,
            "Linalyl Acetate": 5.0,
            "Linalool": 3.2,
            "Ethyl Linalool": 3.0,
            "Dihydromyrcenol": 6.0,
            "cis-3-Hexenol": 0.45,
            "Hedione": 14.0,
            "Geraniol": 2.0,
            "Coumarin": 5.0,
            "Evernyl": 0.35,
            "Iso E Super": 12.0,
            "Cedarwood oil Virginia": 4.5,
            "Vetiver EO": 2.8,
            "Patchouli EO": 1.8,
            "Ambrox Super": 3.0,
            "Habanolide": 6.0,
            "Romandolide": 3.5,
            "Galaxolide": 2.3,
            "Hexyl Salicylate": 4.0,
        },
        "target": {
            "top": {"citrus": 900, "aromatic": 260, "fresh": 235, "green": 70, "radiance": 18},
            "heart": {"citrus": 420, "aromatic": 260, "fresh": 190, "green": 80, "radiance": 24, "coumarin": 16, "geranium": 18},
            "base": {"aromatic": 95, "wood": 45, "musk": 28, "moss": 10, "coumarin": 12, "amber": 15, "green": 8},
        },
    },
    {
        "name": "Andaman Mineral Fougere",
        "family_archetype": "aromatic_fougere.modern_mineral",
        "tagline": "Marine-green aromatic fougere: grapefruit spray, lavender metal, clear cedar musk.",
        "market_logic": (
            "A humid-climate fresh masculine direction: SEA-friendly aquatic lift, "
            "but with lavender, coumarin, moss, and vetiver to keep it fougere rather than shower gel."
        ),
        "initial": {
            "Bergamot FCF": 8.5,
            "Grapefruit FCF": 7.0,
            "Cedrat FCF oil Sicilian": 4.0,
            "Methyl Pamplemousse": 3.0,
            "Dihydromyrcenol": 12.0,
            "Floralozone": 4.0,
            "Calone": 2.0,
            "Scentenal": 1.2,
            "Lavender EO": 5.5,
            "Clary Sage EO": 2.5,
            "Linalool": 3.5,
            "Hedione": 15.0,
            "Phenethyl Alcohol": 1.5,
            "Nympheal": 1.4,
            "Geraniol": 1.2,
            "Coumarin": 2.8,
            "Evernyl": 0.3,
            "Iso E Super": 14.0,
            "Cedarwood EO": 4.8,
            "Vetiver EO": 2.4,
            "Ambrox Super": 4.0,
            "Cashmeran": 0.8,
            "Romandolide": 5.0,
            "Habanolide": 4.0,
            "Galaxolide": 2.2,
            "Hexyl Salicylate": 3.4,
        },
        "target": {
            "top": {"fresh": 1200, "citrus": 1050, "marine": 360, "aromatic": 170, "radiance": 16, "floral": 12},
            "heart": {"fresh": 1000, "citrus": 460, "marine": 320, "aromatic": 170, "radiance": 22, "floral": 45, "coumarin": 8},
            "base": {"fresh": 420, "wood": 42, "musk": 26, "amber": 25, "aromatic": 55, "floral": 16, "moss": 5},
        },
    },
    {
        "name": "Bangkok Tonka Fougere",
        "family_archetype": "aromatic_fougere.modern_tonka_mass",
        "tagline": "Mass-appeal sweet aromatic fougere: mandarin-lavender, apple-tonka, polished woods.",
        "market_logic": (
            "Uses the Layton lesson, not the Layton family: a small fruity-spiced hook "
            "over a real lavender-coumarin-moss fougere body, with sweetness capped for heat."
        ),
        "initial": {
            "Bergamot FCF": 8.0,
            "Red Mandarin EO": 5.0,
            "Grapefruit FCF": 3.0,
            "Apritone": 2.3,
            "Hexyl Acetate": 1.8,
            "Ethyl 2-Methylbutyrate": 0.35,
            "Lavender EO": 7.5,
            "Clary Sage EO": 2.2,
            "Linalyl Acetate": 5.0,
            "Ethyl Linalool": 3.0,
            "Dihydromyrcenol": 4.5,
            "Linalool": 2.5,
            "cis-3-Hexenol": 0.35,
            "Hedione": 12.5,
            "Geraniol": 2.0,
            "Citronellol": 1.0,
            "Coumarin": 7.0,
            "Evernyl": 0.35,
            "Iso E Super": 10.0,
            "Cedarwood oil Virginia": 3.2,
            "Vetiver EO": 2.0,
            "Patchouli EO": 2.2,
            "Sandalore": 3.0,
            "Ambrox Super": 3.0,
            "Habanolide": 5.0,
            "Romandolide": 3.0,
            "Ethylene Brassylate": 3.0,
            "Vanillin": 2.5,
            "Ethyl Vanillin": 3.0,
        },
        "target": {
            "top": {"citrus": 680, "aromatic": 230, "fresh": 175, "green": 55, "fruity": 100, "radiance": 16},
            "heart": {"aromatic": 235, "citrus": 300, "fresh": 145, "green": 65, "fruity": 75, "coumarin": 22, "radiance": 22},
            "base": {"aromatic": 85, "wood": 42, "musk": 30, "coumarin": 18, "gourmand": 18, "amber": 18, "green": 6},
        },
    },
]


REGISTRY = load_registry()
ODT_INDEX = {normalize_name(k): v for k, v in ODT_DATA.items()}


def stock_for(name: str) -> Stock:
    return STOCKS.get(name, Stock("neat", 1.0))


def stock_dilutions_for(raw_pct: Mapping[str, float]) -> dict[str, float]:
    return {name: stock_for(name).dilution for name in raw_pct}


def _material_physics(name: str) -> tuple[float, float, tuple[float, float, float] | None]:
    if name == "Ethanol":
        return 46.07, 7900.0, (15.8, 8.8, 19.4)
    if name == "Carrier":
        return 134.0, 0.01, (17.4, 11.2, 21.0)

    rec = REGISTRY.get(name)
    if rec is not None:
        mw = rec.mw_g_mol or None
        vp = rec.vp_25c_pa or None
        hsp = None
        if rec.hsp.delta_d is not None:
            hsp = (rec.hsp.delta_d, rec.hsp.delta_p or 0.0, rec.hsp.delta_h or 0.0)
        if mw is not None and vp is not None:
            return float(mw), float(vp), hsp

    prof = get_profile(name)
    if prof is not None:
        return float(prof.mw or 200.0), float(prof.vp or 1.0), None

    return 200.0, 1.0, None


def build_tables(materials: list[str]) -> dict[str, dict]:
    all_names = ["Ethanol", "Carrier", *materials]
    mw_t: dict[str, float] = {}
    vp_t: dict[str, float] = {}
    hsp_t: dict[str, tuple[float, float, float]] = {}
    odt_t: dict[str, float] = {}
    missing: list[str] = []

    for name in all_names:
        mw, vp, hsp = _material_physics(name)
        mw_t[name] = mw
        vp_t[name] = vp
        if hsp is not None:
            hsp_t[name] = hsp
        if name not in ("Ethanol", "Carrier"):
            odt_t[name] = odt_air_ppm(name)
            if REGISTRY.get(name) is None and get_profile(name) is None:
                missing.append(name)

    return {"mw": mw_t, "vp": vp_t, "hsp": hsp_t, "odt": odt_t, "missing": missing}


def odt_air_ppm(name: str) -> float:
    data = ODT_INDEX.get(normalize_name(name))
    if data is not None and data.get("odt_air") is not None:
        return float(data["odt_air"]) / 1000.0
    return 0.05


def normalize_raw_pct(raw_pct: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(v, 0.0) for v in raw_pct.values())
    if total <= 0:
        return {k: 0.0 for k in raw_pct}
    return {k: max(v, 0.0) * 100.0 / total for k, v in raw_pct.items()}


def final_edp_wt_pct(raw_concentrate_pct: Mapping[str, float]) -> dict[str, float]:
    raw_norm = normalize_raw_pct(raw_concentrate_pct)
    final: dict[str, float] = {"Ethanol": 80.0}
    active_sum = 0.0
    for mat, pct in raw_norm.items():
        active = pct * EDP_CONCENTRATION * stock_for(mat).dilution
        if active > 0:
            final[mat] = active
            active_sum += active
    carrier = 20.0 - active_sum
    if carrier > 0:
        final["Carrier"] = carrier
    return final


def trajectory_snapshots(
    raw_concentrate_pct: Mapping[str, float],
    tables: dict[str, dict],
    *,
    n_steps: int = 18,
) -> dict[str, dict[str, dict[str, float]]]:
    final_wt = final_edp_wt_pct(raw_concentrate_pct)
    frames = evaporate(
        final_wt,
        initial_mass_g=0.05,
        duration_s=14400.0,
        n_steps=n_steps,
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
                "liquid_moles": frame.moles_remaining.get(mat, 0.0),
            }
        out[window] = rows
    return out


def family_envelope(snapshot: dict[str, dict[str, dict[str, float]]]) -> dict[str, dict[str, float]]:
    env: dict[str, dict[str, float]] = {}
    for window, rows in snapshot.items():
        fams: dict[str, float] = {}
        for mat, payload in rows.items():
            fam = FAMILY.get(mat, "default")
            fams[fam] = fams.get(fam, 0.0) + payload["oav"]
        env[window] = fams
    return env


def _log_error(obs: dict[str, float], target: dict[str, float]) -> float:
    err = 0.0
    keys = set(target)
    for key in keys:
        err += (math.log1p(obs.get(key, 0.0)) - math.log1p(target.get(key, 0.0))) ** 2
    return err


def objective_score(raw_pct: Mapping[str, float], concept: dict, tables: dict[str, dict]) -> float:
    raw_norm = normalize_raw_pct(raw_pct)
    snap = trajectory_snapshots(raw_norm, tables, n_steps=12)
    env = family_envelope(snap)

    error = 0.0
    for window in ("top", "heart", "base"):
        error += _log_error(env.get(window, {}), concept["target"].get(window, {}))
    error += archetype_penalty(
        {
            "ingredients_pct": raw_norm,
            "dilutions": stock_dilutions_for(raw_norm),
        },
        concept.get("family_archetype", ""),
        fail_weight=3.0,
    )

    # Fougere grammar: lavender/aromatic in top-heart; coumarin+moss/wood in base.
    top = env.get("top", {})
    heart = env.get("heart", {})
    base = env.get("base", {})
    fougere_penalty = 0.0
    if top.get("aromatic", 0.0) < 90:
        fougere_penalty += 1.0
    if heart.get("aromatic", 0.0) < 90:
        fougere_penalty += 1.0
    if base.get("coumarin", 0.0) < 4:
        fougere_penalty += 0.8
    if base.get("moss", 0.0) + base.get("wood", 0.0) < 20:
        fougere_penalty += 0.8

    # Thai heat adaptation: cap sticky sweetness and dense amber dominance.
    heat_penalty = 0.0
    if base.get("gourmand", 0.0) > 45:
        heat_penalty += (base["gourmand"] - 45.0) / 25.0
    if top.get("amber", 0.0) > top.get("citrus", 0.0) * 0.45 + 60:
        heat_penalty += 0.6

    # Reduce one-material perceptual flooding in each window.
    flood_penalty = 0.0
    for rows in snap.values():
        total_oav = sum(row["oav"] for row in rows.values())
        if total_oav <= 0:
            continue
        max_share = max((row["oav"] / total_oav for row in rows.values()), default=0.0)
        if max_share > 0.72:
            flood_penalty += (max_share - 0.72) * 3.0

    return -(error + fougere_penalty + heat_penalty + flood_penalty)


def optimize_concept(concept: dict, *, seed: int, gate_config: ReleaseGateConfig = GATE_CONFIG) -> dict:
    initial = normalize_raw_pct(concept["initial"])
    materials = list(initial.keys())
    tables = build_tables(materials)
    bounds = []
    for mat in materials:
        base = initial[mat]
        lo = max(0.0, base * 0.60)
        hi = base * 1.42
        if mat in ("Calone", "Scentenal", "Ethyl 2-Methylbutyrate", "Ethyl Maltol"):
            hi = base * 1.20
        cap = IFRA_CAP_RAW_PCT.get(mat)
        if cap is not None:
            hi = min(hi, cap)
        bounds.append((lo, hi))

    def neg(x: list[float]) -> float:
        raw = {mat: float(value) for mat, value in zip(materials, x)}
        return -objective_score(raw, concept, tables)

    if differential_evolution is None:  # pragma: no cover
        best_x = [initial[m] for m in materials]
        best = neg(best_x)
    else:
        result = differential_evolution(
            neg,
            bounds=bounds,
            maxiter=18,
            popsize=7,
            seed=seed,
            polish=True,
            tol=1e-5,
            updating="immediate",
        )
        best_x = [float(v) for v in result.x]
        best = float(result.fun)

    optimized_candidate = normalize_raw_pct({mat: value for mat, value in zip(materials, best_x)})
    gate_result = optimize_until_release_ready(
        concept["name"],
        optimized_candidate,
        stock_dilutions_for(optimized_candidate),
        config=gate_config,
        concentrate_ul=CONCENTRATE_ML * 1000.0,
        repair_pool=THAI_GATE_REPAIR_POOL,
        body=concept["market_logic"],
        family_archetype=concept.get("family_archetype", ""),
        max_passes=4,
    )
    optimized = normalize_raw_pct(gate_result.raw_concentrate_pct)
    init_snap = trajectory_snapshots(initial, tables, n_steps=24)
    opt_snap = trajectory_snapshots(optimized, tables, n_steps=24)
    init_score = objective_score(initial, concept, tables)
    pre_repair_score = objective_score(optimized_candidate, concept, tables)
    opt_score = objective_score(optimized, concept, tables)

    return {
        "name": concept["name"],
        "family_archetype": concept.get("family_archetype", ""),
        "tagline": concept["tagline"],
        "market_logic": concept["market_logic"],
        "target": concept["target"],
        "missing_from_spine": tables["missing"],
        "initial": {
            "raw_concentrate_pct": {k: round(v, 4) for k, v in sorted(initial.items(), key=lambda item: -item[1])},
            "score": init_score,
            "envelope": family_envelope(init_snap),
            "windows": init_snap,
        },
        "optimized": {
            "raw_concentrate_pct": {k: round(v, 4) for k, v in sorted(optimized.items(), key=lambda item: -item[1])},
            "score": opt_score,
            "pre_repair_score": pre_repair_score,
            "optimizer_fun": best,
            "envelope": family_envelope(opt_snap),
            "windows": opt_snap,
            "gate_status": gate_result.status,
            "commercial_readiness": gate_result.commercial_readiness,
        },
        "gate_aware": gate_result.as_dict(),
        "score_delta": opt_score - init_score,
    }


def top_window_rows(window_rows: dict[str, dict[str, float]], n: int = 8) -> list[tuple[str, dict[str, float]]]:
    return sorted(window_rows.items(), key=lambda item: -item[1]["oav"])[:n]


def format_family_line(env: dict[str, float]) -> str:
    parts = []
    for fam, value in sorted(env.items(), key=lambda item: -item[1])[:8]:
        parts.append(f"`{fam}`={value:.1f}")
    return ", ".join(parts)


def fougere_mixing_phase(mat: str) -> tuple[int, str]:
    family = FAMILY.get(mat, "default")
    if family in {"musk", "wood", "moss", "coumarin", "cushion", "amber", "gourmand"}:
        return 1, "Foundation"
    if family in {"radiance", "geranium", "floral"}:
        return 2, "Heart Bridge"
    if family in {"aromatic"}:
        return 3, "Aromatic Support"
    if family in {"citrus", "fresh", "marine", "green", "fruity", "sparkle", "spice"}:
        return 4, "Top Impact"
    return 3, "Aromatic Support"


def render_fougere_mixing_order(rows: list[tuple[str, float, int]]) -> list[str]:
    indexed: list[tuple[int, str, int, str]] = []
    for mat, _raw_pct, amount_ul in rows:
        phase_num, phase_name = fougere_mixing_phase(mat)
        indexed.append((phase_num, phase_name, amount_ul, mat))
    indexed.sort(key=lambda item: (item[0], -item[2], item[3]))

    lines = [
        "### Mixing Order",
        "",
        "| Step | Phase | Material | Dilution | Amount (uL) | Amount (mL) |",
        "|---:|---|---|---|---:|---:|",
    ]
    for step, (_phase_num, phase_name, amount_ul, mat) in enumerate(indexed, start=1):
        lines.append(
            f"| {step} | {phase_name} | {mat} | {stock_for(mat).label} | {amount_ul} | {amount_ul / 1000.0:.3f} |"
        )
    lines.extend([
        f"| {len(indexed) + 1} | Final Dilution | Ethanol 96% bottle fill | neat | {int((BATCH_ML - CONCENTRATE_ML) * 1000)} | {BATCH_ML - CONCENTRATE_ML:.3f} |",
        "",
        "1. Add foundation materials first so the moss-wood-musk body and coumarin cushion are fully integrated.",
        "2. Add the heart bridge next to lock the fougere body into the base before the fresh top goes on.",
        "3. Add aromatic support once the concentrate is uniform.",
        "4. Add the top-impact materials last to preserve lift, freshness, and volatility.",
        "5. Rest 48 hours before first read; judge seriously after 14 days.",
        "",
    ])
    return lines


def render_markdown(results: list[dict]) -> str:
    lines: list[str] = [
        "# Thai Aromatic Fougere - 3 Optimized 30 mL EDPs",
        "",
        "**Status:** Commercial-trial candidates when generated with `--commercial-trial`; not sellable until calibrated with real wear-test records.",
        "",
        "These are final 30 mL EDP builds at 20% concentrate: 6.00 mL concentrate plus 24.00 mL ethanol.",
        "Optimization used final-solution evaporation snapshots rather than static concentrate percentages.",
        "",
        "Layton classification note: Layton is treated here as an amber-floral / oriental-floral masculine, not a true aromatic fougere. The fougeres below borrow only the mass-appeal lesson: freshness plus comfort, with sweetness controlled for Thai heat.",
        "Exploration order: build Andaman Mineral Fougere first for the new modern direction, Bangkok Tonka Fougere second for mass appeal, and keep Siam Barber Citrus as the reference/control.",
        "",
        "## Optimization Model",
        "",
        "- Final EDP liquid model: 80% ethanol plus 20% raw concentrate.",
        "- Diluted stocks are handled as active material plus low-volatility carrier.",
        "- Vapor ppm comes from modified Raoult headspace inside the evaporation trajectory.",
        "- OAV = vapor ppm / ODT ppm, using `engine/odor_thresholds.py`.",
        "- Target windows: top ~1 min, heart ~30 min, base ~4 hr.",
        "",
    ]

    for idx, result in enumerate(results, start=1):
        opt = result["optimized"]
        pct = opt["raw_concentrate_pct"]
        lines.extend([
            f"## {idx}. {result['name']}",
            "",
            f"*{result['tagline']}*",
            "",
            f"**Market logic:** {result['market_logic']}",
            "",
            f"**Family archetype:** `{result['family_archetype']}`",
            "",
            f"**Optimizer score:** `{result['initial']['score']:.3f} -> {opt['score']:.3f}` (`{result['score_delta']:+.3f}`)",
            "",
        ])
        lines.extend(render_gate_audit_markdown(result["gate_aware"]))
        lines.extend([
            "### Optimized Formula - 30 mL EDP",
            "",
            "| # | Material | Dilution | Amount (uL) | Amount (mL) |",
            "|---:|---|---:|---:|---:|",
        ])
        rows: list[tuple[str, float, int]] = []
        total_ul = 0
        for mat, raw_pct in pct.items():
            amount_ul = int(round(CONCENTRATE_ML * 1000.0 * raw_pct / 100.0))
            rows.append((mat, raw_pct, amount_ul))
            total_ul += amount_ul
        adjust = int(CONCENTRATE_ML * 1000.0) - total_ul
        if adjust != 0 and rows:
            largest_idx = max(range(len(rows)), key=lambda i: rows[i][2])
            mat, raw_pct, amount_ul = rows[largest_idx]
            rows[largest_idx] = (mat, raw_pct, amount_ul + adjust)
            total_ul += adjust

        for row_idx, (mat, _raw_pct, amount_ul) in enumerate(rows, start=1):
            stock = stock_for(mat)
            lines.append(f"| {row_idx} | {mat} | {stock.label} | {amount_ul} | {amount_ul / 1000.0:.3f} |")
        lines.extend([
            f"| - | **Fragrance concentrate subtotal** | - | **{total_ul}** | **{total_ul / 1000.0:.3f}** |",
            f"| - | Ethanol 96% bottle fill | neat | **{int((BATCH_ML - CONCENTRATE_ML) * 1000)}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** |",
            f"| - | **Final bottle total** | - | **{int(BATCH_ML * 1000)}** | **{BATCH_ML:.3f}** |",
            "",
            "### Family OAV Envelope",
            "",
            "| Window | Optimized family OAV |",
            "|---|---|",
        ])
        for window in ("top", "heart", "base"):
            lines.append(f"| {window} | {format_family_line(opt['envelope'][window])} |")

        lines.extend([
            "",
            "### Vapor ppm / ODT / OAV Leaders",
            "",
        ])
        for window in ("top", "heart", "base"):
            lines.extend([
                f"**{window} window**",
                "",
                "| Material | Vapor ppm | ODT ppm | OAV |",
                "|---|---:|---:|---:|",
            ])
            for mat, payload in top_window_rows(opt["windows"][window], n=8):
                lines.append(
                    f"| {mat} | {payload['vapor_ppm']:.6f} | "
                    f"{payload['odt_ppm']:.6f} | {payload['oav']:.1f} |"
                )
            lines.append("")

        lines.extend(render_fougere_mixing_order(rows))

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Thai aromatic fougere optimized formulas.")
    commercial = parser.add_mutually_exclusive_group()
    commercial.add_argument("--commercial-ready", action="store_true")
    commercial.add_argument("--commercial-trial", action="store_true")
    parser.add_argument("--ifra-headroom", type=float, default=None)
    parser.add_argument("--scaling-target-ml", type=float, action="append", default=[])
    parser.add_argument("--no-audit", action="store_true")
    args = parser.parse_args(argv)
    gate_config = build_gate_config(
        commercial_ready=args.commercial_ready,
        commercial_trial=args.commercial_trial,
        ifra_headroom=args.ifra_headroom,
        scaling_targets_ml=tuple(args.scaling_target_ml or ()),
        audit_enabled=not args.no_audit,
    )
    results = [
        optimize_concept(concept, seed=1776 + i, gate_config=gate_config)
        for i, concept in enumerate(CONCEPTS)
    ]
    OUT_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    failed = [result["name"] for result in results if result["gate_aware"]["status"] == "FAIL"]
    if failed:
        raise RuntimeError(
            "Release gates failed; refusing to write Optimized markdown for: "
            + ", ".join(failed)
        )
    OUT_MD.write_text(render_markdown(results), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    for result in results:
        opt = result["optimized"]
        gate = result["gate_aware"]
        print(
            f"{result['name']}: {result['initial']['score']:.3f} -> {opt['score']:.3f} "
            f"[gate={gate['status']} readiness={gate['commercial_readiness']}]"
        )
        print("  top:", format_family_line(opt["envelope"]["top"]))
        print("  heart:", format_family_line(opt["envelope"]["heart"]))
        print("  base:", format_family_line(opt["envelope"]["base"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
