"""Generate 30mL compounding instructions by scaling all doses 0.6x."""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0
SCALE = 0.6  # 30mL / 50mL

ODT_ENS = {
    "petitgrain eo":4,"cardamom eo":3,"ethyl linalool":15,"norlimbanol dextro":0.8,
    "vetival":7.0,"paradisamide":8.0,"romandolide":4.9,"ethylene brassylate":0.97,
    "ambrettolide":0.136,"dihydrojasmone":0.75,"aurantiol":30,"benzoin resinoid":3,
    "javanol":0.0016,"iso e super":0.05,"hedione":0.05,"hedione hc":20,
    "linalyl acetate":2.7,"bergamot fcf sicilian":15,"cedrat fcf sicilian":10,
    "grapefruit fcf":3,"lime distilled eo":12,"red mandarin eo":10,
    "blood orange sicilian":8,"lemon fcf oil sicilian":10,"ambrofix":0.3,
    "kephalis":50,"floralozone":1.0,"scentenal":0.02,"damascenone":0.004,
    "alpha damascone":0.04,"geraniol":2.22,"citronellol":40,
    "methyl pamplemousse":3.0,"hydroxycitronellal":15,"nympheal":2,"mayol":3,
    "jasmine fo":15,
}
for k,o in ODT_ENS.items():
    if k in ODT_DATA: ODT_DATA[k]["odt_air"]=o
    else: ODT_DATA[k]={"odt_air":o}

