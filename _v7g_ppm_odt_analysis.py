"""v7g chemical & perfumer analysis — ppm, ODT, OAV (Odor Activity Value).

Conversion model:
  Concentrate volume (active) = sum(µL × dilution) — the actual perfume oil.
  ppm_in_concentrate(material) = (µL × dilution) / total_active_µL × 1e6
                              ≈ mg/kg in the concentrate (assuming ρ ≈ 1)

Odor science layer:
  ODT (in air, ppb) — Devos/Salesses-Laffon database; physiological detection
                      threshold in vapor phase. Lower = more potent.
  ODT_ppm (in solvent, ppm) — solution-phase threshold; for OAV in liquid.
  OAV_solution = ppm_in_concentrate / ODT_ppm
                — how many "detection units" the material exceeds threshold
                  by in the perfume oil. Stevens 1957 / Patte 1975.
  Headspace_relative = ppm_in_concentrate × VP × γ / (MW × ODT_air_ppb × 1000)
                — proxy for the material's contribution to perceived note in
                  vapor above skin (Raoult-deviated by activity coefficient γ).
                  Higher = stronger headspace presence per unit threshold.

Then ppm_change → smell_change via Stevens' power law:
  ΔPerception ≈ (ppm_new / ppm_old)^β   with β ≈ 0.4–0.7 for olfaction
                                          (Cain 1969 mean β = 0.55 across panel).
  +50 % ppm  → ~+24 % perceived intensity (β = 0.55)
  +100 % ppm → ~+47 %
  −50 % ppm  → ~−32 %

Output:
  • per-material table: µL, dilution, active µL, ppm_concentrate, ODT_ppm,
    ODT_air, OAV_solution, headspace_index, ppm/Stevens
  • register summary (iris / muguet / cream / musk / wood / citrus / fixative)
  • critical perfumer commentary
"""

from __future__ import annotations
import json
import math

from engine.ingredient_intelligence import get_profile

with open("_opt_v7g_helio_musk.json", "r", encoding="utf-8") as f:
    SNAP = json.load(f)
V7G = SNAP["v7g"]
ING = V7G["ing"]
DIL = V7G["dil"]

# Total ACTIVE concentrate (µL of pure aroma chemical, excluding dilution carrier)
def dil_of(name):
    return DIL.get(name, 1.0)

total_active_uL = sum(ING[k] * dil_of(k) for k in ING)

print("=" * 96)
print(f"  v7g — ppm / ODT / OAV analysis      (total active concentrate {total_active_uL:.0f} µL)")
print("=" * 96)

# Build per-material analysis
rows = []
no_profile = []
for name, vol_uL in sorted(ING.items(), key=lambda kv: -kv[1] * dil_of(kv[0])):
    if vol_uL <= 0:
        continue
    dil = dil_of(name)
    active_uL = vol_uL * dil
    ppm_conc = active_uL / total_active_uL * 1e6  # ppm (m/m at ρ≈1)
    prof = get_profile(name)
    if prof is None:
        no_profile.append(name)
        rows.append({
            "name": name, "vol": vol_uL, "dil": dil, "active": active_uL,
            "ppm": ppm_conc,
            "mw": None, "vp": None, "clogp": None, "odt_air": None, "odt_ppm": None,
            "OAV_sol": None, "hs_index": None,
        })
        continue
    odt_air = prof.odt           # ppb air
    odt_ppm = prof.odt_ppm       # ppm solution
    OAV_sol = (ppm_conc / odt_ppm) if odt_ppm and odt_ppm > 0 else None
    # Headspace index: ppm × VP / (MW × ODT_air); units arbitrary, use for ranking
    if prof.vp and prof.mw and odt_air and odt_air > 0:
        hs_index = ppm_conc * prof.vp / (prof.mw * odt_air)
    else:
        hs_index = None
    rows.append({
        "name": name, "vol": vol_uL, "dil": dil, "active": active_uL,
        "ppm": ppm_conc,
        "mw": prof.mw, "vp": prof.vp, "clogp": prof.clogp,
        "odt_air": odt_air, "odt_ppm": odt_ppm,
        "OAV_sol": OAV_sol, "hs_index": hs_index,
    })

# Print master table
print()
print(f"{'Material':<32}{'µL':>6}{'dil':>5}{'act µL':>8}{'ppm':>9}{'MW':>6}{'VP/Pa':>9}{'cLogP':>7}{'ODT(ppb)':>10}{'ODT(ppm)':>10}{'OAV_sol':>10}{'HS_idx':>10}")
print("─" * 122)
for r in rows:
    def fmt(v, w, p=2):
        return f"{v:{w}.{p}f}" if (v is not None and isinstance(v, (int, float))) else " " * (w - 1) + "·"
    print(f"{r['name'][:32]:<32}{r['vol']:>6.0f}{r['dil']:>5.2f}{r['active']:>8.1f}{r['ppm']:>9.0f}"
          f"{fmt(r['mw'],6,0)}{fmt(r['vp'],9,3)}{fmt(r['clogp'],7,1)}"
          f"{fmt(r['odt_air'],10,3)}{fmt(r['odt_ppm'],10,2)}"
          f"{fmt(r['OAV_sol'],10,1)}{fmt(r['hs_index'],10,2)}")

