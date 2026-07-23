"""Score all three versions of Jasmin d'Orris side by side."""
import sys

sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.hedonic_model import HEDONIC_VALENCE
from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.skin_interaction import SKIN_PHYSCHEM

# ODT overrides for materials not in system
ODT_OVERRIDE = {
    "Myristic Acid Powder":  {"odt_eth": 10.0, "odt_air": 50.0},
    "Olibanum Resinoid":      {"odt_eth": 2.0,  "odt_air": 10.0},
    "Labdanum Absolute":      {"odt_eth": 0.5,  "odt_air": 2.0},
    "Jasmine Absolute":       {"odt_eth": 0.5,  "odt_air": 2.0},
    "Cardamom EO":            {"odt_eth": 1.0,  "odt_air": 5.0},
    "Petitgrain EO":          {"odt_eth": 1.0,  "odt_air": 5.0},
    "Hedione HC":             {"odt_eth": 3.0,  "odt_air": 20.0},
    "Paradisamide":           {"odt_eth": 0.5,  "odt_air": 3.0},
    "Dihydrojasmone":         {"odt_eth": 3.0,  "odt_air": 15.0},
    "Dihydro Beta Ionone":    {"odt_eth": 0.5,  "odt_air": 3.0},
    "Cedarwood EO":           {"odt_eth": 3.0,  "odt_air": 15.0},
    "Ebanol":                 {"odt_eth": 1.5,  "odt_air": 8.0},
    "Vertofix":               {"odt_eth": 2.0,  "odt_air": 10.0},
    "Sandalore":              {"odt_eth": 1.0,  "odt_air": 5.0},
    "Javanol":                {"odt_eth": 0.5,  "odt_air": 3.0},
    "Allyl Ionone":           {"odt_eth": 0.5,  "odt_air": 3.0},
    "Ethyl Safranate":        {"odt_eth": 0.5,  "odt_air": 3.0},
    "Olibanum Resinoid 10%":  {"odt_eth": 0.2,  "odt_air": 1.0},
    "Siam Benzoin 50%":       {"odt_eth": 10.0, "odt_air": 50.0},
}

def get_odt(name):
    p = get_profile(name)
    odt_eth = None; odt_air = None
    if p:
        if p.odt_ppm: odt_eth = p.odt_ppm
        if p.odt: odt_air = p.odt
    key = name.lower().replace(" ", "")
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key:
            if not odt_eth: odt_eth = v.get("odt_eth")
            if not odt_air: odt_air = v.get("odt_air")
            break
    if name in ODT_OVERRIDE:
        d = ODT_OVERRIDE[name]
        if not odt_eth: odt_eth = d.get("odt_eth")
        if not odt_air: odt_air = d.get("odt_air")
    return odt_eth, odt_air

# ── Define three versions ──
# Format: (material, uL, dilution_pct)
def make_v1():
    return [
        ("Iso E Super", 800, 100), ("Cedarwood EO", 500, 100),
        ("Benzoin Resinoid", 300, 50), ("Romandolide", 250, 100),
        ("Olibanum Resinoid", 200, 100), ("Ethylene Brassylate", 200, 100),
        ("Ebanol", 180, 100), ("Musk Ketone", 180, 10),
        ("Cashmeran", 120, 100), ("Sandalore", 120, 100),
        ("Patchouli EO", 100, 100), ("Labdanum Absolute", 100, 10),
        ("Vertofix", 80, 100), ("Azarbre", 60, 100),
        ("Kephalis", 50, 100), ("Javanol", 40, 100),
        ("Hedione", 1200, 100), ("Jasmine Absolute", 600, 10),
        ("Hedione HC", 600, 100), ("Myristic Acid Powder", 600, 1),
        ("Benzyl Acetate", 200, 100), ("Orivone", 180, 100),
        ("cis-Jasmone", 150, 100), ("Dihydro Beta Ionone", 150, 100),
        ("Dihydrojasmone", 120, 100), ("Alpha Isomethyl Ionone", 120, 100),
        ("PEA", 100, 100), ("Gamma Undecalactone", 100, 100),
        ("Alpha Ionone", 100, 100), ("Geraniol", 60, 100),
        ("Allyl Ionone", 40, 100), ("Paradisamide", 30, 10),
        ("Alpha Irone", 25, 30), ("Indole", 25, 10),
        ("Ultralia", 20, 100), ("Rose Oxide", 10, 1),
        ("Alpha Damascone", 4, 10),
        ("Benzyl Benzoate", 400, 100), ("Benzyl Salicylate", 250, 100),
        ("Hexyl Salicylate", 180, 100),
        ("Bergamot FCF oil Sicilian", 300, 100), ("Petitgrain EO", 100, 100),
        ("Cardamom EO", 80, 100), ("D-Limonene", 60, 100),
        ("Ethyl Safranate", 15, 100),
    ]

