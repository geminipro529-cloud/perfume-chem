#!/usr/bin/env python3
"""DHC OAV-first reformulation: define target headspace OAV percentages, back-calculate uL."""

import sys
sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM_FACTOR = 20.0  # 1e6 / 50,000 uL

# Material data needed for back-calculation
materials = [
    "Bergamot FCF Sicilian",
    "Cedrat FCF Sicilian",
    "Grapefruit FCF",
    "Lime Distilled EO",
    "Red Mandarin EO",
    "Linalyl Acetate",
    "Petitgrain EO",
    "Hedione",
    "Ethyl Linalool",
    "Paradisamide",
    "Hedione HC",
    "Romandolide",
    "Iso E Super",
    "Ethylene Brassylate",
    "Ambrofix",
    "Ambrettolide",
    "Norlimbanol Dextro",
    "Vetival",
]

mat_data = {}
for name in materials:
    norm = normalize_name(name)
    profile = get_profile(name)
    vp = profile.vp if profile and profile.vp else 0.0
    odt_data = ODT_DATA.get(norm, {})
    if not odt_data:
        odt_data = ODT_DATA.get(name.lower(), {})
    odt_air = odt_data.get('odt_air', None) if odt_data else None
    mat_data[name] = {'vp': vp, 'odt_air': odt_air}

def oav_to_ul(target_oav, vp, odt_air):
    """active_uL = target_oav * odt_air / vp / PPM_FACTOR"""
    if not vp or not odt_air or vp <= 0 or odt_air <= 0:
        return None
    return target_oav * odt_air / vp / PPM_FACTOR

def ul_to_oav(active_ul, vp, odt_air):
    if not vp or not odt_air or vp <= 0 or odt_air <= 0:
        return None
    ppm = active_ul * PPM_FACTOR
    return vp * ppm / odt_air

# === OAV TARGETS (mass-market Demachy DHC style) ===
# Principles:
# 1. Citrus star ~50% of total headspace -- unmistakable, dominant
# 2. Petitgrain ~25% -- structural citrus bridge, always #2
# 3. Linalyl Acetate ~12% -- freshness amplifier, modulated per citrus
# 4. Romandolide ~5.5% -- macrocyclic clean projection musk
# 5. Hedione ~1.6% -- radiance amplifier, transparent
# 6. Iso E Super ~1.5% -- molecular cocoon
# 7. Ambrofix ~0.9% -- Demachy crystalline signature (boosted)
# 8. Ethyl Linalool ~0.65% -- floral-woody transparency
# 9. Vetival ~0.4% -- suede-mineral texture
# 10. Hedione HC ~0.18% -- radiance boost
# 11. EB ~0.16% -- lactonic body
# 12. Paradisamide ~0.014% -- tropical ghost
# 13. Norlimbanol ~0.009% -- architectural tenacity
# 14. Ambrettolide ~0.003% -- skin warmth whisper

# Target total OAV: ~20,000 for a well-balanced DHC
# The star citrus OAV target varies by material (different ODT/VP ratios)

# Per-variant citrus star OAV targets (what "50% of headspace" means for each):
citrus_targets = {
    "I Bergamot":   ("Bergamot FCF Sicilian", 10000),   # softer, refined
    "II Cedrat":    ("Cedrat FCF Sicilian",   10800),   # sharper, mineral
    "III Grapefruit": ("Grapefruit FCF",      14000),   # lowest ODT, punches hardest
    "IV Lime":      ("Lime Distilled EO",     10000),   # green-transparent
    "V Mandarin":   ("Red Mandarin EO",       11000),   # warm-golden
}

# Common base OAV targets (same across all 5 DHCs)
common_targets = {
    "Petitgrain EO":        5800,
    "Romandolide":          1200,
    "Iso E Super":          290,
    "Ambrofix":             185,
    "Hedione HC":           36,
    "Ethylene Brassylate":  33,
    "Vetival":              85,
    "Paradisamide":         2.8,
    "Norlimbanol Dextro":   1.8,
    "Ambrettolide":         0.5,
}

# Heart materials that vary per citrus (for structural balance):
# More volatile/loud citrus needs less Hedione & Linalyl Acetate support
# Softer citrus needs more
heart_variants = {
    "I Bergamot":   {"Hedione": 300, "Ethyl Linalool": 135, "Linalyl Acetate": 2700},
    "II Cedrat":    {"Hedione": 260, "Ethyl Linalool": 115, "Linalyl Acetate": 1800},
    "III Grapefruit": {"Hedione": 280, "Ethyl Linalool": 155, "Linalyl Acetate": 4000},
    "IV Lime":      {"Hedione": 260, "Ethyl Linalool": 120, "Linalyl Acetate": 1800},
    "V Mandarin":   {"Hedione": 260, "Ethyl Linalool": 115, "Linalyl Acetate": 2400},
}

