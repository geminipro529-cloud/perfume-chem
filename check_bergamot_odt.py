from engine.odor_thresholds import lookup_odt_entry, ODT_DATA
for k, v in ODT_DATA.items():
    if 'bergamot' in k:
        print(f"  {k}: odt_air={v.get('odt_air','?')} odt_eth={v.get('odt_eth','?')}")
print()
for name in ['Bergamot FCF oil Sicilian', 'Bergamot FCF Sicilian', 'Bergamot FCF', 'bergamot fcf sicilian', 'bergamot fcf']:
    e = lookup_odt_entry(name) or {}
    print(f"  {name} -> odt_air={e.get('odt_air','MISS')} odt_eth={e.get('odt_eth','MISS')}")
