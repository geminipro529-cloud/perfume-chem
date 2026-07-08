#!/usr/bin/env python3
"""Score the architecturally-tuned DHC formulas on Demachy-relevant axes."""

import sys, math
sys.path.insert(0, '.')
from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM = 20.0  # 50 mL

def mat(name):
    n = normalize_name(name)
    p = get_profile(name)
    odt = ODT_DATA.get(n, {}) or ODT_DATA.get(name.lower(), {})
    return p.vp if p and p.vp else 0, odt.get('odt_air'), odt.get('odt_eth')

def h_oav(active, vp, odt_a):
    return vp * active * PPM / odt_a if vp and odt_a else 0

# --- Architecturally-tuned DHC formulas (Demachy's citrus-first approach) ---
# Each material: (name, dilution, active_uL, layer)
# Architecture choices: flower, bridge, drydown all chosen to serve the citrus.

variants = {
    "I Bergamot (Calabria)": {
        "citrus": "Bergamot FCF Sicilian",
        "origin": "Calabria",
        "flower": "Aurantiol 10% — orange blossom honey. Bergamot + neroli are Calabrian siblings.",
        "bridge": "Petitgrain max. Bergamot and petitgrain grow together.",
        "drydown": "Classical woody-amber. Vertofix for structure.",
        "formula": [
            # TOP
            ("Bergamot FCF Sicilian", "neat", 2800, "top"),
            ("Linalyl Acetate", "neat", 280, "top"),
            ("Aurantiol", "10%", 8, "top"),  # 0.8 active
            # HEART
            ("Petitgrain EO", "neat", 700, "heart"),
            ("Hedione", "neat", 1450, "heart"),
            ("Ethyl Linalool", "neat", 500, "heart"),
            ("Hedione HC", "neat", 180, "heart"),
            ("Paradisamide", "10%", 35, "heart"),
            # BASE
            ("Romandolide", "neat", 500, "base"),
            ("Iso E Super", "neat", 480, "base"),
            ("Vertofix", "neat", 60, "base"),
            ("Ambrofix", "30%", 55.5, "base"),
            ("Ethylene Brassylate", "neat", 413, "base"),
            ("Ambrettolide", "10%", 12.5, "base"),
            ("Norlimbanol Dextro", "neat", 45, "base"),
            ("Vetival", "neat", 43, "base"),
            ("Cardamom EO", "neat", 5, "base"),
            ("Alpha Irone", "30% DEP", 1.5, "base"),
        ],
    },
    "II Cedrat (Mediterranean)": {
        "citrus": "Cedrat FCF Sicilian",
        "origin": "Mediterranean",
        "flower": "None. The citrus IS the architecture. Mineral, stark, no floral softness.",
        "bridge": "Petitgrain moderate. Cedrat is already sharp enough to span registers alone.",
        "drydown": "Cold mineral. Kephalis edge. Ambrofix boosted. Most crystalline of the five.",
        "formula": [
            ("Cedrat FCF Sicilian", "neat", 3000, "top"),
            ("Linalyl Acetate", "neat", 200, "top"),
            ("Petitgrain EO", "neat", 650, "heart"),
            ("Hedione", "neat", 1300, "heart"),
            ("Ethyl Linalool", "neat", 400, "heart"),
            ("Hedione HC", "neat", 160, "heart"),
            ("Paradisamide", "10%", 35, "heart"),
            ("Romandolide", "neat", 480, "base"),
            ("Iso E Super", "neat", 420, "base"),
            ("Kephalis", "neat", 8, "base"),
            ("Ambrofix", "30%", 60, "base"),  # boosted
            ("Ethylene Brassylate", "neat", 370, "base"),
            ("Ambrettolide", "10%", 12.5, "base"),
            ("Norlimbanol Dextro", "neat", 45, "base"),
            ("Vetival", "neat", 43, "base"),
            ("Cardamom EO", "neat", 5, "base"),
            ("Alpha Irone", "30% DEP", 1.5, "base"),
        ],
    },
    "III Grapefruit (Tropical)": {
        "citrus": "Grapefruit FCF",
        "origin": "Tropical",
        "flower": "Grapefruit blossom = Petitgrain + Paradisamide boost. Demachy's DHC 2013 approach.",
        "bridge": "Petitgrain + Paradisamide boost. Grapefruit's explosive top needs help bridging.",
        "drydown": "Clean-crystalline. Ambrofix generous. Cheerful citrus wants a clean finish.",
        "formula": [
            ("Grapefruit FCF", "neat", 1850, "top"),
            ("Linalyl Acetate", "neat", 450, "top"),
            ("Petitgrain EO", "neat", 650, "heart"),
            ("Hedione", "neat", 1400, "heart"),
            ("Ethyl Linalool", "neat", 600, "heart"),
            ("Hedione HC", "neat", 170, "heart"),
            ("Paradisamide", "10%", 45, "heart"),  # boosted — grapefruit blossom
            ("Romandolide", "neat", 500, "base"),
            ("Iso E Super", "neat", 500, "base"),
            ("Ambrofix", "30%", 65, "base"),  # generous
            ("Ethylene Brassylate", "neat", 380, "base"),
            ("Ambrettolide", "10%", 12.5, "base"),
            ("Norlimbanol Dextro", "neat", 45, "base"),
            ("Vetival", "neat", 43, "base"),
            ("Cardamom EO", "neat", 5, "base"),
            ("Alpha Irone", "30% DEP", 1.5, "base"),
        ],
    },
    "IV Lime (Caribbean)": {
        "citrus": "Lime Distilled EO",
        "origin": "Caribbean",
        "flower": "None. Lime's transparency IS the flower. Adding one would cloud it.",
        "bridge": "Petitgrain max + Vetiver boost. Lime is ethereal — needs the most structural support.",
        "drydown": "Ghost-transparent. Least Ambrofix, least Romandolide, most Vetival.",
        "formula": [
            ("Lime Distilled EO", "neat", 3100, "top"),
            ("Linalyl Acetate", "neat", 180, "top"),
            ("Petitgrain EO", "neat", 680, "heart"),
            ("Hedione", "neat", 1300, "heart"),
            ("Ethyl Linalool", "neat", 400, "heart"),
            ("Hedione HC", "neat", 150, "heart"),
            ("Paradisamide", "10%", 35, "heart"),
            ("Romandolide", "neat", 420, "base"),  # least — ghost musk
            ("Iso E Super", "neat", 380, "base"),  # least cocoon
            ("Ambrofix", "30%", 48, "base"),  # least ambery
            ("Ethylene Brassylate", "neat", 330, "base"),
            ("Ambrettolide", "10%", 12.5, "base"),
            ("Norlimbanol Dextro", "neat", 45, "base"),
            ("Vetival", "neat", 70, "base"),  # boosted — earthy anchor for ethereal lime
            ("Cardamom EO", "neat", 5, "base"),
            ("Alpha Irone", "30% DEP", 1.5, "base"),
        ],
    },
    "V Mandarin (Sicily)": {
        "citrus": "Red Mandarin EO",
        "origin": "Sicily",
        "flower": "Jasmine FO + Dihydrojasmone — warm golden citrus meets warm golden floral.",
        "bridge": "Petitgrain min. Mandarin is already full-bodied. Bridge would crowd it.",
        "drydown": "Golden-warm. Benzoin trace. Richest base — the sunset deserves weight.",
        "formula": [
            ("Red Mandarin EO", "neat", 2800, "top"),
            ("Linalyl Acetate", "neat", 280, "top"),
            ("Petitgrain EO", "neat", 600, "heart"),
            ("Hedione", "neat", 1350, "heart"),
            ("Ethyl Linalool", "neat", 480, "heart"),
            ("Hedione HC", "neat", 180, "heart"),
            ("Paradisamide", "10%", 35, "heart"),
            ("Dihydrojasmone", "neat", 20, "heart"),  # golden jasmine
            ("Jasmine FO", "neat", 40, "heart"),  # warm floral
            ("Romandolide", "neat", 520, "base"),  # warmest musk
            ("Iso E Super", "neat", 500, "base"),
            ("Benzoin Resinoid", "50% DPG", 25, "base"),  # sunset warmth
            ("Ambrofix", "30%", 60, "base"),
            ("Ethylene Brassylate", "neat", 350, "base"),
            ("Ambrettolide", "10%", 12.5, "base"),
            ("Norlimbanol Dextro", "neat", 45, "base"),
            ("Vetival", "neat", 43, "base"),
            ("Cardamom EO", "neat", 5, "base"),
            ("Alpha Irone", "30% DEP", 1.5, "base"),
        ],
    },
}

