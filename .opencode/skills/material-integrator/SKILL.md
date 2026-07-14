---
name: material-integrator
description: Step-by-step guided workflow for adding a new material to inventory across all 4 required data locations with verification.
---

## What I do
- Guide the user through adding a new material to the perfume inventory
- Touch all 4 required locations in the correct order
- Verify data consistency across all sources
- Run the material property generator after completion
- Clean up any alias or naming issues

## When to use me
Use when adding ANY new material to the inventory — whether it's an aroma chemical, EO, absolute, FTEC, or fragrance oil.

## The 4-Step Integration

### Step 1: `inventory.txt`
Add the material under the correct category header:
```
--- CITRUS / TOP NOTES ---
- New Material (dilution%)  — μcat: category_name
```
Guidelines:
- Use the canonical name consistently
- Mark dilution in parentheses after the name
- Add `— μcat:` with the fragrance family category
- If the material is depleted, add `[DEPLETED]` after the dilution

### Step 2: `data/materials/<LETTER>.yaml`
Add a complete YAML entry with all physical properties:
```yaml
- name: "New Material"
  aliases: ["new material", "new material (alt name)"]
  cas: "123-45-6"
  mw_g_mol: 150.0
  logp: 3.5
  vp_25c_pa: 0.5
  odt_air_ppb: 10.0
  odt_eth_ppm: 0.5
  user_stock_dilution: 1.0
  user_in_inventory: true
```
- Place in the file corresponding to the first letter of the material name
- Omit CAS if unknown (leave as empty string or null)

### Step 3: `engine/ingredient_intelligence.py`
Add to `_PROFILES`:
```python
"new material": {
    "character": "description",
    "note": "floral|citrus|woody|etc",
    "role": "top|heart|base|fixative|modifier",
    "texture": "description",
    "mw": 150.0,
    "vp": 0.5,
    "clogp": 3.5,
    "odt_air_ppb": 10.0,
    "odt_eth_ppm": 0.5,
    "odor_family": "family_name",
    "activity_coef": 1.5,
    "synergies": ["related_material1", "related_material2"],
    "hedonic": 0.5,
    "impact": 3
}
```
Also add to:
- `_TYPICAL_DOSE` — recommended dose range in % of concentrate
- `_ODOR_FAMILY_MAP` — if introducing a new odor family
- `_ACTIVITY_COEF_MAP` — activity coefficient for ethanol matrix

### Step 4: `engine/odor_thresholds.py` — `ODT_DATA`
Add to the `ODT_DATA` dict:
```python
"new material": {
    "odt_air_ppb": 10.0,
    "odt_eth_ppm": 0.5,
    "source": "PubChem/Calkin&Jellinek/GC-MS",
    "notes": "Any relevant notes about threshold determination"
}
```
Also add to `ODT_VERIFICATION` if metadata tracking is enabled.

## Post-Integration

### Update aliases
Check `engine/name_utils.py` — `_ALIASES` dict:
- Add any name variants that appear in formulas or inventory
- Ensure lowercase canonical normalization works

### Run the generator
```bash
python _generate_material_properties.py
```

### Run the duplicate scanner
```python
python -c "from engine.odor_thresholds import ODT_DATA; print([k for k,v in ODT_DATA.items() if v.get('odt_air_ppb') is None])"
```

### Verify with material-audit
Run the `/material-audit` or load the material-audit skill for a final cross-check.

## Common Pitfalls
- Forgetting aliases → pipeline can't find material → "not in inventory" error
- ODT in `ODT_DATA` but not in profile → pipeline uses wrong ODT
- VP mismatch between YAML and profile → stale VP warning in gates
- Dilution mismatch between inventory and profile → incorrect active µL in calculations
