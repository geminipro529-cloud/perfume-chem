"""Score Mr. Sandman YSL — 10-axis + brand perspectives."""
import sys

sys.path.insert(0, r'D:\chatbots\perfume-chem')

from engine.hedonic_model import HEDONIC_VALENCE
from engine.ifra_safety import IFRA_CAT4_LIMITS
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.skin_interaction import SKIN_PHYSCHEM

ODT_OVERRIDE = {
    "Cardamom EO":           {"odt_eth": 1.0},
    "Vertofix":              {"odt_eth": 2.0},
}

def get_odt(name):
    key = name.lower().replace(" ", "")
    for k, v in ODT_DATA.items():
        if k.replace(" ", "") == key:
            return v.get("odt_eth")
    if name in ODT_OVERRIDE:
        return ODT_OVERRIDE[name].get("odt_eth")
    p = get_profile(name)
    if p and p.odt_ppm: return p.odt_ppm
    return None

# YSL Formula: (name, uL, dilution_pct)
FORMULA = [
    ("Bergamot FCF oil Sicilian", 487, 100),
    ("Aldehyde C11 undecylenic",   75, 100),
    ("Aldehyde C12 MNA",          412,   1),
    ("Red Mandarin EO",           250, 100),
    ("Cardamom EO",                56, 100),
    ("Hedione",                  1500, 100),
    ("Hedione HC",                375, 100),
    ("Heliotropal",               650, 100),
    ("Anisaldehyde",              325, 100),
    ("Coumarin",                  750,  20),
    ("Vanillin",                  500,  10),
    ("Alpha Irone",               733,  30),
    ("Eugenol",                    24, 100),
    ("DBCA",                      138, 100),
    ("Phenethyl Alcohol",          95, 100),
    ("Geraniol",                   51, 100),
    ("Damascol",                   94,  10),
    ("Farnesol",                   24, 100),
    ("Habanolide",                275, 100),
    ("Romandolide",               375, 100),
    ("Ethylene Brassylate",       900, 100),
    ("Musk Ketone",               600,  10),
    ("Ambrettolide",              350,  10),
    ("Exaltolide",                107,  10),
    ("Cashmeran",                 875,  20),
    ("Iso E Super",               400, 100),
    ("Azarbre",                   175, 100),
    ("Polysantol",                 44, 100),
    ("Vertofix",                  165, 100),
    ("Hexyl Salicylate",          787, 100),
    ("Siam Benzoin 50%",          110,  50),
]

TOTAL_CONC_UL = sum(ul for _, ul, _ in FORMULA)
EDP_CONC = 0.234

names_set = set(name for name, _, _ in FORMULA)

# ---- CLASSIFY SECTIONS ----
top_names = {"Bergamot FCF oil Sicilian","Aldehyde C11 undecylenic","Aldehyde C12 MNA","Red Mandarin EO","Cardamom EO"}
heart_names = {"Hedione","Hedione HC","Heliotropal","Anisaldehyde","Coumarin","Vanillin","Alpha Irone","Eugenol","DBCA","Phenethyl Alcohol","Geraniol","Damascol","Farnesol"}
base_names = {"Habanolide","Romandolide","Ethylene Brassylate","Musk Ketone","Ambrettolide","Exaltolide","Cashmeran","Iso E Super","Azarbre","Polysantol","Vertofix","Hexyl Salicylate","Siam Benzoin 50%"}

top_act = sum(ul*dil/100 for n,ul,dil in FORMULA if n in top_names)
heart_act = sum(ul*dil/100 for n,ul,dil in FORMULA if n in heart_names)
base_act = sum(ul*dil/100 for n,ul,dil in FORMULA if n in base_names)
total_act = top_act + heart_act + base_act

# ---- 1. LONGEVITY ----
base_pct = base_act / total_act * 100 if total_act else 0
mw_vals = []
logp_vals = []
for name, ul, dil in FORMULA:
    p = get_profile(name)
    act = ul * dil / 100
    if p and p.mw: mw_vals.append((p.mw, act))
    if p and p.clogp: logp_vals.append((p.clogp, act))
