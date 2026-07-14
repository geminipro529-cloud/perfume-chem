"""Vapour-phase diffusion and sillage projection model.

Combines three physical transport mechanisms that determine how a
fragrance moves from the application point to a perceiver's nose:

1. **Graham's Law** — Diffusion rate in air ∝ 1/√MW.
   Light molecules (MW <150, citrus terpenes) diffuse rapidly → wide
   initial sillage cone.  Heavy molecules (MW >250, musks) diffuse
   slowly → intimate skin-scent.  Graham (1833).

2. **Air–Liquid Partition (Henry regime)** — The dimensionless
   air–water partition coefficient Kaw approximates how readily a
   molecule leaves the ethanol–skin matrix into the gas phase.
   Kaw = VP × γ / (R × T × [c_sat]).
   Materials with high Kaw project strongly (citrus, green).
   Materials with low Kaw stay close (musks, ambers).
   Roberts et al. (2000) Flavour Fragrance J.

3. **Sillage Cone Geometry** — Combining diffusion coefficient with
   volatility gives a radial reach estimate at time t:
     r(t) ≈ √(4 × D_air × t) × OAV_fraction
   where D_air ∝ 1/√MW.

Scoring:
  Evaluates the diffusion profile of a formula — does it project with
  a clear near/mid/far field architecture?  Formulas with ALL heavy
  materials lack projection.  Formulas with ALL light materials lack
  intimacy.  The optimal formula layers the diffusion field.

Sources:
  Graham (1833) Phil Trans Roy Soc — diffusion of gases
  Roberts et al. (2000) Flavour Fragrance J — air-liquid partition
  Sell (2006) Chemistry of Fragrances — fragrance delivery physics
  Calkin & Jellinek (1994) Perfumery: Practice and Principles
"""

from __future__ import annotations

from dataclasses import dataclass
import math

from engine.name_utils import normalize_name
from engine.thermo.antoine import (
    vp_pa,
)  # shared VP-at-temperature — used by headspace.py too

# Skin temperature for diffusion modelling (32 °C = 305.15 K).
# Used by both diffusion_model.py and headspace.py via the shared vp_pa() helper.
_T_SKIN = 305.15  # K


# ═══════════════════════════════════════════════════════════════════════════════
# Molecular Weight + Vapour Pressure Data
# MW (Da), VP_25 (Pa at 25 °C), Kaw_eff (dimensionless, estimated)
# Sources: Arctander (1969), Sell (2006), PubChem, EPI Suite
# ═══════════════════════════════════════════════════════════════════════════════

