from pathlib import Path

import yaml

checks = ['methyl anthranilate', 'ambrettolide', 'bergamot fcf sicilian', 'bergamot fcf oil sicilian', 'blood orange sicilian', 'blood orange oil sicilian']
found = set()
for yfile in sorted(Path('data/materials').glob('*.yaml')):
    with open(yfile, encoding='utf-8') as f:
        for entry in yaml.safe_load(f) or []:
            cn = (entry.get('canonical_name') or '').lower()
            if cn in checks:
                print(f"YAML: {entry['canonical_name']}")
                print(f"  mw={entry.get('mw_g_mol')} logp={entry.get('logp')} vp={entry.get('vp_25c_pa')}")
                found.add(cn)

for c in checks:
    if c not in found:
        print(f"MISSING: {c}")

print()
# Also check formulas resolve correctly
from engine.inventory_parser import _canonical_name, _parse_dilution

tests = [
    "Bergamot FCF oil Sicilian",
    "Blood Orange oil Sicilian",
    "Methyl Anthranilate",
]
for t in tests:
    print(f"'{t}' -> canon='{_canonical_name(t)}' dil={_parse_dilution(t)}")
