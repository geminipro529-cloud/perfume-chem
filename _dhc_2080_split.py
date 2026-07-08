"""DHC 20:80 SPLIT -- Bottle A (DHC Lemon), Bottle B (Fougere).

20% of existing batch -> Bottle A (DHC lemon, minimal bad)
80% of existing batch -> Bottle B (fougere, locked materials reclassified)
Both target 50 mL at ~12% v/v.
"""
import sys
sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA
from engine.ingredient_intelligence import get_profile
from engine.name_utils import normalize_name

PPM = 20.0

EXISTING = {
    "Lemon FCF oil Sicilian": 4200.0, "Hedione": 900.0, "Hedione HC": 360.0,
    "Ethyl Linalool": 330.0, "Linalyl Acetate": 120.0, "Petitgrain EO": 150.0,
    "Ambrofix": 10.8,
    "Ethyl Maltol": 1.8, "Dihydrojasmone": 30.0, "Aurantiol": 9.0,
    "Mayol": 8.4, "Nympheal": 3.6, "Scentenal": 0.012, "Floralozone": 0.06,
    "Iso E Super": 300.0, "Romandolide": 288.0, "Ethylene Brassylate": 228.0,
    "Norlimbanol Dextro": 25.2, "Vetival": 24.0, "Javanol": 9.6, "Cardamom EO": 3.0,
}

TARGET_ML = 50.0
CONC_PCT = 12.0
TARGET_ACTIVE = TARGET_ML * CONC_PCT * 10  # = 6000 uL
EXISTING_ML = 33.0  # actual batch volume per user

# DHC A Cedrat formula (% of concentrate)
DHC_A_PCT = {
    "Hedione": 25.0, "Cedrat FCF oil Sicilian": 20.0, "Lemon FCF oil Sicilian": 20.0,
    "Iso E Super": 4.0, "Galaxolide": 6.0, "Hedione HC": 5.0, "Lime Distilled EO": 5.0,
    "Alpha Irone": 3.0, "Habanolide": 2.0, "Ambrofix": 1.0, "Petitgrain EO": 1.0,
    "Aldehyde C10 (1%)": 0.1, "Citral": 0.1,
}

# Fougere formula (% of concentrate) -- Bergamot + Lavender, same core, draws on existing
FOUGERE_PCT = {
    "Hedione": 25.0, "Bergamot FCF oil Sicilian": 12.0, "Lemon FCF oil Sicilian": 10.0,
    "Iso E Super": 4.0, "Galaxolide": 6.0, "Hedione HC": 5.0,
    "Lavender EO High Altitude": 2.0, "Alpha Irone": 3.0, "Habanolide": 2.0,
    "Coumarin (20%)": 1.0, "Petitgrain EO": 1.0, "Ambrofix": 1.0,
}

STOCK = {"Alpha Irone": 0.30, "Galaxolide": 0.50, "Ambrofix": 0.30,
         "Aldehyde C10 (1%)": 0.01, "Coumarin (20%)": 0.20}

DHC_GOOD = set(DHC_A_PCT.keys())
FOUGERE_GOOD = set(FOUGERE_PCT.keys())

def sf(name):
    for k, v in STOCK.items():
        if k in name: return v
    return 1.0

def sl(name):
    v = sf(name)
    return "neat" if v >= 1.0 else f"{v*100:.0f}%"

def get_vp_odt(n):
    p = get_profile(n)
    vp = p.vp if p and p.vp else 0
    odt = (ODT_DATA.get(normalize_name(n), {}).get("odt_air"))
    return vp, odt or 0

def calc_oav(a, vp, odt):
    return a * vp * PPM / odt if vp and odt else 0