w_mw = sum(m*a for m,a in mw_vals)/sum(a for _,a in mw_vals) if mw_vals else 0
w_logp = sum(l*a for l,a in logp_vals)/sum(a for _,a in logp_vals) if logp_vals else 0
longevity = min(9.5, 5 + base_pct/7)

# ---- 2. SILLAGE ----
high_vp = []
for name, ul, dil in FORMULA:
    p = get_profile(name)
    if p and p.vp and p.vp > 1.0:
        act = ul * dil / 100
        high_vp.append((name, p.vp, act))
sillage = min(9.5, 5 + len(high_vp)*0.4)

# ---- 3. SYNERGY ----
pairs = set()
for name in names_set:
    p = get_profile(name)
    if p and p.synergies:
        for syn in p.synergies:
            if syn in names_set:
                pairs.add(tuple(sorted([name, syn])))
synergy = min(9.5, 4 + len(pairs)*0.1)

# ---- 4. LUXURY ----
luxury_set = {"Alpha Irone","Damascol","Hedione HC","DBCA","Habanolide","Ambrettolide","Musk Ketone","Polysantol","Cardamom EO","Eugenol"}
lux_hits = sum(1 for m in luxury_set if m in names_set)
luxury = min(9.5, 5 + lux_hits*0.3)

# ---- 5. TEXTURE ----
textures = set()
for name in names_set:
    p = get_profile(name)
    if p and p.texture: textures.add(p.texture)
texture = min(9.5, 4 + len(textures)*0.6)

# ---- 6. STACKING/STRUCTURE ----
roles = set()
for name in names_set:
    p = get_profile(name)
    if p and p.role: roles.add(p.role)
structure = min(9.5, 4 + len(roles)*0.55)

# ---- 7. SAFETY ----
ifra_issues = 0
for name, ul, dil in FORMULA:
    limit = IFRA_CAT4_LIMITS.get(name)
    if limit:
        edp_pct = (ul*dil/100)/TOTAL_CONC_UL*EDP_CONC*100
        if edp_pct > limit:
            ifra_issues += 1
safety = 9.5 if ifra_issues == 0 else 7.5 if ifra_issues == 1 else 5

# ---- 8. SKIN ----
subst_vals = []
for name, ul, dil in FORMULA:
    sd = SKIN_PHYSCHEM.get(name, {})
    if sd:
        subst_vals.append((sd.get("substantivity", 0.5), ul*dil/100))
w_subst = sum(s*a for s,a in subst_vals)/sum(a for _,a in subst_vals) if subst_vals else 0.5
skin_perf = min(9.5, 3 + w_subst*8)

# ---- 9. HEDONIC ----
hed_vals = []
for name, ul, dil in FORMULA:
    h = HEDONIC_VALENCE.get(name, 0)
    if h != 0:
        hed_vals.append((h, ul*dil/100))
w_hed = sum(h*a for h,a in hed_vals)/sum(a for _,a in hed_vals) if hed_vals else 0
hedonic = min(9.5, 5 + w_hed*4)

# ---- 10. PERCEPTUAL ----
oav_list = []
for name, ul, dil in FORMULA:
    act = ul * dil / 100
    odt = get_odt(name)
    if odt and odt > 0:
        edp_ppm = act / TOTAL_CONC_UL * 1e6 * EDP_CONC
        oav_val = edp_ppm / odt
        oav_list.append(oav_val)

dims = {}
for name in names_set:
    p = get_profile(name)
    if p:
        for d, s in p.character.items():
            if s >= 3: dims[d] = dims.get(d, 0) + 1

oav_range = max(oav_list)/min(oav_list) if oav_list else 0
perceptual = min(9.5, 3 + len(dims)*0.35)

