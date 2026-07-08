"""Run the new physics-grounded engine against Iris Rêverie Lactée v7h (50 mL).

Formula source: formulas/Iris_Reverie_Lactee_v7h_50mL_BUILD.md
Build geo score: 82.224 (legacy 10-axis scorer)

Goal: see what the new modules say about
  • headspace at skin T (modified Raoult)
  • OAV ranking with mixture shift
  • phase-separation risk (Hansen RED)
  • OR receptor activation (where data exists)
  • spray Dv50 + initial droplet evaporation

Materials with no literature data are dropped from physics computation but the
script reports the coverage gap explicitly.
"""
from __future__ import annotations

from engine.thermo.headspace import headspace_from_wt_pct
from engine.thermo.phase import micro_phase_risk
from engine.perception.oav import oav_profile
from engine.delivery.spray import droplet_distribution, droplet_d2_evaporation
from engine.delivery.sniff import olfactory_cleft_concentration

# ---------------------------------------------------------------------------
# 1) Formula (active µL in 50 mL EDP, NOT stock-dilution µL).
#    Pulled from the BUILD sheet "µL active in 50 mL" column.
# ---------------------------------------------------------------------------
ACTIVE_UL: dict[str, float] = {
    "Hedione": 1700,
    "Ethyl Linalool": 1300,
    "Ethylene Brassylate": 1150,
    "Ebanol": 900,
    "Hedione HC": 800,
    "Romandolide": 700,
    "Benzoin Resinoid": 650,
    "Cedarwood EO": 600,
    "Hydroxycitronellal": 500,
    "Orivone": 450,
    "Alpha Irone": 375,
    "Bergamot FCF Sicilian": 265,
    "Habanolide": 240,
    "Galaxolide": 240,
    "Carrot Seed EO": 210,
    "Iso E Super": 200,
    "Hexyl Salicylate": 200,
    "Ambrox Super": 135,
    "Anisaldehyde": 130,
    "Alpha Ionone": 110,
    "Zenolide": 100,
    "Alpha Isomethyl Ionone": 80,
    "DBCA": 75,
    "Freesia HDI": 75,
    "Lilyreal": 65,
    "Beta Ionone": 60,
    "Javanol": 55,
    "Heliotropal": 55,
    "gamma-Decalactone": 50,
    "Ambrettolide": 30,
    "Allyl Ionone": 30,
    "Vanillin": 30,
    "PEDMC": 25,
    "Mayol": 25,
    "Ethyl Vanillin": 25,
    "gamma-Nonalactone": 20,
    "Musk Ketone": 20,
    "Coumarin": 15,
    "Tonalide": 15,
    "Isoeugenol": 10,
    "Bourgeonal": 4,
    "Damascol": 2.5,
    "Indole": 1.5,
    "Scentenal": 0.25,
    # Solvent — explicit. 35.07 mL ethanol → 35070 µL.
    "Ethanol": 35070,
}

# ---------------------------------------------------------------------------
# 2) Literature physical/olfactory data for the load-bearing players.
#    MW (g/mol), VP@25C (Pa), ODT_air (ppm v/v), HSP (δD, δP, δH, MPa^0.5),
#    family for Stevens.
#    Sources: PubChem, RIFM, "Compilation of Odour Threshold Values" (van Gemert),
#    Hansen Solubility Parameters in Practice (Hansen), Steltenkamp 1989,
#    The Good Scents Co.
# ---------------------------------------------------------------------------
MW = {
    "Ethanol": 46.07,
    "Hedione": 226.31, "Ethyl Linalool": 168.28, "Ethylene Brassylate": 270.41,
    "Ebanol": 222.37, "Hedione HC": 240.34, "Romandolide": 264.36,
    "Benzoin Resinoid": 350.0,  # avg resin mass (mostly benzyl benzoate / cinnamate)
    "Cedarwood EO": 204.4, "Hydroxycitronellal": 172.27, "Orivone": 208.34,
    "Alpha Irone": 206.32, "Bergamot FCF Sicilian": 152.0,  # avg of d-limonene/linalool/linalyl ac
    "Habanolide": 252.40, "Galaxolide": 258.40, "Carrot Seed EO": 222.37,  # carotol-dom
    "Iso E Super": 234.38, "Hexyl Salicylate": 222.28, "Ambrox Super": 236.40,
    "Anisaldehyde": 136.15, "Alpha Ionone": 192.30, "Zenolide": 254.40,
    "Alpha Isomethyl Ionone": 206.32, "DBCA": 222.28, "Freesia HDI": 192.30,
    "Lilyreal": 192.30, "Beta Ionone": 192.30, "Javanol": 222.37,
    "Heliotropal": 178.18, "gamma-Decalactone": 170.25, "Ambrettolide": 252.40,
    "Allyl Ionone": 218.34, "Vanillin": 152.15, "PEDMC": 218.30,
    "Mayol": 192.30, "Ethyl Vanillin": 166.18, "gamma-Nonalactone": 156.22,
    "Musk Ketone": 294.30, "Coumarin": 146.14, "Tonalide": 258.40,
    "Isoeugenol": 164.20, "Bourgeonal": 190.28, "Damascol": 194.31,
    "Indole": 117.15, "Scentenal": 192.30,
}