def make_v2():
    # Current file version
    v = make_v1()
    for i, (name, ul, dil) in enumerate(v):
        if name == "Olibanum Resinoid":
            v[i] = ("Olibanum Resinoid 10%", 500, 10)
        if name == "Benzoin Resinoid":
            v[i] = ("Siam Benzoin 50%", 300, 50)
    return v

def make_v3():
    # Collaboration Edition
    v = []
    for name, ul, dil in make_v2():
        if name == "Paradisamide":
            continue  # dropped
        if name == "Allyl Ionone":
            continue  # dropped
        if name == "cis-Jasmone":
            v.append((name, 80, dil))  # cut
        elif name == "PEA":
            v.append((name, 180, dil))  # boosted
        elif name == "Geraniol":
            v.append((name, 100, dil))  # boosted
        elif name == "Myristic Acid Powder":
            v.append((name, 600, 2))  # 2% stock
        else:
            v.append((name, ul, dil))
    return v

def score_version(version, label):
    TOTAL_UL = sum(ul for _, ul, _ in version)
    print(f"\n{'='*100}")
    print(f"  {label}")
    print(f"{'='*100}")

    # OAV computation
    active = sum(ul * dil / 100 for _, ul, dil in version)
    print(f"  Materials:  {len(version)}")
    print(f"  Concentrate: {TOTAL_UL} uL")
    print(f"  Active:     {active:.0f} uL ({active/TOTAL_UL*100:.1f}%)")

    # Section breakdown
    sections = {"top": [], "heart": [], "base": [], "structure": []}
    section_map = {}
    for name, ul, dil in version:
        if name in ("Bergamot FCF oil Sicilian","Petitgrain EO","Cardamom EO","D-Limonene","Ethyl Safranate"):
            s = "top"
        elif name in ("Benzyl Benzoate","Benzyl Salicylate","Hexyl Salicylate"):
            s = "structure"
        elif name in ("Hedione","Jasmine Absolute","Hedione HC","Benzyl Acetate","cis-Jasmone","Dihydrojasmone","Gamma Undecalactone","Paradisamide","Indole","Myristic Acid Powder","Orivone","Dihydro Beta Ionone","Alpha Isomethyl Ionone","Alpha Ionone","Allyl Ionone","Alpha Irone","Ultralia","PEA","Geraniol","Rose Oxide","Alpha Damascone","Phenethyl Alcohol"):
            s = "heart"
        else:
            s = "base"
        sections[s].append((name, ul, dil))
        section_map[name] = s

    for s in ["top","heart","structure","base"]:
        sul = sum(ul for _, ul, _ in sections[s])
        sact = sum(ul*dil/100 for _, ul, dil in sections[s])
        print(f"    {s.upper():>9}: {sul:>5} uL, {sact:>6.1f} active")

    # OAV analysis
    print("\n  OAV Profile (top 10 + bottom 3):")
    print(f"  {'Material':<28} {'uL':>5} {'Act%':>6} {'ODT_eth':>8} {'OAV':>10}")
    print(f"  {'-'*60}")

    oav_list = []
    for name, ul, dil in version:
        act = ul * dil / 100
        odt_eth, _ = get_odt(name)
        if odt_eth and odt_eth > 0:
            # EDP ppm = act/TOTAL_UL * 1e6 * 0.29
            edp_ppm = act / TOTAL_UL * 1e6 * 0.294
            oav_val = edp_ppm / odt_eth
        else:
            oav_val = 0
        oav_list.append((name, ul, dil, act, odt_eth, oav_val))

    oav_list.sort(key=lambda x: -x[5])
    for name, ul, dil, act, odt, oav_val in oav_list[:10]:
        odt_s = f"{odt:.3f}" if odt else "N/A"
        print(f"  {name:<28} {ul:>5} {dil:>5}% {odt_s:>8} {oav_val:>10.0f}")

    bottom = [x for x in oav_list if x[5] > 0 and x[5] < 50]
    if bottom:
        print(f"  {'(quietest)':>50}")
        for name, ul, dil, act, odt, oav_val in bottom[:3]:
            odt_s = f"{odt:.3f}" if odt else "N/A"
            print(f"  {name:<28} {ul:>5} {dil:>5}% {odt_s:>8} {oav_val:>10.1f}")

    # 1. LONGEVITY
    base_act = sum(ul*dil/100 for _, ul, dil in sections["base"])
    total_act = active
    base_pct = base_act / total_act * 100 if total_act > 0 else 0

    mw_vals = []
    logp_vals = []
    for name, ul, dil in version:
        p = get_profile(name)
        act = ul * dil / 100
        if p and p.mw:
            mw_vals.append((p.mw, act))
        if p and p.clogp:
            logp_vals.append((p.clogp, act))

    w_mw = sum(m*a for m, a in mw_vals) / sum(a for _, a in mw_vals) if mw_vals else 0
    w_logp = sum(l*a for l, a in logp_vals) / sum(a for _, a in logp_vals) if logp_vals else 0

    # 2. SYNERGY
    names_in_formula = set(name for name, _, _ in version)
    synergy_hits = 0
    pairs = set()
    for name in names_in_formula:
        p = get_profile(name)
        if p and p.synergies:
            for syn in p.synergies:
                if syn in names_in_formula:
                    synergy_hits += 1
                    pairs.add(tuple(sorted([name, syn])))

    # 3. LUXURY
    luxury_set = {"Alpha Irone","Alpha Damascone","Jasmine Absolute","Musk Ketone",
                  "Javanol","Labdanum Absolute","Olibanum Resinoid","Olibanum Resinoid 10%",
                  "Siam Benzoin 50%","Benzoin Resinoid","Ultralia","Orivone",
                  "Hedione HC","cis-Jasmone"}
    luxury_hits = sum(1 for m in luxury_set if m in names_in_formula)

    # 4. TEXTURE
    textures = set()
    for name in names_in_formula:
        p = get_profile(name)
        if p and p.texture:
            textures.add(p.texture)

    # 5. ROLES
    roles = set()
    for name in names_in_formula:
        p = get_profile(name)
        if p and p.role:
            roles.add(p.role)

    # 6. HEDONIC
    hedonic_vals = []
    for name, ul, dil in version:
        h = HEDONIC_VALENCE.get(name, 0)
        if h != 0:
            act = ul * dil / 100
            hedonic_vals.append((h, act))
    avg_hedonic = sum(h*a for h, a in hedonic_vals) / sum(a for _, a in hedonic_vals) if hedonic_vals else 0

    # 7. SKIN
    subst_vals = []
    for name, ul, dil in version:
        sd = SKIN_PHYSCHEM.get(name, {})
        if sd:
            act = ul * dil / 100
            subst_vals.append((sd.get("substantivity", 0.5), act))
    avg_subst = sum(s*a for s, a in subst_vals) / sum(a for _, a in subst_vals) if subst_vals else 0.5

    # 8. IFRA
    ifra_issues = 0
    for name, ul, dil in version:
        limit = IFRA_CAT4_LIMITS.get(name)
        if limit:
            edp_pct = (ul * dil / 100) / TOTAL_UL * 29.4
            if edp_pct > limit:
                ifra_issues += 1

    # 9. CHARACTER DIMENSIONS
    dims = {}
    for name in names_in_formula:
        p = get_profile(name)
        if p:
            for dim, score in p.character.items():
                if score >= 3:
                    dims[dim] = dims.get(dim, 0) + 1

    # 10. PERCEPTUAL (OAV dynamic range)
    oav_values = [x[5] for x in oav_list if x[5] > 0]
    if oav_values:
        oav_range = max(oav_values) / min(oav_values) if min(oav_values) > 0 else 0
    else:
        oav_range = 0

    # ── SCORES ──
    longevity = min(9.5, 5 + base_pct / 8)
    synergy = min(9.5, 4 + len(pairs) * 0.15)
    luxury = min(9.5, 5 + luxury_hits * 0.3)
    texture = min(9.5, 4 + len(textures) * 0.7)
    roles_score = min(9.5, 4 + len(roles) * 0.6)
    hedonic = min(9.5, 5 + avg_hedonic * 4)
    skin_score = min(9.5, 3 + avg_subst * 8)
    safety = 9.5 if ifra_issues == 0 else 7.5 if ifra_issues == 1 else 5
    perceptual = min(9.5, 3 + len(dims) * 0.4)
    sillage = min(9.5, 5 + (base_pct/45)*3)

    weights = {
        "longevity": 0.8, "sillage": 0.8, "synergy": 0.5,
        "luxury": 0.8, "texture": 0.8, "structure": 0.8,
        "safety": 1.2, "skin_perf": 0.7, "hedonic": 0.5, "perceptual": 0.6
    }
    scores = {
        "longevity": longevity, "sillage": sillage, "synergy": synergy,
        "luxury": luxury, "texture": texture, "structure": roles_score,
        "safety": safety, "skin_perf": skin_score, "hedonic": hedonic, "perceptual": perceptual
    }

    total_w = sum(weights.values())
    composite = 1.0
    for axis, s in scores.items():
        w = weights[axis]
        composite *= s ** (w / total_w)

    print("\n  SCORING:")
    for axis, s in scores.items():
        w = weights[axis]
        print(f"    {axis:>12}: {s:.2f}  (x{w:.1f})")
    print(f"    {'COMPOSITE':>12}: {composite:.2f}/10")

    print("\n  METRICS:")
    print(f"    Base fraction:  {base_pct:.0f}%")
    print(f"    Avg MW:        {w_mw:.0f} g/mol")
    print(f"    Avg logP:       {w_logp:.2f}")
    print(f"    Synergy pairs:  {len(pairs)}")
    print(f"    Luxury hits:   {luxury_hits}/{len(luxury_set)}")
    print(f"    Textures:      {len(textures)} ({', '.join(sorted(list(textures)[:5]))})")
    print(f"    Roles:         {len(roles)}")
    print(f"    Hedonic avg:   {avg_hedonic:+.2f}")
    print(f"    Substantivity: {avg_subst:.2f}")
    print(f"    IFRA issues:   {ifra_issues}")
    print(f"    OAV range:     {oav_range:,.0f}x (max/min)")
    print(f"    Dims covered:  {len(dims)}/13")

    return composite, scores, len(version), base_pct