def score_formula(formula_rows):
    """Compute Demachy-relevant scores for a formula."""
    total_h = 0
    top_h = 0
    heart_h = 0
    base_h = 0
    star_h = 0
    ambrofix_h = 0
    petitgrain_h = 0
    romandolide_h = 0
    hedrg_h = 0  # hedione + hc
    n_mats = 0
    dominant_n = 0
    sub_n = 0
    unique_families = set()

    for name, dil, active, layer in formula_rows:
        vp, odt_a, _ = mat(name)
        oav = h_oav(active, vp, odt_a)
        n_mats += 1
        total_h += oav
        if layer == "top": top_h += oav
        elif layer == "heart": heart_h += oav
        else: base_h += oav

        if oav >= 50: dominant_n += 1
        if oav < 1: sub_n += 1
        if "Petitgrain" in name: petitgrain_h = oav
        if "Ambrofix" in name: ambrofix_h = oav
        if "Romandolide" in name: romandolide_h = oav
        if "Hedione" in name: hedrg_h += oav

    # Star citrus = first row (top material with highest active)
    star_name_data = [(n, d, a, l) for n, d, a, l in formula_rows if l == "top"]
    if star_name_data:
        star_name = star_name_data[0][0]
        vp_s, odt_s, _ = mat(star_name)
        star_h = h_oav(star_name_data[0][2], vp_s, odt_s)
    else:
        star_name = "?"

    citrus_dom = star_h / total_h * 100 if total_h else 0
    bt = base_h / top_h if top_h else 0
    ptgrain_pct = petitgrain_h / total_h * 100 if total_h else 0

    # Cologne balance target: 40/35/25
    t_pct, h_pct, b_pct = top_h/total_h*100, heart_h/total_h*100, base_h/total_h*100
    cologne_dist = abs(t_pct - 40) + abs(h_pct - 35) + abs(b_pct - 25)

    # Scores (0-100, Demachy-weighted)
    citrus_score = min(100, max(0, 100 - abs(citrus_dom - 45) * 4))       # target 40-50%
    bridge_score = min(100, max(0, 100 - abs(ptgrain_pct - 30) * 5))      # target 25-35%
    balance_score = max(0, 100 - cologne_dist * 3)                         # cologne balance
    ambrofix_score = min(100, max(0, 100 - abs(ambrofix_h - 185) * 1.5))  # target 150-200
    french_score = min(100, max(0, 100 - (total_h / 20000 - 1) * 40))      # not too loud
    elegance_score = min(100, max(0, 100 - (n_mats - 14) * 8))              # fewer = better
    complexity_score = 100 - sub_n * 10 - max(0, (dominant_n - 10) * 5)    # right complexity

    composite = (citrus_score * 0.25 + bridge_score * 0.20 + balance_score * 0.15
               + ambrofix_score * 0.15 + french_score * 0.10
               + elegance_score * 0.08 + complexity_score * 0.07)

    return {
        "citrus_dom_pct": citrus_dom,
        "star_name": star_name,
        "star_oav": star_h,
        "bt_ratio": bt,
        "ptgrain_pct": ptgrain_pct,
        "ambrofix_oav": ambrofix_h,
        "romandolide_oav": romandolide_h,
        "hedrcg_oav": hedrg_h,
        "total_oav": total_h,
        "t_pct": t_pct, "h_pct": h_pct, "b_pct": b_pct,
        "n_mats": n_mats,
        "dominant": dominant_n, "subliminal": sub_n,
        "scores": {
            "Citrus dominance": citrus_score,
            "Bridge (Petitgrain)": bridge_score,
            "Layer balance": balance_score,
            "Ambrofix presence": ambrofix_score,
            "French quietness": french_score,
            "Elegance (fewer mats)": elegance_score,
            "Complexity depth": complexity_score,
        },
        "composite": composite,
    }