DIFFUSION_DATA: dict[str, dict[str, float]] = {
    # ── Top notes: high MW, high VP, high Kaw → strong projection ──
    "D-Limonene": {"MW": 136.2, "VP_25": 190.0, "Kaw_eff": 0.050},
    "Linalool": {"MW": 154.3, "VP_25": 21.3, "Kaw_eff": 0.012},
    "Linalyl Acetate": {"MW": 196.3, "VP_25": 5.0, "Kaw_eff": 0.008},
    "Bergamot FCF": {"MW": 148.0, "VP_25": 40.0, "Kaw_eff": 0.025},
    "Bergamot FCF Sicilian": {"MW": 148.0, "VP_25": 40.0, "Kaw_eff": 0.025},
    "Cedrat FCF Sicilian": {"MW": 152.0, "VP_25": 35.0, "Kaw_eff": 0.022},
    "Blood Orange Sicilian": {"MW": 136.2, "VP_25": 180.0, "Kaw_eff": 0.048},
    "Grapefruit FCF": {"MW": 136.2, "VP_25": 170.0, "Kaw_eff": 0.045},
    "Red Mandarin EO": {"MW": 136.2, "VP_25": 170.0, "Kaw_eff": 0.045},
    "Dihydromyrcenol": {"MW": 156.3, "VP_25": 17.0, "Kaw_eff": 0.011},
    "Terpinyl Acetate": {"MW": 196.3, "VP_25": 3.0, "Kaw_eff": 0.005},
    "Methyl Pamplemousse": {"MW": 168.2, "VP_25": 12.0, "Kaw_eff": 0.010},
    "cis-3-Hexenol": {"MW": 100.2, "VP_25": 120.0, "Kaw_eff": 0.008},
    "Allyl Amyl Glycolate": {"MW": 158.2, "VP_25": 8.0, "Kaw_eff": 0.006},
    "Petitgrain EO": {"MW": 196.3, "VP_25": 6.0, "Kaw_eff": 0.007},
    "Neroli EO": {"MW": 154.3, "VP_25": 18.0, "Kaw_eff": 0.012},
    "Clary Sage EO": {"MW": 196.3, "VP_25": 5.0, "Kaw_eff": 0.007},
    "Rosemary EO (French Rosmarinus Officinalis leaf oil)": {
        "MW": 154.3,
        "VP_25": 18.0,
        "Kaw_eff": 0.011,
    },
    "Lavender EO": {"MW": 154.3, "VP_25": 20.0, "Kaw_eff": 0.012},
    "Lavender EO (BONTAUX SAS)": {"MW": 154.3, "VP_25": 22.0, "Kaw_eff": 0.013},
    "Dynascone": {"MW": 192.3, "VP_25": 4.5, "Kaw_eff": 0.005},
    "Leafovert": {"MW": 154.3, "VP_25": 15.0, "Kaw_eff": 0.010},
    "Parmavert": {"MW": 154.3, "VP_25": 12.0, "Kaw_eff": 0.009},
    # ── Heart notes: moderate MW, moderate VP ──
    "Hedione": {"MW": 226.3, "VP_25": 0.5, "Kaw_eff": 0.003},
    "DBCA": {"MW": 204.3, "VP_25": 0.8, "Kaw_eff": 0.003},
    "Hydroxycitronellal": {"MW": 172.3, "VP_25": 2.0, "Kaw_eff": 0.005},
    "Phenethyl Alcohol": {"MW": 122.2, "VP_25": 12.0, "Kaw_eff": 0.002},
    "Lilyreal ND": {"MW": 192.3, "VP_25": 1.5, "Kaw_eff": 0.003},
    "Bourgeonal": {"MW": 204.3, "VP_25": 1.0, "Kaw_eff": 0.003},
    "Nympheal": {"MW": 204.3, "VP_25": 0.6, "Kaw_eff": 0.002},
    "Florol": {"MW": 170.3, "VP_25": 3.0, "Kaw_eff": 0.005},
    "Freesia HDI": {"MW": 182.3, "VP_25": 2.5, "Kaw_eff": 0.004},
    "Cyclamen Aldehyde": {"MW": 190.3, "VP_25": 1.8, "Kaw_eff": 0.004},
    "Eugenol": {"MW": 164.2, "VP_25": 2.5, "Kaw_eff": 0.003},
    "Ylang Comoros Complete EO": {"MW": 204.4, "VP_25": 0.5, "Kaw_eff": 0.002},
    "Champaca Flower EO": {"MW": 204.4, "VP_25": 0.4, "Kaw_eff": 0.002},
    "Orivone": {"MW": 168.28, "VP_25": 0.5, "Kaw_eff": 0.002},
    "Alpha Irone": {"MW": 206.3, "VP_25": 0.3, "Kaw_eff": 0.002},
    "Alpha Ionone": {"MW": 192.3, "VP_25": 1.5, "Kaw_eff": 0.003},
    "Beta Ionone": {"MW": 192.3, "VP_25": 1.2, "Kaw_eff": 0.003},
    "Methyl Ionone Pure": {"MW": 192.3, "VP_25": 1.0, "Kaw_eff": 0.003},
    "Ultralia": {"MW": 192.3, "VP_25": 0.5, "Kaw_eff": 0.002},
    # ── Damascones (OR5A1/A2 family, structurally related to ionones) ──
    "Alpha Damascone": {"MW": 192.3, "VP_25": 2.0, "Kaw_eff": 0.003},
    "Damascone Beta": {"MW": 192.3, "VP_25": 1.5, "Kaw_eff": 0.003},
    "Damascenone": {"MW": 190.3, "VP_25": 1.0, "Kaw_eff": 0.002},
    "Damascol": {"MW": 194.3, "VP_25": 0.6, "Kaw_eff": 0.001},
    # ── Muguet heart (additions) ──
    "Mayol": {"MW": 166.3, "VP_25": 1.5, "Kaw_eff": 0.002},
    "Farnesol": {"MW": 222.4, "VP_25": 0.08, "Kaw_eff": 0.0004},
    "Geraniol": {"MW": 154.3, "VP_25": 4.0, "Kaw_eff": 0.005},
    "Citronellol": {"MW": 156.3, "VP_25": 4.5, "Kaw_eff": 0.005},
    "Ethyl Safranate": {"MW": 166.2, "VP_25": 3.5, "Kaw_eff": 0.005},
    "Indole": {"MW": 117.2, "VP_25": 1.5, "Kaw_eff": 0.001},
    "Guaiacol": {"MW": 124.1, "VP_25": 10.0, "Kaw_eff": 0.004},
    # ── Aldehydes (1% dilutions but extremely high impact/VP ratio) ──
    "Aldehyde C10": {"MW": 156.3, "VP_25": 10.0, "Kaw_eff": 0.008},
    "Aldehyde C11": {"MW": 170.3, "VP_25": 5.0, "Kaw_eff": 0.006},
    "Aldehyde C12 MNA": {"MW": 184.3, "VP_25": 3.0, "Kaw_eff": 0.005},
    "Scentenal": {"MW": 166.2, "VP_25": 6.0, "Kaw_eff": 0.007},
    "Calone": {"MW": 192.2, "VP_25": 2.0, "Kaw_eff": 0.004},
    # ── Base notes: high MW, very low VP, very low Kaw → intimate ──
    "Galaxolide": {"MW": 258.4, "VP_25": 0.01, "Kaw_eff": 0.0001},
    "Habanolide": {"MW": 238.4, "VP_25": 0.02, "Kaw_eff": 0.0002},
    "Ethylene Brassylate": {"MW": 270.4, "VP_25": 0.008, "Kaw_eff": 0.00008},
    "Exaltolide": {"MW": 240.4, "VP_25": 0.015, "Kaw_eff": 0.00015},
    "Musk Ketone": {"MW": 294.3, "VP_25": 0.003, "Kaw_eff": 0.00003},
    "Ambrettolide": {"MW": 252.4, "VP_25": 0.012, "Kaw_eff": 0.00012},
    "Iso E Super": {"MW": 234.4, "VP_25": 0.15, "Kaw_eff": 0.0008},
    "Cashmeran": {"MW": 206.3, "VP_25": 0.4, "Kaw_eff": 0.001},
    "Vertofix Coeur": {"MW": 234.4, "VP_25": 0.08, "Kaw_eff": 0.0005},
    "Timberol": {"MW": 220.4, "VP_25": 0.12, "Kaw_eff": 0.0006},
    "Kephalis": {"MW": 234.4, "VP_25": 0.05, "Kaw_eff": 0.0003},
    "Koavone": {"MW": 192.3, "VP_25": 0.3, "Kaw_eff": 0.001},
    "Amberwood F": {"MW": 234.4, "VP_25": 0.10, "Kaw_eff": 0.0005},
    "Vetival": {"MW": 206.3, "VP_25": 0.20, "Kaw_eff": 0.0008},
    "Suederal": {"MW": 238.4, "VP_25": 0.06, "Kaw_eff": 0.0003},
    "Javanol": {"MW": 210.4, "VP_25": 0.10, "Kaw_eff": 0.0005},
    "Ebanol": {"MW": 220.4, "VP_25": 0.08, "Kaw_eff": 0.0004},
    "Ambrox Super": {"MW": 236.4, "VP_25": 0.05, "Kaw_eff": 0.0003},
    "Benzyl Salicylate": {"MW": 228.3, "VP_25": 0.03, "Kaw_eff": 0.0002},
    "Hexyl Salicylate": {"MW": 222.3, "VP_25": 0.05, "Kaw_eff": 0.0003},
    "Evernyl": {"MW": 196.2, "VP_25": 0.10, "Kaw_eff": 0.0005},
    "Isobutyl Quinoline": {"MW": 185.3, "VP_25": 0.25, "Kaw_eff": 0.001},
    # ── Naturals (base) ──
    "Patchouli EO": {"MW": 222.4, "VP_25": 0.06, "Kaw_eff": 0.0003},
    "Vetiver EO": {"MW": 222.4, "VP_25": 0.05, "Kaw_eff": 0.0003},
    "Vetiver EO (India)": {"MW": 222.4, "VP_25": 0.04, "Kaw_eff": 0.0002},
    "Cedarwood EO": {"MW": 204.4, "VP_25": 0.25, "Kaw_eff": 0.001},
    "Labdanum Absolute": {"MW": 234.4, "VP_25": 0.03, "Kaw_eff": 0.0002},
    "Myrrh EO": {"MW": 222.4, "VP_25": 0.04, "Kaw_eff": 0.0002},
    "Olibanum Resinoid": {"MW": 222.4, "VP_25": 0.08, "Kaw_eff": 0.0004},
    "Benzoin Resinoid": {"MW": 212.2, "VP_25": 0.02, "Kaw_eff": 0.0001},
    "Birch Tar Rectified": {"MW": 124.1, "VP_25": 13.3, "Kaw_eff": 0.003},
    "Carrot Seed EO": {"MW": 218.3, "VP_25": 0.15, "Kaw_eff": 0.0006},
    # ── Coumarin / vanillins ──
    "Coumarin": {"MW": 146.2, "VP_25": 0.5, "Kaw_eff": 0.0005},
    "Vanillin": {"MW": 152.2, "VP_25": 0.2, "Kaw_eff": 0.0002},
    "Ethyl Vanillin": {"MW": 166.2, "VP_25": 0.15, "Kaw_eff": 0.0002},
    "Maple Lactone": {"MW": 128.1, "VP_25": 1.5, "Kaw_eff": 0.001},
    "Gamma Decalactone": {"MW": 170.3, "VP_25": 0.8, "Kaw_eff": 0.001},
    "Raspberry Ketone": {"MW": 164.2, "VP_25": 0.3, "Kaw_eff": 0.0004},
    "Paradisamide": {"MW": 289.4, "VP_25": 0.01, "Kaw_eff": 0.00008},
    "Tonka Bean FO": {"MW": 166.2, "VP_25": 0.3, "Kaw_eff": 0.0003},
    # ── Styrax ──
    "Styrax FTEC": {"MW": 148.2, "VP_25": 1.5, "Kaw_eff": 0.002},
    # ── Added 2026-04-25: previously-missing materials used in Mr_Sandman and similar ──
    "Anisaldehyde": {"MW": 136.2, "VP_25": 0.05, "Kaw_eff": 0.0002},
    "Ethyl Maltol": {"MW": 140.1, "VP_25": 0.02, "Kaw_eff": 0.0001},
    "Romandolide": {"MW": 268.4, "VP_25": 0.0005, "Kaw_eff": 0.00005},
    "Azarbre": {"MW": 234.4, "VP_25": 0.001, "Kaw_eff": 0.0002},
    # Cedarwood oil Virginia: alias "cedarwood oil virginia" → "cedarwood virginia" in name_utils
    "Cedarwood oil Virginia": {"MW": 204.4, "VP_25": 0.15, "Kaw_eff": 0.001},
    # ── Added 2026-04-28: active formula materials missing from DIFFUSION_DATA ──
    # VP_25 in Pa at 25 °C (not mmHg — Pa = mmHg × 133.322)
    # Ionone / violet
    "Alpha Isomethyl Ionone": {
        "MW": 206.3,
        "VP_25": 0.13,
        "Kaw_eff": 0.00006,
    },  # Pa, not mmHg
    # Fruity / top
    "Apritone": {"MW": 180.3, "VP_25": 5.0, "Kaw_eff": 0.0008},
    "Ethyl 2-Methylbutyrate": {"MW": 130.2, "VP_25": 1860.0, "Kaw_eff": 0.02},
    "Hexyl Acetate": {"MW": 144.2, "VP_25": 190.0, "Kaw_eff": 0.004},
    # Floral / jasmine
    "Benzyl Acetate": {"MW": 150.2, "VP_25": 24.0, "Kaw_eff": 0.002},
    "Cis Jasmone": {"MW": 164.2, "VP_25": 5.0, "Kaw_eff": 0.0008},
    # Aromatic / linalool-type
    "Ethyl Linalool": {"MW": 182.3, "VP_25": 8.0, "Kaw_eff": 0.0007},
    "Cardamom EO": {"MW": 154.3, "VP_25": 15.0, "Kaw_eff": 0.010},
    # Sandalwood / woody (heavy — Pa not mmHg)
    "Sandalore": {"MW": 226.4, "VP_25": 0.5, "Kaw_eff": 0.00004},  # Pa, not mmHg
    "Norlimbanol Dextro": {
        "MW": 222.4,
        "VP_25": 0.2,
        "Kaw_eff": 0.00003,
    },  # Pa, not mmHg
    # Macrocyclic musk (heavy — Pa not mmHg)
    "Zenolide": {"MW": 238.4, "VP_25": 0.05, "Kaw_eff": 0.00005},  # Pa, not mmHg
}