print("=" * 95)
print("DHC OAV-FIRST REFORMULATION -- DEMACHY MASS-MARKET TARGETS")
print("uL = OAV_target * ODT_air(ppb) / VP(Pa) / 20")
print("=" * 95)

for dhc_name, (citrus_name, citrus_oav_target) in citrus_targets.items():
    print(f"\n{'-'*95}")
    print(f"  {dhc_name}  --  {citrus_name} star")
    print(f"{'-'*95}")
    print(f"  {'Material':<28} {'Target OAV':>10} {'VP(Pa)':>8} {'ODT(ppb)':>10} {'OAV%':>6} {'Active uL':>10} {'Dilution':>10} {'Raw uL':>10}")
    print(f"  {'-'*85}")

    # Build formula: citrus + heart variants + common base
    formula = []
    formula.append((citrus_name, citrus_oav_target, "neat", "top"))
    for mat, oav_t in heart_variants[dhc_name].items():
        formula.append((mat, oav_t, "neat", "heart"))
    for mat, oav_t in common_targets.items():
        layer = "heart" if mat in ("Hedione", "Ethyl Linalool", "Paradisamide") else "base"
        dil = "10%" if mat in ("Paradisamide", "Ambrettolide") else ("30%" if mat == "Ambrofix" else "neat")
        formula.append((mat, oav_t, dil, layer))

    total_oav = sum(o for _, o, _, _ in formula)
    total_ul = 0

    for mat, target_oav, dilution, layer in formula:
        d = mat_data[mat]
        active_ul = oav_to_ul(target_oav, d['vp'], d['odt_air'])
        if active_ul is None:
            print(f"  ! {mat}: missing VP or ODT data")
            continue

        # Raw uL from dilution
        dil_factor = 1.0
        if "10%" in dilution:
            dil_factor = 0.1
        elif "30%" in dilution:
            dil_factor = 0.3
        raw_ul = active_ul / dil_factor if dil_factor > 0 else active_ul

        oav_pct = target_oav / total_oav * 100
        total_ul += active_ul

        # Verify computed OAV matches target
        check_oav = ul_to_oav(active_ul, d['vp'], d['odt_air'])
        marker = ""
        if check_oav and abs(check_oav - target_oav) / target_oav > 0.01:
            marker = f" (actual={check_oav:.0f})"

        print(f"  {mat:<28} {target_oav:>10,.0f} {d['vp']:>8.4f} {d['odt_air']:>10.4f} {oav_pct:>5.1f}% {active_ul:>10.1f} {dilution:>10} {raw_ul:>10.1f}{marker}")

    # Layer summary
    top_sum = sum(o for m, o, _, l in formula if l == 'top')
    heart_sum = sum(o for m, o, _, l in formula if l == 'heart')
    base_sum = sum(o for m, o, _, l in formula if l == 'base')
    bt = base_sum / top_sum if top_sum else 0

    print(f"\n  Total OAV: {total_oav:,.0f}  |  T:{top_sum/total_oav*100:.0f}% H:{heart_sum/total_oav*100:.0f}% B:{base_sum/total_oav*100:.0f}%  |  B:T={bt:.2f}:1")
    print(f"  Total concentrate: {total_ul:.0f} uL active")

# Cross-comparison
print(f"\n\n{'='*95}")
print("  OAV CROSS-COMPARISON (ideal targets)")
print(f"{'='*95}")
print(f"  {'Metric':<28} {'I Bergamot':>14} {'II Cedrat':>14} {'III Grapefruit':>14} {'IV Lime':>14} {'V Mandarin':>14}")
print(f"  {'-'*82}")

for dhc_name in citrus_targets:
    c_name, c_oav = citrus_targets[dhc_name]
    h = heart_variants[dhc_name]
    all_oav = {c_name: c_oav, **h, **common_targets}
    total = sum(all_oav.values())
    top = c_oav
    heart = sum(h.values()) + common_targets.get("Paradisamide", 0)
    base = total - top - heart
    bt = base / top if top else 0

    print(f"  {dhc_name:<28} OAV={total:>8,.0f}  T={top/total*100:.0f}%  B:T={bt:.2f}:1")
    print(f"    Star: {c_name} OAV={c_oav:,} ({c_oav/total*100:.0f}%)")

print(f"\n{'='*95}")
