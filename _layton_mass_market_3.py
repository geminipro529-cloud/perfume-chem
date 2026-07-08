"""Generate three mass-market Layton-DNA-inspired 30 mL EDP variants.

The formulas are not aromatic fougeres. They preserve a Layton-axis grammar:
apple/citrus/cardamom-like top, lavender as support, Hedione-led radiance, and an
amber-vanilla-sandalwood/musk drydown. Proprietary cardamom-base fidelity is
intentionally sacrificed for transparent commercial-trial buildability.
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
OUT_JSON = ROOT / "_layton_mass_market_3_out.json"
OUT_MD = ROOT / "formulas" / "collections" / "Layton_DNA_Mass_Market_3_Optimized.md"

BATCH_ML = 30.0
CONCENTRATE_ML = 6.0
CONCENTRATE_UL = int(CONCENTRATE_ML * 1000)
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
        expected_concentrate_ul=CONCENTRATE_UL,
        batch_volume_ml=BATCH_ML,
        brief="layton_dna",
        allow_preblends=False,
        min_confidence_score=25.0,
        ifra_headroom=ifra_headroom if ifra_headroom is not None else (0.8 if commercial_mode else 1.0),
        commercial_mode=commercial_mode,
        commercial_confidence_policy="warn" if commercial_trial else "block",
        batch_scaling_targets_ml=scaling_targets_ml,
        audit_enabled=audit_enabled,
        audit_source="_layton_mass_market_3.py",
    )


GATE_CONFIG = build_gate_config()


@dataclass(frozen=True)
class Stock:
    label: str
    dilution: float = 1.0


STOCKS: dict[str, Stock] = {
    "Aldehyde C12 MNA": Stock("1%", 0.01),
    "Ambrettolide": Stock("10%", 0.10),
    "Ambrox Super": Stock("30%", 0.30),
    "Apritone": Stock("10%", 0.10),
    "Benzoin Resinoid": Stock("50%", 0.50),
    "Coumarin": Stock("20%", 0.20),
    "Ethyl Maltol": Stock("10%", 0.10),
    "Ethyl 2-Methylbutyrate": Stock("10% prep", 0.10),
    "Ethyl Vanillin": Stock("10%", 0.10),
    "Galaxolide": Stock("80%", 0.80),
    "Hexyl Acetate": Stock("10%", 0.10),
    "Vanillin": Stock("10%", 0.10),
}


FAMILY: dict[str, str] = {
    "Bergamot FCF": "citrus",
    "Cedrat FCF oil Sicilian": "citrus",
    "Grapefruit FCF": "citrus",
    "Red Mandarin EO": "citrus",
    "Dihydromyrcenol": "fresh",
    "Lavender EO": "aromatic",
    "Linalyl Acetate": "aromatic",
    "Ethyl Linalool": "aromatic",
    "Linalool": "aromatic",
    "Terpinyl Acetate": "aromatic",
    "Aldehyde C12 MNA": "sparkle",
    "Apritone": "fruity",
    "Hexyl Acetate": "fruity",
    "Ethyl 2-Methylbutyrate": "fruity",
    "Eugenol": "spice",
    "Hedione": "radiance",
    "Benzyl Acetate": "floral",
    "Dihydrojasmone": "floral",
    "Geraniol": "floral",
    "Phenethyl Alcohol": "floral",
    "Nympheal": "floral",
    "Alpha Isomethyl Ionone": "powdery",
    "Iso E Super": "wood",
    "Sandalore": "wood",
    "Timberol": "wood",
    "Norlimbanol Dextro": "wood",
    "Cashmeran": "wood",
    "Ambrox Super": "amber",
    "Azarbre": "amber",
    "Vanillin": "gourmand",
    "Ethyl Vanillin": "gourmand",
    "Benzoin Resinoid": "balsamic",
    "Coumarin": "coumarin",
    "Habanolide": "musk",
    "Romandolide": "musk",
    "Galaxolide": "musk",
    "Ethylene Brassylate": "musk",
    "Ambrettolide": "musk",
}


# Raw concentrate caps. For diluted materials this caps the stock-as-held row.
CAP_RAW_PCT: dict[str, float] = {
    "Lavender EO": 4.5,
    "Ethyl 2-Methylbutyrate": 1.00,
    "Terpinyl Acetate": 4.5,
    "Eugenol": 0.45,
    "Norlimbanol Dextro": 0.65,
    "Coumarin": 3.5,
    "Benzyl Acetate": 3.0,
    "Benzoin Resinoid": 3.0,
    "Ethyl Vanillin": 6.0,
    "Dihydromyrcenol": 2.40,
    "Aldehyde C12 MNA": 0.45,
    "Nympheal": 0.90,
    "Phenethyl Alcohol": 3.00,
}


LAYTON_GATE_REPAIR_POOL: dict[str, float] = {
    "Iso E Super": 2.0,
    "Ambrox Super": 1.5,
    "Habanolide": 1.2,
    "Ethylene Brassylate": 1.0,
    "Romandolide": 1.0,
    "Sandalore": 1.0,
    "Hedione": 0.8,
    "Benzoin Resinoid": 0.5,
    "Vanillin": 0.4,
}


CONCEPTS: list[dict] = [
    {
        "name": "Bangkok Fresh Layton",
        "family_archetype": "layton_dna.fresh_thai",
        "tagline": "Daytime Layton DNA-inspired: bergamot-citron apple, transparent cardamom air, clean amber musk.",
        "market_logic": (
            "Built for Thai daytime and malls: keep the apple-cardamom-like hook, reduce winter "
            "vanilla density, and let citrus/fresh musks carry projection."
        ),
        "perfumer_literacy": (
            "A non-technical perfumer should read this as a commercial fresh amber: apple "
            "and a transparent cardamom impression are obvious in the top, lavender is support, and the drydown is "
            "soft vanilla amber rather than barbershop fougere."
        ),
        "initial": {
            "Bergamot FCF": 7.2,
            "Cedrat FCF oil Sicilian": 3.0,
            "Grapefruit FCF": 3.2,
            "Red Mandarin EO": 2.7,
            "Dihydromyrcenol": 1.6,
            "Apritone": 3.1,
            "Hexyl Acetate": 1.6,
            "Ethyl 2-Methylbutyrate": 0.90,
            "Lavender EO": 2.2,
            "Linalyl Acetate": 2.5,
            "Linalool": 1.0,
            "Ethyl Linalool": 1.6,
            "Terpinyl Acetate": 3.4,
            "Eugenol": 0.22,
            "Hedione": 11.0,
            "Benzyl Acetate": 1.0,
            "Alpha Isomethyl Ionone": 1.8,
            "Iso E Super": 11.0,
            "Ambrox Super": 10.0,
            "Azarbre": 1.5,
            "Sandalore": 3.5,
            "Vanillin": 4.8,
            "Ethyl Vanillin": 3.0,
            "Coumarin": 1.4,
            "Habanolide": 6.0,
            "Romandolide": 3.0,
            "Galaxolide": 2.2,
            "Ethylene Brassylate": 2.0,
        },
        "target": {
            "top": {
                "citrus": 1700,
                "fruity": 85,
                "spice": 3,
                "fresh": 420,
                "aromatic": 230,
                "radiance": 45,
            },
            "heart": {
                "citrus": 900,
                "fruity": 110,
                "fresh": 780,
                "amber": 140,
                "radiance": 90,
                "powdery": 130,
                "aromatic": 170,
            },
            "base": {
                "amber": 280,
                "gourmand": 12,
                "wood": 45,
                "musk": 24,
                "fruity": 35,
                "coumarin": 4,
                "balsamic": 30,
            },
        },
    },
    {
        "name": "Air-Conditioned Amber Layton",
        "family_archetype": "layton_dna.indoor_amber",
        "tagline": "Polished indoor amber: luminous jasmine air, apple-cardamom-like trace, vanilla woods.",
        "market_logic": (
            "SEA office/evening version: recognizable amber-vanilla Layton architecture, "
            "but transparent enough for air-conditioned interiors and not syrupy outdoors."
        ),
        "perfumer_literacy": (
            "A perfumer should see one clear amber anchor, one sandalwood layer, one dry "
            "wood trace, and one musk cushion. The formula avoids the v4 problem of every "
            "warm base material shouting at once."
        ),
        "initial": {
            "Bergamot FCF": 5.0,
            "Cedrat FCF oil Sicilian": 2.0,
            "Red Mandarin EO": 1.5,
            "Apritone": 2.1,
            "Hexyl Acetate": 1.0,
            "Ethyl 2-Methylbutyrate": 0.60,
            "Lavender EO": 2.2,
            "Linalyl Acetate": 2.4,
            "Linalool": 1.0,
            "Ethyl Linalool": 1.8,
            "Terpinyl Acetate": 2.8,
            "Eugenol": 0.18,
            "Hedione": 16.0,
            "Benzyl Acetate": 1.5,
            "Dihydrojasmone": 0.6,
            "Geraniol": 0.8,
            "Phenethyl Alcohol": 1.0,
            "Alpha Isomethyl Ionone": 2.2,
            "Iso E Super": 12.0,
            "Ambrox Super": 11.0,
            "Azarbre": 2.0,
            "Sandalore": 4.0,
            "Timberol": 1.0,
            "Norlimbanol Dextro": 0.30,
            "Vanillin": 4.0,
            "Ethyl Vanillin": 2.5,
            "Coumarin": 1.2,
            "Benzoin Resinoid": 1.2,
            "Habanolide": 6.0,
            "Ethylene Brassylate": 3.0,
            "Ambrettolide": 2.0,
        },
        "target": {
            "top": {
                "citrus": 1150,
                "fruity": 65,
                "spice": 2,
                "aromatic": 175,
                "radiance": 80,
                "amber": 190,
            },
            "heart": {
                "amber": 145,
                "fruity": 85,
                "radiance": 140,
                "powdery": 175,
                "wood": 70,
                "gourmand": 14,
                "aromatic": 130,
            },
            "base": {
                "amber": 145,
                "gourmand": 12,
                "wood": 42,
                "musk": 24,
                "balsamic": 18,
                "coumarin": 4,
                "powdery": 1,
            },
        },
    },
    {
        "name": "Tropical Night Layton Intense",
        "family_archetype": "layton_dna.night_intense",
        "tagline": "Warm night-market amber: transparent cardamom apple, polished vanilla, dry sandalwood musk.",
        "market_logic": (
            "Evening/date variant for humid weather: richer than the fresh version, but "
            "drier than v4 by using woods, musks, and transparent cardamom-like aromatics instead of simply adding resin."
        ),
        "perfumer_literacy": (
            "This is the most Layton-like of the three: the opening should say apple spice, "
            "the heart should turn radiant amber, and the base should be vanilla sandalwood "
            "with restraint rather than sticky benzoin syrup."
        ),
        "initial": {
            "Bergamot FCF": 5.0,
            "Cedrat FCF oil Sicilian": 2.0,
            "Red Mandarin EO": 2.0,
            "Apritone": 2.6,
            "Hexyl Acetate": 1.1,
            "Ethyl 2-Methylbutyrate": 0.75,
            "Lavender EO": 2.4,
            "Linalyl Acetate": 2.5,
            "Linalool": 1.0,
            "Ethyl Linalool": 1.8,
            "Terpinyl Acetate": 3.6,
            "Eugenol": 0.28,
            "Hedione": 9.0,
            "Benzyl Acetate": 0.9,
            "Phenethyl Alcohol": 0.8,
            "Alpha Isomethyl Ionone": 2.0,
            "Iso E Super": 10.0,
            "Ambrox Super": 12.0,
            "Azarbre": 2.5,
            "Sandalore": 5.0,
            "Timberol": 1.8,
            "Cashmeran": 1.2,
            "Norlimbanol Dextro": 0.45,
            "Vanillin": 6.4,
            "Ethyl Vanillin": 3.5,
            "Coumarin": 1.8,
            "Benzoin Resinoid": 2.0,
            "Habanolide": 5.5,
            "Romandolide": 3.0,
            "Ambrettolide": 2.2,
        },
        "target": {
            "top": {
                "citrus": 1200,
                "fruity": 85,
                "spice": 3,
                "aromatic": 180,
                "amber": 190,
                "gourmand": 8,
            },
            "heart": {
                "amber": 165,
                "fruity": 115,
                "radiance": 105,
                "powdery": 160,
                "spice": 3,
                "gourmand": 18,
                "wood": 70,
            },
            "base": {
                "amber": 165,
                "gourmand": 20,
                "wood": 72,
                "musk": 25,
                "balsamic": 25,
                "coumarin": 5,
                "powdery": 1,
            },
        },
    },
]


REGISTRY = load_registry()
ODT_INDEX = {normalize_name(k): v for k, v in ODT_DATA.items()}


def stock_for(name: str) -> Stock:
    return STOCKS.get(name, Stock("neat", 1.0))


def stock_dilutions_for(raw_pct: Mapping[str, float]) -> dict[str, float]:
    return {name: stock_for(name).dilution for name in raw_pct}


def odt_air_ppm(name: str) -> float:
    data = ODT_INDEX.get(normalize_name(name))
    if data is not None and data.get("odt_air") is not None:
        return float(data["odt_air"]) / 1000.0
    return 0.05


def _material_physics(name: str) -> tuple[float, float, tuple[float, float, float] | None]:
    if name == "Ethanol":
        return 46.07, 7900.0, (15.8, 8.8, 19.4)
    if name == "Carrier":
        return 134.0, 0.01, (17.4, 11.2, 21.0)

    rec = REGISTRY.get(name)
    if rec is not None:
        mw = rec.mw_g_mol
        vp = rec.vp_25c_pa
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
    missing_odt: list[str] = []

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
            if normalize_name(name) not in ODT_INDEX:
                missing_odt.append(name)

    return {
        "mw": mw_t,
        "vp": vp_t,
        "hsp": hsp_t,
        "odt": odt_t,
        "missing": sorted(set(missing)),
        "missing_odt": sorted(set(missing_odt)),
    }


def normalize_raw_pct(raw_pct: Mapping[str, float]) -> dict[str, float]:
    total = sum(max(v, 0.0) for v in raw_pct.values())
    if total <= 0:
        return {k: 0.0 for k in raw_pct}
    return {k: max(v, 0.0) * 100.0 / total for k, v in raw_pct.items()}


def enforce_caps(raw_pct: Mapping[str, float]) -> dict[str, float]:
    """Normalize to 100% while keeping capped materials at or below caps."""
    free = {k: max(v, 0.0) for k, v in raw_pct.items()}
    fixed: dict[str, float] = {}
    remaining = 100.0

    while free:
        total_free = sum(free.values())
        if total_free <= 0:
            break
        scale = remaining / total_free
        changed = False
        for mat, value in list(free.items()):
            scaled = value * scale
            cap = CAP_RAW_PCT.get(mat)
            if cap is not None and scaled > cap:
                fixed[mat] = cap
                remaining -= cap
                del free[mat]
                changed = True
        if not changed:
            fixed.update({mat: value * scale for mat, value in free.items()})
            break

    return fixed


def final_edp_wt_pct(raw_concentrate_pct: Mapping[str, float]) -> dict[str, float]:
    raw_norm = enforce_caps(raw_concentrate_pct)
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
    return sum(
        (math.log1p(obs.get(key, 0.0)) - math.log1p(value)) ** 2
        for key, value in target.items()
    )


def _low_penalty(value: float, floor: float, weight: float = 1.0) -> float:
    if value >= floor:
        return 0.0
    return weight * (math.log1p(floor) - math.log1p(max(value, 0.0))) ** 2


def objective_score(raw_pct: Mapping[str, float], concept: dict, tables: dict[str, dict]) -> float:
    raw_norm = enforce_caps(raw_pct)
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

    top = env.get("top", {})
    heart = env.get("heart", {})
    base = env.get("base", {})

    # Layton DNA-inspired grammar: apple/citrus/cardamom-like lift first,
    # lavender only support, then radiance, then amber/vanilla/wood/musk.
    grammar = 0.0
    apple_stock = (
        raw_norm.get("Apritone", 0.0)
        + raw_norm.get("Hexyl Acetate", 0.0)
        + raw_norm.get("Ethyl 2-Methylbutyrate", 0.0)
    )
    vanilla_active = (
        raw_norm.get("Vanillin", 0.0) * stock_for("Vanillin").dilution
        + raw_norm.get("Ethyl Vanillin", 0.0) * stock_for("Ethyl Vanillin").dilution
    )
    grammar += _low_penalty(top.get("citrus", 0.0), 700, 0.8)
    grammar += _low_penalty(top.get("fruity", 0.0), 35, 0.8)
    if apple_stock < 3.6:
        grammar += (3.6 - apple_stock) * 0.5
    cardamom_proxy = (
        raw_norm.get("Terpinyl Acetate", 0.0)
        + 0.45 * raw_norm.get("Ethyl Linalool", 0.0)
        + 0.35 * raw_norm.get("Linalyl Acetate", 0.0)
        + 5.0 * raw_norm.get("Eugenol", 0.0)
    )
    if cardamom_proxy < 4.0:
        grammar += (4.0 - cardamom_proxy) * 0.45
    grammar += _low_penalty(heart.get("radiance", 0.0), 45, 0.8)
    grammar += _low_penalty(base.get("amber", 0.0), 95, 1.0)
    grammar += _low_penalty(base.get("gourmand", 0.0), 5, 0.6)
    grammar += _low_penalty(base.get("wood", 0.0), 20, 0.8)
    grammar += _low_penalty(base.get("musk", 0.0), 12, 0.6)
    if vanilla_active < 1.20:
        grammar += (1.20 - vanilla_active) * 0.7

    if top.get("aromatic", 0.0) > top.get("fruity", 0.0) * 0.85 + 250:
        grammar += 1.2
    if base.get("balsamic", 0.0) > base.get("gourmand", 0.0) * 0.85 + 120:
        grammar += 0.8
    if base.get("gourmand", 0.0) > 450 and "Night" not in concept["name"]:
        grammar += (base["gourmand"] - 450.0) / 80.0

    cap_penalty = 0.0
    for mat, cap in CAP_RAW_PCT.items():
        excess = raw_norm.get(mat, 0.0) - cap
        if excess > 0:
            cap_penalty += excess * excess * 0.4

    flood = 0.0
    for rows in snap.values():
        total_oav = sum(row["oav"] for row in rows.values())
        if total_oav <= 0:
            continue
        max_share = max((row["oav"] / total_oav for row in rows.values()), default=0.0)
        if max_share > 0.66:
            flood += (max_share - 0.66) * 4.0

    return -(error + grammar + cap_penalty + flood)


def optimize_concept(concept: dict, *, seed: int, gate_config: ReleaseGateConfig = GATE_CONFIG) -> dict:
    initial = enforce_caps(concept["initial"])
    materials = list(initial.keys())
    tables = build_tables(materials)
    bounds = []
    for mat in materials:
        base = initial[mat]
        lo = max(0.0, base * 0.62)
        hi = base * 1.36
        if mat in ("Ethyl 2-Methylbutyrate", "Ethyl Vanillin", "Norlimbanol Dextro"):
            hi = base * 1.18
        if mat in ("Apritone", "Hexyl Acetate", "Terpinyl Acetate"):
            lo = max(0.0, base * 0.82)
        cap = CAP_RAW_PCT.get(mat)
        if cap is not None:
            hi = min(hi, cap)
        bounds.append((lo, hi))

    def neg(values: list[float]) -> float:
        raw = {mat: float(value) for mat, value in zip(materials, values)}
        return -objective_score(raw, concept, tables)

    if differential_evolution is None:  # pragma: no cover
        best_x = [initial[m] for m in materials]
        best_fun = neg(best_x)
    else:
        result = differential_evolution(
            neg,
            bounds=bounds,
            maxiter=22,
            popsize=7,
            seed=seed,
            polish=True,
            tol=1e-5,
            updating="immediate",
        )
        best_x = [float(value) for value in result.x]
        best_fun = float(result.fun)

    optimized_candidate = enforce_caps({mat: value for mat, value in zip(materials, best_x)})
    gate_result = optimize_until_release_ready(
        concept["name"],
        optimized_candidate,
        stock_dilutions_for(optimized_candidate),
        config=gate_config,
        concentrate_ul=CONCENTRATE_UL,
        repair_pool=LAYTON_GATE_REPAIR_POOL,
        body=concept["perfumer_literacy"],
        family_archetype=concept.get("family_archetype", ""),
        max_passes=4,
    )
    optimized = gate_result.raw_concentrate_pct
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
        "perfumer_literacy": concept["perfumer_literacy"],
        "target": concept["target"],
        "missing_from_spine": tables["missing"],
        "missing_odt": tables["missing_odt"],
        "initial": {
            "raw_concentrate_pct": {
                key: round(value, 4)
                for key, value in sorted(initial.items(), key=lambda item: -item[1])
            },
            "score": init_score,
            "envelope": family_envelope(init_snap),
            "windows": init_snap,
        },
        "optimized": {
            "raw_concentrate_pct": {
                key: round(value, 4)
                for key, value in sorted(optimized.items(), key=lambda item: -item[1])
            },
            "score": opt_score,
            "pre_repair_score": pre_repair_score,
            "optimizer_fun": best_fun,
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
    return ", ".join(
        f"`{family}`={value:.1f}"
        for family, value in sorted(env.items(), key=lambda item: -item[1])[:8]
    )


def rounded_amounts(raw_pct: Mapping[str, float]) -> list[tuple[str, float, int]]:
    rows: list[tuple[str, float, int]] = []
    total_ul = 0
    for mat, pct in raw_pct.items():
        amount = int(round(CONCENTRATE_UL * pct / 100.0))
        rows.append((mat, pct, amount))
        total_ul += amount

    diff = CONCENTRATE_UL - total_ul
    if diff and rows:
        idx = max(range(len(rows)), key=lambda i: rows[i][2])
        mat, pct, amount = rows[idx]
        rows[idx] = (mat, pct, amount + diff)
    return rows


def active_equivalent_pct(raw_pct: Mapping[str, float]) -> dict[str, float]:
    return {
        mat: pct * stock_for(mat).dilution
        for mat, pct in raw_pct.items()
        if pct * stock_for(mat).dilution > 0
    }


def layton_mixing_phase(mat: str) -> tuple[int, str]:
    family = FAMILY.get(mat, "default")
    if family in {"amber", "wood", "musk", "gourmand", "balsamic", "coumarin"}:
        return 1, "Foundation"
    if family in {"radiance", "powdery", "floral"}:
        return 2, "Heart Bridge"
    if family in {"aromatic"}:
        return 3, "Aromatic Support"
    if family in {"fruity", "citrus", "fresh", "spice", "sparkle"}:
        return 4, "Top Impact"
    return 3, "Aromatic Support"


def render_layton_mixing_order(rows: list[tuple[str, float, int]]) -> list[str]:
    indexed: list[tuple[int, str, int, str]] = []
    for mat, _pct, amount_ul in rows:
        phase_num, phase_name = layton_mixing_phase(mat)
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
        "1. Add foundation materials first so the amber-wood-musk-vanilla body is fully homogeneous.",
        "2. Add the heart bridge next to connect diffusion, floral lift, and powdery volume into the base.",
        "3. Add aromatic support after the body is clear and uniform.",
        "4. Add the top-impact materials last to preserve freshness and the apple-citrus-cardamom-like effect.",
        "5. Rest 48 hours before first read; judge seriously after 14-21 days.",
        "",
    ])
    return lines


def render_gate_status(results: list[dict]) -> list[str]:
    lines = [
        "## Release Gate Summary",
        "",
        "| Formula | Gate status | Commercial readiness | Confidence | Repair actions |",
        "|---|---:|---|---:|---:|",
    ]
    for result in results:
        gate = result["gate_aware"]
        confidence = gate["gate_report"].get("confidence", {})
        lines.append(
            f"| {result['name']} | {gate['status']} | {gate['commercial_readiness']} | "
            f"{confidence.get('combined_confidence', 0.0):.1f} | {len(gate.get('repair_actions', []))} |"
        )
    lines.append("")
    return lines


def render_markdown(results: list[dict]) -> str:
    lines: list[str] = [
        "# Layton DNA-Inspired Mass-Market Trio - 3 Optimized 30 mL EDPs",
        "",
        "Classification: amber-vanilla fruity-spiced masculine / modern oriental amber, not aromatic fougere.",
        "",
        "**Status:** Commercial-trial candidates when generated with `--commercial-trial`; not sellable until calibrated with real wear-test records.",
        "",
        "Each build is a 30 mL EDP at 20% concentrate: 6.00 mL concentrate plus 24.00 mL ethanol.",
        "The optimizer models the final mixed solution: ethanol, active raw materials, diluted-stock carrier, vapor ppm, ODT, and OAV over top/heart/base windows.",
        "",
        "Layton DNA-inspired target: apple-citrus-cardamom-like opening, lavender as support only, Hedione-led radiance, then amber-vanilla-sandalwood/musk drydown.",
        "True proprietary cardamom-base fidelity is intentionally sacrificed for transparent commercial-trial buildability: the impression is rebuilt from Terpinyl Acetate, Linalyl Acetate, Ethyl Linalool, and trace Eugenol.",
        "These are explicitly not aromatic fougeres; the family gate blocks moss/coumarin drift into fougere territory.",
        "",
    ]
    lines.extend(render_gate_status(results))
    lines.extend([
        "## Perfumist Verdict",
        "",
        "Would a real perfumer who does not care about the chemistry read these as good formulas? Yes, as transparent commercial-trial sketches. The caveat is deliberate: these are Layton DNA-inspired, not proprietary-cardamom-base faithful, and they still need empirical wear-test calibration before sale.",
        "",
    ])

    for idx, result in enumerate(results, start=1):
        opt = result["optimized"]
        raw_pct = opt["raw_concentrate_pct"]
        rows = rounded_amounts(raw_pct)
        active_pct = active_equivalent_pct(raw_pct)

        lines.extend([
            f"## {idx}. {result['name']}",
            "",
            f"*{result['tagline']}*",
            "",
            f"**Market logic:** {result['market_logic']}",
            "",
            f"**Perfumer-readable verdict:** {result['perfumer_literacy']}",
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
        total_ul = 0
        for row_idx, (mat, _pct, amount_ul) in enumerate(rows, start=1):
            total_ul += amount_ul
            stock = stock_for(mat)
            lines.append(f"| {row_idx} | {mat} | {stock.label} | {amount_ul} | {amount_ul / 1000.0:.3f} |")
        lines.extend([
            f"| - | **Fragrance concentrate subtotal** | - | **{total_ul}** | **{total_ul / 1000.0:.3f}** |",
            f"| - | Ethanol 96% bottle fill | neat | **{int((BATCH_ML - CONCENTRATE_ML) * 1000)}** | **{BATCH_ML - CONCENTRATE_ML:.3f}** |",
            f"| - | **Final bottle total** | - | **{int(BATCH_ML * 1000)}** | **{BATCH_ML:.3f}** |",
            "",
            "### Active Neat-Equivalent View",
            "",
            "| Material | Raw concentrate % | Active neat-equivalent % of concentrate |",
            "|---|---:|---:|",
        ])
        for mat, pct in raw_pct.items():
            lines.append(f"| {mat} | {pct:.3f} | {active_pct.get(mat, 0.0):.3f} |")

        lines.extend([
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

        lines.extend(render_layton_mixing_order(rows))

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Layton-DNA optimized formulas.")
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
        optimize_concept(concept, seed=4200 + i, gate_config=gate_config)
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
