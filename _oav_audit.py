#!/usr/bin/env python3
"""Clean OAV audit of architecturally-tuned DHC formulas."""

import sys
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0

def mat(name):
    n = normalize_name(name)
    p = get_profile(name)
    odt = ODT_DATA.get(n, {}) or ODT_DATA.get(name.lower(), {})
    return p.vp if p and p.vp else 0, odt.get('odt_air'), odt.get('odt_eth')

def h_oav(active, vp, odt_a):
    return vp * active * PPM / odt_a if vp and odt_a else 0

def band(o):
    if o >= 50: return 'DOM'
    if o >= 5:  return 'STR'
    if o >= 1:  return 'ACT'
    return 'SUB'

variants = {
    "I Bergamot (Calabria)": [
        ("Bergamot FCF Sicilian", "neat", 2800, "T"),
        ("Linalyl Acetate",       "neat",  280, "T"),
        ("Aurantiol",             "10%",     8, "T"),
        ("Petitgrain EO",         "neat",  700, "H"),
        ("Hedione",               "neat", 1450, "H"),
        ("Ethyl Linalool",        "neat",  500, "H"),
        ("Hedione HC",            "neat",  180, "H"),
        ("Paradisamide",          "10%",    35, "H"),
        ("Romandolide",           "neat",  500, "B"),
        ("Iso E Super",           "neat",  480, "B"),
        ("Vertofix",              "neat",   60, "B"),
        ("Ambrofix",              "30%",  55.5, "B"),
        ("Ethylene Brassylate",   "neat",  413, "B"),
        ("Ambrettolide",          "10%",  12.5, "B"),
        ("Norlimbanol Dextro",    "neat",   45, "B"),
        ("Vetival",               "neat",   43, "B"),
        ("Cardamom EO",           "neat",    5, "B"),
        ("Alpha Irone",           "30% DEP",1.5, "B"),
    ],
    "II Cedrat (Mediterranean)": [
        ("Cedrat FCF Sicilian",   "neat", 3000, "T"),
        ("Linalyl Acetate",       "neat",  200, "T"),
        ("Petitgrain EO",         "neat",  650, "H"),
        ("Hedione",               "neat", 1300, "H"),
        ("Ethyl Linalool",        "neat",  400, "H"),
        ("Hedione HC",            "neat",  160, "H"),
        ("Paradisamide",          "10%",    35, "H"),
        ("Romandolide",           "neat",  480, "B"),
        ("Iso E Super",           "neat",  420, "B"),
        ("Kephalis",              "neat",    8, "B"),
        ("Ambrofix",              "30%",    60, "B"),
        ("Ethylene Brassylate",   "neat",  370, "B"),
        ("Ambrettolide",          "10%",  12.5, "B"),
        ("Norlimbanol Dextro",    "neat",   45, "B"),
        ("Vetival",               "neat",   43, "B"),
        ("Cardamom EO",           "neat",    5, "B"),
        ("Alpha Irone",           "30% DEP",1.5, "B"),
    ],
    "III Grapefruit (Tropical)": [
        ("Grapefruit FCF",        "neat", 1850, "T"),
        ("Linalyl Acetate",       "neat",  450, "T"),
        ("Petitgrain EO",         "neat",  650, "H"),
        ("Hedione",               "neat", 1400, "H"),
        ("Ethyl Linalool",        "neat",  600, "H"),
        ("Hedione HC",            "neat",  170, "H"),
        ("Paradisamide",          "10%",    45, "H"),
        ("Romandolide",           "neat",  500, "B"),
        ("Iso E Super",           "neat",  500, "B"),
        ("Ambrofix",              "30%",    65, "B"),
        ("Ethylene Brassylate",   "neat",  380, "B"),
        ("Ambrettolide",          "10%",  12.5, "B"),
        ("Norlimbanol Dextro",    "neat",   45, "B"),
        ("Vetival",               "neat",   43, "B"),
        ("Cardamom EO",           "neat",    5, "B"),
        ("Alpha Irone",           "30% DEP",1.5, "B"),
    ],
    "IV Lime (Caribbean)": [
        ("Lime Distilled EO",     "neat", 3100, "T"),
        ("Linalyl Acetate",       "neat",  180, "T"),
        ("Petitgrain EO",         "neat",  680, "H"),
        ("Hedione",               "neat", 1300, "H"),
        ("Ethyl Linalool",        "neat",  400, "H"),
        ("Hedione HC",            "neat",  150, "H"),
        ("Paradisamide",          "10%",    35, "H"),
        ("Romandolide",           "neat",  420, "B"),
        ("Iso E Super",           "neat",  380, "B"),
        ("Ambrofix",              "30%",    48, "B"),
        ("Ethylene Brassylate",   "neat",  330, "B"),
        ("Ambrettolide",          "10%",  12.5, "B"),
        ("Norlimbanol Dextro",    "neat",   45, "B"),
        ("Vetival",               "neat",   70, "B"),
        ("Cardamom EO",           "neat",    5, "B"),
        ("Alpha Irone",           "30% DEP",1.5, "B"),
    ],
    "V Mandarin (Sicily)": [
        ("Red Mandarin EO",       "neat", 2800, "T"),
        ("Linalyl Acetate",       "neat",  280, "T"),
        ("Petitgrain EO",         "neat",  600, "H"),
        ("Hedione",               "neat", 1350, "H"),
        ("Ethyl Linalool",        "neat",  480, "H"),
        ("Hedione HC",            "neat",  180, "H"),
        ("Paradisamide",          "10%",    35, "H"),
        ("Dihydrojasmone",        "neat",   20, "H"),
        ("Jasmine FO",            "neat",   40, "H"),
        ("Romandolide",           "neat",  520, "B"),
        ("Iso E Super",           "neat",  500, "B"),
        ("Benzoin Resinoid",      "50% DPG",25, "B"),
        ("Ambrofix",              "30%",    60, "B"),
        ("Ethylene Brassylate",   "neat",  350, "B"),
        ("Ambrettolide",          "10%",  12.5, "B"),
        ("Norlimbanol Dextro",    "neat",   45, "B"),
        ("Vetival",               "neat",   43, "B"),
        ("Cardamom EO",           "neat",    5, "B"),
        ("Alpha Irone",           "30% DEP",1.5, "B"),
    ],
}