# VP at 25 °C in Pa (literature; many fragrance materials only have ranges)
VP25 = {
    "Ethanol": 7900,
    "Bergamot FCF Sicilian": 250,            # bergamot ~ linalyl acetate / limonene avg
    "Carrot Seed EO": 5,
    "Cedarwood EO": 0.20,                    # cedrol-dominated
    "Hydroxycitronellal": 0.5,
    "Anisaldehyde": 1.0,
    "Bourgeonal": 0.4,
    "Hedione": 0.07,
    "Hedione HC": 0.05,
    "Ethyl Linalool": 13.0,
    "Iso E Super": 0.36,
    "Hexyl Salicylate": 0.04,
    "Alpha Ionone": 1.5,
    "Beta Ionone": 0.5,
    "Alpha Isomethyl Ionone": 0.6,
    "Allyl Ionone": 1.0,
    "Lilyreal": 1.2, "Mayol": 1.0, "DBCA": 0.5, "Freesia HDI": 0.8,
    "Heliotropal": 0.3,
    "Orivone": 0.04, "Alpha Irone": 0.10,
    "Ebanol": 0.005, "Javanol": 0.003,
    "Romandolide": 0.0008, "Habanolide": 0.0005, "Galaxolide": 0.0007,
    "Ambrettolide": 0.0003, "Ethylene Brassylate": 0.001,
    "Tonalide": 0.0007, "Zenolide": 0.001, "Musk Ketone": 0.00006,
    "Ambrox Super": 0.001,
    "Vanillin": 0.012, "Ethyl Vanillin": 0.008, "Coumarin": 0.013,
    "Isoeugenol": 0.5, "Indole": 1.6, "PEDMC": 0.8, "Damascol": 0.05,
    "gamma-Decalactone": 0.05, "gamma-Nonalactone": 0.10,
    "Scentenal": 0.4,
    "Benzoin Resinoid": 0.0001,
}

# Odor detection threshold in air, ppm v/v (mass-equiv conversion handled inside oav)
# We store as ppm v/v to match `oav` signature. Literature mostly reports ng/L → convert.
# 1 ng/L ≈ (1e-9 g / L) / (MW g/mol) × 24.45 L/mol(air,25C) × 1e6 ppm  =  24.45 / MW * 1e-3 ppm
def _ngL_to_ppm(ng_per_L: float, mw: float) -> float:
    return 24.45 / mw * 1e-3 * ng_per_L

