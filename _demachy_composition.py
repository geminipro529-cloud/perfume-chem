"""Compositional analysis of all 7 Demachy formulas.
Scores on 6 axes: Balance, Architecture, Courage, Economy, Cohesion, Originality.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

# Rebuild formulas as data structures for analysis
F = {}

def _ensure(k, odt):
    if k in ODT_DATA and "odt_air" not in ODT_DATA.get(k, {}):
        ODT_DATA[k]["odt_air"] = odt
    elif k not in ODT_DATA:
        ODT_DATA[k] = {"odt_air": odt}

for k,o in [("blood orange sicilian",8),("lemon fcf oil sicilian",10),("lemon fcf sicilian",10),
    ("petitgrain eo",4),("cardamom eo",3),("ethyl linalool",1.5),("kephalis",0.5),
    ("norlimbanol dextro",0.5),("vetival",2.0),("paradisamide",0.5),("floralozone",0.5),
    ("scentenal",0.5),("hydroxycitronellal",15),("nympheal",2),("damascenone",0.004),
    ("alpha damascone",0.04),("romandolide",4.9),("ethylene brassylate",0.97),
    ("ambrettolide",0.136),("dihydrojasmone",0.75),("aurantiol",30),("benzoin resinoid",3),
    ("jasmine fo",15),("alpha irone",0.9),("javanol",0.0016),("iso e super",0.05),
    ("hedione",0.05),("hedione hc",20),("linalyl acetate",50),("bergamot fcf sicilian",4),
    ("cedrat fcf sicilian",12),("grapefruit fcf",5),("lime distilled eo",12),
    ("red mandarin eo",10),("linalool",0.51),("suederal",0.5),("costus olifac",10),
    ("apritone",3.5),("mayol",3),("geraniol",2.22),("citronellol",40),("jessemal",5),
    ("ambrofix",0.3)]:
    _ensure(k, o)

def vp_odt(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    d = ODT_DATA.get(n, {})
    return vp, d.get('odt_air')

def oav(active, vp, odt):
    return vp * active * PPM / odt if vp and odt else 0

# Define all 7 formulas
F["I Bergamot"] = {
    "citrus": ("Bergamot FCF Sicilian", 4200),
    "flower": [("Aurantiol",6,60), ("Dihydrojasmone",30,30)],
    "petitgrain": 600, "linalyl_acetate": 200, "hedione": 1500, "hedione_hc": 180, "ethyl_linalool": 550,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Dior", "Creed"], "perfumer": "François Demachy",
}
F["II Cedrat"] = {
    "citrus": ("Cedrat FCF Sicilian", 4200),
    "flower": [("Suederal",0.15,1.5), ("Costus Olifac",0.05,0.5), ("Dihydrojasmone",30,30), ("Damascenone",0.0012,0.12)],
    "petitgrain": 650, "linalyl_acetate": 180, "hedione": 1400, "hedione_hc": 160, "ethyl_linalool": 500,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Le Labo", "Prada"], "perfumer": "Daphné Bugey",
}
F["III Grapefruit"] = {
    "citrus": ("Grapefruit FCF", 3800),
    "flower": [("Dihydrojasmone",35,35), ("Jessemal",8,8), ("Paradisamide",0.6,6)],
    "petitgrain": 650, "linalyl_acetate": 350, "hedione": 1600, "hedione_hc": 180, "ethyl_linalool": 600,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Tom Ford", "Jo Malone"], "perfumer": "Rodrigo Flores-Roux",
}
F["IV Lime"] = {
    "citrus": ("Lime Distilled EO", 4200),
    "flower": [("Hydroxycitronellal",10,10), ("Mayol",6,6), ("Floralozone",0.15,1.5)],
    "petitgrain": 700, "linalyl_acetate": 160, "hedione": 1400, "hedione_hc": 150, "ethyl_linalool": 500,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Hermès", "Byredo"], "perfumer": "Christine Nagel",
}
F["V Mandarin"] = {
    "citrus": ("Red Mandarin EO", 3800),
    "flower": [("Dihydrojasmone",40,40), ("Aurantiol",6,60), ("Jasmine FO",60,60), ("Benzoin Resinoid",12,12)],
    "petitgrain": 550, "linalyl_acetate": 280, "hedione": 1500, "hedione_hc": 190, "ethyl_linalool": 500,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Frédéric Malle"], "perfumer": "Dominique Ropion",
}
F["VI Blood Orange"] = {
    "citrus": ("Blood Orange Sicilian", 4000),
    "flower": [("Alpha Damascone",0.08,0.8), ("Damascenone",0.003,0.3), ("Citronellol",30,30),
               ("Geraniol",15,15), ("Aurantiol",4,40), ("Benzoin Resinoid",10,10)],
    "petitgrain": 550, "linalyl_acetate": 220, "hedione": 1500, "hedione_hc": 180, "ethyl_linalool": 550,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Guerlain"], "perfumer": "Thierry Wasser",
}
F["VII Lemon"] = {
    "citrus": ("Lemon FCF oil Sicilian", 4200),
    "flower": [("Hydroxycitronellal",12,12), ("Nympheal",5,5), ("Floralozone",0.15,1.5), ("Scentenal",0.06,6)],
    "petitgrain": 550, "linalyl_acetate": 200, "hedione": 1500, "hedione_hc": 180, "ethyl_linalool": 550,
    "dry": {"Iso E Super":480, "Romandolide":460, "Ethylene Brassylate":360, "Ambrofix":17,
            "Norlimbanol Dextro":42, "Vetival":40, "Javanol":16, "Cardamom EO":4},
    "houses": ["Chanel", "Acqua di Parma"], "perfumer": "Olivier Polge",
}

def analyze(formulas):
    rows = {}
    for name, f in formulas.items():
        cname, cdose = f["citrus"]
        flower_count = len(f["flower"])
        flower_active = sum(fl[1] for fl in f["flower"])
        total_dry = sum(f["dry"].values())
        total_active = f["petitgrain"] + f["linalyl_acetate"] + f["hedione"] + f["hedione_hc"] + f["ethyl_linalool"] + cdose + flower_active + total_dry
        total_raw = f["petitgrain"] + f["linalyl_acetate"] + f["hedione"] + f["hedione_hc"] + f["ethyl_linalool"] + cdose + sum(fl[2] for fl in f["flower"]) + total_dry
        mat_count = 8 + flower_count + len(f["dry"])
        
        # Score: BalANCE (citrus:flower ratio)
        ratio = cdose / max(flower_active, 0.01)
        if 50 < ratio < 200:        bal = 9  # Ideal range
        elif 200 < ratio < 500:     bal = 7
        elif 500 < ratio < 1000:    bal = 5
        elif 1000 < ratio < 5000:   bal = 4
        elif ratio > 5000:          bal = 2
        else:                       bal = 8
        
        # Score: ARCHITECTURE (drydown quality — shared, so score on nuance)
        # All have the same drydown, so score based on how well drydown serves the citrus
        dry_scores = {
            "Bergamot FCF Sicilian": 9,    # Classic pairing
            "Cedrat FCF Sicilian": 8,      # Drydown supports the weirdness
            "Grapefruit FCF": 9,           # Clean drydown for clean citrus
            "Lime Distilled EO": 7,        # Could use more green
            "Red Mandarin EO": 8,          # Works well
            "Blood Orange Sicilian": 9,    # Drydown lets rose shine
            "Lemon FCF oil Sicilian": 8,   # Clean, effective
        }
        arch = dry_scores.get(cname, 7)
        
        # Score: COURAGE (overdose boldness)
        courage = 0
        # High hedione dose = courage
        if f["hedione"] >= 1600: courage += 2
        elif f["hedione"] >= 1500: courage += 1
        # High citrus dose
        if cdose >= 4200: courage += 2
        elif cdose >= 4000: courage += 1
        # Unusual flower materials
        unusual_flowers = {"Suederal", "Costus Olifac", "Damascenone", "Alpha Damascone", "Scentenal"}
        courage += sum(2 for fl in f["flower"] if fl[0] in unusual_flowers)
        courage = min(courage, 9)
        
        # Score: ECONOMY (fewer materials = more focused)
        if mat_count <= 16:       eco = 10
        elif mat_count <= 17:     eco = 9
        elif mat_count <= 18:     eco = 8
        elif mat_count <= 19:     eco = 7
        else:                     eco = 6
        
        # Score: COHESION (do layers integrate?)
        # Flower should bridge citrus to drydown
        flower_mats = {fl[0] for fl in f["flower"]}
        citrus_floral = {"Aurantiol", "Dihydrojasmone", "Jasmine FO", "Hydroxycitronellal", "Nympheal", "Mayol"}
        bridging = len(flower_mats & citrus_floral)
        if bridging >= 2:         coh = 9
        elif bridging >= 1:       coh = 7
        else:                     coh = 5
        # Extra point if flower has a base material (benzoin, etc)
        if "Benzoin Resinoid" in flower_mats: coh = min(coh+1, 10)
        
        # Score: ORIGINALITY (how different from standard DHC?)
        # Standard DHC = Bergamot + Orange Blossom
        orig = 0
        if cname != "Bergamot FCF Sicilian": orig += 1
        if "Costus Olifac" in flower_mats: orig += 3
        if "Suederal" in flower_mats: orig += 2
        if "Damascenone" in flower_mats: orig += 2
        if "Alpha Damascone" in flower_mats: orig += 2
        if "Geraniol" in flower_mats: orig += 1
        if "Citronellol" in flower_mats: orig += 1
        if "Benzoin Resinoid" in flower_mats: orig += 1
        if "Jasmine FO" in flower_mats: orig += 1
        if cname == "Blood Orange Sicilian": orig += 2
        if cname == "Lemon FCF oil Sicilian": orig += 1
        orig = min(orig, 10)
        
        total_score = (bal + arch + courage + eco + coh + orig) / 6
        rows[name] = {"bal": bal, "arch": arch, "courage": courage, "eco": eco, "coh": coh, "orig": orig,
                      "total": total_score, "citrus": cdose, "mats": mat_count, "flower_n": flower_count,
                      "citrus_name": cname, "flower_mats": sorted(flower_mats), "ratio": ratio}
    return rows

scores = analyze(F)

out = []
w = out.append
w("# COMPOSITIONAL ANALYSIS — 7 Demachy DHC Formulas")
w("")
w("Scored on 6 axes (1-10): Balance, Architecture, Courage, Economy, Cohesion, Originality")
w("")

# Detail table
w("## Detailed Scores")
w("")
w(f"| Formula | Bal | Arch | Cour | Eco | Coh | Orig | **Avg** | Citrus | Mats |")
w(f"|---------|----:|-----:|-----:|----:|----:|----:|------:|-------:|-----:|")
for name in ["I Bergamot", "II Cedrat", "III Grapefruit", "IV Lime", "V Mandarin", "VI Blood Orange", "VII Lemon"]:
    s = scores[name]
    w(f"| {name:<20} | {s['bal']:>2} | {s['arch']:>3} | {s['courage']:>3} | {s['eco']:>3} | {s['coh']:>3} | {s['orig']:>3} | **{s['total']:.1f}** | {s['citrus']}µL | {s['mats']} |")

w("")
w("## Composition Notes")
w("")
for name in ["I Bergamot", "II Cedrat", "III Grapefruit", "IV Lime", "V Mandarin", "VI Blood Orange", "VII Lemon"]:
    s = scores[name]
    w(f"### {name}")
    w(f"**{s['total']:.1f}/10** — {s['citrus']}µL {s['citrus_name']}, {s['flower_n']} flower materials, {s['mats']} total")
    notes = []
    if s['bal'] >= 8: notes.append(f"Excellent citrus:flower ratio ({s['ratio']:.0f}:1)")
    elif s['bal'] >= 6: notes.append(f"Good citrus:flower ratio")
    else: notes.append(f"Citrus-flower imbalance — flower too faint")
    if s['courage'] >= 6: notes.append(f"Bold dose decisions")
    if s['orig'] >= 7: notes.append(f"Highly original — distinct from standard DHC")
    elif s['orig'] >= 4: notes.append(f"Moderately original")
    else: notes.append(f"Close to reference DHC architecture")
    if s['coh'] >= 9: notes.append(f"Excellent layer integration")
    flower_list = ", ".join(s['flower_mats'])
    w(f"- {'. '.join(notes)}")
    w(f"- Flower materials: {flower_list}")
    w("")

# Final ranking
w("## Final Compositional Ranking")
w("")
ranked = sorted(scores.items(), key=lambda x: x[1]["total"], reverse=True)
w(f"| # | Formula | Score | Strength | Weakness |")
w(f"|---:|---------|------:|----------|----------|")
for i, (name, s) in enumerate(ranked):
    axes = [(s['bal'],"Balance"),(s['arch'],"Arch"),(s['courage'],"Cour"),(s['eco'],"Eco"),(s['coh'],"Coh"),(s['orig'],"Orig")]
    best = max(axes, key=lambda x: x[0])
    worst = min(axes, key=lambda x: x[0])
    w(f"| {i+1} | {name} | **{s['total']:.1f}** | {best[1]} ({best[0]}) | {worst[1]} ({worst[0]}) |")

# Cluster analysis
w("")
w("## Compositional Clusters")
w("")
w("### Cluster 1: Clean Florals (Muguet + Citrus)")
w("- IV Lime + Muguet — cool, green, transparent")
w("- VII Lemon + Muguet-Lily — bright, crystalline, precise")
w("Both use Hydroxycitronellal + ozonic materials. Lightest of the 7.")
w("")
w("### Cluster 2: Jasmine-Heavy (Jasmine + Citrus)")
w("- I Bergamot + Orange Blossom — classic, warm jasmine heart")
w("- III Grapefruit + Jasmine — tropical jasmine, bold")
w("- V Mandarin + Jasmine-Orange Blossom — opulent, layered jasmine")
w("Three different jasmine interpretations. Bergamot is reference, Grapefruit is bold, Mandarin is opulent.")
w("")
w("### Cluster 3: Oriental-Dark (Unusual Flower + Citrus)")
w("- II Cedrat + Costus-Suede — animalic, strange, Le Labo")
w("- VI Blood Orange + Rose — rich, damascene, Guerlain-esque")
w("Both use unexpected flower pairings. Cedrat is the anti-DHC. Blood Orange is the oriental DHC.")
w("")

# Material frequency
w("## Cross-Formula Material Analysis")
w("")
shared = set(["Petitgrain EO","Linalyl Acetate","Hedione","Hedione HC","Ethyl Linalool",
              "Iso E Super","Romandolide","Ethylene Brassylate","Ambrofix",
              "Norlimbanol Dextro","Vetival","Javanol","Cardamom EO"])
w(f"**Universal backbone (13 materials, all 7 formulas):** {', '.join(sorted(shared))}")
w("")

# Unique materials per formula
for name in ["I Bergamot", "II Cedrat", "III Grapefruit", "IV Lime", "V Mandarin", "VI Blood Orange", "VII Lemon"]:
    f = F[name]
    fm = {fl[0] for fl in f["flower"]}
    fm.add(f["citrus"][0])
    w(f"- **{name}:** {', '.join(sorted(fm))}")

# Cost tier estimation
w("")
w("## Cost Tier (Estimated)")
w("")
cost_map = {
    "I Bergamot": "$$ (bergamot cost moderate, aurantiol affordable)",
    "II Cedrat": "$$$ (cedrat rare, suederal/costus expensive captives)",
    "III Grapefruit": "$$ (grapefruit FCF standard, jessemal mid-cost)",
    "IV Lime": "$$ (lime affordable, hydroxycitronellal standard)",
    "V Mandarin": "$$$ (jasmine FO, aurantiol, benzoin all mid-high)",
    "VI Blood Orange": "$$$$ (blood orange premium, damascone/damascenone costly, geraniol/citronellol real rose materials)",
    "VII Lemon": "$$ (lemon affordable, nympheal mid-cost, scentenal captive)",
}
for name in ["I Bergamot", "II Cedrat", "III Grapefruit", "IV Lime", "V Mandarin", "VI Blood Orange", "VII Lemon"]:
    w(f"- **{name}:** {cost_map[name]}")

with open("_demachy_composition_analysis.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written _demachy_composition_analysis.txt")
