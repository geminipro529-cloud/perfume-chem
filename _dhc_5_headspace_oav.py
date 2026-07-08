#!/usr/bin/env python3
"""Headspace OAV for 5 DHC formulas. Output written to file to avoid Windows encoding issues."""

import sys, io
sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

PPM_FACTOR = 20.0  # 1e6 / 50,000 uL

dhc_defs = {
    "I Bergamot": {
        "top": [
            ("Bergamot FCF Sicilian", "neat", 2338.0),
            ("Linalyl Acetate",        "neat",  417.5),
        ],
        "heart": [
            ("Hedione",               "neat", 1753.5),
            ("Petitgrain EO",         "neat",  634.6),
            ("Ethyl Linalool",        "neat",  684.7),
            ("Paradisamide",          "10%",    33.4),
            ("Hedione HC",            "neat",  200.4),
        ],
        "base": [
            ("Romandolide",           "neat",  634.6),
            ("Iso E Super",           "neat",  651.3),
            ("Ethylene Brassylate",   "neat",  417.5),
            ("Ambrofix",              "30%",    35.1),
            ("Ambrettolide",          "10%",     8.3),
            ("Norlimbanol Dextro",    "neat",   41.8),
            ("Vetival",               "neat",   41.8),
        ],
    },
    "II Cedrat": {
        "top": [
            ("Cedrat FCF Sicilian",   "neat", 3039.4),
            ("Linalyl Acetate",        "neat",  250.5),
        ],
        "heart": [
            ("Hedione",               "neat", 1469.6),
            ("Petitgrain EO",         "neat",  584.5),
            ("Ethyl Linalool",        "neat",  551.1),
            ("Paradisamide",          "10%",    33.4),
            ("Hedione HC",            "neat",  200.4),
        ],
        "base": [
            ("Romandolide",           "neat",  651.3),
            ("Iso E Super",           "neat",  567.8),
            ("Ethylene Brassylate",   "neat",  367.4),
            ("Ambrofix",              "30%",    50.1),
            ("Ambrettolide",          "10%",     8.3),
            ("Norlimbanol Dextro",    "neat",   41.8),
            ("Vetival",               "neat",   41.8),
        ],
    },
    "III Grapefruit": {
        "top": [
            ("Grapefruit FCF",        "neat", 1837.0),
            ("Linalyl Acetate",        "neat",  584.5),
        ],
        "heart": [
            ("Hedione",               "neat", 1870.4),
            ("Petitgrain EO",         "neat",  668.0),
            ("Ethyl Linalool",        "neat",  759.9),
            ("Paradisamide",          "10%",    33.4),
            ("Hedione HC",            "neat",  200.4),
        ],
        "base": [
            ("Romandolide",           "neat",  734.8),
            ("Iso E Super",           "neat",  592.9),
            ("Ethylene Brassylate",   "neat",  417.5),
            ("Ambrofix",              "30%",    55.1),
            ("Ambrettolide",          "10%",     8.3),
            ("Norlimbanol Dextro",    "neat",   41.8),
            ("Vetival",               "neat",   41.8),
        ],
    },
    "IV Lime": {
        "top": [
            ("Lime Distilled EO",     "neat", 3039.4),
            ("Linalyl Acetate",        "neat",  250.5),
        ],
        "heart": [
            ("Hedione",               "neat", 1486.3),
            ("Petitgrain EO",         "neat",  617.9),
            ("Ethyl Linalool",        "neat",  584.5),
            ("Paradisamide",          "10%",    33.4),
            ("Hedione HC",            "neat",  200.4),
        ],
        "base": [
            ("Romandolide",           "neat",  601.2),
            ("Iso E Super",           "neat",  534.4),
            ("Ethylene Brassylate",   "neat",  367.4),
            ("Ambrofix",              "30%",    50.1),
            ("Ambrettolide",          "10%",     8.3),
            ("Norlimbanol Dextro",    "neat",   41.8),
            ("Vetival",               "neat",   41.8),
        ],
    },
    "V Mandarin": {
        "top": [
            ("Red Mandarin EO",       "neat", 3039.4),
            ("Linalyl Acetate",        "neat",  334.0),
        ],
        "heart": [
            ("Hedione",               "neat", 1469.6),
            ("Petitgrain EO",         "neat",  584.5),
            ("Ethyl Linalool",        "neat",  567.8),
            ("Paradisamide",          "10%",    33.4),
            ("Hedione HC",            "neat",  200.4),
        ],
        "base": [
            ("Romandolide",           "neat",  567.8),
            ("Iso E Super",           "neat",  517.7),
            ("Ethylene Brassylate",   "neat",  350.7),
            ("Ambrofix",              "30%",    55.1),
            ("Ambrettolide",          "10%",    11.7),
            ("Norlimbanol Dextro",    "neat",   41.8),
            ("Vetival",               "neat",   41.8),
        ],
    },
}


