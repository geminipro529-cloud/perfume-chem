"""Optimal split: find f such that Bottle A matches real DHC OAV profile."""
import sys; sys.path.insert(0,'.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8, "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

# Real DHC target (% of concentrate)
TARGET = {"Hedione": 25, "Cedrat FCF oil Sicilian": 20, "Lemon FCF oil Sicilian": 20,
          "Hedione HC": 5, "ISO E SUPER": 4, "Lime Distilled EO": 5, "Alpha Irone": 3,
          "Galaxolide": 6, "Habanolide": 2, "Ambrofix": 1, "Petitgrain EO": 1,
          "Aldehyde C10 (1%)": 0.1, "Citral": 0.1}
TOTAL_ACTIVE = 6000

def vp_odt(name):
    p = get_profile(name)
    vp = p.vp if p and p.vp else 0
    odt = (ODT_DATA.get(normalize_name(name), {}).get("odt_air"))
    return vp, odt or 0

def oav(a, vp, odt):
    return a * vp * PPM / odt if vp and odt else 0

def sim(f):
    existing = {n: v * f for n, v in EXISTING.items()}
    final = dict(existing)
    add = {}
    for m, pct in TARGET.items():
        key = "Iso E Super" if m == "ISO E SUPER" else m
        target = TOTAL_ACTIVE * pct / 100
        have = existing.get(key, 0)
        if target > have:
            add[m] = target - have
        final[key] = max(target, have)

    rows = []
    for n, a in final.items():
        v, o = vp_odt(n)
        if v and o: rows.append((n, a, oav(a, v, o)))
    total = sum(r[2] for r in rows)
    rows.sort(key=lambda x: x[2], reverse=True)

    iso_oav_pct = next((r[2]/total*100 for r in rows if "Iso" in r[0]), 0)
    bad = sum(r[2] for r in rows if r[0] not in set(TARGET.keys()) | {"Linalyl Acetate","Ethyl Linalool"} and "Iso" not in r[0] and "Ambrofix" not in r[0] and "Petitgrain" not in r[0] and "Hedione" not in r[0] and "Lemon" not in r[0] and "Cedrat" not in r[0])
    bad_pct = bad / total * 100
    citrus = sum(r[2] for r in rows if "Lemon" in r[0] or "Cedrat" in r[0] or "Lime" in r[0] or "Citral" in r[0] or "Aldehyde" in r[0])
    citrus_pct = citrus / total * 100
    hed = next((r[2] for r in rows if "Hedione" in r[0] and "HC" not in r[0]), 0)
    hed_pct = hed / total * 100

    add_total = sum(add.values())
    return f, iso_oav_pct, bad_pct, citrus_pct, hed_pct, add_total

print(f"{'f':>6} {'Iso ES%':>8} {'Bad%':>7} {'Citr%':>7} {'Hed%':>7} {'Add uL':>8}")
print("-" * 50)
for f_int in range(10, 55, 5):
    f = f_int / 100
    fv, iso, bad, cit, hed, add = sim(f)
    ok = " <- DHC range" if 12 < iso < 22 else ""
    print(f"{f:>6.2f} {iso:>8.1f}% {bad:>6.1f}% {cit:>6.1f}% {hed:>6.1f}% {add:>8.0f}{ok}")