print("=" * 100)
print(f"{'JASMIN D\'ORRIS — VERSION COMPARISON':^100}")
print("=" * 100)

v1_score, v1_s, v1_mat, v1_base = score_version(make_v1(), "V1 — ORIGINAL (Olibanum neat, Benzoin Resinoid 50%)")
v2_score, v2_s, v2_mat, v2_base = score_version(make_v2(), "V2 — CURRENT (Olibanum 10%, Siam Benzoin 50%)")
v3_score, v3_s, v3_mat, v3_base = score_version(make_v3(), "V3 — COLLABORATION (Amouage x HJ compromise)")

print(f"\n{'='*100}")
print(f"{'HEAD-TO-HEAD':^100}")
print(f"{'='*100}")
print(f"{'Axis':<15} {'V1 Original':>12} {'V2 Current':>12} {'V3 Collab':>12}")
print(f"{'-'*55}")
for axis in v1_s:
    print(f"{axis:<15} {v1_s[axis]:>12.2f} {v2_s[axis]:>12.2f} {v3_s[axis]:>12.2f}")
print(f"{'-'*55}")
print(f"{'COMPOSITE':<15} {v1_score:>12.2f} {v2_score:>12.2f} {v3_score:>12.2f}")
print()
print(f"{'Materials':<15} {v1_mat:>12} {v2_mat:>12} {v3_mat:>12}")
print(f"{'Base %':<15} {v1_base:>11.0f}% {v2_base:>11.0f}% {v3_base:>11.0f}%")
print()
print("COLLABORATION vs CURRENT:")
for axis in v3_s:
    diff = v3_s[axis] - v2_s[axis]
    sym = "+" if diff > 0 else ""
    print(f"  {axis:<15}: {diff:+.2f}")
print(f"  {'COMPOSITE':<15}: {v3_score - v2_score:+.2f}")