# ---- COMPOSITE ----
scores = {
    "longevity": longevity, "sillage": sillage, "synergy": synergy,
    "luxury": luxury, "texture": texture, "structure": structure,
    "safety": safety, "skin_perf": skin_perf, "hedonic": hedonic, "perceptual": perceptual,
}
weights = {
    "longevity": 0.8, "sillage": 0.8, "synergy": 0.5,
    "luxury": 0.8, "texture": 0.8, "structure": 0.8,
    "safety": 1.2, "skin_perf": 0.7, "hedonic": 0.5, "perceptual": 0.6,
}
total_w = sum(weights.values())
composite = 1.0
for axis, s in scores.items():
    composite *= s ** (weights[axis]/total_w)

print("=" * 100)
print(f"{'MR. SANDMAN — YSL OAV-FIRST EDITION':^100}")
print(f"{'10-Axis Score + Brand Perspectives':^100}")
print("=" * 100)
print()
print(f"  31 materials | {TOTAL_CONC_UL:,} uL concentrate | {EDP_CONC*100:.1f}% EDP | {total_act:.0f} uL active")
print()
print("--- 10-AXIS SCORE ---")
print(f"  {'Axis':<15} {'Score':>6} {'Weight':>6} {'Detail'}")
print(f"  {'-'*50}")
for axis, s in scores.items():
    w = weights[axis]
    detail = f"weighted: {s** (w/total_w):.2f}"
    print(f"  {axis:<15} {s:>6.2f}  x{w:.1f}   {detail}")

print(f"  {'-'*50}")
print(f"  {'COMPOSITE':<15} {composite:>6.2f}/10")
print()
print(f"  Base fraction: {base_pct:.0f}%  |  MW: {w_mw:.0f}  |  LogP: {w_logp:.2f}")
print(f"  Synergy pairs: {len(pairs)}  |  Luxury hits: {lux_hits}/{len(luxury_set)}")
print(f"  Textures: {len(textures)} ({', '.join(sorted(list(textures)[:6]))})")
print(f"  Roles: {len(roles)} ({', '.join(sorted(roles))})")
print(f"  Hedonic avg: {w_hed:+.2f}  |  Substantivity: {w_subst:.2f}")
print(f"  IFRA issues: {ifra_issues}  |  OAV range: {oav_range:,.0f}x  |  Dims: {len(dims)}")
print(f"  High-VP projection: {len(high_vp)} materials")

print()
print("=" * 100)
print(f"{'SEPHORA BRAND RATING':^100}")
print("=" * 100)
print()

sephora = {
    "Chanel":      {"base": 8.0, "add": "Aldehydes recognized as No.5 homage. Clean musk respected. Cardamom + HC would be questioned — 'too modern spice + jasmine for Chanel purity.'"},
    "Dior":        {"base": 7.5, "add": "Iris at 6.7% stock (2% active) — Dior wants 12%+ for Homme territory. 'Nice iris. Where's the rest?'"},
    "YSL":         {"base": 9.2, "add": "This IS a YSL perfume. Aldehydic confidence, clean projection musk, spice warmth. 'This belongs on our shelf.'"},
    "Prada":       {"base": 6.0, "add": "Too loud. Too spicy. Too many materials. Prada Infusion has 4 musks max. 'Simplify by half.'"},
    "Tom Ford":    {"base": 7.8, "add": "Good bones. Needs more vanilla, more labdanum, more skin. 'Make it sexier. The lullaby is after midnight.'"},
    "Kilian":      {"base": 6.5, "add": "Where's the gourmand? Maple Lactone, more Ethyl Maltol, more vanilla. 'This lullaby has no dessert.'"},
    "Armani":      {"base": 7.0, "add": "Clean, elegant, wearable. 'Would sell. Not exciting. Good for the Sephora shelf.'"},
    "Gucci":       {"base": 6.8, "add": "Too aldehydic. Gucci Bloom is floral-first. 'Where are the white flowers?'"},
    "Hermes":      {"base": 8.2, "add": "Ellena would approve the transparency. Nagel would add fig leaf. 'A French garden lullaby — almost.'"},
    "Jo Malone":   {"base": 5.5, "add": "31 materials? We use 8. 'This is not a cologne. This is a novel.'"},
}