ODT_NGL = {       # ng/L air, perfumery literature
    "Ethanol": 1e6,                          # essentially threshold-irrelevant here
    "Hedione": 400, "Hedione HC": 400, "Ethyl Linalool": 6,
    "Ethylene Brassylate": 100, "Ebanol": 0.05, "Romandolide": 50,
    "Benzoin Resinoid": 200, "Cedarwood EO": 30,
    "Hydroxycitronellal": 0.5, "Orivone": 5, "Alpha Irone": 0.07,
    "Bergamot FCF Sicilian": 30, "Habanolide": 6, "Galaxolide": 1,
    "Carrot Seed EO": 50, "Iso E Super": 2.5, "Hexyl Salicylate": 50,
    "Ambrox Super": 0.2, "Anisaldehyde": 6, "Alpha Ionone": 0.4,
    "Zenolide": 5, "Alpha Isomethyl Ionone": 1, "DBCA": 0.5,
    "Freesia HDI": 0.5, "Lilyreal": 1, "Beta Ionone": 0.007,
    "Javanol": 0.05, "Heliotropal": 0.5, "gamma-Decalactone": 0.5,
    "Ambrettolide": 1, "Allyl Ionone": 0.5, "Vanillin": 0.2,
    "PEDMC": 1, "Mayol": 0.5, "Ethyl Vanillin": 0.1,
    "gamma-Nonalactone": 0.3, "Musk Ketone": 1, "Coumarin": 5,
    "Tonalide": 1, "Isoeugenol": 1, "Bourgeonal": 0.05,
    "Damascol": 0.05, "Indole": 0.3, "Scentenal": 0.05,
}

ODT_PPM = {n: _ngL_to_ppm(v, MW.get(n, 200.0)) for n, v in ODT_NGL.items()}

# Hansen solubility parameters (δD, δP, δH) MPa^0.5 — best available
HSP = {
    "Ethanol": (15.8, 8.8, 19.4),
    # broad fragrance defaults; specific overrides where known
    "Hedione": (16.5, 5.0, 6.5), "Hedione HC": (16.5, 5.0, 6.5),
    "Ethyl Linalool": (15.5, 4.5, 8.0),
    "Ethylene Brassylate": (16.5, 3.5, 5.0), "Ebanol": (16.5, 4.0, 6.0),
    "Romandolide": (16.0, 4.0, 5.0), "Benzoin Resinoid": (18.0, 6.0, 9.0),
    "Cedarwood EO": (16.0, 2.5, 5.0), "Hydroxycitronellal": (16.5, 7.0, 11.0),
    "Orivone": (16.5, 4.5, 6.5), "Alpha Irone": (16.5, 4.0, 6.0),
    "Bergamot FCF Sicilian": (16.0, 2.5, 5.5),
    "Habanolide": (16.0, 3.0, 4.0), "Galaxolide": (16.5, 3.0, 4.0),
    "Carrot Seed EO": (16.0, 3.5, 6.0),
    "Iso E Super": (16.0, 1.5, 3.0), "Hexyl Salicylate": (17.0, 5.0, 8.0),
    "Ambrox Super": (16.5, 2.5, 4.0), "Anisaldehyde": (18.5, 8.0, 6.0),
    "Alpha Ionone": (16.5, 4.0, 5.5), "Beta Ionone": (16.5, 4.0, 5.5),
    "Alpha Isomethyl Ionone": (16.5, 4.0, 5.5), "Allyl Ionone": (16.5, 4.0, 5.5),
    "Zenolide": (16.0, 3.0, 4.0),
    "DBCA": (17.0, 5.5, 7.0), "Freesia HDI": (16.5, 5.5, 7.5),
    "Lilyreal": (16.5, 5.5, 7.5), "Mayol": (16.5, 5.5, 7.5),
    "Heliotropal": (18.0, 7.0, 7.0),
    "Javanol": (16.5, 3.5, 5.5),
    "gamma-Decalactone": (16.5, 5.5, 8.0), "gamma-Nonalactone": (16.5, 6.0, 8.5),
    "Ambrettolide": (16.0, 3.0, 4.0),
    "Vanillin": (19.0, 9.0, 12.0), "Ethyl Vanillin": (19.0, 9.0, 12.0),
    "Coumarin": (19.0, 7.0, 8.0),
    "PEDMC": (17.0, 5.0, 6.0), "Damascol": (16.5, 4.5, 6.5),
    "Musk Ketone": (18.0, 6.0, 4.0), "Tonalide": (16.5, 3.0, 4.0),
    "Isoeugenol": (18.0, 6.5, 11.0),
    "Bourgeonal": (17.5, 6.0, 7.0), "Indole": (19.5, 5.5, 9.0),
    "Scentenal": (16.5, 5.0, 7.0),
}