def _estimate_kaw_eff(vp_25: float, mw: float, activity_coef: float = 1.0) -> float:
    """Estimate Kaw at skin temperature when only profile MW/VP data exists.

    VP_25 (measured at 25 °C) is scaled to skin temperature (32 °C) via
    Clausius–Clapeyron before computing Kaw, so auto-populated materials use
    the same thermal basis as headspace.py (305 K). Hand-curated DIFFUSION_DATA
    entries are not affected — only profile-fallback entries use this path.
    """
    vp_skin = vp_pa(_T_SKIN, vp_25c_pa=float(vp_25), dhvap_kj_mol=50.0)
    mw_term = max(float(mw), 1.0)
    gamma_term = max(float(activity_coef), 0.1)
    kaw = (
        0.003 * math.sqrt(vp_skin) * math.sqrt(gamma_term) * math.sqrt(180.0 / mw_term)
    )
    return min(0.05, max(0.00005, kaw))


def _clone_diffusion_row(row: dict[str, float]) -> dict[str, float]:
    return {
        "MW": float(row["MW"]),
        "VP_25": float(row["VP_25"]),
        "Kaw_eff": float(row["Kaw_eff"]),
    }


_DIFFUSION_INDEX: dict[str, dict[str, float]] = {}
for _name, _row in DIFFUSION_DATA.items():
    _DIFFUSION_INDEX[normalize_name(_name)] = _row

