"""OAV + Score + Collaboration View for Jasmin d'Orris."""
import sys
sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.hedonic_model import HEDONIC_VALENCE
from engine.skin_interaction import SKIN_PHYSCHEM
from engine.perception.oav import oav

ODT_OVERRIDE = {
    "Myristic Acid Powder":  {"odt_eth": 1000.0, "odt_air": 5000.0},
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
    v = make_v1()
    for i, (name, ul, dil) in enumerate(v):
        if name == "Olibanum Resinoid":
            v[i] = ("Olibanum Resinoid 10%", 500, 10)
        if name == "Benzoin Resinoid":
            v[i] = ("Siam Benzoin 50%", 300, 50)
    return v

def make_v4():
    # Collaboration Edition — current state with 15% Myristic Acid stock
    v = []
    for name, ul, dil in make_v2():
        if name == "Paradisamide":
            continue
        if name == "Allyl Ionone":
            continue
        if name == "cis-Jasmone":
            v.append((name, 80, dil))
        elif name == "PEA":
            v.append((name, 180, dil))
        elif name == "Geraniol":
            v.append((name, 100, dil))
        elif name == "Myristic Acid Powder":
            v.append((name, 600, 15))  # 15% stock
        else:
            v.append((name, ul, dil))
    return v

def analyze(version, label):
    TOTAL_UL = sum(ul for _, ul, _ in version)
    active = sum(ul * dil / 100 for _, ul, dil in version)
    
    print(f"\n{'='*120}")
    print(f"  {label}")
    print(f"  Materials: {len(version)}  |  Concentrate: {TOTAL_UL} uL  |  Active: {active:.1f} uL ({active/TOTAL_UL*100:.1f}%)")
    print(f"{'='*120}")
    
    # Sections
    base_list = []; heart_list = []; top_list = []; struct_list = []
    for name, ul, dil in version:
        if name in ("Bergamot FCF oil Sicilian","Petitgrain EO","Cardamom EO","D-Limonene","Ethyl Safranate"):
            top_list.append((name, ul, dil))
        elif name in ("Benzyl Benzoate","Benzyl Salicylate","Hexyl Salicylate"):
            struct_list.append((name, ul, dil))
        elif name in ("Hedione","Jasmine Absolute","Hedione HC","Benzyl Acetate","cis-Jasmone","Dihydrojasmone","Gamma Undecalactone","Indole","Myristic Acid Powder","Orivone","Dihydro Beta Ionone","Alpha Isomethyl Ionone","Alpha Ionone","Alpha Irone","Ultralia","PEA","Geraniol","Rose Oxide","Alpha Damascone","Paradisamide","Allyl Ionone"):
            heart_list.append((name, ul, dil))
        else:
            base_list.append((name, ul, dil))
    
    for sec_name, items in [("TOP", top_list), ("HEART", heart_list), ("STRUCTURE", struct_list), ("BASE", base_list)]:
        sul = sum(ul for _, ul, _ in items)
        sact = sum(ul*dil/100 for _, ul, dil in items)
        print(f"  {sec_name:>12}: {sul:>5} uL  active={sact:>6.1f} uL")
    
    # OAV
    print(f"\n  {'OAV LEADERBOARD':^60}")
    print(f"  {'Material':<28} {'uL':>5} {'Dil%':>5} {'ODT_eth':>8} {'OAV':>10}")
    print(f"  {'-'*58}")
    
    oav_list = []
    for name, ul, dil in version:
        act = ul * dil / 100
        odt_eth, _ = get_odt(name)
        if odt_eth and odt_eth > 0:
            edp_ppm = act / TOTAL_UL * 1e6 * 0.294
            oav_val = edp_ppm / odt_eth
        else:
            oav_val = 0
        oav_list.append((name, ul, dil, act, odt_eth, oav_val))
    
    oav_list.sort(key=lambda x: -x[5])
    for name, ul, dil, act, odt, oav_val in oav_list:
        odt_s = f"{odt:.3f}" if odt else "N/A"
        print(f"  {name:<28} {ul:>5} {dil:>5}% {odt_s:>8} {oav_val:>10.0f}")
    
    # Metrics
    base_act = sum(ul*dil/100 for _, ul, dil in base_list)
    base_pct = base_act/active*100 if active else 0
    
    mw_vals = []
    for name, ul, dil in version:
        p = get_profile(name)
        act = ul*dil/100
        if p and p.mw: mw_vals.append((p.mw, act))
    w_mw = sum(m*a for m,a in mw_vals)/sum(a for _,a in mw_vals) if mw_vals else 0
    
    names_set = set(name for name,_,_ in version)
    pairs = set()
    for name in names_set:
        p = get_profile(name)
        if p and p.synergies:
            for syn in p.synergies:
                if syn in names_set:
                    pairs.add(tuple(sorted([name, syn])))
    
    hed_vals = []
    for name, ul, dil in version:
        h = HEDONIC_VALENCE.get(name, 0)
        if h != 0:
            hed_vals.append((h, ul*dil/100))
    w_hed = sum(h*a for h,a in hed_vals)/sum(a for _,a in hed_vals) if hed_vals else 0
    
    subst_vals = []
    for name, ul, dil in version:
        sd = SKIN_PHYSCHEM.get(name, {})
        if sd:
            subst_vals.append((sd.get("substantivity", 0.5), ul*dil/100))
    w_subst = sum(s*a for s,a in subst_vals)/sum(a for _,a in subst_vals) if subst_vals else 0.5
    
    ifra_issues = 0
    for name, ul, dil in version:
        limit = IFRA_CAT4_LIMITS.get(name)
        if limit:
            edp_pct = (ul*dil/100)/TOTAL_UL*29.4
            if edp_pct > limit:
                ifra_issues += 1
    
    textures = set()
    roles = set()
    for name in names_set:
        p = get_profile(name)
        if p:
            if p.texture: textures.add(p.texture)
            if p.role: roles.add(p.role)
    
    dims = {}
    for name in names_set:
        p = get_profile(name)
        if p:
            for d, s in p.character.items():
                if s >= 3: dims[d] = dims.get(d,0) + 1
    
    oav_vals = [x[5] for x in oav_list if x[5] > 0]
    oav_range = max(oav_vals)/min(oav_vals) if oav_vals else 0
    
    scores = {
        "longevity": min(9.5, 5 + base_pct/8),
        "sillage": min(9.5, 5 + base_pct/45*3),
        "synergy": min(9.5, 4 + len(pairs)*0.15),
        "luxury": min(9.5, 5 + sum(1 for m in {"Alpha Irone","Alpha Damascone","Jasmine Absolute","Musk Ketone","Javanol","Labdanum Absolute","Ultralia","Orivone","Hedione HC","cis-Jasmone"} if m in names_set)*0.3),
        "texture": min(9.5, 4 + len(textures)*0.7),
        "structure": min(9.5, 4 + len(roles)*0.6),
        "safety": 9.5 if ifra_issues==0 else 7.5 if ifra_issues==1 else 5,
        "skin_perf": min(9.5, 3 + w_subst*8),
        "hedonic": min(9.5, 5 + w_hed*4),
        "perceptual": min(9.5, 3 + len(dims)*0.4),
    }
    weights = {"longevity":0.8,"sillage":0.8,"synergy":0.5,"luxury":0.8,"texture":0.8,"structure":0.8,"safety":1.2,"skin_perf":0.7,"hedonic":0.5,"perceptual":0.6}
    total_w = sum(weights.values())
    comp = 1.0
    for a,s in scores.items(): comp *= s**(weights[a]/total_w)
    
    print(f"\n  {'SCORE':^58}")
    for a,s in scores.items():
        print(f"  {a:>12}: {s:.2f}  (x{weights[a]:.1f})")
    print(f"  {'COMPOSITE':>12}: {comp:.2f}/10")
    
    print(f"\n  Base: {base_pct:.0f}% | MW: {w_mw:.0f} | LogP: - | Pairs: {len(pairs)} | IFRA: {ifra_issues} issues")
    print(f"  Textures: {len(textures)} | Roles: {len(roles)} | Hedonic: {w_hed:+.2f} | Subs: {w_subst:.2f} | OAV range: {oav_range:,.0f}x")
    
    return comp, oav_list

# ── RUN ──
print("="*120)
print(f"{'JASMIN D\'ORRIS — FULL ANALYSIS':^120}")
print("="*120)

# V1 - Original
c1, o1 = analyze(make_v1(), "V1 — ORIGINAL (45 mat, neat Olibanum, Benzoin Resinoid)")
# V2 - Current
c2, o2 = analyze(make_v2(), "V2 — CURRENT (45 mat, Olibanum 10%, Siam Benzoin)")
# V4 - Collaboration (15% Myristic Acid stock)
c4, o4 = analyze(make_v4(), "V4 — COLLABORATION (43 mat, Myristic 15%, jasmone/Para/Allyl edits)")

# ── Collaboration view ──
print(f"\n{'='*120}")
print(f"{'COLLABORATION VIEW — What changed between V2 and V4':^120}")
print(f"{'='*120}")

# Find differences
v2_dict = {name: (ul, dil) for name, ul, dil in make_v2()}
v4_dict = {name: (ul, dil) for name, ul, dil in make_v4()}

changes = []
for name in set(list(v2_dict.keys()) + list(v4_dict.keys())):
    v2u, v2d = v2_dict.get(name, (0, 0))
    v4u, v4d = v4_dict.get(name, (0, 0))
    if v2u != v4u or v2d != v4d or (name in v2_dict) != (name in v4_dict):
        changes.append((name, v2u, v2d, v4u, v4d))

# Sort by type: removed, modified, added
removed = [(n, v2u, v2d) for n, v2u, v2d, v4u, v4d in changes if v4u == 0]
modified = [(n, v2u, v2d, v4u, v4d) for n, v2u, v2d, v4u, v4d in changes if v4u > 0 and v2u > 0]
added = [(n, v4u, v4d) for n, v2u, v2d, v4u, v4d in changes if v2u == 0]

print()
print("  REMOVED:")
for n, u, d in removed:
    act = u*d/100
    print(f"    {n:<28} was {u:>4} uL ({d:>3}%, {act:.1f} active)")
if not removed: print("    (none)")

print()
print("  MODIFIED:")
for n, v2u, v2d, v4u, v4d in modified:
    v2act = v2u*v2d/100
    v4act = v4u*v4d/100
    print(f"    {n:<28} {v2u:>4} uL ({v2d:>3}%) → {v4u:>4} uL ({v4d:>3}%)   active: {v2act:.1f} → {v4act:.1f} mg")

if added:
    print()
    print("  ADDED:")
    for n, u, d in added:
        print(f"    {n:<28} {u:>4} uL ({d:>3}%)")

print()
print(f"  SCORE: V1={c1:.2f} → V2={c2:.2f} → V4={c4:.2f}")

print()
print("="*120)
print("PERCEPTUAL DIFFERENCE (V2 vs V4 OAV leaderboard)")
print("="*120)
print(f"  {'Rank':<5} {'V2 Material':<28} {'V2 OAV':>8} | {'Rank':<5} {'V4 Material':<28} {'V4 OAV':>8}")
print(f"  {'-'*80}")
for i in range(max(len(o2), len(o4))):
    r2 = o2[i] if i < len(o2) else ("", 0, 0, 0, 0, 0)
    r4 = o4[i] if i < len(o4) else ("", 0, 0, 0, 0, 0)
    print(f"  {i+1:<5} {r2[0]:<28} {r2[5]:>8.0f} | {i+1:<5} {r4[0]:<28} {r4[5]:>8.0f}")

print()
print("="*120)
print("KEY OAV SHIFTS")
print("="*120)

# Compare OAV for key materials
for name in ["cis-Jasmone", "Alpha Ionone", "Alpha Irone", "PEA", "Geraniol", "Myristic Acid Powder"]:
    v2o = next((x[5] for x in o2 if x[0] == name), 0)
    v4o = next((x[5] for x in o4 if x[0] == name), 0)
    direction = "↑" if v4o > v2o else "↓" if v4o < v2o else "="
    print(f"  {name:<28}: {v2o:>8.0f} → {v4o:>8.0f}  {direction}")
