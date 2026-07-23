from pathlib import Path

import yaml

from engine.ingredient_intelligence import _ACTIVITY_COEF_OVERRIDES, _PROFILES
from engine.odor_thresholds import ODT_DATA

materials = [
    "Iso E Super", "Galaxolide", "Ambrofix", "Hedione", "Paradisamide",
    "Cashmeran", "Javanol", "Ambrettolide", "Habanolide", "Ethylene Brassylate",
    "Aurantiol", "Linalool", "Lemonile", "Nerolin Bromelia", "Nerol",
    "Methyl Anthranilate", "Bergamot FCF oil Sicilian", "Grapefruit FCF",
    "Pamzest", "Blood Orange oil Sicilian"
]

def get_yaml(name):
    n = name.lower()
    for yfile in Path('data/materials').glob('*.yaml'):
        with open(yfile, encoding='utf-8') as f:
            for entry in (yaml.safe_load(f) or []):
                if (entry.get('canonical_name') or '').lower() == n:
                    return entry
    return {}

print(f"{'Material':30s} {'MW':>8s} {'VP':>12s} {'logP':>8s} {'ODT_air':>8s} {'ODT_eth':>8s} {'gamma':>6s}  STATUS")
print("-"*90)

for name in materials:
    y = get_yaml(name)
    p = _PROFILES.get(name, {})
    n = name.lower()
    odt = ODT_DATA.get(n, {})

    mw = y.get('mw_g_mol') or p.get('mw', 'MISS')
    vp = y.get('vp_25c_pa') or p.get('vp', 'MISS')
    lp = y.get('logp') or p.get('clogp', 'MISS')
    oa = odt.get('odt_air', 'MISS')
    oe = odt.get('odt_eth', 'MISS')
    ga = _ACTIVITY_COEF_OVERRIDES.get(n, 'est')

    missing = []
    for field, val, label in [('MW', mw, 'MW'), ('VP', vp, 'VP'), ('logP', lp, 'logP'), ('ODT_a', oa, 'ODT_air'), ('ODT_e', oe, 'ODT_eth'), ('γ', ga, 'gamma')]:
        if val == 'MISS':
            missing.append(label)

    status = "LOCKED" if not missing else f"MISSING: {', '.join(missing)}"
    print(f"{name:30s} {str(mw):>8s} {str(vp):>12s} {str(lp):>8s} {str(oa):>8s} {str(oe):>8s} {str(ga):>6s}  {status}")