try:
    from engine.ingredient_intelligence import _PROFILES as _INGREDIENT_PROFILES
except Exception:
    _INGREDIENT_PROFILES = {}

for _name, _profile in _INGREDIENT_PROFILES.items():
    _norm = normalize_name(_name)
    _existing = _DIFFUSION_INDEX.get(_norm)
    if _existing is not None:
        DIFFUSION_DATA.setdefault(_name, _clone_diffusion_row(_existing))
        continue

    _mw = _profile.get("mw")
    _vp = _profile.get("vp")
    if _mw is None or _vp is None:
        continue

    _row = {
        "MW": float(_mw),
        "VP_25": float(_vp),
        "Kaw_eff": _estimate_kaw_eff(_vp, _mw, _profile.get("activity_coef", 1.0)),
    }
    DIFFUSION_DATA[_name] = _row
    _DIFFUSION_INDEX[_norm] = _row

del _name, _row, _norm, _existing, _mw, _vp


# ═══════════════════════════════════════════════════════════════════════════════
# Diffusion Field Classification
# ═══════════════════════════════════════════════════════════════════════════════

# D_air reference: D_air for a typical MW-150 fragrance molecule ≈ 0.06 cm²/s at 25°C
# Scaling: D_air ∝ 1/√MW (Graham's law for ideal gases)
_D_REF = 0.06  # cm²/s for MW=150 reference
_MW_REF = 150.0