print(f"  {'Brand':<15} {'Score':>6} {'Verdict'}")
print(f"  {'-'*70}")
for brand, data in sorted(sephora.items(), key=lambda x: -x[1]["base"]):
    print(f"  {brand:<15} {data['base']:>6.1f}/10  {data['add']}")

print()
print("=" * 100)
print(f"{'NICHE BRAND RATING':^100}")
print("=" * 100)
print()

niche = {
    "Le Labo":         {"base": 4.0, "add": "'31 materials? Our candles have fewer ingredients.' Would strip to 9. Scentenal at 50 uL becomes the signature. Name: SAND 52."},
    "Byredo":          {"base": 7.5, "add": "Good memory-object. 'Cinema 1952' sells. 'The aldehydes are the mother's lipstick. Smart. The HC is your jasmine — also smart.'"},
    "Serge Lutens":    {"base": 6.0, "add": "Not dark enough. 'Where is the shadow under the bed? Where is the skatole? This is a lullaby for children.'"},
    "Diptyque":        {"base": 5.5, "add": "'Where is the green? cis-3-Hexenol. Galbanum. Evernyl. The aldehydes are a garden party, not a cinema.'"},
    "Frederic Malle":  {"base": 8.5, "add": "'Ropion would sign this. C11 at 0.68% is brave. OAV-first design is rigorous. The iris is right. The Habanolide is right.'"},
    "Roja Dove":       {"base": 7.0, "add": "'Good. Not great. Where is the rose absolute? Where is the real jasmine? You built this with synthetics.'"},
    "Amouage":         {"base": 6.5, "add": "'No olibanum. No frankincense. This is European, not Omani. Respectable but not ours.'"},
    "Areej le Dore":   {"base": 4.5, "add": "'Every synthetic you could replace, you didn't. Ylang, Vetiver, Champaca — all available. You chose Habanolide over real musk.'"},
    "Francesca Bianchi":{"base": 7.2, "add": "'Too clean. I want more Costus Olifac. More labdanum. More skin. The aldehydes are cold — I'd wrap them in body heat.'"},
    "Tauer":           {"base": 7.8, "add": "'OAV-first design — I respect the rigor. But where is the Labdanum? No Labdanum = not Tauer. Still: 7.8 for the math.'"},
    "Papillon":        {"base": 7.0, "add": "'Clean musk + aldehydic lipstick = not lived-in enough. I'd add Champaca narcotic and dirty up the base. But the bones are solid.'"},
    "Ormonde Jayne":   {"base": 6.2, "add": "'No green. No moss. No garden. The aldehydes are lovely but they're in a cinema, not an English garden.'"},
}

print(f"  {'Brand':<20} {'Score':>6} {'Verdict'}")
print(f"  {'-'*80}")
for brand, data in sorted(niche.items(), key=lambda x: -x[1]["base"]):
    print(f"  {brand:<20} {data['base']:>6.1f}/10  {data['add']}")

print()
print("=" * 100)
print("BRAND FIT SUMMARY")
print("=" * 100)
print()
print("  BEST FIT: YSL (9.2) — this IS a YSL perfume.")
print("  CLOSE:    Frederic Malle (8.5), Hermes (8.2)")
print("  RESPECTED: Tauer (7.8), Tom Ford (7.8), Byredo (7.5)")
print("  WRONG HOUSE: Le Labo (4.0), Areej (4.5), Jo Malone (5.5)")
print()
print("  This is a designer-dominant formula. It belongs at a Sephora counter.")
print("  It would survive in niche only if sold through Frederic Malle (where")
print("  Ropion signs off on OAV-rigor) or Byredo (where the memory-object concept")
print("  carries it). Le Labo and Areej would reject it on philosophy alone.")
