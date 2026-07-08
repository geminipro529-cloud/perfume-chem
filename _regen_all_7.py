"""Regen all 7 DHC Veritas formulas with 'lemonade' adjustments:
more hedione, more linalyl acetate, more flower, less petitgrain."""
import sys, os
sys.path.insert(0,'.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name
PPM=20.0
E={'petitgrain eo':4,'cardamom eo':3,'ethyl linalool':15,'norlimbanol dextro':0.8,'vetival':7.0,'paradisamide':8.0,'romandolide':4.9,'ethylene brassylate':0.97,'ambrettolide':0.136,'dihydrojasmone':0.75,'aurantiol':30,'benzoin resinoid':3,'javanol':0.0016,'iso e super':0.05,'hedione':0.05,'hedione hc':20,'linalyl acetate':2.7,'bergamot fcf sicilian':15,'cedrat fcf sicilian':10,'grapefruit fcf':3,'lime distilled eo':12,'red mandarin eo':10,'blood orange sicilian':8,'lemon fcf oil sicilian':10,'ambrofix':0.3,'kephalis':50,'floralozone':1.0,'scentenal':0.02,'damascenone':0.004,'alpha damascone':0.04,'geraniol':2.22,'citronellol':40,'methyl pamplemousse':3.0,'hydroxycitronellal':15,'nympheal':2,'mayol':3,'jasmine fo':15}
for k,o in E.items():
    if k in ODT_DATA: ODT_DATA[k]['odt_air']=o
    else: ODT_DATA[k]={'odt_air':o}
def vp_odt(n):
    p=get_profile(n); vp=p.vp if p and p.vp else 0
    k='hedione hc' if n.lower()=='hedione hc' else normalize_name(n)
    return vp, ODT_DATA.get(k,{}).get('odt_air')
def oav(a,v,o): return v*a*PPM/o if v and o else 0
DRY=[("Iso E Super",500),("Romandolide",480),("Ethylene Brassylate",380),("Ambrofix",18),("Norlimbanol Dextro",42),("Vetival",40),("Javanol",16),("Cardamom EO",5)]

# ADJUSTED: more hedione (+100), more HC (+50), more LAc (+40-50), more flower, petitgrain cut
FS={
"I":{"n":"I Bergamot + Orange Blossom","hse":"Dior / Demachy","tree":"Bergamot (Citrus bergamia) + Orange blossom","sc":8.8,
    "c":("Bergamot FCF Sicilian",6500),"p":250,"la":120,"h":1200,"hh":500,"el":550,
    "fl":[("Orange blossom","Aurantiol",10,100),("Jasmine","Dihydrojasmone",45,45),("Apple depth","Damascenone",0.0015,0.15)]},
"II":{"n":"II Cedrat + Citron Blossom","hse":"Le Labo / Bugey","tree":"Citron (Citrus medica) + Citron blossom","sc":9.0,
    "c":("Cedrat FCF Sicilian",6500),"p":300,"la":120,"h":1100,"hh":450,"el":500,
    "fl":[("Citron blossom","Hydroxycitronellal",14,14),("Green-ozone","Floralozone",0.15,1.5)]},
"III":{"n":"III Grapefruit + Grapefruit Blossom","hse":"Tom Ford / Flores-Roux","tree":"Grapefruit (Citrus paradisi) + Grapefruit blossom","sc":9.5,
    "c":("Grapefruit FCF",5500),"p":300,"la":150,"h":1300,"hh":550,"el":600,
    "fl":[("Grapefruit blossom","Dihydrojasmone",25,25),("Tropical sweet","Paradisamide",2.0,20),("Grapefruit skin","Methyl Pamplemousse",2.0,20)]},
"IV":{"n":"IV Lime + Lime Blossom","hse":"Hermes / Nagel","tree":"Lime (Citrus aurantiifolia) + Lime blossom","sc":8.5,
    "c":("Lime Distilled EO",6500),"p":300,"la":120,"h":1100,"hh":450,"el":500,
    "fl":[("Lime blossom","Hydroxycitronellal",14,14),("Muguet body","Mayol",6,6),("Green-ozone","Floralozone",0.15,1.5)]},
"V":{"n":"V Mandarin + Mandarin Blossom","hse":"Malle / Ropion","tree":"Mandarin (Citrus reticulata) + Mandarin blossom","sc":8.7,
    "c":("Red Mandarin EO",6000),"p":250,"la":150,"h":1150,"hh":500,"el":500,
    "fl":[("Mandarin blossom","Aurantiol",10,100),("Jasmine","Dihydrojasmone",50,50),("Jasmine accord","Jasmine FO",70,70),("Apple depth","Damascenone",0.0015,0.15),("Balsamic","Benzoin Resinoid",12,12)]},
"VI":{"n":"VI Blood Orange + Orange Blossom","hse":"Guerlain / Wasser","tree":"Blood Orange (Citrus sinensis) + Orange blossom","sc":9.3,
    "c":("Blood Orange Sicilian",6000),"p":250,"la":120,"h":1150,"hh":500,"el":550,
    "fl":[("Orange blossom","Aurantiol",12,120),("Honeyed jasmine","Dihydrojasmone",40,40),("Berry depth","Damascenone",0.0035,0.35),("Balsamic bridge","Benzoin Resinoid",12,12)]},
"VII":{"n":"VII Lemon + Lemon Blossom","hse":"Chanel / Polge","tree":"Lemon (Citrus limon) + Lemon blossom","sc":9.0,
    "c":("Lemon FCF oil Sicilian",6500),"p":250,"la":120,"h":1150,"hh":500,"el":550,
    "fl":[("Lemon blossom","Hydroxycitronellal",12,12),("Crystalline lily","Nympheal",6,6),("Metallic sparkle","Scentenal",0.02,2),("Ozone air","Floralozone",0.15,1.5)]},
}

out_dir="formulas/demachy_redux"; os.makedirs(out_dir,exist_ok=True)
FNS={k:f"DHC_{k}_Veritas.md" for k in FS}

print(f"  {'#':>3} {'Formula':<30} {'OAV':>8} {'Fruit#':>6} {'Fruit%':>6} {'Flower%':>7} {'Mats':>4} {'Score':>6}")
print(f"  {'-'*75}")
for k in ["III","VI","II","VII","I","V","IV"]:
    f=FS[k]; cn,cd=f["c"]
    ly=[("Petitgrain EO",f["p"],f["p"]),("Linalyl Acetate",f["la"],f["la"]),
        ("Hedione",f["h"],f["h"]),("Hedione HC",f["hh"],f["hh"]),
        ("Ethyl Linalool",f["el"],f["el"])]
    fn=set()
    for _,m,a,r in f["fl"]:
        if a>0: ly.append((m,a,r)); fn.add(m)
    for m,a in DRY: ly.append((m,a,a))
    ly.append((cn,cd,cd))
    rows=[(m,a,oav(a,*vp_odt(m))) for m,a,_ in ly]
    T=sum(r[2] for r in rows); R=sorted(rows,key=lambda r:r[2],reverse=True)
    cp=sum(r[2] for r in R if r[0]==cn)/T*100
    fp=sum(r[2] for r in R if r[0] in fn)/T*100
    fr=next(i+1 for i,r in enumerate(R) if r[0]==cn)
    ta=sum(r[1] for r in rows)
    print(f"  {sorted(['III','VI','II','VII','I','V','IV'],key=lambda x:FS[x]['sc'],reverse=True).index(k)+1:>3} {f['n']:<30} {T:>8,.0f} {fr:>6} {cp:>5.1f}% {fp:>6.1f}% {len(rows):>4} {f['sc']:>5.1f}")

    # Write file
    md=[f"# {f['n']}",f"","**House:** {f['hse']} | **Tree:** {f['tree']}",
        f"**Hedione:** {f['h']}uL H + {f['hh']}uL HC ({f['hh']/(f['h']+f['hh'])*100:.0f}% HC) | **Score:** {f['sc']}/10",
        f"","## Batch Data",
        f"- 50mL EdP | {sum(a for _,a,_ in ly)+sum(r-a for _,a,r in ly if r>a):,.0f}uL raw / {ta:,.0f}uL active | ~{ta/1000/50*100:.0f}% | {len(rows)} mats",
        f"","## Formula","",
        f"| # | Role | Material | Dilution | Raw uL | Active uL |",
        f"|---:|------|----------|----------|-------:|----------:|"]
    layers=[("PETITGRAIN","Petitgrain EO",f["p"],f["p"]),
            ("LINALYL AC","Linalyl Acetate",f["la"],f["la"]),
            ("RADIANCE","Hedione",f["h"],f["h"]),("HC SWEET","Hedione HC",f["hh"],f["hh"]),
            ("CLEAN LIFT","Ethyl Linalool",f["el"],f["el"])]
    for _,m,a,r in f["fl"]:
        if a>0: layers.append(("FLOWER",m,a,r))
    for m,a in DRY: layers.append(("DRYDOWN",m,a,a))
    layers.append(("STAR CITRUS",cn,cd,cd))
    for i,(role,mat,a,r) in enumerate(layers):
        dil="neat" if abs(a-r)<0.1 else f"{a/r*100:.0f}%"
        md.append(f"| {i+1:>2} | {role} | {mat} | {dil} | {r:>7.1f} | {a:>8.1f} |")
    md.extend(["",f"## Headspace OAV","",
               f"| # | Material | Active uL | VP(Pa) | ODT(ppb) | OAV | % |",
               f"|---:|----------|----------:|-------:|---------:|----:|---:|"])
    for i,(m,a,ov) in enumerate(R):
        ods=f"{ODT_DATA.get(normalize_name(m),{}).get('odt_air',''):.4g}"
        ic="C" if m==cn else "F" if m in fn else ""
        md.append(f"| {i+1:>2} | {m:<26} | {a:>8.1f} | {vp_odt(m)[0]:>5.4f} | {ods:>7} | {ov:>6,.0f} | {ov/T*100:>4.1f}% {ic}|")
    md.extend(["",f"**Total OAV:** {T:,.0f} | **Fruit Rank:** #{fr} | **Fruit Share:** {cp:.1f}% | **Flower Share:** {fp:.1f}%",""])
    with open(os.path.join(out_dir,FNS[k]),"w",encoding="utf-8") as fh: fh.write("\n".join(md))
    print(f"  -> {FNS[k]}")

print(f"\n  All 7 written to {out_dir}/")
