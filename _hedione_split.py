"""Rebuild optimized formulas with Hedione split to Hedione HC.
HC = higher cis, more natural-floral, less diffusive. Better balance, more citrus visible.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

# Ensure ODT
E = [
    ("petitgrain eo",4),("cardamom eo",3),("ethyl linalool",1.5),("norlimbanol dextro",0.5),
    ("vetival",2.0),("paradisamide",0.5),("romandolide",4.9),("ethylene brassylate",0.97),
    ("ambrettolide",0.136),("dihydrojasmone",0.75),("aurantiol",30),("benzoin resinoid",3),
    ("jasmine fo",15),("javanol",0.0016),("iso e super",0.05),
    ("hedione",0.05),("hedione hc",20),("linalyl acetate",50),("bergamot fcf sicilian",4),
    ("cedrat fcf sicilian",12),("grapefruit fcf",5),("lime distilled eo",12),
    ("red mandarin eo",10),("blood orange sicilian",8),("lemon fcf oil sicilian",10),
    ("ambrofix",0.3),("methyl pamplemousse",3),("damascenone",0.004),("alpha damascone",0.04),
    ("hydroxycitronellal",15),("nympheal",2),("floralozone",0.5),("scentenal",0.5),
    ("geraniol",2.22),("citronellol",40),("suederal",0.5),("costus olifac",10),
    ("mayol",3),("alpha irone",0.9),
]
for k,o in E:
    if k not in ODT_DATA or "odt_air" not in ODT_DATA.get(k,{}):
        if k in ODT_DATA: ODT_DATA[k]["odt_air"]=o
        else: ODT_DATA[k]={"odt_air":o}

def vp_odt(n):
    p = get_profile(n)
    return (p.vp if p and p.vp else 0), ODT_DATA.get(normalize_name(n),{}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0

DRY = [
    ("STRUCTURE",   "Iso E Super",             500),
    ("PROJ MUSK",   "Romandolide",             480),
    ("CREAMY MUSK", "Ethylene Brassylate",      380),
    ("AMBER",       "Ambrofix",                 18),
    ("DRY WOOD",    "Norlimbanol Dextro",       42),
    ("VETIVER",     "Vetival",                  40),
    ("SANDALWOOD",  "Javanol",                  16),
    ("SPARKLE",     "Cardamom EO",               5),
]

# Splits: (Hedione, Hedione_HC) — HC = ~25-35% of total jasmonate
OPT = {
"I": {
    "title": "DHC I — Bergamot + Orange Blossom (50mL EdP)",
    "house": "Dior / François Demachy",
    "citrus": ("Bergamot FCF Sicilian", 5000),
    "petitgrain": 700, "la": 220, "h": 1100, "hh": 450, "el": 550,
    "flower": [("Orange blossom","Aurantiol",8,80),("Jasmine radiance","Dihydrojasmone",40,40),
               ("Apple depth","Damascenone",0.0015,0.15)],
    "score": 8.8,
},
"II": {
    "title": "DHC II — Cedrat + Costus-Suede (50mL EdP)",
    "house": "Le Labo / Daphné Bugey",
    "citrus": ("Cedrat FCF Sicilian", 5200),
    "petitgrain": 650, "la": 160, "h": 1000, "hh": 400, "el": 500,
    "flower": [("Suede leather","Suederal",0.18,1.8),("Costus animalic","Costus Olifac",0.07,0.7),
               ("Apple depth","Damascenone",0.0018,0.18),("Jasmine bridge","Dihydrojasmone",35,35)],
    "score": 9.1,
},
"III": {
    "title": "DHC III — Grapefruit Puriste (50mL EdP)",
    "house": "Tom Ford / Rodrigo Flores-Roux",
    "citrus": ("Grapefruit FCF", 5200),
    "petitgrain": 650, "la": 480, "h": 1200, "hh": 500, "el": 600,
    "flower": [("Grapefruit flower","Dihydrojasmone",20,20),
               ("Tropical juicy","Paradisamide",2.0,20),("Grapefruit skin","Methyl Pamplemousse",2.0,20)],
    "score": 9.5,
},
"IV": {
    "title": "DHC IV — Lime + Muguet (50mL EdP)",
    "house": "Hermès / Christine Nagel",
    "citrus": ("Lime Distilled EO", 5200),
    "petitgrain": 700, "la": 160, "h": 1000, "hh": 400, "el": 500,
    "flower": [("Muguet heart","Hydroxycitronellal",12,12),("Muguet body","Mayol",6,6),
               ("Ozone lift","Floralozone",0.15,1.5)],
    "score": 8.5,
},
"V": {
    "title": "DHC V — Mandarin + Jasmine-Orange Blossom (50mL EdP)",
    "house": "Frédéric Malle / Dominique Ropion",
    "citrus": ("Red Mandarin EO", 5000),
    "petitgrain": 550, "la": 280, "h": 1050, "hh": 450, "el": 500,
    "flower": [("Jasmine heart","Dihydrojasmone",45,45),("Orange blossom","Aurantiol",8,80),
               ("Jasmine accord","Jasmine FO",70,70),("Apple depth","Damascenone",0.0015,0.15),
               ("Balsamic warmth","Benzoin Resinoid",12,12)],
    "score": 8.7,
},
"VI": {
    "title": "DHC VI — Blood Orange + Rose-Damascone (50mL EdP)",
    "house": "Guerlain / Thierry Wasser",
    "citrus": ("Blood Orange Sicilian", 5000),
    "petitgrain": 550, "la": 220, "h": 1050, "hh": 450, "el": 550,
    "flower": [("Rose heart","Alpha Damascone",0.12,1.2),("Rose-plum","Damascenone",0.0035,0.35),
               ("Rose fresh","Citronellol",35,35),("Rose sweet","Geraniol",18,18),
               ("Balsamic bridge","Benzoin Resinoid",12,12)],
    "score": 9.3,
},
"VII": {
    "title": "DHC VII — Lemon + Muguet-Lily (50mL EdP)",
    "house": "Chanel / Olivier Polge",
    "citrus": ("Lemon FCF oil Sicilian", 5200),
    "petitgrain": 550, "la": 200, "h": 1050, "hh": 450, "el": 550,
    "flower": [("Muguet anchor","Hydroxycitronellal",10,10),("Muguet-lily","Nympheal",6,6),
               ("Metallic sparkle","Scentenal",0.08,8),("Ozone air","Floralozone",0.15,1.5)],
    "score": 9.0,
},
}

out_dir = "formulas/demachy_redux"
os.makedirs(out_dir, exist_ok=True)
fnames = {
    "I":"DHC_I_Bergamot_50mL_EdP_Optimized_Dior.md","II":"DHC_II_Cedrat_50mL_EdP_Optimized_LeLabo.md",
    "III":"DHC_III_Grapefruit_50mL_EdP_Optimized_TomFord.md","IV":"DHC_IV_Lime_50mL_EdP_Optimized_Hermes.md",
    "V":"DHC_V_Mandarin_50mL_EdP_Optimized_Malle.md","VI":"DHC_VI_BloodOrange_50mL_EdP_Optimized_Guerlain.md",
    "VII":"DHC_VII_Lemon_50mL_EdP_Optimized_Chanel.md",
}

print(f"\n{'='*80}")
print(f"  HEDIONE SPLIT TO HC — OAV IMPACT")
print(f"{'='*80}")
print(f"  {'Formula':<38} {'H':>5} {'HC':>5} {'H OAV':>8} {'HC OAV':>7} {'Total Jas':>9} {'Citrus%':>7}")
for k in ["I","II","III","IV","V","VI","VII"]:
    f = OPT[k]; cn,cd = f["citrus"]
    h_ov = oav(f["h"],0.21,0.05); hc_ov = oav(f["hh"],0.21,20)
    tj = h_ov + hc_ov
    
    ly = [("P","Petitgrain EO",f["petitgrain"],f["petitgrain"]),
          ("LA","Linalyl Acetate",f["la"],f["la"]),
          ("H","Hedione",f["h"],f["h"]),("HC","Hedione HC",f["hh"],f["hh"]),
          ("EL","Ethyl Linalool",f["el"],f["el"])]
    for _,mat,a,r in f["flower"]: ly.append(("F",mat,a,r))
    for _,mat,a in DRY: ly.append(("D",mat,a,a))
    ly.append(("C",cn,cd,cd))
    rows = []; 
    for _,mat,a,r in ly:
        vp,odt = vp_odt(mat); rows.append(oav(a,vp,odt))
    T = sum(rows)
    citrus_all = sum(r for _,r in enumerate(rows) if _ == len(ly)-1 or any(fl[1]==mat for fl in f["flower"] if fl[1]=="Petitgrain EO"))
    
    # Rank
    ranked = [(mat, a, r, oav(a,*vp_odt(mat))) for _,mat,a,r in ly if _ not in ('',' ')]
    ranked = sorted([(mat, a, r, oav(a, *vp_odt(mat))) for _,mat,a,r in ly], key=lambda x: x[3], reverse=True)
    fr = next(i+1 for i,x in enumerate(ranked) if x[0]==cn)
    citrus_pct = sum(x[3] for x in ranked if x[0]==cn or x[0]=="Petitgrain EO")/T*100
    
    print(f"  {f['title'][:38]:<38} {f['h']:>5} {f['hh']:>5} {h_ov:>8,.0f} {hc_ov:>7,.0f} {tj:>9,.0f} {citrus_pct:>6.1f}%")

print()
print(f"  Hedione ODT=0.05ppb (OAV/µL=84). Hedione HC ODT=20ppb (OAV/µL=0.21).")
print(f"  HC is 400x less OAV-dominant. Splitting 25-35% to HC reduces Hedione's")
print(f"  headspace monopoly, letting citrus breathe at the opening.")

# Write files
for k in ["I","II","III","IV","V","VI","VII"]:
    f = OPT[k]; cn,cd = f["citrus"]
    ly = [("PETITGRAIN","Petitgrain EO",f["petitgrain"],f["petitgrain"]),
          ("LINALYL AC","Linalyl Acetate",f["la"],f["la"]),
          ("RADIANCE","Hedione",f["h"],f["h"]),
          ("HC NUANCE","Hedione HC",f["hh"],f["hh"]),
          ("CLEAN LIFT","Ethyl Linalool",f["el"],f["el"])]
    for role,mat,a,r in f["flower"]: ly.append(("FLOWER",mat,a,r))
    for role,mat,a in DRY: ly.append((role,mat,a,a))
    ly.append(("STAR CITRUS",cn,cd,cd))
    
    rows = []
    for role,mat,a,r in ly:
        vp,odt = vp_odt(mat); ov = oav(a,vp,odt)
        dil = "neat" if abs(a-r)<0.01 else f"{a/r*100:.0f}%"
        rows.append({"role":role,"mat":mat,"a":a,"raw":r,"dil":dil,"vp":vp,"odt":odt,"oav":ov})
    
    T = sum(r["oav"] for r in rows); R = sorted(rows,key=lambda r:r["oav"],reverse=True)
    ta = sum(r["a"] for r in rows); tr = sum(r["raw"] for r in rows)
    fs = sum(r["oav"] for r in R if "STAR" in r["role"])/T*100
    fls = sum(r["oav"] for r in R if "FLOWER" in r["role"])/T*100
    fr = next(i+1 for i,r in enumerate(R) if "STAR" in r["role"])
    
    md = [f"# {f['title']}", f"",
          f"**House/Perfumer:** {f['house']}",
          f"**Hedione split:** {f['h']}µL H + {f['hh']}µL HC ({f['hh']/(f['h']+f['hh'])*100:.0f}% high-cis)",
          f"**Compositional Score:** {f['score']:.1f}/10", f"",
          f"## Batch Data",
          f"- 50 mL EdP | {tr:,.0f}µL raw / {ta:,.0f}µL active | ~{ta/1000/50*100:.0f}% conc | {len(rows)} materials | Ethanol ~{50-tr/1000:.0f}mL",
          f"", f"## Formula", f"",
          f"| # | Role | Material | Dilution | Raw µL | Active µL |",
          f"|---:|------|----------|----------|-------:|----------:|"]
    for i,r in enumerate(rows):
        md.append(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['a']:>8.1f} |")
    md.extend(["",f"## Headspace OAV (32°C)",f"",
               f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | % |",
               f"|---:|----------|----------:|-------:|---------:|----:|---:|"])
    for i,r in enumerate(R):
        ods = f"{r['odt']:.4g}" if r['odt'] else "-"
        ic = "🍊" if "STAR" in r["role"] else "🌸" if "FLOWER" in r["role"] else ""
        md.append(f"| {i+1:>2} | {r['mat']:<26} | {r['a']:>8.1f} | {r['vp']:>5.4f} | {ods:>7} | {r['oav']:>6,.0f} | {r['oav']/T*100:>4.1f}% {ic}|")
    md.extend(["",f"**Total OAV:** {T:,.0f} | **Fruit Rank:** #{fr} | **Fruit Share:** {fs:.1f}% | **Flower Share:** {fls:.1f}%", ""])
    
    with open(os.path.join(out_dir,fnames[k]),"w",encoding="utf-8") as fh:
        fh.write("\n".join(md))
    print(f"  Written {fnames[k]}")