out = []
def w(s=""): out.append(s)

w("DHC ARCHITECTURAL OAV AUDIT  (VP x ppm / ODT_air -- headspace at 32C, 50 mL EDP)")
w("=" * 87)

for label, formula in variants.items():
    rows = []
    for name, dil, active, layer in formula:
        vp, odt_a, _ = mat(name)
        oav = h_oav(active, vp, odt_a)
        rows.append({"name": name, "layer": layer, "active": active, "oav": round(oav), "vp": vp, "odt_air": odt_a})

    ranked = sorted(rows, key=lambda r: r["oav"], reverse=True)

    total = sum(r["oav"] for r in rows)
    top_h = sum(r["oav"] for r in rows if r["layer"] == "T")
    heart_h = sum(r["oav"] for r in rows if r["layer"] == "H")
    base_h = sum(r["oav"] for r in rows if r["layer"] == "B")
    dom = sum(1 for r in rows if r["oav"] >= 50)
    sub = sum(1 for r in rows if r["oav"] < 1)
    star = ranked[0]

    w(f"\n  {'-' * 80}")
    w(f"  {label}")
    w(f"  {'-' * 80}")
    w(f"  {'#':<4} {'Material':<26} {'uL':>7} {'OAV':>8} {'%':>5} {'Band':>6}  {'Layer'}")
    w(f"  {'-' * 72}")
    for i, r in enumerate(ranked, 1):
        pct = r["oav"] / total * 100 if total else 0
        marker = " <-- STAR" if i == 1 else ""
        w(f"  {i:<4} {r['name']:<26} {r['active']:>7.0f} {r['oav']:>8,} {pct:>4.0f}% {band(r['oav']):>6}  {r['layer']}{marker}")
    w(f"\n  Total: {total:,.0f} OAV  |  T:{top_h/total*100:.0f}% H:{heart_h/total*100:.0f}% B:{base_h/total*100:.0f}%  |  B:T={base_h/top_h:.2f}:1")
    w(f"  {dom} dominant  |  {sub} subliminal  |  {len(rows)} materials")
    w(f"  Star: {star['name']} -- {star['oav']:,} OAV ({star['oav']/total*100:.0f}%)")

# Summary
w(f"\n\n{'='*87}")
w(f"  CONSOLIDATED")
w(f"{'='*87}")
w(f"  {'Metric':<24} {'I Bergamot':>13} {'II Cedrat':>13} {'III Grape':>13} {'IV Lime':>13} {'V Mandarin':>13}")
w(f"  {'-'*82}")

all_data = {}
for label, formula in variants.items():
    rows = []
    for name, dil, active, layer in formula:
        vp, odt_a, _ = mat(name)
        oav = h_oav(active, vp, odt_a)
        rows.append(oav)
    total = sum(rows)
    ranked = sorted(rows, reverse=True)
    top_sum = sum(r for i,r in enumerate(rows) if any("T" == formula[j][3] for j in range(len(formula)) if abs(formula[j][2] - formula[i][2]) < 0.01))  # this won't work cleanly

    # Recompute properly
    tsum = hsum = bsum = 0
    for (n, d, a, l), o in zip(formula, rows):
        if l == "T": tsum += o
        elif l == "H": hsum += o
        else: bsum += o

    dom_n = sum(1 for o in rows if o >= 50)
    sub_n = sum(1 for o in rows if o < 1)
    star_oav = ranked[0]
    star_pct = star_oav / total * 100

    all_data[label] = {
        "total": total, "dom": dom_n, "sub": sub_n, "n": len(rows),
        "star_oav": star_oav, "star_pct": star_pct,
        "tpct": tsum/total*100, "hpct": hsum/total*100, "bpct": bsum/total*100,
        "bt": bsum/tsum
    }

for metric, fmt in [
    ("Total OAV",      lambda d: f"{d['total']:>13,.0f}"),
    ("Star OAV",       lambda d: f"{d['star_oav']:>13,.0f}"),
    ("Star %",         lambda d: f"{d['star_pct']:>12.0f}%"),
    ("Dominant",       lambda d: f"{d['dom']:>13d}"),
    ("Subliminal",     lambda d: f"{d['sub']:>13d}"),
    ("OAV T/H/B",      lambda d: f"{d['tpct']:.0f}/{d['hpct']:.0f}/{d['bpct']:.0f}%".rjust(13)),
    ("B:T",            lambda d: f"{d['bt']:>12.2f}:1"),
    ("Materials",      lambda d: f"{d['n']:>13d}"),
]:
    vals = "".join(fmt(all_data[d]) for d in variants)
    print(f"  {metric:<24}{vals}", file=sys.stderr if False else None)
    out.append(f"  {metric:<24}{vals}")

w(f"{'='*87}")

with open("_oav_audit_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Output written to _oav_audit_output.txt")
print("\n".join(out))