def vp_odt(n):
    p = get_profile(n)
    key = "hedione hc" if n.lower()=="hedione hc" else normalize_name(n)
    return (p.vp if p and p.vp else 0), ODT_DATA.get(key,{}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0

DRY = [("Iso E Super",500),("Romandolide",480),("Ethylene Brassylate",380),("Ambrofix",18),
       ("Norlimbanol Dextro",42),("Vetival",40),("Javanol",16),("Cardamom EO",5)]

TREES = {
    "I Bergamot": {
        "tree": "Bergamot + Orange Blossom", "house": "Dior / Demachy", "score": 8.8,
        "citrus": ("Bergamot FCF Sicilian", 6500), "p": 650, "la": 80,
        "h": 1100, "hh": 450, "el": 550,
        "flower": [("Aurantiol",8,80,0.10),("Dihydrojasmone",40,40,1),("Damascenone",0.0015,0.15,0.01)],
    },
    "II Cedrat": {
        "tree": "Citron + Citron Blossom", "house": "Le Labo / Bugey", "score": 9.0,
        "citrus": ("Cedrat FCF Sicilian", 6500), "p": 650, "la": 80,
        "h": 1000, "hh": 400, "el": 500,
        "flower": [("Hydroxycitronellal",12,12,1),("Floralozone",0.15,1.5,0.10)],
    },
    "III Grapefruit": {
        "tree": "Grapefruit + Grapefruit Blossom", "house": "Tom Ford / Flores-Roux", "score": 9.5,
        "citrus": ("Grapefruit FCF", 5500), "p": 650, "la": 100,
        "h": 1200, "hh": 500, "el": 600,
        "flower": [("Dihydrojasmone",20,20,1),("Paradisamide",2.0,20,0.10),("Methyl Pamplemousse",2.0,20,0.10)],
    },
    "IV Lime": {
        "tree": "Lime + Lime Blossom", "house": "Hermes / Nagel", "score": 8.5,
        "citrus": ("Lime Distilled EO", 6500), "p": 700, "la": 80,
        "h": 1000, "hh": 400, "el": 500,
        "flower": [("Hydroxycitronellal",12,12,1),("Mayol",6,6,1),("Floralozone",0.15,1.5,0.10)],
    },
    "V Mandarin": {
        "tree": "Mandarin + Mandarin Blossom", "house": "Malle / Ropion", "score": 8.7,
        "citrus": ("Red Mandarin EO", 6000), "p": 550, "la": 100,
        "h": 1050, "hh": 450, "el": 500,
        "flower": [("Aurantiol",8,80,0.10),("Dihydrojasmone",45,45,1),("Jasmine FO",70,70,1),("Damascenone",0.0015,0.15,0.01),("Benzoin Resinoid",12,12,1)],
    },
    "VI Blood Orange": {
        "tree": "Blood Orange + Orange Blossom", "house": "Guerlain / Wasser", "score": 9.3,
        "citrus": ("Blood Orange Sicilian", 6000), "p": 550, "la": 80,
        "h": 1050, "hh": 450, "el": 550,
        "flower": [("Aurantiol",10,100,0.10),("Dihydrojasmone",35,35,1),("Damascenone",0.0035,0.35,0.01),("Benzoin Resinoid",12,12,1)],
    },
    "VII Lemon": {
        "tree": "Lemon + Lemon Blossom", "house": "Chanel / Polge", "score": 9.0,
        "citrus": ("Lemon FCF oil Sicilian", 6500), "p": 550, "la": 80,
        "h": 1050, "hh": 450, "el": 550,
        "flower": [("Hydroxycitronellal",10,10,1),("Nympheal",6,6,1),("Scentenal",0.02,2,0.01),("Floralozone",0.15,1.5,0.10)],
    },
}

out = []
w = out.append
w("# DHC Veritas — 30 mL Compounding Instructions")
w("")
w("> **All doses scaled 0.6x from 50mL. Same concentration, same OAV.**")
w("> **Fill to 30 mL line with ethanol after concentrate.**")
w("")

for key in ["I Bergamot","II Cedrat","III Grapefruit","IV Lime","V Mandarin","VI Blood Orange","VII Lemon"]:
    f = TREES[key]; cn,cd = f["citrus"]
    
    # Build layers in compounding order
    layers = []
    # Drydown
    for m,a in DRY: layers.append(("Base", m, round(a*SCALE,1), "neat"))
    # Hediones
    layers.append(("Heart", "Hedione", round(f["h"]*SCALE,1), "neat"))
    layers.append(("Heart", "Hedione HC", round(f["hh"]*SCALE,1), "neat"))
    layers.append(("Heart", "Ethyl Linalool", round(f["el"]*SCALE,1), "neat"))
    # Flowers
    for m,a,r,d in f["flower"]:
        raw30 = round(r*SCALE,1)
        dil_pct = a/r*100
        if dil_pct >= 99: dil_str = "neat"
        elif dil_pct >= 9: dil_str = f"{dil_pct:.0f}%"
        else: dil_str = f"{dil_pct:.1f}%"
        layers.append(("Flower", m, raw30, dil_str))
    # Top
    layers.append(("Top", "Petitgrain EO", round(f["p"]*SCALE,1), "neat"))
    layers.append(("Top", "Linalyl Acetate", round(f["la"]*SCALE,1), "neat"))
    # Star
    layers.append(("Top", cn, round(cd*SCALE,1), "neat"))
    
    total_raw = sum(l[2] for l in layers)
    
    w(f"---")
    w(f"")
    w(f"## {key.split()[1]} {f['tree']} — 30 mL")
    w(f"**House:** {f['house']} | **Score:** {f['score']}/10")
    w(f"**Concentrate:** {total_raw:.0f} µL | **Fill to 30 mL** with ethanol")
    w("")
    w("| # | Layer | Material | Dilution | Raw µL |")
    w("|---:|-------|----------|----------|-------:|")
    for i, (layer, mat, raw, dil) in enumerate(layers):
        w(f"| {i+1:>2} | {layer} | {mat} | {dil} | {raw:>7.1f} |")
    w(f"")
    w(f"> Pipette in order shown. Fill to 30 mL line with ethanol. Invert 50x. Macerate 4 weeks.")
    w("")

with open("formulas/demachy_redux/DHC_VERITAS_30mL.md","w",encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written formulas/demachy_redux/DHC_VERITAS_30mL.md")