def _diffusion_coeff(mw: float) -> float:
    """Graham's law diffusion coefficient in air (cm²/s)."""
    return _D_REF * math.sqrt(_MW_REF / mw)


def _classify_reach(mw: float, kaw: float) -> str:
    """Classify into near/mid/far field based on MW and air partition."""
    # Projection index combines diffusion speed with headspace tendency
    proj = kaw * _diffusion_coeff(mw) * 1000  # arbitrary scaling
    if proj > 0.3:
        return "far"  # projects >2m — sillage beast
    elif proj > 0.01:
        return "mid"  # projects 0.5-2m — moderate trail
    else:
        return "near"  # <0.5m — skin scent / intimate


# ═══════════════════════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DiffusionReport:
    """Vapour-phase diffusion analysis."""

    score: float  # 0-100 diffusion architecture
    far_field_pct: float  # % of active mass in far field
    mid_field_pct: float  # % in mid field
    near_field_pct: float  # % in near field
    projection_index: float  # weighted mean Kaw
    molecular_weight_spread: float  # MW range across layers
    sillage_class: str  # beast / moderate / intimate / flat
    field_materials: dict[str, list[str]]  # near/mid/far → material names
    diagnostics: list[str]


def score_diffusion(
    ingredients: dict[str, float],
    dilutions: dict[str, float] | None = None,
    gamma_map: dict[str, float] | None = None,
) -> DiffusionReport:
    """Score vapour-phase diffusion architecture.

    A high score means the formula has a layered diffusion field:
    - Far field materials for initial sillage and trail
    - Mid field for moderate projection
    - Near field for intimate skin-scent base

    A low score means the diffusion is flat (all near or all far).

    gamma_map: per-material activity coefficient γᵢ (optional). When provided,
      Kaw_eff is scaled by √γ before reach classification, so non-ideal mixing
      (γ > 1 → salted-out, projects further; γ < 1 → retained, projects less)
      is reflected dynamically. If omitted, the static γ baked into DIFFUSION_DATA
      Kaw_eff at module init time is used.
    """
    dilutions = dilutions or {}
    gamma_map = gamma_map or {}
    field_mass = {"far": 0.0, "mid": 0.0, "near": 0.0}
    field_names: dict[str, list[str]] = {"far": [], "mid": [], "near": []}
    total_active = 0.0
    kaw_sum = 0.0
    mw_values: list[float] = []
    diagnostics: list[str] = []

    for name, amount in ingredients.items():
        dil = dilutions.get(name, 1.0)
        active = amount * dil
        total_active += active

        data = DIFFUSION_DATA.get(name)
        if not data:
            data = _DIFFUSION_INDEX.get(normalize_name(name))
        if not data:
            continue

        mw = data["MW"]
        kaw = data["Kaw_eff"]
        # Apply dynamic γ correction if provided. kaw is proportional to √γ
        # (from Henry's law: Kaw ∝ VP × γ), so scaling by √(γ_dynamic/γ_static)
        # adjusts the baked-in static γ to the mixture-specific value.
        gamma = gamma_map.get(name, 1.0)
        kaw_effective = kaw * math.sqrt(max(gamma, 0.1))
        reach = _classify_reach(mw, kaw_effective)

        field_mass[reach] += active
        field_names[reach].append(name)
        kaw_sum += kaw_effective * active
        mw_values.append(mw)

    profiled = sum(field_mass.values())
    if profiled == 0:
        return DiffusionReport(
            score=50,
            far_field_pct=0,
            mid_field_pct=0,
            near_field_pct=0,
            projection_index=0,
            molecular_weight_spread=0,
            sillage_class="unknown",
            field_materials=field_names,
            diagnostics=["No diffusion data for ingredients"],
        )

    far_pct = field_mass["far"] / profiled * 100
    mid_pct = field_mass["mid"] / profiled * 100
    near_pct = field_mass["near"] / profiled * 100
    proj_idx = kaw_sum / profiled if profiled > 0 else 0
    mw_spread = max(mw_values) - min(mw_values) if len(mw_values) >= 2 else 0

    # Classify overall sillage
    if far_pct > 40:
        sillage_class = "beast"
    elif far_pct + mid_pct > 50:
        sillage_class = "moderate"
    elif near_pct > 70:
        sillage_class = "intimate"
    else:
        sillage_class = "balanced"

    # Score: reward layered architecture
    # Ideal: ~15-25% far, ~30-45% mid, ~30-45% near
    score = 0.0

    # Layering bonus (all three fields populated)
    if field_mass["far"] > 0 and field_mass["mid"] > 0 and field_mass["near"] > 0:
        score += 30
    elif sum(1 for m in field_mass.values() if m > 0) == 2:
        score += 15

    # Distribution balance — ideal is not too concentrated in any one field
    # Entropy-like measure
    fracs = [far_pct / 100, mid_pct / 100, near_pct / 100]
    entropy = 0.0
    for f in fracs:
        if f > 0:
            entropy -= f * math.log2(f)
    # Max entropy = log2(3) ≈ 1.585
    entropy_norm = entropy / 1.585
    score += entropy_norm * 40  # up to 40 points for balanced distribution

    # MW spread bonus — broader range = more temporal depth
    if mw_spread > 100:
        score += 20
    elif mw_spread > 60:
        score += 10

    # Penalty for extreme imbalance
    if far_pct > 60:
        score -= 10
        diagnostics.append(
            "⚠ Over-projected — too much far-field material, may lack intimacy"
        )
    if near_pct > 80:
        score -= 15
        diagnostics.append(
            "⚠ Under-projected — most materials are near-field only, limited sillage"
        )

    score = max(0, min(100, score))

    # Diagnostics
    diagnostics.insert(
        0,
        f"Field distribution: far={far_pct:.0f}% | mid={mid_pct:.0f}% | near={near_pct:.0f}%",
    )
    diagnostics.append(
        f"MW spread: {mw_spread:.0f} Da ({min(mw_values):.0f}–{max(mw_values):.0f})"
    )
    diagnostics.append(f"Sillage class: {sillage_class}")
    diagnostics.append(f"Projection index (mean Kaw): {proj_idx:.5f}")

    if far_pct > 0:
        diagnostics.append(f"Far-field: {', '.join(field_names['far'][:5])}")
    if mid_pct > 0:
        diagnostics.append(f"Mid-field: {', '.join(field_names['mid'][:5])}")
    if near_pct > 0:
        diagnostics.append(f"Near-field: {', '.join(field_names['near'][:5])}")

    return DiffusionReport(
        score=round(score, 1),
        far_field_pct=round(far_pct, 1),
        mid_field_pct=round(mid_pct, 1),
        near_field_pct=round(near_pct, 1),
        projection_index=round(proj_idx, 6),
        molecular_weight_spread=round(mw_spread, 1),
        sillage_class=sillage_class,
        field_materials=field_names,
        diagnostics=diagnostics,
    )
