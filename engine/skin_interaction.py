"""Skin interaction, absorption kinetics, and substantivity modelling.

Models three physicochemical phenomena:
1. **Stratum corneum partitioning** — LogP-driven absorption into skin
   creating a "reservoir" that slowly re-releases fragrance (Fick's 2nd law).
   Materials with LogP 2–4 absorb optimally. This is WHY Iso E Super
   seems to "grow" — it partitions into lipid layers and re-diffuses.

2. **Percutaneous absorption rate** — Potts-Guy model:
   log Kp (cm/h) = −2.72 + 0.71·logP − 0.0061·MW
   Lower Kp = slower skin penetration = longer surface residence.

3. **Fabric substantivity** — Materials with moderate LogP (2–3.5) and
   MW > 200 adhere to textile fibers via hydrophobic interaction and
   Van der Waals forces. Musks, woods, and salicylates are most substantive.
   Improved via Hansen solubility distance to skin lipids
   (δd=17, δp=8, δh=8) — see _hansen_substantivity().

Sources:
  Potts & Guy (1992) Pharmaceutical Research — Kp model
  Johnson et al. (1995) CRC Critical Reviews Toxicology — skin penetration
  Roberts et al. (2000) Flavour & Fragrance Journal — headspace partition
  Vuilleumier et al. (2001) Chimia — fabric substantivity
  Cal & Stefaniak (2005) J Appl Toxicol — fragrance skin absorption
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any

from engine.name_utils import normalize_name


# Hansen solubility parameters for skin (stratum corneum lipids).
# δd=17, δp=8, δh=8 (MJ/m³)^½ — approximates human sebum/lipid bilayer.
# Sources: Liron & Cohen (1994) J Pharm Sci; Sato et al. (1999) Int J Pharm.
_SKIN_HSP: tuple[float, float, float] = (17.0, 8.0, 8.0)

# Scale factor for Hansen-distance → substantivity mapping.
# Ra (distance in HSP space) of 0 → substantivity=1.0, Ra=10 → ~0.37.
_HANSEN_SUBST_SCALE: float = 10.0


# ═══════════════════════════════════════════════════════════════════════════════
# LogP and MW data for inventory materials
# LogP = octanol-water partition coefficient (lipophilicity)
# MW = molecular weight (g/mol)
# Sources: PubChem, EPI Suite, Givaudan/IFF safety data sheets
# ═══════════════════════════════════════════════════════════════════════════════

SKIN_PHYSCHEM: dict[str, dict[str, float]] = {
    # ── Musks ──
    "Galaxolide": {"logP": 4.8, "MW": 258.4, "substantivity": 0.95},
    "Habanolide": {"logP": 4.5, "MW": 238.4, "substantivity": 0.90},
    "Ethylene Brassylate": {"logP": 4.2, "MW": 270.4, "substantivity": 0.92},
    "Exaltolide": {"logP": 5.8, "MW": 240.4, "substantivity": 0.88},
    "Musk Ketone": {"logP": 3.8, "MW": 294.3, "substantivity": 0.80},
    "Ambretone": {"logP": 5.5, "MW": 252.4, "substantivity": 0.90},
    # ── Woods ──
    "Iso E Super": {"logP": 3.6, "MW": 234.4, "substantivity": 0.85},
    "Cashmeran": {"logP": 3.3, "MW": 206.3, "substantivity": 0.80},
    "Vertofix Coeur": {"logP": 4.0, "MW": 234.4, "substantivity": 0.88},
    "Timberol": {"logP": 3.8, "MW": 220.4, "substantivity": 0.82},
    "Kephalis": {"logP": 4.5, "MW": 234.4, "substantivity": 0.85},
    "Koavone": {"logP": 3.5, "MW": 192.3, "substantivity": 0.75},
    "Amberwood F": {"logP": 3.8, "MW": 234.4, "substantivity": 0.80},
    "Cedroxyde": {"logP": 3.5, "MW": 238.4, "substantivity": 0.78},
    "Vetival": {"logP": 3.0, "MW": 206.3, "substantivity": 0.72},
    # ── Sandalwoods ──
    "Javanol": {"logP": 3.6, "MW": 210.4, "substantivity": 0.82},
    "Ebanol": {"logP": 3.3, "MW": 208.3, "substantivity": 0.80},
    # ── Amber ──
    "Ambrox Super": {"logP": 4.5, "MW": 236.4, "substantivity": 0.90},
    # ── Salicylates ──
    "Benzyl Salicylate": {"logP": 3.2, "MW": 228.3, "substantivity": 0.85},
    "Hexyl Salicylate": {"logP": 5.7, "MW": 222.3, "substantivity": 0.82},
    # ── Florals ──
    "Hedione": {"logP": 2.7, "MW": 226.3, "substantivity": 0.55},
    "DBCA": {"logP": 3.5, "MW": 204.3, "substantivity": 0.65},
    "Lilyreal ND": {"logP": 3.5, "MW": 192.3, "substantivity": 0.60},
    "Bourgeonal": {"logP": 2.8, "MW": 204.3, "substantivity": 0.50},
    "Nympheal": {"logP": 3.0, "MW": 204.3, "substantivity": 0.55},
    "Hydroxycitronellal": {"logP": 1.8, "MW": 172.3, "substantivity": 0.40},
    "Florol": {"logP": 2.5, "MW": 170.3, "substantivity": 0.45},
    "Freesia HDI": {"logP": 2.5, "MW": 182.3, "substantivity": 0.45},
    "Phenethyl Alcohol": {"logP": 1.4, "MW": 122.2, "substantivity": 0.25},
    # ── Ionones ──
    "Orivone": {"logP": 2.9, "MW": 168.28, "substantivity": 0.60},
    "Alpha Irone": {"logP": 3.2, "MW": 206.3, "substantivity": 0.68},
    "Ultralia": {"logP": 2.5, "MW": 192.3, "substantivity": 0.50},
    "Methyl Ionone Pure": {"logP": 3.2, "MW": 192.3, "substantivity": 0.60},
    "Alpha Ionone": {"logP": 3.0, "MW": 192.3, "substantivity": 0.58},
    "Beta Ionone": {"logP": 3.0, "MW": 192.3, "substantivity": 0.58},
    # ── Lactones / tonka ──
    "Coumarin": {"logP": 1.4, "MW": 146.1, "substantivity": 0.40},
    "Gamma Decalactone": {"logP": 3.0, "MW": 170.3, "substantivity": 0.60},
    "Maple Lactone": {"logP": 0.5, "MW": 128.1, "substantivity": 0.20},
    # ── Balsamic ──
    "Vanillin": {"logP": 1.2, "MW": 152.2, "substantivity": 0.35},
    "Ethyl Vanillin": {"logP": 1.6, "MW": 166.2, "substantivity": 0.38},
    "Benzoin Resinoid": {"logP": 2.0, "MW": 212.2, "substantivity": 0.55},
    "Labdanum Absolute": {"logP": 3.5, "MW": 300.0, "substantivity": 0.75},
    # ── Aldehydes ──
    "Aldehyde C10": {"logP": 3.0, "MW": 156.3, "substantivity": 0.30},
    "Aldehyde C11": {"logP": 3.5, "MW": 170.3, "substantivity": 0.35},
    "Aldehyde C11 Undecylenic": {"logP": 3.3, "MW": 168.3, "substantivity": 0.32},
    "Aldehyde C12 MNA": {"logP": 3.0, "MW": 184.3, "substantivity": 0.38},
    "Cyclamen Aldehyde": {"logP": 3.2, "MW": 190.3, "substantivity": 0.45},
    # ── Green ──
    "cis-3-Hexenol": {"logP": 1.6, "MW": 100.2, "substantivity": 0.10},
    "Dynascone": {"logP": 2.5, "MW": 166.3, "substantivity": 0.30},
    "Allyl Amyl Glycolate": {"logP": 1.0, "MW": 172.2, "substantivity": 0.15},
    "Parmavert": {"logP": 2.5, "MW": 166.3, "substantivity": 0.30},
    "Leafovert": {"logP": 2.0, "MW": 156.3, "substantivity": 0.20},
    # ── Citrus (volatile — low skin absorption) ──
    "D-Limonene": {"logP": 4.6, "MW": 136.2, "substantivity": 0.10},
    "Linalool": {"logP": 2.7, "MW": 154.3, "substantivity": 0.30},
    "Linalyl Acetate": {"logP": 3.2, "MW": 196.3, "substantivity": 0.35},
    # ── Leather / smoke ──
    "Suederal": {"logP": 3.5, "MW": 210.3, "substantivity": 0.70},
    "Guaiacol": {"logP": 1.3, "MW": 124.1, "substantivity": 0.20},
    "Birch Tar Rectified": {"logP": 1.5, "MW": 124.1, "substantivity": 0.45},
    "Evernyl": {"logP": 2.8, "MW": 196.2, "substantivity": 0.60},
    "Isobutyl Quinoline": {"logP": 2.9, "MW": 185.3, "substantivity": 0.50},
    # ── Spice ──
    "Eugenol": {"logP": 2.2, "MW": 164.2, "substantivity": 0.40},
    "Ethyl Safranate": {"logP": 2.5, "MW": 166.2, "substantivity": 0.35},
    "Cardamom EO": {"logP": 2.5, "MW": 154.3, "substantivity": 0.25},
    # ── Animalic ──
    "Indole": {"logP": 2.1, "MW": 117.2, "substantivity": 0.30},
    # ── Heliotropin ──
    # ── Ozonic ──
    "Scentenal": {"logP": 2.0, "MW": 154.2, "substantivity": 0.20},
    "Calone": {"logP": 1.5, "MW": 192.2, "substantivity": 0.25},
    # ── Paradisamide ──
    "Paradisamide": {"logP": 3.5, "MW": 253.3, "substantivity": 0.75},
    # ── EOs (multi-component — weighted average) ──
    "Bergamot FCF": {"logP": 2.5, "MW": 175.0, "substantivity": 0.20},
    "Neroli EO": {"logP": 2.5, "MW": 170.0, "substantivity": 0.25},
    "Vetiver EO": {"logP": 3.8, "MW": 220.0, "substantivity": 0.70},
    "Vetiver EO (India)": {"logP": 3.8, "MW": 222.4, "substantivity": 0.75},
    "Patchouli EO": {"logP": 4.1, "MW": 222.4, "substantivity": 0.75},
    "Cedarwood EO": {"logP": 3.9, "MW": 222.4, "substantivity": 0.70},
    "Lavender EO": {"logP": 2.2, "MW": 170.0, "substantivity": 0.25},
    "Lavender EO (BONTAUX SAS)": {"logP": 2.3, "MW": 154.3, "substantivity": 0.30},
    "Ylang Comoros Complete EO": {"logP": 3.0, "MW": 200.0, "substantivity": 0.50},
    "Champaca Flower EO": {"logP": 2.8, "MW": 190.0, "substantivity": 0.40},
    "Myrrh EO": {"logP": 3.5, "MW": 230.0, "substantivity": 0.65},
    "Olibanum Resinoid": {"logP": 3.0, "MW": 210.0, "substantivity": 0.60},
    # ── Additional formula materials (PubChem-verified) ──
    # Musks (missing from original)
    "Romandolide": {"logP": 5.0, "MW": 268.4, "substantivity": 0.88},
    "Zenolide": {"logP": 3.6, "MW": 256.3, "substantivity": 0.82},
    "Macrolide": {"logP": 5.0, "MW": 240.4, "substantivity": 0.85},
    "Tonalide": {"logP": 5.7, "MW": 258.4, "substantivity": 0.85},
    # Sandalwoods
    "Bacdanol": {"logP": 3.6, "MW": 208.3, "substantivity": 0.78},
    "Sandalore": {"logP": 3.9, "MW": 210.4, "substantivity": 0.70},
    # Woods
    "Clearwood": {"logP": 4.0, "MW": 222.4, "substantivity": 0.72},
    "Norlimbanol Dextro": {"logP": 5.2, "MW": 226.4, "substantivity": 0.90},
    "Vertofix": {"logP": 4.0, "MW": 234.4, "substantivity": 0.88},
    # Amber
    "Ambrofix": {"logP": 4.7, "MW": 236.4, "substantivity": 0.88},
    "Ambermax": {"logP": 4.2, "MW": 236.4, "substantivity": 0.80},
    # Fixatives
    "Benzyl Benzoate": {"logP": 4.0, "MW": 212.2, "substantivity": 0.70},
    # Florals
    "Hedione HC": {"logP": 2.7, "MW": 226.3, "substantivity": 0.55},
    "Dihydro Beta Ionone": {"logP": 2.7, "MW": 194.3, "substantivity": 0.55},
    "Helional": {"logP": 2.2, "MW": 192.2, "substantivity": 0.40},
    "Benzyl Acetate": {"logP": 2.0, "MW": 150.2, "substantivity": 0.25},
    "Jessemal": {"logP": 2.8, "MW": 214.3, "substantivity": 0.40},
    "Floralozone": {"logP": 3.3, "MW": 190.3, "substantivity": 0.40},
    "Aurantiol": {"logP": 3.3, "MW": 305.4, "substantivity": 0.55},
    "Dihydrojasmone": {"logP": 2.9, "MW": 166.3, "substantivity": 0.45},
    "Cis Jasmone": {"logP": 2.2, "MW": 164.2, "substantivity": 0.30},
    # Ketones
    "Methyl Nonyl Ketone": {"logP": 4.1, "MW": 170.3, "substantivity": 0.55},
    # Lactones
    "Gamma Undecalactone": {"logP": 3.3, "MW": 184.3, "substantivity": 0.60},
    "Delta Decalactone": {"logP": 2.5, "MW": 170.3, "substantivity": 0.50},
    # Balsamic / aldehydes
    "Anisaldehyde": {"logP": 1.8, "MW": 136.2, "substantivity": 0.25},
    "Damascenone": {"logP": 3.2, "MW": 190.3, "substantivity": 0.45},
    # Terpenes
    "Rose Oxide": {"logP": 2.9, "MW": 154.3, "substantivity": 0.30},
    "Ethyl Maltol": {"logP": 0.8, "MW": 140.1, "substantivity": 0.15},
    # EOs
    "Ylang III": {"logP": 3.0, "MW": 200.0, "substantivity": 0.50},
    "Carrot Seed EO": {"logP": 3.5, "MW": 210.0, "substantivity": 0.50},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Skin Reservoir Classification
# ═══════════════════════════════════════════════════════════════════════════════


def _reservoir_class(logP: float) -> str:
    """Classify skin absorption behaviour by LogP.

    LogP 1–2:   Hydrophilic — washes off easily, poor skin retention
    LogP 2–4:   Optimal partition — absorbs into stratum corneum lipids,
                slow radial diffusion back to surface ("blooming" effect)
    LogP 4–6:   Lipophilic — deep skin absorption, very slow release,
                strong skin-scent intimacy
    LogP >6:    Hyper-lipophilic — trapped in lipid matrix, minimal volatility
    """
    if logP < 1.0:
        return "surface_only"
    elif logP < 2.0:
        return "hydrophilic"
    elif logP < 4.0:
        return "optimal_reservoir"
    elif logP < 6.0:
        return "deep_lipophilic"
    else:
        return "lipid_trapped"


def _potts_guy_kp(logP: float, MW: float) -> float:
    """Potts-Guy permeability coefficient (cm/h).

    log Kp = −2.72 + 0.71·logP − 0.0061·MW
    """
    log_kp = -2.72 + 0.71 * logP - 0.0061 * MW
    return 10**log_kp


# ═══════════════════════════════════════════════════════════════════════════════
# Hansen-based substantivity fallback
# ═══════════════════════════════════════════════════════════════════════════════

# Lazy-loaded HSP table from the data spine registry. Avoids circular imports
# at module level — loaded on first call to _hansen_substantivity().
_HSP_REGISTRY: dict[str, tuple[float, float, float]] | None = None


def _load_hsp_registry() -> dict[str, tuple[float, float, float]]:
    """Load HSP data from the data spine Material registry."""
    global _HSP_REGISTRY
    if _HSP_REGISTRY is not None:
        return _HSP_REGISTRY
    try:
        from engine.data_spine import load_registry

        reg = load_registry()
        hsp: dict[str, tuple[float, float, float]] = {}
        for mat in reg.all():
            h = mat.hsp
            if (
                h is not None
                and h.delta_d is not None
                and h.delta_p is not None
                and h.delta_h is not None
            ):
                hsp[normalize_name(mat.canonical_name)] = (
                    float(h.delta_d),
                    float(h.delta_p),
                    float(h.delta_h),
                )
        _HSP_REGISTRY = hsp
    except Exception:
        _HSP_REGISTRY = {}
    return _HSP_REGISTRY


def _hansen_substantivity(name: str) -> float | None:
    """Estimate fabric substantivity from Hansen solubility distance to skin.

    substantivity = exp(−Ra / scale) where Ra is the Euclidean distance
    in (δd, δp, δh) space to _SKIN_HSP, and scale = _HANSEN_SUBST_SCALE.

    Returns None when no HSP data is available for the material.
    """
    hsp = _load_hsp_registry().get(normalize_name(name))
    if hsp is None:
        return None
    δd, δp, δh = hsp
    Ra = math.sqrt(
        (δd - _SKIN_HSP[0]) ** 2 + (δp - _SKIN_HSP[1]) ** 2 + (δh - _SKIN_HSP[2]) ** 2
    )
    return math.exp(-Ra / _HANSEN_SUBST_SCALE)


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SkinInteractionReport:
    """Skin absorption and substantivity analysis."""

    score: float  # 0-100 composite skin performance
    reservoir_score: float  # 0-100 skin reservoir quality
    substantivity_score: float  # 0-100 fabric adhesion
    reservoir_materials: list[dict]  # materials in optimal partition zone
    blooming_materials: list[dict]  # deep-absorbers that "grow" over time
    surface_materials: list[dict]  # materials that stay on surface
    fabric_anchors: list[dict]  # high-substantivity materials
    permeability_profile: dict  # Kp statistics
    diagnostics: list[str]


def score_skin_interaction(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
) -> SkinInteractionReport:
    """Score skin absorption and fabric substantivity of a formula.

    Optimal formula has:
    - 30-50% of materials in LogP 2-4 ("reservoir zone") for blooming effect
    - 10-20% deep lipophilic anchors (LogP 4-6) for tenacity
    - Good fabric substantivity from woods/musks/salicylates
    - Balanced Kp distribution for layered temporal release

    Args:
        ingredients: {name: amount_uL}
        dilutions: {name: dilution_factor}
    """
    dilutions = dilutions or {}
    total_active = 0.0
    reservoir_mats: list[dict] = []
    blooming_mats: list[dict] = []
    surface_mats: list[dict] = []
    fabric_anchors: list[dict] = []
    kp_values: list[float] = []
    weighted_subst = 0.0
    weighted_logP = 0.0
    reservoir_mass = 0.0
    deep_mass = 0.0
    surface_mass = 0.0
    diagnostics: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        data = SKIN_PHYSCHEM.get(name)
        if not data:
            # Fall back to Hansen-estimated substantivity for unknown materials.
            hansen_subst = _hansen_substantivity(name)
            if hansen_subst is not None:
                weighted_subst += hansen_subst * active
                subst_used = hansen_subst
            else:
                continue
            if hansen_subst >= 0.70:
                fabric_anchors.append(
                    {
                        "material": name,
                        "substantivity": hansen_subst,
                        "amount_uL": active,
                    }
                )
        else:
            logP = data["logP"]
            MW = data["MW"]
            subst_used = data["substantivity"]
            kp = _potts_guy_kp(logP, MW)
            reservoir = _reservoir_class(logP)
            kp_values.append(kp)
            weighted_logP += logP * active
            weighted_subst += subst_used * active

            info = {
                "material": name,
                "logP": logP,
                "MW": MW,
                "Kp": round(kp, 6),
                "reservoir_class": reservoir,
                "amount_uL": active,
            }

            if reservoir == "optimal_reservoir":
                reservoir_mats.append(info)
                reservoir_mass += active
            elif reservoir in ("deep_lipophilic", "lipid_trapped"):
                blooming_mats.append(info)
                deep_mass += active
            else:
                surface_mats.append(info)
                surface_mass += active

            if subst_used >= 0.70:
                fabric_anchors.append(
                    {
                        "material": name,
                        "substantivity": subst_used,
                        "amount_uL": active,
                    }
                )

        if reservoir == "optimal_reservoir":
            reservoir_mats.append(info)
            reservoir_mass += active
        elif reservoir in ("deep_lipophilic", "lipid_trapped"):
            blooming_mats.append(info)
            deep_mass += active
        else:
            surface_mats.append(info)
            surface_mass += active

    # ── Score computation ──
    if total_active == 0:
        return SkinInteractionReport(
            score=0,
            reservoir_score=0,
            substantivity_score=0,
            reservoir_materials=[],
            blooming_materials=[],
            surface_materials=[],
            fabric_anchors=[],
            permeability_profile={},
            diagnostics=["No data"],
        )

    # Reservoir score: optimal is 40-55% in reservoir zone + 15-25% deep
    # Perfumery skin-scent favours reservoir dominance (logP 2-4) more than
    # transdermal drug-delivery models suggest.  EDPs with dense bases
    # routinely reach 55-65% reservoir.  Wider Gaussian sigma tolerates
    # realistic EDP distributions without over-penalising.
    res_pct = reservoir_mass / total_active
    deep_pct = deep_mass / total_active
    # Bell curve scoring around optimal
    #   Reservoir: centre 0.50, sigma 0.12 (was 0.40 / 0.08)
    #   Deep:      centre 0.22, sigma 0.06 (was 0.20 / 0.05)
    res_component = 100 * math.exp(-((res_pct - 0.50) ** 2) / 0.12)
    deep_component = 100 * math.exp(-((deep_pct - 0.22) ** 2) / 0.06)
    reservoir_score = res_component * 0.65 + deep_component * 0.35

    # Substantivity score
    avg_subst = weighted_subst / total_active
    substantivity_score = min(100, avg_subst * 130)  # scale 0.77 → ~100

    # Kp distribution for temporal layering
    if len(kp_values) >= 3:
        kp_spread = max(kp_values) / (min(kp_values) + 1e-12)
        # Good spread (3-5 orders of magnitude) = layered release
        spread_score = min(100, 20 * math.log10(kp_spread + 1))
    else:
        spread_score = 50

    composite = (
        reservoir_score * 0.40 + substantivity_score * 0.35 + spread_score * 0.25
    )

    # Permeability stats
    perm_stats = {}
    if kp_values:
        perm_stats = {
            "min_Kp": round(min(kp_values), 8),
            "max_Kp": round(max(kp_values), 6),
            "mean_logP": round(weighted_logP / total_active, 2),
            "reservoir_pct": round(res_pct * 100, 1),
            "deep_lipophilic_pct": round(deep_pct * 100, 1),
        }

    # Diagnostics
    if res_pct < 0.20:
        diagnostics.append(
            "⚠ Low reservoir fraction — formula may lack skin-scent intimacy"
        )
    elif res_pct > 0.60:
        diagnostics.append(
            "ℹ Very high reservoir fraction — excellent blooming potential"
        )
    if deep_pct > 0.35:
        diagnostics.append(
            "ℹ Dense lipophilic base — deep skin absorption, slow evolution"
        )
    if avg_subst > 0.65:
        diagnostics.append("✓ Strong fabric substantivity — will last well on clothing")
    elif avg_subst < 0.30:
        diagnostics.append("⚠ Low fabric substantivity — may not persist on clothing")
    if blooming_mats:
        names = [m["material"] for m in blooming_mats[:5]]
        diagnostics.append(f"Blooming materials (Iso-E-effect): {', '.join(names)}")

    return SkinInteractionReport(
        score=round(composite, 1),
        reservoir_score=round(reservoir_score, 1),
        substantivity_score=round(substantivity_score, 1),
        reservoir_materials=sorted(
            reservoir_mats, key=lambda x: x["logP"], reverse=True
        ),
        blooming_materials=sorted(blooming_mats, key=lambda x: x["logP"], reverse=True),
        surface_materials=surface_mats,
        fabric_anchors=sorted(
            fabric_anchors, key=lambda x: x["substantivity"], reverse=True
        ),
        permeability_profile=perm_stats,
        diagnostics=diagnostics,
    )
