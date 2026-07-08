#!/usr/bin/env python3
"""Generate final DHC I-V formulas after house reviews. 50 mL EDP."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0
def mat(name):
    n = normalize_name(name)
    p = get_profile(name)
    odt = ODT_DATA.get(n,{}) or ODT_DATA.get(name.lower(),{})
    return p.vp if p and p.vp else 0, odt.get('odt_air'), odt.get('odt_eth')
def h_oav(a,vp,odt): return vp*a*PPM/odt if vp and odt else 0

variants = {
    "I Bergamot": {
        "profile": "Classical reference. Naked bergamot with Dior structure, Creed whisper.",
        "reviewers": "Dior + Creed",
        "dior_notes": "More naked bergamot. Less Petitgrain bridge. Vertofix backbone. Ambrofix slight boost.",
        "creed_notes": "Less Linalyl Acetate (synthetic freshness cheapens). More Ethyl Linalool. Javanol whisper.",
        "formula": [
            ("Bergamot FCF Sicilian","neat",2900),
            ("Linalyl Acetate","neat",200),
            ("Aurantiol","10%",8),
            ("Hedione","neat",1450),
            ("Petitgrain EO","neat",620),
            ("Ethyl Linalool","neat",600),
            ("Hedione HC","neat",180),
            ("Paradisamide","10%",35),
            ("Romandolide","neat",500),
            ("Iso E Super","neat",480),
            ("Vertofix","neat",80),
            ("Javanol","neat",20),
            ("Ambrofix","30%",58),
            ("Ethylene Brassylate","neat",413),
            ("Ambrettolide","10%",12.5),
            ("Norlimbanol Dextro","neat",45),
            ("Vetival","neat",43),
            ("Cardamom EO","neat",5),
            ("Alpha Irone","30% DEP",1.5),
        ],
    },
    "II Cedrat": {
        "profile": "Mineral extreme. Prada industrial precision, Le Labo head-tilt.",
        "reviewers": "Prada + Le Labo",
        "prada_notes": "No floral softness. Suede whisper. Kephalis edge. Less IES cocoon.",
        "le_labo_notes": "Costus Olifac trace -- does not belong, makes them ask. No Cardamom -- too conventional. Ambrofix boosted.",
        "formula": [
            ("Cedrat FCF Sicilian","neat",3000),
            ("Linalyl Acetate","neat",200),
            ("Petitgrain EO","neat",650),
            ("Hedione","neat",1300),
            ("Hedione HC","neat",160),
            ("Paradisamide","10%",35),
            ("Romandolide","neat",480),
            ("Iso E Super","neat",380),
            ("Kephalis","neat",12),
            ("Suederal","10%",12),
            ("Costus Olifac","10% DPG",5),
            ("Ambrofix","30%",65),
            ("Ethylene Brassylate","neat",370),
            ("Ambrettolide","10%",12.5),
            ("Norlimbanol Dextro","neat",45),
            ("Vetival","neat",43),
            ("Alpha Irone","30% DEP",1.5),
        ],
    },
    "III Grapefruit": {
        "profile": "Cheerful crowd. Jo Malone botanical truth, Atelier citrus saturation.",
        "reviewers": "Jo Malone + Atelier Cologne",
        "jo_malone_notes": "More Paradisamide -- grapefruit blossom IS the story. Floralozone grove-air. Romandolide boost for layering projection. Less Ambrofix to stay botanical.",
        "atelier_notes": "More Grapefruit -- saturated. Apritone fruity lift. Less Ethyl Linalool -- let grapefruit sing.",
        "formula": [
            ("Grapefruit FCF","neat",1950),
            ("Linalyl Acetate","neat",450),
            ("Apritone","10%",20),
            ("Hedione","neat",1400),
            ("Petitgrain EO","neat",650),
            ("Ethyl Linalool","neat",550),
            ("Floralozone","10%",12),
            ("Hedione HC","neat",170),
            ("Paradisamide","10%",55),
            ("Romandolide","neat",550),
            ("Iso E Super","neat",500),
            ("Ambrofix","30%",55),
            ("Ethylene Brassylate","neat",380),
            ("Ambrettolide","10%",12.5),
            ("Norlimbanol Dextro","neat",45),
            ("Vetival","neat",43),
            ("Cardamom EO","neat",5),
            ("Alpha Irone","30% DEP",1.5),
        ],
    },
    "IV Lime": {
        "profile": "Transparent ghost. Hermes Ellena water-color, Byredo skin-feel.",
        "reviewers": "Hermes + Byredo",
        "hermes_notes": "Scentenal -- the water. The lime should feel like a freshly cut wedge on a wet counter. Floralozone for Ellena transparency. Vetival skeleton.",
        "byredo_notes": "More Ambrofix -- Ben Gorham skin-feel. More IES cocoon -- Byredo fragrances cling to fabric.",
        "formula": [
            ("Lime Distilled EO","neat",3100),
            ("Linalyl Acetate","neat",180),
            ("Scentenal","1%",10),
            ("Hedione","neat",1300),
            ("Petitgrain EO","neat",680),
            ("Floralozone","10%",8),
            ("Hedione HC","neat",150),
            ("Paradisamide","10%",35),
            ("Romandolide","neat",420),
            ("Iso E Super","neat",400),
            ("Ambrofix","30%",52),
            ("Ethylene Brassylate","neat",330),
            ("Ambrettolide","10%",12.5),
            ("Norlimbanol Dextro","neat",45),
            ("Vetival","neat",80),
            ("Cardamom EO","neat",5),
            ("Alpha Irone","30% DEP",1.5),
        ],
    },
    "V Mandarin": {
        "profile": "Golden sunset. Tom Ford sensual warmth, Malle perfumer's balance.",
        "reviewers": "Tom Ford + Frederic Malle",
        "tom_ford_notes": "More Ambrettolide -- skin intimacy. Stronger Dihydrojasmone. More Benzoin warmth. Tom Ford fragrances are worn ON the body.",
        "malle_notes": "Slightly less Mandarin -- let jasmine share the stage. More Jasmine FO. Jasmine IS the bridge, reduce Petitgrain accordingly.",
        "formula": [
            ("Red Mandarin EO","neat",2600),
            ("Linalyl Acetate","neat",280),
            ("Hedione","neat",1350),
            ("Petitgrain EO","neat",550),
            ("Ethyl Linalool","neat",480),
            ("Hedione HC","neat",180),
            ("Paradisamide","10%",35),
            ("Dihydrojasmone","neat",30),
            ("Jasmine FO","neat",60),
            ("Romandolide","neat",520),
            ("Iso E Super","neat",500),
            ("Benzoin Resinoid","50% DPG",35),
            ("Ambrofix","30%",60),
            ("Ethylene Brassylate","neat",350),
            ("Ambrettolide","10%",20),
            ("Norlimbanol Dextro","neat",45),
            ("Vetival","neat",43),
            ("Cardamom EO","neat",5),
            ("Alpha Irone","30% DEP",1.5),
        ],
    },
}

OUT = "formulas/oav_balanced"
files = {
    "I Bergamot":"DHC_I__Bergamot_50mL_EdP.md",
    "II Cedrat":"DHC_II_Cedrat_50mL_EdP.md",
    "III Grapefruit":"DHC_III_Grapefruit_50mL_EdP.md",
    "IV Lime":"DHC_IV_Lime_50mL_EdP.md",
    "V Mandarin":"DHC_V__Mandarin_50mL_EdP.md",
}

for label, spec in variants.items():
    rows = []
    for name, dil, active in spec["formula"]:
        vp, odt_a, odt_e = mat(name)
        oav_h = h_oav(active, vp, odt_a)
        l_oav = active*PPM/odt_e if odt_e else 0
        dil_f = 1.0
        if "30%" in dil: dil_f = 0.3
        elif "10%" in dil: dil_f = 0.1
        elif "50%" in dil: dil_f = 0.5
        elif "1%" in dil: dil_f = 0.01
        raw = active / dil_f
        rows.append({"name":name,"dil":dil,"active":active,"raw":raw,"h_oav":round(oav_h),"l_oav":round(l_oav),"vp":vp,"odt_a":odt_a})

    total_h = sum(r["h_oav"] for r in rows)
    ranked = sorted(rows, key=lambda r: r["h_oav"], reverse=True)
    star = ranked[0]
    total_active = sum(r["active"] for r in rows)
    total_raw = sum(r["raw"] for r in rows)
    conc = total_active / 50000 * 100

    md = []
    w = md.append
    w(f"# DHC {label} -- 50 mL EdP ({conc:.0f}%) -- House-Reviewed")
    w("")
    w(f"**Profile:** {spec['profile']}")
    w(f"**Reviewed by:** {spec['reviewers']}")
    w(f"**Concentrate:** {total_raw:.0f} uL raw / {total_active:.0f} active  |  Ethanol: ~{50-total_raw/1000:.0f} mL")
    w("")
    for house_key in [k for k in spec if k.endswith("_notes")]:
        house = house_key.replace("_notes","").replace("_"," ").title()
        w(f"**{house}:** {spec[house_key]}")
    w("")
    w("## Formula")
    w("")
    w("Pipette base first, then heart, then top. Swirl gently between layers.")
    w("")
    w("| # | Material | Dilution | Raw uL | Active uL | Headspace OAV |")
    w("|--:|----------|----------|-------:|----------:|-------------:|")
    n = 0
    for r in sorted(rows, key=lambda r: r["h_oav"], reverse=True):
        n += 1
        star_mark = " <-- STAR" if r is star else ""
        w(f"| {n} | {r['name']} | {r['dil']} | {r['raw']:.1f} | {r['active']:.1f} | {r['h_oav']:,}{star_mark} |")
    w("")
    w(f"Add ethanol to 50 mL line. Invert 50x. Macerate 4 weeks.")
    w("")
    w("## Headspace OAV Ranked")
    w("")
    w("| # | Material | Active uL | VP(Pa) | ODT(ppb) | OAV | % of Total |")
    w("|--:|----------|----------:|-------:|---------:|----:|----------:|")
    for i, r in enumerate(ranked, 1):
        pct = r["h_oav"]/total_h*100 if total_h else 0
        star_m = " <-- STAR" if i == 1 else ""
        w(f"| {i} | {r['name']} | {r['active']:.1f} | {r['vp']:.3f} | {r['odt_a']:.1f} | {r['h_oav']:,} | {pct:.0f}%{star_m} |")
    w("")
    dom = sum(1 for r in rows if r["h_oav"]>=50)
    sub = sum(1 for r in rows if r["h_oav"]<1)
    w(f"Total: {total_h:,}  |  Star: {star['name']} ({star['h_oav']/total_h*100:.0f}%)  |  Dominant:{dom}  Subliminal:{sub}")
    w(f"Materials: {len(rows)}")
    w("")
    w("Allergens: Linalool, Geraniol (from citrus EO, Petitgrain, Linalyl Acetate)")

    with open(f"{OUT}/{files[label]}", "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"Wrote {files[label]}")

print("\nAll 5 final DHC formulas written with house reviews applied.")