FAMILY = {       # Stevens-exponent buckets
    "Ethanol": "solvent",
    "Hedione": "floral", "Hedione HC": "floral", "Ethyl Linalool": "citrus",
    "Bergamot FCF Sicilian": "citrus",
    "Ethylene Brassylate": "musk", "Romandolide": "musk", "Habanolide": "musk",
    "Galaxolide": "musk", "Ambrettolide": "musk", "Tonalide": "musk",
    "Musk Ketone": "musk", "Zenolide": "musk",
    "Ebanol": "wood", "Iso E Super": "wood", "Cedarwood EO": "wood",
    "Javanol": "wood",
    "Hydroxycitronellal": "floral", "Orivone": "powder", "Alpha Irone": "powder",
    "Carrot Seed EO": "earthy", "Hexyl Salicylate": "salicylate",
    "Ambrox Super": "amber", "Anisaldehyde": "anisic",
    "Alpha Ionone": "violet", "Beta Ionone": "violet",
    "Alpha Isomethyl Ionone": "violet", "Allyl Ionone": "violet",
    "DBCA": "floral", "Freesia HDI": "green", "Lilyreal": "muguet",
    "Mayol": "muguet", "Heliotropal": "powder",
    "gamma-Decalactone": "lactone", "gamma-Nonalactone": "lactone",
    "Vanillin": "vanilla", "Ethyl Vanillin": "vanilla", "Coumarin": "balsamic",
    "Isoeugenol": "spice", "Bourgeonal": "muguet", "Indole": "indolic",
    "Damascol": "rose", "PEDMC": "musk", "Scentenal": "ozone",
    "Benzoin Resinoid": "balsamic",
}

# ---------------------------------------------------------------------------
# 3) Convert active µL → wt% (assume ρ ≈ 1.0 g/mL for all so µL ≈ mg)
# ---------------------------------------------------------------------------
total_mass = sum(ACTIVE_UL.values())
WT_PCT = {n: 100.0 * v / total_mass for n, v in ACTIVE_UL.items()}

# Coverage report
covered = [n for n in ACTIVE_UL if n in MW and n in VP25]
missing = [n for n in ACTIVE_UL if n not in covered]
print("=" * 78)
print("DATA COVERAGE")
print("=" * 78)
print(f"  Materials in formula      : {len(ACTIVE_UL)}")
print(f"  Materials with MW + VP    : {len(covered)}")
print(f"  Materials missing physics : {len(missing)}  {missing if missing else ''}")
print()

# ---------------------------------------------------------------------------
# 4) Headspace at skin T = 305 K (32 °C wrist)
# ---------------------------------------------------------------------------
hs = headspace_from_wt_pct(
    WT_PCT, T_K=305.0,
    mw_table=MW, vp_table=VP25, hsp_table=HSP,
)

# Top headspace contributors by partial pressure (excluding ethanol)
ranked = sorted(
    ((c.name, c.partial_pressure_pa, c.gamma, c.vapor_ppm)
     for c in hs.values()),
    key=lambda r: r[1], reverse=True,
)
print("=" * 78)
print("HEADSPACE @ 305 K  (top 20 by partial pressure)")
print("=" * 78)
print(f"{'#':>2} {'material':28s} {'P_i(Pa)':>10s} {'ppm':>10s} {'γ':>6s}")
for i, (name, p, g, ppm) in enumerate(ranked[:20], 1):
    print(f"{i:2d} {name:28s} {p:10.3f} {ppm:10.2f} {g:6.2f}")
print()

# ---------------------------------------------------------------------------
# 5) OAV ranking — what is actually perceived
# ---------------------------------------------------------------------------
conc_ppm = {c.name: c.vapor_ppm for c in hs.values() if c.name in ODT_PPM}
odt_used = {n: ODT_PPM[n] for n in conc_ppm}
prof = oav_profile(conc_ppm, odt_used, FAMILY, use_mixture_shift=True, beta=0.3)

# Sort by perceived intensity (Stevens)
oav_sorted = sorted(prof.items(), key=lambda kv: kv[1]["intensity"], reverse=True)
print("=" * 78)
print("OAV PROFILE  (mixture-shifted, top 25 by perceived intensity)")
print("=" * 78)
print(f"{'#':>2} {'material':28s} {'OAV':>10s} {'I(Stevens)':>11s} {'ODT_eff':>10s}")
for i, (name, v) in enumerate(oav_sorted[:25], 1):
    print(f"{i:2d} {name:28s} {v['oav']:10.2f} {v['intensity']:11.2f} {v['odt_eff']:10.4f}")

