"""OAV recalculation after internet-verified ODT corrections.
Uses updated engine/odor_thresholds.py with peer-reviewed values.
"""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

def mat_odt_and_vp(name):
    n = normalize_name(name)
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    odt = ODT_DATA.get(n, {}) or ODT_DATA.get(name.lower(), {})
    odt_air = odt.get('odt_air')
    return vp, odt_air

def h_oav(a, vp, odt):
    return vp * a * PPM / odt if vp and odt else 0

# Full formula data from the 5 DHCs
# Format: (material_name, active_uL)
formulas = {
    "I Bergamot (Dior+Creed)": [
        ("Bergamot FCF Sicilian",2900),("Linalyl Acetate",200),("Aurantiol",0.8),
        ("Hedione",1450),("Petitgrain EO",620),("Ethyl Linalool",600),("Hedione HC",180),("Paradisamide",3.5),
        ("Romandolide",500),("Iso E Super",480),("Vertofix",80),("Javanol",20),("Ambrofix",17.4),
        ("Ethylene Brassylate",413),("Ambrettolide",1.25),("Norlimbanol Dextro",45),("Vetival",43),("Cardamom EO",5),("Alpha Irone",0.45),
    ],
    "II Cedrat (Prada+Le Labo)": [
        ("Cedrat FCF Sicilian",3000),("Linalyl Acetate",200),
        ("Petitgrain EO",650),("Hedione",1300),("Hedione HC",160),("Paradisamide",3.5),
        ("Romandolide",480),("Iso E Super",380),("Kephalis",12),("Suederal",1.2),("Costus Olifac",0.5),
        ("Ambrofix",19.5),("Ethylene Brassylate",370),("Ambrettolide",1.25),("Norlimbanol Dextro",45),("Vetival",43),("Alpha Irone",0.45),
    ],
    "III Grapefruit (JM+Atelier)": [
        ("Grapefruit FCF",1950),("Linalyl Acetate",450),("Apritone",2),
        ("Hedione",1400),("Petitgrain EO",650),("Ethyl Linalool",550),("Floralozone",1.2),("Hedione HC",170),("Paradisamide",5.5),
        ("Romandolide",550),("Iso E Super",500),("Ambrofix",16.5),
        ("Ethylene Brassylate",380),("Ambrettolide",1.25),("Norlimbanol Dextro",45),("Vetival",43),("Cardamom EO",5),("Alpha Irone",0.45),
    ],
    "IV Lime (Hermes+Byredo)": [
        ("Lime Distilled EO",3100),("Linalyl Acetate",180),("Scentenal",0.1),
        ("Hedione",1300),("Petitgrain EO",680),("Floralozone",0.8),("Hedione HC",150),("Paradisamide",3.5),
        ("Romandolide",420),("Iso E Super",400),("Ambrofix",15.6),
        ("Ethylene Brassylate",330),("Ambrettolide",1.25),("Norlimbanol Dextro",45),("Vetival",80),("Cardamom EO",5),("Alpha Irone",0.45),
    ],
    "V Mandarin (TF+Malle)": [
        ("Red Mandarin EO",2600),("Linalyl Acetate",280),
        ("Hedione",1350),("Petitgrain EO",550),("Ethyl Linalool",480),("Hedione HC",180),("Paradisamide",3.5),("Dihydrojasmone",30),("Jasmine FO",60),
        ("Romandolide",520),("Iso E Super",500),("Benzoin Resinoid",17.5),
        ("Ambrofix",18),("Ethylene Brassylate",350),("Ambrettolide",2),("Norlimbanol Dextro",45),("Vetival",43),("Cardamom EO",5),("Alpha Irone",0.45),
    ],
}

out = []
w = out.append