print("=" * 105)
print("DEMACHY DHC ARCHITECTURAL SCORES")
print("=" * 105)

all_results = {}
for label, spec in variants.items():
    result = score_formula(spec["formula"])
    all_results[label] = result

    print(f"\n{'-'*105}")
    print(f"  {label}")
    print(f"  Citrus: {spec['citrus']}  |  Origin: {spec['origin']}")
    print(f"  Flower: {spec['flower']}")
    print(f"  Bridge: {spec['bridge']}")
    print(f"  Drydown: {spec['drydown']}")
    print(f"{'-'*105}")
    print(f"  Headspace OAV: {result['total_oav']:,.0f} total")
    print(f"    Star: {result['star_name']} — OAV {result['star_oav']:,.0f} ({result['citrus_dom_pct']:.0f}%)")
    print(f"    Petitgrain: {result['ptgrain_pct']:.0f}%  |  Ambrofix: {result['ambrofix_oav']:.0f}  |  IES+Hed: {result['hedrcg_oav']:.0f}")
    print(f"    Layers: T{result['t_pct']:.0f}% / H{result['h_pct']:.0f}% / B{result['b_pct']:.0f}%  |  B:T={result['bt_ratio']:.2f}:1")
    print(f"    Materials: {result['n_mats']}  |  Dominant: {result['dominant']}  Subliminal: {result['subliminal']}")
    print(f"\n  Scores:")
    for dim, sc in result['scores'].items():
        bar = '#' * int(sc / 5) + '.' * (20 - int(sc / 5))
        print(f"    {dim:<30s} {sc:>5.0f}  [{bar}]")
    print(f"  {'COMPOSITE':<30s} {result['composite']:>5.0f}  [{'#' * int(result['composite']/5) + '.' * (20 - int(result['composite']/5))}]")

