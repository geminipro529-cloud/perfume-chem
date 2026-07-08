"""DHC VII Lemon — Lemonade Edition. Sweet, bright, effervescent citrus.
Ethyl Maltol adds the sugared-citrus quality without gourmand heaviness."""

import sys, os
sys.path.insert(0,'.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM=20.0
E={'petitgrain eo':4,'cardamom eo':3,'ethyl linalool':15,'norlimbanol dextro':0.8,
   'vetival':7.0,'romandolide':4.9,'ethylene brassylate':0.97,'dihydrojasmone':0.75,
   'javanol':0.0016,'iso e super':0.05,'hedione':0.05,'hedione hc':20,
   'linalyl acetate':2.7,'lemon fcf oil sicilian':10,'ambrofix':0.3,
   'hydroxycitronellal':15,'nympheal':2,'floralozone':1.0,'scentenal':0.02,
    'ethyl maltol':0.3,'mayol':3}
for k,o in E.items():
    if k in ODT_DATA: ODT_DATA[k]['odt_air']=o
    else: ODT_DATA[k]={'odt_air':o}

def vp_odt(n):
    p=get_profile(n); vp=p.vp if p and p.vp else 0
    k='hedione hc' if n.lower()=='hedione hc' else normalize_name(n)
    return vp, ODT_DATA.get(k,{}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0

DRY=[("Iso E Super",500),("Romandolide",480),("Ethylene Brassylate",380),
     ("Ambrofix",18),("Norlimbanol Dextro",42),("Vetival",40),("Javanol",16),("Cardamom EO",5)]

# Lemonade Edition — sweet, bright, sugared-citrus
layers=[
    ("PETITGRAIN","Petitgrain EO",250,250),
    ("LINALYL AC","Linalyl Acetate",200,200),
    ("RADIANCE","Hedione",1500,1500),
    ("HC SWEET","Hedione HC",600,600),
    ("CLEAN LIFT","Ethyl Linalool",550,550),
    ("LEMONADE SUGAR","Ethyl Maltol",3,30),
    ("LEMON BLOSSOM","Dihydrojasmone",50,50),
    ("ORANGE BLOSSOM","Aurantiol",15,150),
    ("MUGUET IN AIR","Mayol",14,14),
    ("CRYSTALLINE LILY","Nympheal",6,6),
    ("METALLIC SPARKLE","Scentenal",0.02,2),
    ("OZONE AIR","Floralozone",0.15,1.5),
    ("DRYDOWN","Iso E Super",500,500),
    ("DRYDOWN","Romandolide",480,480),
    ("DRYDOWN","Ethylene Brassylate",380,380),
    ("DRYDOWN","Ambrofix",18,60),
    ("DRYDOWN","Norlimbanol Dextro",42,42),
    ("DRYDOWN","Vetival",40,40),
    ("DRYDOWN","Javanol",16,16),
    ("DRYDOWN","Cardamom EO",5,5),
    ("STAR CITRUS","Lemon FCF oil Sicilian",7000,7000),
]

rows=[]
for role,mat,a,r in layers:
    vp,odt=vp_odt(mat); ov=oav(a,vp,odt)
    dil="neat" if abs(a-r)<0.1 else f"{a/r*100:.0f}%"
    # fix ambrofix display
    if mat=="Ambrofix": dil="30%"
    rows.append({"role":role,"mat":mat,"a":a,"raw":r,"dil":dil,"vp":vp,"odt":odt,"oav":ov})

T=sum(r["oav"] for r in rows); R=sorted(rows,key=lambda r:r["oav"],reverse=True)
ta=sum(r["a"] for r in rows); tr=sum(r["raw"] for r in rows)
cn="Lemon FCF oil Sicilian"
cp=sum(r["oav"] for r in R if r["mat"]==cn)/T*100
fr=next(i+1 for i,r in enumerate(R) if r["mat"]==cn)
fp=sum(r["oav"] for r in R if r["mat"] in ("Dihydrojasmone","Hydroxycitronellal","Nympheal","Scentenal","Floralozone"))/T*100

out=[]
w=out.append
w("# DHC VII — Lemon Lemonade (Chanel / Polge)")
w("")
w("**Tree:** Lemon (Citrus limon) + Lemon blossom")
w("**Character:** Bright Amalfi lemon, sugared-citrus effervescence, crystalline lily flower.")
w("**Hedione:** 1300uL H + 550uL HC (30% HC) | **Score:** 9.0/10")
w("")
w("## What Makes It 'Lemonade'")
w("")
w("| Material | Role |")
w("|----------|------|")
w("| Ethyl Maltol 2uL (10% x 20uL) | The sugar. Dior's lemonade trick. Vanishingly low OAV, works via taste/tactile sweetness. |")
w("| Hedione 1300 + HC 550 | Jasmine radiance carries the sweet impression. HC adds natural floral nuance. |")
w("| Linalyl Acetate 160uL | Sweet lavender-bergamot lift. ODT 2.7 = very visible brightness. |")
w("| Lemon blossom (Hydroxycitronellal + Nympheal) | The tree's own white flower. Muguet-lily crystalline. |")
w("| Scentenal 0.02uL | Metallic sparkle = the effervescence. Like tonic water bubbles. |")
w("")
w(f"## Batch Data")
w(f"- 50mL EdP | {tr:,.0f}uL raw / {ta:,.0f}uL active | ~{ta/1000/50*100:.0f}% | {len(rows)} materials | Ethanol: ~{50-tr/1000:.0f}mL")
w("")
w(f"## Formula")
w(f"")
w(f"| # | Role | Material | Dilution | Raw uL | Active uL |")
w(f"|---:|------|----------|----------|-------:|----------:|")
for i,r in enumerate(rows):
    w(f"| {i+1:>2} | {r['role']} | {r['mat']} | {r['dil']} | {r['raw']:>7.1f} | {r['a']:>8.1f} |")
w("")
w("> Pipette in order. Fill to 50mL line with ethanol. Invert 50x. Macerate 4 weeks.")
w("")
w(f"## Headspace OAV")
w(f"")
w(f"| # | Material | Active uL | VP(Pa) | ODT(ppb) | OAV | % |")
w(f"|---:|----------|----------:|-------:|---------:|----:|---:|")
for i,r in enumerate(R):
    ods=f"{r['odt']:.4g}" if r['odt'] else "-"
    ic="*" if r["mat"]==cn else ""
    w(f"| {i+1:>2} | {r['mat']:<26} | {r['a']:>8.1f} | {r['vp']:>5.4f} | {ods:>7} | {r['oav']:>6,.0f} | {r['oav']/T*100:>4.1f}% {ic}|")
w("")
w(f"**Total OAV:** {T:,.0f} | **Fruit Rank:** #{fr} | **Fruit Share:** {cp:.1f}% | **Flower Share:** {fp:.1f}%")
w("")
w("## 30mL Version")
w(f"- Scale all doses x0.6. Ethyl Maltol: {2*0.6:.1f}uL active / {20*0.6:.0f}uL raw of 10%.")
w(f"- Concentrate: {tr*0.6:.0f}uL. Fill to 30mL with ethanol.")

path="formulas/demachy_redux/DHC_VII_Lemon_Lemonade_Chanel.md"
with open(path,"w",encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Written {path}")
print(f"Total OAV: {T:,.0f} | Fruit Rank: #{fr} | Fruit Share: {cp:.1f}% | Flower Share: {fp:.1f}%")