# Sub-perceptible casualties
silent = [(n, v) for n, v in prof.items() if v["oav"] < 1.0]
print()
print(f"SUB-THRESHOLD (OAV < 1):  {len(silent)} of {len(prof)} scored materials")
for n, v in sorted(silent, key=lambda kv: kv[1]["oav"]):
    print(f"   {n:28s}  OAV={v['oav']:6.3f}  ← in liquid but not in air")
print()

# ---------------------------------------------------------------------------
# 6) Phase-separation risk (RED vs ethanol)
# ---------------------------------------------------------------------------
phase = micro_phase_risk(WT_PCT, HSP)
print("=" * 78)
print("PHASE-SEPARATION RISK  (Hansen RED vs ethanol-rich solvent, top 10)")
print("=" * 78)
print(f"{'material':28s} {'RED':>8s}  flag")
for name, red in phase[:10]:
    flag = "MISCIBLE" if red < 1.0 else ("BORDERLINE" if red < 1.3 else "BLOOM RISK")
    print(f"{name:28s} {red:8.2f}  {flag}")
print()

# ---------------------------------------------------------------------------
# 7) Spray atomisation + first-second flight
# ---------------------------------------------------------------------------
stats = droplet_distribution(dv50_um=30.0, sigma_g=1.5)
d_after_05s = droplet_d2_evaporation(d0_um=30.0, K_um2_s=400.0, t_s=0.5)
print("=" * 78)
print("SPRAY DELIVERY")
print("=" * 78)
print(f"  Dv50 (atomiser typical)   : {stats.dv50_um:.1f} µm")
print(f"  Dv90                      : {stats.dv90_um:.1f} µm")
print(f"  30 µm drop after 0.5 s    : {d_after_05s:.1f} µm  (ethanol d²-law)")
cleft = olfactory_cleft_concentration(vapor_conc_ug_m3=100.0)
print(f"  Cleft conc @ 100 µg/m³ HS : {cleft:.1f} µg/m³ (10% diversion)")
print()

# ---------------------------------------------------------------------------
# 8) Verdict against the brief
# ---------------------------------------------------------------------------
print("=" * 78)
print("VERDICT vs BRIEF (cosmetic-creamy iris, NOT rooty)")
print("=" * 78)
top5 = [n for n, *_ in ranked[:6] if n != "Ethanol"][:5]
print(f"  Top-5 headspace drivers (post-EtOH) : {top5}")
top_intensity = [n for n, _ in oav_sorted[:5]]
print(f"  Top-5 perceived intensity           : {top_intensity}")
iris_axis = sum(prof.get(n, {}).get("intensity", 0)
                for n in ("Alpha Irone", "Orivone", "Alpha Ionone",
                          "Beta Ionone", "Alpha Isomethyl Ionone"))
rooty_axis = prof.get("Carrot Seed EO", {}).get("intensity", 0)
muguet_axis = sum(prof.get(n, {}).get("intensity", 0)
                  for n in ("Lilyreal", "Mayol", "Bourgeonal",
                            "Hydroxycitronellal", "DBCA"))
musk_axis = sum(prof.get(n, {}).get("intensity", 0)
                for n in ("Habanolide", "Romandolide", "Ethylene Brassylate",
                          "Galaxolide", "Ambrettolide", "Zenolide"))
salicylate_axis = prof.get("Hexyl Salicylate", {}).get("intensity", 0)
print()
print(f"  Iris/orris-powder axis              : {iris_axis:6.2f}")
print(f"  Muguet-cushion axis                 : {muguet_axis:6.2f}")
print(f"  Salicylate cushion                  : {salicylate_axis:6.2f}")
print(f"  Macrocyclic-musk skin halo          : {musk_axis:6.2f}")
print(f"  Rooty (carrot-seed) intrusion       : {rooty_axis:6.2f}")
print()
ratio = iris_axis / (rooty_axis + 1e-6)
print(f"  iris : rooty ratio                  : {ratio:5.1f}× (target ≥ 5×)")
if ratio >= 5:
    print("  → Brief held: iris-powder dominates over carrot-seed earth.")
else:
    print("  → Brief at risk: rooty axis too prominent for the Infusion d'Iris brief.")