def compute_dhc_oav(layers):
    results = []
    for layer_name, materials in layers.items():
        for name, dilution, active_ul in materials:
            try:
                norm = normalize_name(name)
                profile = get_profile(name)
                vp = profile.vp if profile and profile.vp else 0.0
                odt_data = ODT_DATA.get(norm, {})
                if not odt_data:
                    odt_data = ODT_DATA.get(name.lower(), {})
                odt_air = odt_data.get('odt_air', None) if odt_data else None
                ppm_fin = active_ul * PPM_FACTOR
                if vp and odt_air and odt_air > 0:
                    oav_val = vp * ppm_fin / odt_air
                else:
                    oav_val = None
                results.append({
                    'name': name, 'layer': layer_name, 'active_ul': active_ul,
                    'ppm_fin': ppm_fin, 'vp': vp, 'odt_air': odt_air, 'oav': oav_val,
                })
            except Exception as e:
                results.append({
                    'name': name, 'layer': layer_name, 'active_ul': active_ul,
                    'ppm_fin': active_ul * PPM_FACTOR, 'vp': None, 'odt_air': None,
                    'oav': None, 'error': str(e),
                })
    return results


def band(oav_val):
    if oav_val >= 50: return 'DOMINANT'
    if oav_val >= 5:  return 'Strong'
    if oav_val >= 1:  return 'Active'
    return 'Shadow'


out = io.StringIO()
w = out.write

w('=' * 90 + '\n')
w('DHC 5-FORMULA HEADSPACE OAV COMPARISON\n')
w('VP x ppm / ODT_air -- skin temp 32C, 50 mL EDP bottle\n')
w('=' * 90 + '\n')

all_dhc = {}
for dhc_name, layers in dhc_defs.items():
    raw = compute_dhc_oav(layers)
    with_oav = [r for r in raw if r['oav'] is not None]
    with_oav.sort(key=lambda x: x['oav'], reverse=True)
    all_dhc[dhc_name] = {'sorted': with_oav,
        'total_oav': sum(r['oav'] for r in with_oav),
        'top_oav': sum(r['oav'] for r in with_oav if r['layer'] == 'top'),
        'heart_oav': sum(r['oav'] for r in with_oav if r['layer'] == 'heart'),
        'base_oav': sum(r['oav'] for r in with_oav if r['layer'] == 'base'),
    }