if no_profile:
    print(f"\n  ⚠ no engine profile for: {', '.join(no_profile)}")

# ───────────── Register groupings ─────────────
REGISTERS = {
    "Iris powder core":   ["Alpha Irone", "Orivone", "Beta Ionone", "Alpha Ionone",
                            "Alpha Isomethyl Ionone", "Ultralia", "Carrot Seed EO"],
    "Muguet white floral": ["Hydroxycitronellal", "Mayol", "Lilyreal ND", "Bourgeonal",
                            "DBCA", "Freesia HDI", "PEDMC"],
    "Cream / coumarin / vanillic": ["Heliotropal", "Vanillin", "Ethyl Vanillin", "Coumarin",
                            "Anisaldehyde", "Ethyl Maltol", "Delta Decalactone",
                            "Gamma Undecalactone", "Benzoin Resinoid"],
    "Floral radiance / fresh": ["Hedione", "Hedione HC", "Ethyl Linalool", "Helional",
                            "Damascol", "Indole", "Isoeugenol"],
    "Sandalwood / wood":  ["Ebanol", "Javanol", "Iso E Super", "Cedarwood EO"],
    "Amber / mineral":    ["Ambrox Super", "Scentenal"],
    "Cushion / fixative": ["Hexyl Salicylate", "Benzyl Salicylate"],
    "Musk chord":         ["Ethylene Brassylate", "Habanolide", "Ambrettolide",
                            "Romandolide", "Galaxolide", "Zenolide",
                            "Musk Ketone", "Tonalide"],
    "Citrus top":         ["Bergamot FCF oil Sicilian"],
}

print("\n" + "=" * 96)
print("  REGISTER SUMMARY  (active µL, ppm of concentrate, % of concentrate)")
print("=" * 96)
register_totals = {}
for reg, mats in REGISTERS.items():
    active = sum(ING.get(m, 0.0) * dil_of(m) for m in mats)
    ppm = active / total_active_uL * 1e6
    pct = ppm / 1e4
    register_totals[reg] = (active, ppm, pct)
    print(f"  {reg:<32s} {active:>8.1f} µL    {ppm:>9.0f} ppm    {pct:>5.2f} %")
unaccounted = total_active_uL - sum(v[0] for v in register_totals.values())
print(f"  {'(unaccounted / overlap)':<32s} {unaccounted:>+8.1f} µL")

# ───────────── Top OAV contributors (signal strength in liquid) ─────────────
print("\n" + "=" * 96)
print("  TOP 15 OAV-SOLUTION CONTRIBUTORS  (signal strength in concentrate)")
print("    OAV = ppm_concentrate / ODT_ppm.  OAV >> 1 = above panel detection.")
print("=" * 96)
ranked_oav = [r for r in rows if r["OAV_sol"] is not None]
ranked_oav.sort(key=lambda r: -r["OAV_sol"])
print(f"  {'Material':<32}{'ppm':>9}{'ODT_ppm':>10}{'OAV_sol':>10}  rank-driver")
for r in ranked_oav[:15]:
    print(f"  {r['name']:<32}{r['ppm']:>9.0f}{r['odt_ppm']:>10.2f}{r['OAV_sol']:>10.1f}")

# ───────────── Top headspace contributors (signal strength in vapor) ─────────────
print("\n" + "=" * 96)
print("  TOP 15 HEADSPACE-INDEX CONTRIBUTORS  (perceived signal in vapor above skin)")
print("    HS_idx = ppm × VP / (MW × ODT_air).  Drives smelt character at distance.")
print("=" * 96)
ranked_hs = [r for r in rows if r["hs_index"] is not None]
ranked_hs.sort(key=lambda r: -r["hs_index"])
print(f"  {'Material':<32}{'ppm':>9}{'VP':>9}{'MW':>6}{'ODT_air':>10}{'HS_idx':>10}")
for r in ranked_hs[:15]:
    print(f"  {r['name']:<32}{r['ppm']:>9.0f}{r['vp']:>9.3f}{r['mw']:>6.0f}{r['odt_air']:>10.3f}{r['hs_index']:>10.2f}")

# ───────────── Stevens-law sensitivity table for top movers ─────────────
print("\n" + "=" * 96)
print("  STEVENS' POWER LAW — perceived intensity change vs ppm change")
print("    ΔPerception = (ppm_new / ppm_old)^β,  β = 0.55 (Cain 1969 olfactory mean)")
print("=" * 96)
beta = 0.55
print(f"  ppm change       perceived change")
for delta in [-0.5, -0.25, -0.1, +0.1, +0.25, +0.5, +1.0, +2.0]:
    factor = (1 + delta) ** beta
    print(f"  {delta*100:+6.0f} %         {(factor-1)*100:+6.1f} %")

print("\n  → Implication: a +100 % dose hike yields only ~+47 % perceived intensity.")
print("    Above OAV ≈ 100 the response saturates (Patte–Laffort suppression).")
print("    Below OAV ≈ 1 a material is sub-threshold and contributes only via mixture")
print("    enhancement / antagonism (Atanasova 2005).")

# Save analysis JSON
out = {
    "total_active_uL": total_active_uL,
    "rows": rows,
    "registers": register_totals,
    "stevens_beta": beta,
}
with open("_opt_v7g_ppm_odt_analysis.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n  → _opt_v7g_ppm_odt_analysis.json")