# --- Cross-comparison ---
print(f"\n\n{'='*105}")
print("  CROSS-COMPARISON")
print(f"{'='*105}")
print(f"  {'Metric':<28} {'I Bergamot':>14} {'II Cedrat':>14} {'III Grapefruit':>14} {'IV Lime':>14} {'V Mandarin':>14}")
print(f"  {'-'*98}")

for metric_key, fmt in [
    ("Composite score", lambda r: f"{r['composite']:>14.0f}"),
    ("Citrus dominance", lambda r: f"{r['citrus_dom_pct']:>13.0f}%"),
    ("Star OAV", lambda r: f"{r['star_oav']:>14,.0f}"),
    ("Bridge % (Petitgrain)", lambda r: f"{r['ptgrain_pct']:>13.0f}%"),
    ("Ambrofix OAV", lambda r: f"{r['ambrofix_oav']:>14.0f}"),
    ("Romandolide OAV", lambda r: f"{r['romandolide_oav']:>14.0f}"),
    ("B:T ratio", lambda r: f"{r['bt_ratio']:>13.2f}:1"),
    ("Layer T/H/B", lambda r: f"{r['t_pct']:.0f}/{r['h_pct']:.0f}/{r['b_pct']:.0f}%".rjust(14)),
    ("Total headspace OAV", lambda r: f"{r['total_oav']:>14,.0f}"),
    ("Material count", lambda r: f"{r['n_mats']:>14d}"),
]:
    vals = ""
    for d in variants:
        vals += fmt(all_results[d])
    print(f"  {metric_key:<28} {vals}")

print(f"\n{'='*105}")
