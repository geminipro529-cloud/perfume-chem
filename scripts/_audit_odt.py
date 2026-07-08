"""Scan ODT database for suspicious or anomalous entries"""
import sys; sys.path.insert(0, '.')
from engine.odor_thresholds import ODT_DATA

# Suspicious patterns:
# 1. Ultra-low ODT (< 0.001 ppb) — either super-potent or data error
# 2. ODT significantly inconsistent with character (e.g., "faint" at 0.001 ppb)
# 3. Duplicates with different values
# 4. Materials with zero or null ODT

flags = []

for name, data in sorted(ODT_DATA.items()):
    odt_air = data.get('odt_air')
    odt_eth = data.get('odt_eth')
    char = data.get('char', '')
    
    if odt_air is None:
        flags.append(('NULL_ODT', name, f'No odt_air value'))
        continue
    if odt_air == 0:
        flags.append(('ZERO_ODT', name, f'odt_air = 0'))
        continue
    
    # Ultra-low thresholds — potentially suspicious
    if odt_air < 0.001:
        flags.append(('ULTRA_LOW', name, f'odt_air = {odt_air} ppb — incredibly potent'))
    elif odt_air < 0.01:
        flags.append(('VERY_LOW', name, f'odt_air = {odt_air} ppb'))
    
    # Material listed as "faint" or "near-odorless" but with low ODT
    faint_keywords = ['faint', 'near-odorless', 'odorless', 'silent', 'mostly fixative']
    low_keywords = ['barely', 'faint', 'mild']
    if any(k in char.lower() for k in faint_keywords) and odt_air < 10:
        flags.append(('FAINT_LOW', name, f'"{char}" but ODT={odt_air} ppb (low for faint material)'))
    
    # Extremely high ODT (> 1000 ppb) — check if intended
    if odt_air > 1000:
        flags.append(('VERY_HIGH', name, f'odt_air = {odt_air} ppb — nearly odorless?'))

# Check for potential duplicates
from collections import defaultdict
name_groups = defaultdict(list)
for name in ODT_DATA:
    base = name.lower().replace('-', ' ').replace('_', ' ').strip()
    name_groups[base].append(name)

for base, names in name_groups.items():
    if len(names) > 1:
        vals = [(n, ODT_DATA[n]['odt_air']) for n in names]
        if len(set(v for _, v in vals)) > 1:
            flags.append(('DUPLICATE', ', '.join(names), f'Multiple entries with different ODT: {vals}'))

print(f'DATABASE SIZE: {len(ODT_DATA)} entries')
print(f'ISSUES FOUND: {len(flags)}\n')

if flags:
    for severity, name, detail in sorted(flags, key=lambda x: {'NULL_ODT':0,'ZERO_ODT':1,'ULTRA_LOW':2,'VERY_LOW':3,'FAINT_LOW':4,'DUPLICATE':5,'VERY_HIGH':6}[x[0]]):
        print(f'[{severity}] {name}')
        print(f'         {detail}\n')
else:
    print('No suspicious entries found.')
