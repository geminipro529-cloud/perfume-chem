"""Redesign formulas based on verified ODT data.
Key changes: Bergamot ODT 4->15 (needs more dose), Linalyl Ac ODT 50->2.7 (needs LESS dose),
Grapefruit ODT 5->3 (more visible), Scentenal 0.5->0.02 (nuclear)."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

# Ensure all ODT values
ODT_ENS = {
    "petitgrain eo":4, "cardamom eo":3, "ethyl linalool":15, "norlimbanol dextro":0.8,
    "vetival":7.0, "paradisamide":8.0, "romandolide":4.9, "ethylene brassylate":0.97,
    "ambrettolide":0.136, "dihydrojasmone":0.75, "aurantiol":30, "benzoin resinoid":3,
    "alpha irone":0.9, "javanol":0.0016, "iso e super":0.05, "hedione":0.05, "hedione hc":20,
    "linalyl acetate":2.7, "bergamot fcf sicilian":15, "cedrat fcf sicilian":10,
    "grapefruit fcf":3, "lime distilled eo":12, "red mandarin eo":10,
    "blood orange sicilian":8, "lemon fcf oil sicilian":10, "ambrofix":0.3,
    "kephalis":50, "floralozone":1.0, "scentenal":0.02, "damascenone":0.004,
    "alpha damascone":0.04, "geraniol":2.22, "citronellol":40, "suederal":0.5,
    "costus olifac":10, "methyl pamplemousse":3.0, "hydroxycitronellal":15,
    "nympheal":2, "mayol":3, "jasmine fo":15, "dbca":50,
}
for k,o in ODT_ENS.items():
    if k in ODT_DATA: ODT_DATA[k]["odt_air"]=o
    else: ODT_DATA[k]={"odt_air":o}

def vp_odt(n):
    p = get_profile(n)
    vp = p.vp if p and p.vp else 0
    key = "hedione hc" if n.lower()=="hedione hc" else normalize_name(n)
    return vp, ODT_DATA.get(key,{}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0

DRY = [("Iso E Super",500),("Romandolide",480),("Ethylene Brassylate",380),("Ambrofix",18),
       ("Norlimbanol Dextro",42),("Vetival",40),("Javanol",16),("Cardamom EO",5)]

# REDESIGNED: Linalyl acetate REDUCED (now 18x more visible). Bergamot INCREASED (ODT 4->15).
# Scentenal at trace (ODT 0.02 is nuclear). Grapefruit benefits from lower ODT (3 ppb). 
FORMULAS = {
"Bergamot": {
    "citrus": ("Bergamot FCF Sicilian", 6500),  # was 5000, increased for ODT 15
    "p": 650, "la": 80, "h": 1100, "hh": 450, "el": 550,
    "flower": [("Orange blossom","Aurantiol",8,80),("Jasmine","Dihydrojasmone",40,40),
               ("Apple depth","Damascenone",0.0015,0.15)],
    "house": "Dior / Demachy", "score": 8.8,
},
"Cedrat": {
    "citrus": ("Cedrat FCF Sicilian", 6500),  # ODT 10ppb, need volume
    "p": 650, "la": 80, "h": 1000, "hh": 400, "el": 500,
    "flower": [("Suede","Suederal",0.18,1.8),("Costus","Costus Olifac",0.07,0.7),
               ("Damascenone","Damascenone",0.0018,0.18),("Jasmine bridge","Dihydrojasmone",35,35)],
    "house": "Le Labo / Bugey", "score": 9.1,
},
"Grapefruit": {
    "citrus": ("Grapefruit FCF", 5500),  # ODT 3ppb = more visible, can reduce slightly from 5200
    "p": 650, "la": 100, "h": 1200, "hh": 500, "el": 600,
    "flower": [("Grapefruit flower","Dihydrojasmone",20,20),
               ("Tropical juicy","Paradisamide",2.0,20),("Grapefruit skin","Methyl Pamplemousse",2.0,20)],
    "house": "Tom Ford / Flores-Roux", "score": 9.5,
},
"Lime": {
    "citrus": ("Lime Distilled EO", 6500),  # ODT 12ppb, need volume
    "p": 700, "la": 80, "h": 1000, "hh": 400, "el": 500,
    "flower": [("Muguet heart","Hydroxycitronellal",12,12),("Muguet body","Mayol",6,6),
               ("Ozone lift","Floralozone",0.15,1.5)],
    "house": "Hermes / Nagel", "score": 8.5,
},
"Mandarin": {
    "citrus": ("Red Mandarin EO", 6000),  # ODT 10ppb, bump
    "p": 550, "la": 100, "h": 1050, "hh": 450, "el": 500,
    "flower": [("Jasmine heart","Dihydrojasmone",45,45),("Orange blossom","Aurantiol",8,80),
               ("Jasmine accord","Jasmine FO",70,70),("Apple depth","Damascenone",0.0015,0.15),
               ("Balsamic","Benzoin Resinoid",12,12)],
    "house": "Malle / Ropion", "score": 8.7,
},
"Blood Orange": {
    "citrus": ("Blood Orange Sicilian", 6000),  # ODT 8ppb, good visibility
    "p": 550, "la": 80, "h": 1050, "hh": 450, "el": 550,
    "flower": [("Rose heart","Alpha Damascone",0.12,1.2),("Rose-plum","Damascenone",0.0035,0.35),
               ("Rose fresh","Citronellol",35,35),("Rose sweet","Geraniol",18,18),
               ("Balsamic bridge","Benzoin Resinoid",12,12)],
    "house": "Guerlain / Wasser", "score": 9.3,
},
"Lemon": {
    "citrus": ("Lemon FCF oil Sicilian", 6500),  # ODT 10ppb, need volume
    "p": 550, "la": 80, "h": 1050, "hh": 450, "el": 550,
    "flower": [("Muguet anchor","Hydroxycitronellal",10,10),("Muguet-lily","Nympheal",6,6),
               ("Metallic sparkle","Scentenal",0.02,2),("Ozone air","Floralozone",0.15,1.5)],
    "house": "Chanel / Polge", "score": 9.0,
},
}

out = []
w = out.append
w("REDESIGNED DHC FORMULAS — Verified ODT Architecture")
w("=" * 90)
w(f"  {'Formula':<20} {'Citrus':>7} {'LAc':>5} {'H':>5} {'HC':>5} {'OAV':>9} {'Cit%':>6} {'Lac%':>6} {'Flower%':>6}")
w(f"  {'-'*70}")

for name in ["Bergamot","Cedrat","Grapefruit","Lime","Mandarin","Blood Orange","Lemon"]:
    f = FORMULAS[name]
    cn, cd = f["citrus"]
    ly = [("Petitgrain EO",f["p"],f["p"]), ("Linalyl Acetate",f["la"],f["la"]),
          ("Hedione",f["h"],f["h"]), ("Hedione HC",f["hh"],f["hh"]),
          ("Ethyl Linalool",f["el"],f["el"])]
    for _,m,a,r in f["flower"]: ly.append((m,a,r))
    for mat,a in DRY: ly.append((mat,a,a))
    ly.append((cn,cd,cd))
    
    rows = [oav(a,*vp_odt(m)) for m,a,_ in ly]
    T = sum(rows)
    cit_share = rows[-1]/T*100
    lac_share = rows[1]/T*100
    flower_mats_names = {fl[1] for fl in f["flower"]}
    flower_rows = [oav(a,*vp_odt(m)) for m,a,_ in ly if m in flower_mats_names]
    fl_share = sum(flower_rows)/T*100
    
    w(f"  {name:<20} {cd:>7} {f['la']:>5} {f['h']:>5} {f['hh']:>5} {T:>9,.0f} {cit_share:>5.1f}% {lac_share:>5.1f}% {fl_share:>5.1f}%")

w("")
w("KEY REDESIGN DECISIONS:")
w("  - Bergamot dose 5000->6500 (ODT 4->15 ppb = 3.75x less visible)")
w("  - Linalyl Acetate slashed to 80-100uL (ODT 50->2.7 = 18x MORE visible)")
w("  - Grapefruit dose 5200->5500 (ODT 5->3 = smaller bump needed)")
w("  - Scentenal trace 0.06->0.02 active (ODT 0.5->0.02 = 25x MORE visible)")
w("  - All citruses bumped +500-1500uL for corrected ODT values")

with open("_redesign_summary.txt","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written _redesign_summary.txt")