def build_split(split_pct, target_pct, good_set, name):
    """Build one 50 mL bottle from split_pct of existing batch."""
    split = split_pct / 100.0
    existing_this = {n: v * split for n, v in EXISTING.items()}
    existing_total = sum(existing_this.values())

    # Compute targets at 6,000 uL total
    targets = {m: TARGET_ACTIVE * pct / 100 for m, pct in target_pct.items()}

    # Calculate additions and excesses
    additions = {}
    excesses = {}
    for m, t in targets.items():
        have = existing_this.get(m, 0.0)
        if t > have:
            additions[m] = t - have
        elif have > t:
            excesses[m] = have - t

    # Calculate actual addition total (accounting for excess overriding budget)
    add_total = sum(additions.values())
    excess_total = sum(excesses.values())

    # Scale additions to fit remaining budget
    # Total target = 6,000. Existing total + excess = already committed.
    committed = existing_total  # includes excesses since they're in existing
    remaining = TARGET_ACTIVE - committed
    # Wait, committed = existing_total. remaining = 6,000 - existing_total.
    # add_total is the target additions. If add_total > remaining, scale down.
    # If add_total < remaining, we have room to scale up.

    remaining = TARGET_ACTIVE - existing_total
    if add_total > 0:
        scale = remaining / add_total
    else:
        scale = 0

    # Only scale additions, excess is locked
    scaled_adds = {m: a * scale for m, a in additions.items()}

    final = dict(existing_this)
    for m, a in scaled_adds.items():
        final[m] = final.get(m, 0.0) + a

    # Compute OAV
    rows = []
    for n, a in final.items():
        vp, odt = get_vp_odt(n)
        if vp and odt:
            rows.append((n, a, vp, odt, calc_oav(a, vp, odt)))
    total_oav = sum(r[4] for r in rows)
    rows.sort(key=lambda x: x[4], reverse=True)

    good_oav = sum(r[4] for r in rows if r[0] in good_set)
    bad_oav = total_oav - good_oav

    # Compute raw volume
    total_raw = sum(a / sf(n) for n, a in scaled_adds.items())
    return {
        "name": name, "split_pct": split_pct,
        "existing_active": round(existing_total, 1),
        "additions": {m: (round(a, 1), round(a / sf(m), 1), sl(m)) for m, a in sorted(scaled_adds.items(), key=lambda x: x[1], reverse=True)},
        "excesses": {m: round(e, 1) for m, e in sorted(excesses.items(), key=lambda x: x[1], reverse=True)},
        "scale": round(scale, 3),
        "add_active": round(sum(scaled_adds.values()), 1),
        "add_raw": round(sum(a / sf(m) for m, a in scaled_adds.items()), 1),
        "final_active": round(sum(final.values()), 1),
        "conc_pct": round(sum(final.values()) / 50000 * 100, 1),
        "bad_oav_pct": round(bad_oav / total_oav * 100, 1) if total_oav else 0,
        "oav_rows": rows,
        "total_oav": round(total_oav, 0),
        "ethanol": 0,  # computed below
    }

bottle_a = build_split(25, DHC_A_PCT, DHC_GOOD, "Bottle A -- DHC Lemon")
bottle_b = build_split(75, FOUGERE_PCT, FOUGERE_GOOD, "Bottle B -- Fougere")

# Compute ethanol
for b in [bottle_a, bottle_b]:
    existing_raw_ml = EXISTING_ML * b["split_pct"] / 100
    b["ethanol"] = round(50.0 - existing_raw_ml - b["add_raw"] / 1000, 1)
    b["existing_raw_ml"] = round(existing_raw_ml, 1)

# Print
for b in [bottle_a, bottle_b]:
    print("=" * 75)
    print(f"  {b['name']} -- {b['split_pct']}% of existing batch -> 50 mL")
    print("=" * 75)
    print(f"  Existing active: {b['existing_active']:.0f} uL  |  Target: {TARGET_ACTIVE:.0f} uL  |  Scale: {b['scale']:.3f}")
    print(f"  Bad OAV: {b['bad_oav_pct']}%")

    if b["excesses"]:
        print(f"\n  EXCESS (already over target -- locked, fine):")
        for m, e in b["excesses"].items():
            print(f"    {m:<30} +{e:>6.1f} uL over target")

    print(f"\n  {'ADDITIONS':<30} {'ACTIVE':>9} {'RAW':>9} {'STOCK':>10}")
    print("  " + "-" * 60)
    for m, (a, r, s) in b["additions"].items():
        print(f"  {m:<30} {a:>8.1f} {r:>8.1f} {s:>10}")

    print(f"  {'TOTAL':<30} {b['add_active']:>8.1f} {b['add_raw']:>8.1f}")
    print(f"\n  Ethanol 96% to add: {b['ethanol']:.1f} mL")
    print(f"  Final: {b['existing_raw_ml']:.1f} + {b['add_raw']/1000:.1f} + {b['ethanol']:.1f} = 50.0 mL")
    print(f"  Final active: {b['final_active']:.0f} uL ({b['conc_pct']:.1f}%)")

    # Top 6 OAV
    print(f"\n  {'TOP 6 OAV':<30}")
    for i, (n, a, vp, odt, o) in enumerate(b["oav_rows"][:6], 1):
        p = o / b["total_oav"] * 100
        ok = "ok" if n in (DHC_GOOD if "Lemon" in b["name"] else FOUGERE_GOOD) else "XX"
        print(f"    {i}. {n:<28} {o:>8,.0f} ({p:>5.1f}%) {ok}")
    print()

print("=" * 75)
print("  SUMMARY")
print("=" * 75)
print(f"  Bottle A: {bottle_a['bad_oav_pct']}% bad OAV -- DHC Realistic Lemon")
print(f"  Bottle B: {bottle_b['bad_oav_pct']}% bad OAV -- but these are fougere materials")
