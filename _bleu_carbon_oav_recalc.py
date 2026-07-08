#!/usr/bin/env python3
"""Recalculate Bleu Carbon OAV with updated ingredient intelligence model."""

import sys
sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA
from engine.name_utils import normalize_name

# Bleu Carbon formula data: (Material Name, Active µL)
formula_data = [
    ('Iso E Super', 650.0), ('Ambrofix', 192.0), ('Romandolide', 200.0),
    ('Cedarwood oil Virginia', 170.0), ('Olibanum Resinoid', 13.0), ('Clearwood', 130.0),
    ('Ebanol', 100.0), ('Ethylene Brassylate', 80.0), ('Zenolide', 80.0),
    ('Javanol', 70.0), ('Vertofix', 70.0), ('Habanolide', 50.0), ('Sandalore', 50.0),
    ('Timberol', 50.0), ('Vetival', 20.0), ('Ambrettolide', 3.5), ('Benzoin Resinoid', 12.5),
    ('Evernyl', 25.0), ('Norlimbanol Dextro', 18.0), ('Patchouli EO', 15.0),
    ('Kephalis', 12.0), ('Suederal', 1.2), ('Costus Olifac', 1.0), ('Nagarmortha Oil', 8.0),
    ('Hedione', 540.0), ('Lavender EO High Altitude', 340.0), ('Hedione HC', 100.0),
    ('Geraniol', 90.0), ('Coumarin', 10.4), ('Linalyl Acetate', 40.0), ('Aurantiol', 4.0),
    ('Clary Sage EO', 25.0), ('Terpinyl Acetate', 20.0), ('Dihydrojasmone', 20.0),
    ('Spike Lavender EO', 15.0), ('Damascenone', 0.12), ('Alpha Damascone', 1.2),
    ('Alpha Irone', 1.5), ('Carrot Seed EO', 5.0), ('Cedrat FCF oil Sicilian', 360.0),
    ('Grapefruit FCF', 200.0), ('Dihydromyrcenol', 180.0), ('Bergamot FCF oil Sicilian', 110.0),
    ('Aldehyde C10', 0.5), ('Black Pepper EO', 45.0), ('Blood Orange oil Sicilian', 35.0),
    ('Petitgrain EO', 35.0), ('Scentenal', 0.2), ('Juniper Berry EO', 15.0),
    ('Rosemary EO', 8.0), ('Ethyl Safranate', 5.0),
]

results = []
for name, active_ul in formula_data:
    try:
        norm_name = normalize_name(name)
        profile = get_profile(name)
        vp = profile.vp if profile and profile.vp else 0.0
        odt_data = ODT_DATA.get(norm_name, {})
        if not odt_data:
            odt_data = ODT_DATA.get(name.lower(), {})
        odt_air = odt_data.get('odt_air', None) if odt_data else None
        ppm = active_ul * 33.33
        if vp and odt_air and odt_air > 0:
            vapor_conc = vp * ppm
            oav = vapor_conc / odt_air
        else:
            oav = None
        results.append({
            'name': name, 'active_ul': active_ul, 'ppm': ppm,
            'vp': vp, 'odt': odt_air, 'oav': oav
        })
    except Exception as e:
        results.append({
            'name': name, 'active_ul': active_ul, 'ppm': active_ul * 33.33,
            'vp': None, 'odt': None, 'oav': None
        })

results_with_oav = [r for r in results if r['oav'] is not None]
results_without = [r for r in results if r['oav'] is None]
results_with_oav.sort(key=lambda x: x['oav'], reverse=True)

print('=' * 100)
print('BLEU CARBON - UPDATED OAV ANALYSIS (with corrected VP from ingredient intelligence model)')
print('Formula Date: 2026-05-08 | Analysis Date: 2026-05-09')
print('=' * 100)
print(f'{"Rank":<6} {"Material":<36} {"ActiveµL":>9} {"ppm":>8} {"VP(Pa)":>9} {"ODT(ppb)":>10} {"OAV":>12} {"Band":>10}')
print('-' * 100)

perceptible = subliminal = 0
for rank, r in enumerate(results_with_oav, 1):
    oav = r['oav']
    if oav >= 100:
        band = 'DOMINANT'
    elif oav >= 10:
        band = 'Strong'
    elif oav >= 1:
        band = 'Active'
        perceptible += 1
    else:
        band = 'Shadow'
        subliminal += 1
    
    vp_str = f"{r['vp']:.3f}" if r['vp'] else 'N/A'
    odt_str = f"{r['odt']:.3f}" if r['odt'] else 'N/A'
    
    print(f"{rank:<6} {r['name']:<36} {r['active_ul']:>9.1f} {r['ppm']:>8.0f} {vp_str:>9} {odt_str:>10} {oav:>12,.1f} {band:>10}")

print()
print('-' * 100)
print('MATERIALS WITHOUT ODT DATA (OAV cannot be calculated):')
print('-' * 100)
for r in results_without:
    print(f"  - {r['name']}")

print()
print('=' * 100)
print('SUMMARY STATISTICS')
print('=' * 100)
print(f"Total materials with OAV calculation: {len(results_with_oav)}")
print(f"  Perceptible (OAV >= 1):   {perceptible}")
print(f"  Subliminal (OAV < 1):     {subliminal}")
print(f"Materials missing ODT data: {len(results_without)}")

# Calculate key insights
total_oav = sum(r['oav'] for r in results_with_oav if r['oav'])
print(f"\nTotal formula OAV: {total_oav:,.0f}")

# Top 5 by OAV
top5 = results_with_oav[:5]
print(f"\nTop 5 Dominant Materials ({sum(r['oav'] for r in top5)/total_oav*100:.1f}% of total OAV):")
for r in top5:
    pct = r['oav'] / total_oav * 100
    print(f"  - {r['name']}: OAV {r['oav']:,.0f} ({pct:.1f}%)")

print('=' * 100)