for dhc_name in dhc_defs:
    info = all_dhc[dhc_name]
    sl = info['sorted']
    w(f'\n{"-"*90}\n')
    w(f'  DHC {dhc_name}\n')
    w(f'{"-"*90}\n')
    w(f'  {"Rank":<5} {"Material":<28} {"ActuL":>7} {"ppm":>8} {"VP(Pa)":>8} {"ODT(ppb)":>10} {"OAV":>10} {"Band":>10}\n')
    w(f'  {"-"*85}\n')
    for rank, r in enumerate(sl, 1):
        star = ' <-- STAR' if rank == 1 else ''
        w(f"  {rank:<5} {r['name']:<28} {r['active_ul']:>7.1f} {r['ppm_fin']:>8.0f} {r['vp']:>8.4f} {r['odt_air']:>10.4f} {r['oav']:>10,.1f} {band(r['oav']):>10}{star}\n")

    t = info['total_oav']
    bt = info['base_oav'] / info['top_oav'] if info['top_oav'] else 0
    n_sub = sum(1 for r in sl if r['oav'] < 1)
    n_dom = sum(1 for r in sl if r['oav'] >= 50)
    star_r = sl[0]
    w(f'\n  Total OAV: {t:,.0f}  |  T:{info["top_oav"]/t*100:.0f}% / H:{info["heart_oav"]/t*100:.0f}% / B:{info["base_oav"]/t*100:.0f}%  |  B:T={bt:.2f}:1\n')
    w(f'  Star: {star_r["name"]} rank #1, OAV={star_r["oav"]:,.0f} ({star_r["oav"]/t*100:.1f}%)\n')
    w(f'  Dominant({n_dom}) / Subliminal({n_sub})\n')

# Cross-comparison
w(f'\n\n{"="*90}\n')
w('CROSS-COMPARISON SUMMARY\n')
w(f'{"="*90}\n')
w(f'  {"Metric":<28} {"I Bergamot":>13} {"II Cedrat":>13} {"III Grape":>13} {"IV Lime":>13} {"V Mandarin":>13}\n')
w(f'  {"-"*80}\n')

rows = [
    ("Total OAV",  lambda i: f'{i["total_oav"]:>13,.0f}'),
    ("Star citrus OAV", lambda i: f'{i["sorted"][0]["oav"]:>13,.0f}'),
    ("Star citrus name", lambda i: f'{i["sorted"][0]["name"]:>13s}'),
    ("Top %", lambda i: f'{i["top_oav"]/i["total_oav"]*100:>12.0f}%'),
    ("Heart %", lambda i: f'{i["heart_oav"]/i["total_oav"]*100:>12.0f}%'),
    ("Base %", lambda i: f'{i["base_oav"]/i["total_oav"]*100:>12.0f}%'),
    ("B:T ratio", lambda i: f'{i["base_oav"]/i["top_oav"]:>12.2f}:1'),
    ("Dominant (>=50)", lambda i: f'{sum(1 for r in i["sorted"] if r["oav"]>=50):>13d}'),
    ("Subliminal (<1)", lambda i: f'{sum(1 for r in i["sorted"] if r["oav"]<1):>13d}'),
]
for label, fn in rows:
    vals = ''.join(fn(all_dhc[d]) for d in dhc_defs)
    w(f'  {label:<28}{vals}\n')

# Per-ul efficiency
w(f'\n  --- Citrus headspace efficiency (OAV per uL of citrus material) ---\n')
for d in dhc_defs:
    r = all_dhc[d]['sorted'][0]
    oav_per = r['oav'] / r['active_ul'] if r['active_ul'] else 0
    w(f'  {d:18s}: {r["name"]:<25s} {r["active_ul"]:>6.0f} uL  OAV={r["oav"]:>12,.0f}  ({oav_per:.1f} OAV/uL)\n')

w(f'\n{"="*90}\n')
w('NOTE: Headspace OAV = VP(Pa) x ppm_fin / ODT_air(ppb). Simplified Raoult heuristic.\n')
w('Gamma-corrected partial pressures would suppress low-VP base materials and boost\n')
w('mid-VP heart materials. Directionally, the citrus star dominates every DHC.\n')
w(f'{"="*90}\n')

with open('_dhc_5_headspace_output.txt', 'w', encoding='utf-8') as f:
    f.write(out.getvalue())
print('Output written to _dhc_5_headspace_output.txt')