w("OAV RECALCULATION — Peer-Reviewed ODT Fixes Applied")
w("=" * 100)
w("")
w("Changed ODT entries:")
w(f"  {'Material':<25} {'Old ODT':>10} {'New ODT':>10} Source")
w(f"  {'─'*75}")
changes = [
    ("dihydrojasmone", "50.0", "0.75", "van Gemert 2011"),
    ("vertofix coeur", "1.0", "6.3", "van Gemert 2011 / Devos 1990"),
    ("vertofix", "1.0", "6.3", "van Gemert 2011 / Devos 1990"),
    ("alpha irone", "3.8", "0.9", "van Gemert 2011 (RIFM)"),
    ("linalyl acetate", "13.8", "50.0", "Elsharif et al. 2015"),
    ("aurantiol", "0.25", "30.0", "TGSC VP + structural analog"),
    ("ethylene brassylate", "2.0", "0.97", "van Gemert 2011 (RIFM)"),
    ("bergamot fcf sicilian", "15.0", "4.0", "constituent estimate (linalool/linalyl acetate)"),
    ("bergamot fcf", "15.0", "4.0", "constituent estimate"),
    ("bergamot", "8.0", "4.0", "constituent estimate"),
    ("petitgrain eo", "12.0", "4.0", "constituent estimate (linalool/linalyl acetate/geraniol)"),
    ("ethyl linalool", "8.0", "1.5", "linalool homolog estimate"),
    ("benzoin resinoid", "50.0", "3.0", "constituent estimate (vanillin)"),
]
for name, old, new, src in changes:
    w(f"  {name:<25} {old:>10} {new:>10} {src}")
w("")

for label, mats in formulas.items():
    rows = []
    for name, active in mats:
        vp, odt = mat_odt_and_vp(name)
        oav = h_oav(active, vp, odt)
        rows.append({"name": name, "active": active, "oav": oav, "odt": odt, "vp": vp})

    total = sum(r["oav"] for r in rows)
    ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)

    w(f"{'─'*100}")
    w(f"  {label}")
    w(f"{'─'*100}")
    w(f"  {'Rank':>4} {'Material':<26} {'Active':>7} {'VP(Pa)':>8} {'ODT(ppb)':>10} {'OAV':>14} {'%Share':>7}")
    w(f"  {'─'*95}")

    for i, r in enumerate(ranked):
        flag = ""
        if r["oav"] == 0 and r["active"] > 0:
            flag = " ⚠ NO VP/ODT"
        odt_str = f"{r['odt']:.4g}" if r['odt'] is not None else "???"
        w(f"  {i+1:>4} {r['name']:<26} {r['active']:>7.1f} {r['vp']:>8.4f} {odt_str:>10} {r['oav']:>14,.0f} {r['oav']/max(total,1)*100:>6.1f}%{flag}")

    w(f"\n  Total OAV: {total:,.0f}")
    w(f"  Star: {ranked[0]['name']} ({ranked[0]['oav']/total*100:.1f}%)")
    w(f"  Top shelf: {', '.join(r['name'] for r in ranked[:5])}")
    w(f"  Citrus headspace share: {sum(r['oav'] for r in ranked if any(c in r['name'].lower() for c in ['bergamot','cedrat','grapefruit','lime','mandarin','petitgrain']))/total*100:.1f}%")
    w("")

w(f"{'='*100}")
w(" COMPARISON: Before vs After ODT Fixes")
w(f"{'='*100}")
w(f"  {'Formula':<30} {'Before':>12} {'After':>12} {'Delta':>12}")
w(f"  {'─'*66}")

# Pre-fix values (from previous run)
before = {"I Bergamot (Dior+Creed)": 207667, "II Cedrat (Prada+Le Labo)": 176252,
           "III Grapefruit (JM+Atelier)": 202799, "IV Lime (Hermes+Byredo)": 177072,
           "V Mandarin (TF+Malle)": 192617}

for label in formulas:
    rows = []
    for name, active in formulas[label]:
        vp, odt = mat_odt_and_vp(name)
        rows.append(h_oav(active, vp, odt))
    after_total = sum(rows)
    bef = before.get(label, 0)
    w(f"  {label:<30} {bef:>12,.0f} {after_total:>12,.0f} {after_total-bef:>+12,.0f}")

with open("_oav_recalc.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Written to _oav_recalc.txt")
