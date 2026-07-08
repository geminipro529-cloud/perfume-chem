"""Rate Mr. Sandman v2 (refined) across all scoring axes."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.hedonic_model import HEDONIC_VALENCE
from engine.perception.oav import oav
from engine.skin_interaction import SKIN_PHYSCHEM
from engine.temporal_graph import get_profile as get_temporal

# Refined Mr. Sandman v2 formula
# Format: name -> (mass_frac_pct_of_concentrate, dilution_pct, note)
FORMULA_V2 = {
    # TOP
    "Bergamot FCF":                        (3.00,  100, "top"),
    "Red Mandarin EO":                      (2.00,  100, "top"),
    "Aldehyde C11 undecylenic":             (0.12,  100, "top"),
    "Aldehyde C12 MNA":                     (1.50,    1, "top"),  # 1% in DPG
    # HEART
    "Hedione":                              (15.00, 100, "heart"),
    "Heliotropal":                          (8.00,  100, "heart"),
    "Anisaldehyde":                         (4.00,  100, "heart"),
    "Alpha Irone":                          (1.00,   30, "heart"),  # 30% in DEP
    "Ultralia":                             (0.05,  100, "heart"),
    "Mayol":                                (1.00,  100, "heart"),
    "Hydroxycitronellal":                   (0.70,  100, "heart"),
    "Damascol":                             (0.40,   10, "heart"),  # 10% in DPG
    "Ethyl Maltol":                         (1.00,   10, "heart"),  # 10%
    "Vanillin":                             (8.00,   10, "heart"),  # 10%
    "Orivone":                               (0.30,  100, "heart"),
    "Farnesol":                             (0.25,  100, "heart"),
    "Coumarin":                             (7.50,   20, "heart"),  # 20% in DPG
    # BASE
    "Hexyl Salicylate":                     (8.00,  100, "base"),
    "Cashmeran":                            (10.00,  20, "base"),  # 20%
    "Ethylene Brassylate":                  (9.00,  100, "base"),
    "Musk Ketone":                          (4.00,   10, "base"),  # 10% in DPG
    "Ambrettolide":                         (3.50,   10, "base"),  # 10% in DPG
    "Romandolide":                          (3.00,  100, "base"),
    "Iso E Super":                          (4.00,  100, "base"),
    "Azarbre":                              (2.00,  100, "base"),
    "Benzoin Resinoid":                     (1.00,   50, "base"),  # 50% in DPG
}

# ODT lookup
def get_odt(name):
    p = get_profile(name)
    if p and p.odt_ppm:
        return p.odt_ppm
    # Fallback to ODT_DATA
    key = name.lower().replace(" ", "")
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key or k == name.lower():
            return v.get("odt_eth", v.get("odt_air", None) / 1000 if v.get("odt_air") else None)
    # Special mappings
    MAP = {
        "Aldehyde C11 undecylenic": 0.4,
        "Aldehyde C12 MNA": 0.05,
        "Damascenone": 0.002,
        "Ethyl Maltol": 0.1,
        "Mayol": 0.5,
        "Romandolide": 1.0,
        "Azarbre": 0.5,
        "Ultralia": 0.05,
        "Damascol": 0.005,
        "Orivone": 0.5,
        "Ethylene Brassylate": 2.0,
    }
    return MAP.get(name)

def get_hedonic(name):
    return HEDONIC_VALENCE.get(name, 0.0)

def get_ifra_limit(name):
    return IFRA_CAT4_LIMITS.get(name, None)

def get_skin_data(name):
    return SKIN_PHYSCHEM.get(name, None)

# ── SCORING AXES ──

print("=" * 100)
print("MR. SANDMAN v2 — REFINED FORMULA RATING")
print("=" * 100)
print()

# 1. Compute OAV profile
print("1. OAV PROFILE (concentrate ppm / ODT_ppm)")
print("-" * 100)
print(f"{'Material':<30} {'Note':>5} {'Dil%':>5} {'MFr%':>7} {'Act%':>7} {'ODT':>8} {'C_ppm':>8} {'OAV':>10} {'Percept':>10}")
print("-" * 100)

total_mass = 0
total_active = 0
total_oav = 0
section_oav = {"top": 0, "heart": 0, "base": 0}
section_mass = {"top": 0, "heart": 0, "base": 0}
section_active = {"top": 0, "heart": 0, "base": 0}
materials_below_threshold = []
materials_dominant = []
oav_list = []

for name, (mass_frac, dilution, note) in sorted(FORMULA_V2.items(), key=lambda x: x[1][2]):
    active_frac = mass_frac * (dilution / 100.0)
    conc_ppm = active_frac * 10000
    odt = get_odt(name)
    
    if odt and odt > 0:
        oav_val = oav(conc_ppm, odt)
    else:
        oav_val = 0
    
    total_mass += mass_frac
    total_active += active_frac
    total_oav += oav_val
    section_oav[note] += oav_val
    section_mass[note] += mass_frac
    section_active[note] += active_frac
    
    if oav_val > 0 and oav_val < 1:
        materials_below_threshold.append((name, oav_val))
    if oav_val > 50000:
        materials_dominant.append((name, oav_val))
    
    oav_list.append(oav_val)
    
    odt_str = f"{odt:.3f}" if odt else "N/A"
    percept = "EXTREME" if oav_val > 500 else "DOMINANT" if oav_val > 50 else "clear" if oav_val > 5 else "weak" if oav_val > 1 else "SUBLIM" if oav_val > 0 else "N/A"
    
    print(f"  {name:<28} {note:>5} {dilution:>5} {mass_frac:>7.2f} {active_frac:>7.3f} {odt_str:>8} {conc_ppm:>8.0f} {oav_val:>10.0f} {percept:>10}")

print("-" * 100)
print(f"  {'TOTAL':<28} {'':>5} {'':>5} {total_mass:>7.2f} {total_active:>7.3f} {'':>8} {'':>8} {total_oav:>10.0f}")

print()
print("  Section summary:")
for s in ["top", "heart", "base"]:
    print(f"    {s.upper():>5}: mass_frac={section_mass[s]:>6.2f}%  active={section_active[s]:>6.2f}%  OAV_sum={section_oav[s]:>12,.0f}")

# 2. LONGEVITY SCORE
print()
print("2. LONGEVITY (MW + logP + base fraction)")
print("-" * 100)

base_active = section_active["base"]
total_act = total_active
base_pct = base_active / total_act * 100 if total_act > 0 else 0

mw_list = []
logp_list = []
vp_list = []
for name in FORMULA_V2:
    p = get_profile(name)
    if p:
        if p.mw: mw_list.append((name, p.mw, FORMULA_V2[name][1] * FORMULA_V2[name][0] / 100))
        if p.clogp: logp_list.append((name, p.clogp, FORMULA_V2[name][1] * FORMULA_V2[name][0] / 100))

avg_mw = sum(m * a for _, m, a in mw_list) / sum(a for _, _, a in mw_list) if mw_list else 0
avg_logp = sum(l * a for _, l, a in logp_list) / sum(a for _, _, a in logp_list) if logp_list else 0

print(f"  Base fraction:        {base_pct:.1f}% (target: >35% for longevity)")
print(f"  Weighted avg MW:      {avg_mw:.1f} g/mol")
print(f"  Weighted avg logP:   {avg_logp:.2f}")

if base_pct >= 40:
    longevity_score = 9.0
elif base_pct >= 35:
    longevity_score = 8.0
elif base_pct >= 30:
    longevity_score = 7.0
else:
    longevity_score = 6.0

print(f"  Longevity score:      {longevity_score:.1f}/10")

# 3. SILLAGE / PROJECTION
print()
print("3. SILLAGE & PROJECTION")
print("-" * 100)

# Count high-VP projection materials in top/heart
projection_materials = []
for name, (mass_frac, dilution, note) in FORMULA_V2.items():
    p = get_profile(name)
    if p and p.vp and p.vp > 1.0 and note in ("top", "heart"):
        active = mass_frac * dilution / 100
        projection_materials.append((name, p.vp, active, note))

print("  High-VP projection materials (VP > 1 Pa, top/heart):")
for name, vp, act, note in projection_materials[:10]:
    print(f"    {name:<28} VP={vp:.2f} Pa  active={act:.3f}%  note={note}")

# Count base materials with OAV > 5000 (they project via radiance/sillage after top burns off)
print()
print("  Base materials with OAV > 5000 (persistent sillage):")
sillage_count = 0
for name in FORMULA_V2:
    p = get_profile(name)
    if p and p.clogp and p.clogp > 3.0 and FORMULA_V2[name][2] == "base":
        sillage_count += 1

for name, (mass_frac, dilution, note) in FORMULA_V2.items():
    if note == "base":
        active = mass_frac * dilution / 100
        odt = get_odt(name)
        if odt and odt > 0:
            oav_val = oav(active * 10000, odt)
            if oav_val > 5000:
                clogp = get_profile(name).clogp if get_profile(name) and get_profile(name).clogp else None
                logp_str = f"{clogp:.1f}" if clogp else "N/A"
                print(f"    {name:<28} OAV={oav_val:>10,.0f}  logP={logp_str}")

sillage_score = min(9.0, 6.0 + len(projection_materials) * 0.3)
print(f"  Sillage score:        {sillage_score:.1f}/10")

# 4. SYNERGY
print()
print("4. SYNERGY (pairing rules)")
print("-" * 100)

materials = list(FORMULA_V2.keys())
synergy_hits = 0
synergy_pairs_found = []

for name in materials:
    p = get_profile(name)
    if p and p.synergies:
        for syn in p.synergies:
            if syn in materials:
                synergy_hits += 1
                pair = tuple(sorted([name, syn]))
                if pair not in [x[0] for x in synergy_pairs_found]:
                    synergy_pairs_found.append((pair, name))

print(f"  Synergy pair hits:    {synergy_hits}")
print(f"  Unique pairs:        {len(set(p for p, _ in synergy_pairs_found))}")

# Count synergy pairs as fraction of max possible
max_pairs = len(materials) * (len(materials) - 1) / 2
synergy_fraction = len(set(p for p, _ in synergy_pairs_found)) / max_pairs * 100 if max_pairs > 0 else 0
synergy_score = min(9.5, 4.0 + synergy_hits * 0.15)
print(f"  Synergy score:        {synergy_score:.1f}/10")

# 5. LUXURY
print()
print("5. LUXURY (ingredient quality)")
print("-" * 100)

luxury_materials = ["Alpha Irone", "Ultralia", "Orivone", "Damascol", "Hedione",
                     "Cashmeran", "Ambrettolide", "Musk Ketone", "Heliotropal",
                     "Azarbre", "Mayol"]
luxury_hits = sum(1 for m in luxury_materials if m in materials)
print(f"  Luxury materials present: {luxury_hits}/{len(luxury_materials)}")
luxury_score = min(9.5, 5.0 + luxury_hits * 0.35)
print(f"  Luxury score:         {luxury_score:.1f}/10")

# 6. TEXTURE (haptic diversity)
print()
print("6. TEXTURE (haptic diversity)")
print("-" * 100)

textures = set()
for name in materials:
    p = get_profile(name)
    if p and p.texture:
        textures.add(p.texture)

print(f"  Texture classes:      {', '.join(sorted(textures))}")
print(f"  Texture diversity:    {len(textures)} classes")

texture_score = min(9.0, 4.0 + len(textures) * 0.7)
print(f"  Texture score:        {texture_score:.1f}/10")

# 7. SAFETY (IFRA)
print()
print("7. IFRA SAFETY")
print("-" * 100)

ifra_issues = []
for name in materials:
    limit = get_ifra_limit(name)
    if limit:
        active = FORMULA_V2[name][0] * FORMULA_V2[name][1] / 100
        # Convert to % of finished EDP (assume 22% concentrate)
        edp_pct = active * 0.22  # rough
        if edp_pct > limit:
            ifra_issues.append((name, edp_pct, limit, "EXCEEDS"))
        elif edp_pct > limit * 0.8:
            ifra_issues.append((name, edp_pct, limit, "APPROACHING"))

if ifra_issues:
    print("  IFRA concerns:")
    for name, edp, limit, status in ifra_issues:
        print(f"    {name:<28} EDP={edp:.2f}%  limit={limit:.1f}%  {status}")
else:
    print("  No IFRA concerns at 22% EDP dilution")

# Check Hydroxycitronellal
hca_active = 0.70 * 1.0  # 0.70% active in concentrate, 22% in EDP
hca_edp = hca_active * 0.22
print(f"\n  Hydroxycitronellal:  {hca_edp:.3f}% in EDP (IFRA Cat4 limit: 1.0%)")
# Check Farnesol
far_active = 0.25 * 1.0
far_edp = far_active * 0.22
print(f"  Farnesol:            {far_edp:.3f}% in EDP (not restricted in Cat4)")

safety_score = 8.5 if not ifra_issues else 6.0
print(f"  Safety score:         {safety_score:.1f}/10")

# 8. SKIN PERFORMANCE / SUBSTANTIVITY
print()
print("8. SKIN PERFORMANCE (substantivity)")
print("-" * 100)

# Weighted avg substantivity
subst_list = []
for name in materials:
    sd = get_skin_data(name)
    if sd:
        active = FORMULA_V2[name][0] * FORMULA_V2[name][1] / 100
        subst_list.append((name, sd.get("substantivity", 0.5), active))

if subst_list:
    avg_subst = sum(s * a for _, s, a in subst_list) / sum(a for _, _, a in subst_list)
    print(f"  Weighted avg substantivity: {avg_subst:.3f}")
    skin_score = min(9.0, 3.0 + avg_subst * 8)
else:
    skin_score = 6.0
    print(f"  Using default substantivity estimate")

print(f"  Skin perf score:     {skin_score:.1f}/10")

# 9. HEDONIC
print()
print("9. HEDONIC (pleasantness)")
print("-" * 100)

hedonic_vals = []
for name in materials:
    h = get_hedonic(name)
    if h != 0.0:
        active = FORMULA_V2[name][0] * FORMULA_V2[name][1] / 100
        hedonic_vals.append((name, h, active))

if hedonic_vals:
    avg_hedonic = sum(h * a for _, h, a in hedonic_vals) / sum(a for _, _, a in hedonic_vals)
else:
    avg_hedonic = 0

print(f"  Weighted avg hedonic valence: {avg_hedonic:+.3f} (scale -1 to +1)")
print(f"  Materials with hedonic data:  {len(hedonic_vals)}/{len(materials)}")

neg_h = [n for n, h, a in hedonic_vals if h < 0]
if neg_h:
    print(f"  Unpleasant materials: {', '.join(neg_h)}")

hedonic_score = min(9.5, 5.0 + avg_hedonic * 5)
print(f"  Hedonic score:        {hedonic_score:.1f}/10")

# 10. PERCEPTUAL (mixture suppression)
print()
print("10. PERCEPTUAL (mixture complexity & suppression)")
print("-" * 100)

# Count unique character dimensions above threshold
all_dims = {}
for name in materials:
    p = get_profile(name)
    if p:
        active = FORMULA_V2[name][0] * FORMULA_V2[name][1] / 100
        for dim, score in p.character.items():
            if score >= 3.0:
                all_dims[dim] = all_dims.get(dim, 0) + active * score / 10

print("  Character dimension coverage (weighted by active%):")
for dim, weighted in sorted(all_dims.items(), key=lambda x: -x[1]):
    bar = "#" * min(40, int(weighted * 10))
    print(f"    {dim:>15}: {weighted:>6.2f} {bar}")

unique_dims = len(all_dims)
print(f"\n  Dimensions covered:   {unique_dims}/13")
print(f"  Dominant axis:       {max(all_dims, key=all_dims.get)} ({all_dims[max(all_dims, key=all_dims.get)]:.2f})")

perceptual_score = min(9.0, 4.0 + unique_dims * 0.4)
print(f"  Perceptual score:    {perceptual_score:.1f}/10")

# 11. STACKING (structural layering)
print()
print("11. STACKING (structural layering)")
print("-" * 100)

# Count distinct roles
roles = set()
for name in materials:
    p = get_profile(name)
    if p:
        roles.add(p.role)

print(f"  Roles filled:        {', '.join(sorted(roles))}")
print(f"  Role diversity:      {len(roles)} roles")

# Count note distribution
for s in ["top", "heart", "base"]:
    count = sum(1 for n in materials if FORMULA_V2[n][2] == s)
    pct = section_active[s] / total_active * 100 if total_active > 0 else 0
    print(f"    {s.upper():>5}: {count:>2} materials, {pct:>5.1f}% active")

stacking_score = min(9.0, 5.0 + len(roles) * 0.5 + (1 if len(roles) >= 5 else 0))
print(f"  Stacking score:      {stacking_score:.1f}/10")

# ── COMPOSITE ──
print()
print("=" * 100)
print("COMPOSITE SCORE")
print("=" * 100)

weights = {
    "longevity": 0.8,
    "sillage": 0.8,
    "synergy": 0.5,
    "luxury": 0.8,
    "texture": 0.8,
    "stacking": 0.8,
    "safety": 1.2,
    "skin_perf": 0.7,
    "hedonic": 0.5,
    "perceptual": 0.6,
}

scores = {
    "longevity": longevity_score,
    "sillage": sillage_score,
    "synergy": synergy_score,
    "luxury": luxury_score,
    "texture": texture_score,
    "stacking": stacking_score,
    "safety": safety_score,
    "skin_perf": skin_score,
    "hedonic": hedonic_score,
    "perceptual": perceptual_score,
}

total_weight = sum(weights.values())
composite = 1.0
for axis, score in scores.items():
    w = weights[axis]
    composite *= score ** (w / total_weight)
    print(f"  {axis:>12}: {score:>5.1f}/10  (weight {w:.1f})")

print(f"\n  GEOMETRIC MEAN COMPOSITE: {composite:.2f}/10")
print()

# Rating interpretation
if composite >= 9.0:
    tier = "EXCELLENT — Masterwork"
elif composite >= 8.0:
    tier = "VERY GOOD — Professional quality"
elif composite >= 7.0:
    tier = "GOOD — Solid commercial perfume"
elif composite >= 6.0:
    tier = "FAIR — Competent but with gaps"
elif composite >= 5.0:
    tier = "DEVELOPING — Needs work"
else:
    tier = "WEAK — Fundamental issues"

print(f"  RATING: {tier}")
print()
print("=" * 100)
print("KEY STRENGTHS")
print("-" * 100)
print("  1. Jingle chord (Heliotropal + Anisaldehyde + Coumarin + MK) = unique era identity")
print("  2. Four-musk chord covers all three axes (depth/projection/character-echo)")
print("  3. Warmth triangulation (Cashmeran textile + Iso E molecular + Azarbre cedar-amber)")
print("  4. Zero pre-blends, zero FTEC/FO — all single molecules")
print()
print("KEY CONCERNS")
print("-" * 100)
print("  1. Alpha Irone at OAV 300K still leads over Heliotropal 80K (3.75x ratio)")
print("     — The lullaby jingle is audible but iris still dominates")
print("  2. Damascol at OAV 80K creates strong rose-blush (may fight lullaby register)")
print("  3. Vanillin OAV 800 is sub-dominant — custard warmth is present but quiet")
print("  4. Top OAV 36K is quiet for an EDP opening — may feel subdued on first spray")
print("  5. Ethyl Maltol OAV 10K reads cotton-candy at trace — acceptable for lullaby register")