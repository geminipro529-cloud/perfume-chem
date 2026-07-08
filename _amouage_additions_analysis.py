#!/usr/bin/env python3
"""Check Amouage-style materials availability."""

import sys
sys.path.insert(0, '.')

from engine.ingredient_intelligence import get_profile
from engine.odor_thresholds import ODT_DATA

# Amouage-typical materials to check
amouage_materials = [
    ('Rose Absolute', 'floral luxury, honeyed depth'),
    ('Jasmine Sambac Absolute', 'indolic white floral'),
    ('Cardamom EO', 'spice, aromatic lift'),
    ('Myrrh EO', 'resinous, bitter, ancient'),
    ('Labdanum Absolute', 'amber, leather, darkness'),
    ('Orris Butter', 'iris root, powder, luxury'),
    ('Orris Concrete', 'orris butter base'),
    ('Saffron', 'precious spice, leathery'),
    ('Oud Oil', 'agarwood, barnyard, smoke'),
    ('Cypriol EO', 'nagarmotha, earthy-smoky'),
    ('Immortelle', 'curry, maple, hay'),
    ('Ylang Ylang EO Extra', 'white floral, narcotic'),
    ('Beeswax Absolute', 'honey, animalic warmth'),
    ('Neroli EO', 'orange blossom, fresh-bitter'),
    ('Champaca Flower EO', 'exotic floral, tea-like'),
]

print('=' * 90)
print('AMOUAGE-STYLE MATERIALS - INVENTORY AVAILABILITY CHECK')
print('=' * 90)
print(f"{'Material':<32} {'Available':>10} {'VP (Pa)':>10} {'ODT (ppb)':>12} {'Notes'}")
print('-' * 90)

available = []
missing = []

for mat, notes in amouage_materials:
    norm = mat.lower()
    profile = get_profile(mat)
    odt_info = ODT_DATA.get(norm, {})
    
    if profile:
        available.append((mat, profile, odt_info, notes))
        in_stock = 'YES'
        vp_val = profile.vp if profile.vp else 0
        vp_str = f'{vp_val:.3f}' if vp_val else 'N/A'
    else:
        missing.append((mat, notes))
        in_stock = 'NO'
        vp_str = 'N/A'
    
    odt = odt_info.get('odt_air', 'N/A') if odt_info else 'N/A'
    print(f"{mat:<32} {in_stock:>10} {vp_str:>10} {str(odt):>12} {notes}")

print()
print('=' * 90)
print('RECOMMENDED AMOUAGE ADDITIONS (based on new OAV profile)')
print('=' * 90)

# Strategic recommendations based on the new bergamot-dominant profile
recommendations = [
    {
        'material': 'Myrrh EO',
        'dose': '20-30 µL',
        'role': 'Amouage resinous signature - pairs with existing Olibanum',
        'impact': 'Adds ancient bitter-resinous depth behind bergamot'
    },
    {
        'material': 'Labdanum Absolute',
        'dose': '15-25 µL',
        'role': 'Amber-leather darkness - Amouage Interlude/Lyric axis',
        'impact': 'Grounds the bergamot with warm animalic amber'
    },
    {
        'material': 'Cardamom EO',
        'dose': '10-15 µL',
        'role': 'Spice bridge between citrus and woods',
        'impact': 'Amouage uses cardamom with bergamot (Reflection Man)'
    },
    {
        'material': 'Ylang Ylang EO Extra',
        'dose': '20-30 µL',
        'role': 'White floral narcotic richness',
        'impact': 'Adds creamy floral body without competing with top'
    },
    {
        'material': 'Cypriol EO',
        'dose': '5-10 µL',
        'role': 'Smoke-earth depth - complements Nagarmortha',
        'impact': 'Doubles down on the Luna Rossa Carbon mineral-smoke axis'
    },
]

for i, rec in enumerate(recommendations, 1):
    print(f"\n{i}. {rec['material']} - {rec['dose']}")
    print(f"   Role: {rec['role']}")
    print(f"   Impact: {rec['impact']}")

print()
print('=' * 90)
print('FORMULA INTEGRATION STRATEGY')
print('=' * 90)
print("""
Given the new OAV profile (Bergamot-dominant, Nagarmortha-emergent):

1. MYRRH + OLIBANUM = Classic Amouage incense backbone
   - Myrrh (20 µL) joins Olibanum (13 µL active) for a true resinous heart
   - Creates "Church of the Desert" depth behind the fresh opening

2. LABDANUM = Amber warmth
   - Bridges the mineral/carbon notes with the macrocyclic musk chord
   - Amouage's signature "hot stone in cool water" effect

3. CARDAMOM = Spice sophistication  
   - Reflection Man uses cardamom + bergamot - you now have the bergamot
   - 10-15 µL adds aromatic complexity without competing

4. CYPROL = Double-down on Carbon axis
   - Nagarmortha (8 µL) + Cypriol (5 µL) = serious mineral-smoke
   - Makes the Luna Rossa Carbon reference unmistakable

5. YLANG = Floral opulence
   - Amouage doesn't shy from florals - they use them differently
   - Ylang adds creamy body that works WITH the 5-musk chord

CONCENTRATION IMPACT:
- Current: 16.8% (5,044 µL concentrate)
- Adding ~80 µL: New concentration ~17.3%
- Still well within EdP range (15-20%)

The bergamot dominance now reads as INTENTIONAL - a classical fougère
structure elevated with Amouage density. The formula becomes:
  Classical opening (bergamot-aromatics) 
  → Amouage heart (myrrh-labdanum-cardamom)
  → Carbon mineral base (nagarmortha-cypriol-patchouli-clearwood)
  → 5-musk skin finish
""")
