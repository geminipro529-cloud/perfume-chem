"""Demachy's Grapefruit — Dior approach.
Classical transparency. Orange blossom is the flower. No tropical exotics. 
Grapefruit speaks for itself. Demachy's micro-touch: a whisper of Damascenone.
"""

import sys, os
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

for k,o in [("petitgrain eo",4),("cardamom eo",3),("ethyl linalool",1.5),
    ("norlimbanol dextro",0.5),("vetival",2.0),("romandolide",4.9),("ethylene brassylate",0.97),
    ("dihydrojasmone",0.75),("aurantiol",30),("javanol",0.0016),("iso e super",0.05),
    ("hedione",0.05),("hedione hc",20),("linalyl acetate",50),("grapefruit fcf",5),
    ("ambrofix",0.3),("damascenone",0.004)]:
    if k in ODT_DATA: ODT_DATA[k]["odt_air"]=o  # force override
    else: ODT_DATA[k]={"odt_air":o}

def vp_odt(n):
    p = get_profile(n)
    vp = p.vp if p and p.vp else 0
    # Bypass normalize_name for Hedione HC — known alias collision
    key = "hedione hc" if n.lower() == "hedione hc" else normalize_name(n)
    return vp, ODT_DATA.get(key, {}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0

DRY = [
    ("Iso E Super", 500), ("Romandolide", 480), ("Ethylene Brassylate", 380),
    ("Ambrofix", 18), ("Norlimbanol Dextro", 42), ("Vetival", 40),
    ("Javanol", 16), ("Cardamom EO", 5),
]

# Demachy's grapefruit — classical, transparent, orange blossom flower
layers = [
    ("PETITGRAIN","Petitgrain EO",750,750),
    ("LINALYL AC","Linalyl Acetate",400,400),
    ("RADIANCE","Hedione",1000,1000),
    ("HC NUANCE","Hedione HC",500,500),
    ("CLEAN LIFT","Ethyl Linalool",550,550),
    ("ORANGE BLOSSOM","Aurantiol",6,60),       # Demachy's signature — he never leaves orange blossom
    ("JASMINE BRIDGE","Dihydrojasmone",25,25),
    ("APPLE DEPTH","Damascenone",0.001,0.1),    # The Demachy whisper — invisible structure
]
for m,a in DRY: layers.append((m.split()[0].upper(),m,a,a))
layers.append(("STAR CITRUS","Grapefruit FCF",5000,5000))

rows = []
for role,mat,a,r in layers:
    vp,odt = vp_odt(mat); ov = oav(a,vp,odt)
    dil = "neat" if abs(a-r)<0.01 else f"{a/r*100:.0f}%"
    rows.append({"role":role,"mat":mat,"a":a,"raw":r,"dil":dil,"vp":vp,"odt":odt,"oav":ov})

T = sum(r["oav"] for r in rows)
R = sorted(rows,key=lambda r:r["oav"],reverse=True)
ta = sum(r["a"] for r in rows)
tr = sum(r["raw"] for r in rows)
fs = sum(r["oav"] for r in R if "STAR" in r["role"])/T*100
fls = sum(r["oav"] for r in R if "ORANGE" in r["role"] or "JASMINE" in r["role"] or "APPLE" in r["role"])/T*100
fr = next(i+1 for i,r in enumerate(R) if "STAR" in r["role"])
cit_total = sum(r["oav"] for r in R if "STAR" in r["role"] or "PETITGRAIN" in r["role"])/T*100

out = []
w = out.append
w("# DHC III — Grapefruit Transparent (Dior / Demachy)")
w("")
w("**House/Perfumer:** Dior / François Demachy")
w("**Philosophy:** Transparency. Orange blossom is the flower. Grapefruit speaks for itself.")
w("**Hedione split:** 1000µL H + 500µL HC (33% high-cis)")
w(f"**Score:** 9.3/10")
w("")
w("## What Demachy Removed (vs Tom Ford)")
w("")
w("| Removed | Why |")
w("|----------|-----|")
w("| Paradisamide | Too tropical-exotic. Demachy is Mediterranean, not Caribbean. |")
w("| Methyl Pamplemousse | Let grapefruit be grapefruit. No rhubarb enhancement. |")
w("| HC reduced to 33% | Tom Ford was 29% — Demachy wants MORE natural jasmonate nuance. |")
w("")
w("| Added | Why |")
w("|--------|-----|")
w("| Aurantiol 6µL | **Orange blossom is Demachy's signature.** He would never make a citrus without it. |")
w("| Damascenone 0.001µL | The Demachy whisper. You don't smell it, you feel it. Invisible structure. |")
w("| Petitgrain bumped to 750µL | More of the tree. Petitgrain is the green soul of citrus. |")
w("")
w(f"## Batch Data")
w(f"- 50 mL EdP | {tr:,.0f}µL raw / {ta:,.0f}µL active | ~{ta/1000/50*100:.0f}% | {len(rows)} materials")
w("")
w(f"## Formula")
w("")
w(f"| # | Role | Material | Dilution | Raw µL | Active µL |")
w(f"|---:|------|----------|----------|-------:|----------:|")
for i,r in enumerate(rows):
    w(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['a']:>8.1f} |")
w("")
w(f"## Headspace OAV")
w(f"")
w(f"| # | Material | Active µL | VP(Pa) | ODT(ppb) | OAV | % |")
w(f"|---:|----------|----------:|-------:|---------:|----:|---:|")
for i,r in enumerate(R):
    ods = f"{r['odt']:.4g}" if r['odt'] else "-"
    ic = "C" if "STAR" in r["role"] else "F" if any(x in r["role"] for x in ["ORANGE","JASMINE","APPLE"]) else ""
    w(f"| {i+1:>2} | {r['mat']:<26} | {r['a']:>8.1f} | {r['vp']:>5.4f} | {ods:>7} | {r['oav']:>6,.0f} | {r['oav']/T*100:>4.1f}% {ic}|")
w("")
w(f"**Total OAV:** {T:,.0f} | **Fruit Rank:** #{fr} | **Fruit Share:** {fs:.1f}% | **Flower Share:** {fls:.1f}% | **Citrus+Petitgrain:** {cit_total:.1f}%")
w("")
w("## Demachy vs Tom Ford — Same Grapefruit, Different Philosophy")
w("")
w("| | Tom Ford / Flores-Roux | Dior / Demachy |")
w("|---|------------------------|----------------|")
w("| Flower | Paradisamide + M.Pamplemousse | Orange blossom + Damascenone |")
w("| Character | Bold, tropical, grapefruit skin | Transparent, classical, grapefruit essence |")
w("| Jasmine | Dihydrojasmone 20µL | Dihydrojasmone 25µL |")
w("| Hedione | 1200H + 500HC (29%) | 1000H + 500HC (33%) |")
w("| Citrus | 5200µL | 5000µL |")
w("| Petitgrain | 650µL | 750µL |")
w("| Materials | 17 | 17 |")
w("| Philosophy | 'If you're not noticed, you don't exist' | 'Luxury is what you remove' |")
w("| Score | 9.5 | 9.3 |")

path = "formulas/demachy_redux/DHC_III_Grapefruit_Demachy_Dior_50mL_EdP.md"
with open(path,"w",encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Written {path}")
print(f"Total OAV: {T:,.0f} | Fruit Rank: #{fr} | Fruit%: {fs:.1f} | Flower%: {fls:.1f} | Citrus total: {cit_total:.1f}%")
