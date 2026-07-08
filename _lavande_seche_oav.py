#!/usr/bin/env python3
"""OAV headspace analysis for Lavande Sèche — Woody-Lavender (2026-05-10).

Uses the same VP × ppm / ODT_air heuristic as the Bleu Carbon recalc script.
Active µL → ppm fin (10 mL EDP bottle), then vapor = VP(Pa) × ppm, OAV = vapor / ODT_air(ppb).
"""

import sys
sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# Lavande Sèche formula: (Material Name, Dilution, Raw µL, Active µL)
# 10.00 mL EDP bottle = 10,000 µL total
# ppm_factor = 1,000,000 / 10,000 = 100.0
formula_data = [
    # ── Base ──
    ('Iso E Super',           'neat',     220, 220.0),
    ('Romandolide',           'neat',     200, 200.0),
    ('Vertofix',              'neat',     60,  60.0),
    ('Evernyl',               'neat',     55,  55.0),
    ('Clearwood',             'neat',     50,  50.0),
    ('Patchouli EO',          'neat',     25,  25.0),
    ('Norlimbanol Dextro',    'neat',     10,  10.0),
    ('Kephalis',              'neat',     10,  10.0),
    ('Nagarmortha Oil',       'neat',     6,   6.0),
    # ── Heart ──
    ('Hedione',               'neat',     250, 250.0),
    ('Javanol',               'neat',     90,  90.0),
    ('Geraniol',              'neat',     60,  60.0),
    ('Clary Sage EO',         'neat',     40,  40.0),
    ('Vetiver EO (India)',    'neat',     35,  35.0),
    ('Dihydrojasmone',        'neat',     18,  18.0),
    ('Ambrettolide',          '10% DPG',  160, 16.0),
    ('Damascenone',           '1%',       4,   0.04),
    ('Alpha Damascone',       '10% DPG',  4,   0.4),
    # ── Top ──
    ('Lavender EO High Altitude', 'neat', 400, 400.0),
    ('Cedarwood oil Virginia',    'neat', 150, 150.0),
    ('Linalyl Acetate',           'neat', 55,  55.0),
    ('Black Pepper EO',           'neat', 35,  35.0),
    ('Spike Lavender EO',         'neat', 18,  18.0),
    ('Rosemary EO',               'neat', 12,  12.0),
    ('Juniper Berry EO',          'neat', 12,  12.0),
]

PPM_FACTOR = 100.0  # 1e6 / 10,000 µL

results = []
for name, dilution, raw_ul, active_ul in formula_data:
    try:
        norm_name = normalize_name(name)
        profile = get_profile(name)
        vp = profile.vp if profile and profile.vp else 0.0
        odt_data = ODT_DATA.get(norm_name, {})
        if not odt_data:
            odt_data = ODT_DATA.get(name.lower(), {})
        odt_air = odt_data.get('odt_air', None) if odt_data else None

        ppm_fin = active_ul * PPM_FACTOR

        if vp and odt_air and odt_air > 0:
            vapor_conc = vp * ppm_fin
            oav_val = vapor_conc / odt_air
        else:
            oav_val = None

        results.append({
            'name': name, 'dilution': dilution, 'raw_ul': raw_ul,
            'active_ul': active_ul, 'ppm_fin': ppm_fin,
            'vp': vp, 'odt_air': odt_air, 'oav': oav_val,
        })
    except Exception as e:
        results.append({
            'name': name, 'dilution': dilution, 'raw_ul': raw_ul,
            'active_ul': active_ul, 'ppm_fin': active_ul * PPM_FACTOR,
            'vp': None, 'odt_air': None, 'oav': None, 'error': str(e),
        })

results_with_oav = [r for r in results if r['oav'] is not None]
results_without = [r for r in results if r['oav'] is None]
results_with_oav.sort(key=lambda x: x['oav'], reverse=True)

print('=' * 100)
print('LAVANDE SÈCHE — HEADSPACE OAV ANALYSIS (skin temp 32°C, 10 mL EDP)')
print('=' * 100)
print(f'{"Rank":<5} {"Material":<35} {"ActµL":>7} {"ppm":>8} {"VP(Pa)":>8} {"ODT(ppb)":>10} {"OAV":>12} {"Band":>10}')
print('-' * 100)

perceptible = 0
subliminal = 0
dominant = 0
strong = 0
active = 0

for rank, r in enumerate(results_with_oav, 1):
    oav_val = r['oav']

    if oav_val >= 50:
        band = 'DOMINANT'
        dominant += 1
    elif oav_val >= 5:
        band = 'Strong'
        strong += 1
    elif oav_val >= 1:
        band = 'Active'
        active += 1
        perceptible += 1
    else:
        band = 'Shadow'
        subliminal += 1

    vp_str = f"{r['vp']:.3f}" if r['vp'] else 'N/A'
    odt_str = f"{r['odt_air']:.4f}" if r['odt_air'] else 'N/A'

    print(f"{rank:<5} {r['name']:<35} {r['active_ul']:>7.1f} {r['ppm_fin']:>8.0f} {vp_str:>8} {odt_str:>10} {oav_val:>12,.1f} {band:>10}")

total_perceptible = dominant + strong + active

print()
if results_without:
    print('-' * 100)
    print('MATERIALS WITHOUT ODT DATA:')
    print('-' * 100)
    for r in results_without:
        print(f"  - {r['name']}")

print()
print('=' * 100)
print('SUMMARY')
print('=' * 100)
print(f"Total materials:                        {len(results)}")
print(f"  Perceptible (OAV >= 1):               {total_perceptible}")
print(f"    Dominant  (OAV >= 50):              {dominant}")
print(f"    Strong    (OAV  5–50):               {strong}")
print(f"    Active    (OAV  1–5):                {active}")
print(f"  Subliminal (OAV < 1):                {subliminal}")
print(f"Materials missing ODT data:             {len(results_without)}")
total_oav = sum(r['oav'] for r in results_with_oav if r['oav'])
print(f"\nTotal formula OAV:                       {total_oav:,.0f}")

top5 = results_with_oav[:5]
print(f"\nTop 5 materials ({sum(r['oav'] for r in top5) / total_oav * 100:.1f}% of total OAV):")
for r in top5:
    pct = r['oav'] / total_oav * 100
    print(f"  #{results_with_oav.index(r)+1:>2} {r['name']:<35} OAV={r['oav']:>10,.1f}  ({pct:5.1f}%)")

# Lavender complex OAV
lavender_complex = [r for r in results_with_oav if 'lavender' in r['name'].lower() or 'linalyl acetate' in r['name'].lower()]
lav_complex_total = sum(r['oav'] for r in lavender_complex if r['oav'])
print(f"\nLavender complex OAV (HA + Linalyl Ac + Spike): {lav_complex_total:,.0f} ({lav_complex_total/total_oav*100:.1f}%)")
for r in lavender_complex:
    print(f"  #{results_with_oav.index(r)+1:>2} {r['name']:<35} OAV={r['oav']:>10,.1f}  (rank {results_with_oav.index(r)+1})")

print('=' * 100)
