---
name: data-consistency
description: Cross-check all 4 data sources for a material — inventory.txt, YAML, ingredient_intelligence profiles, and ODT_DATA. Detect drift, missing entries, stale VPs, and duplicate ODTs.
---

## What I do
- Verify a material exists in all 4 required data locations
- Cross-check physical properties (MW, VP, cLogP, ODT) for consistency across sources
- Detect stale profiles where ingredient_intelligence VP differs from data_spine YAML
- Run the duplicate-odt-scanner to find entries where last-writer-wins
- Flag missing ODT entries, missing profiles, and alias gaps

## When to use me
Use BEFORE:
- Adding a new material to inventory (verify no existing data collision)
- Running the pipeline on a formula with unfamiliar materials
- Debugging "OAV = 0" or "100M+ OAV" pipeline bugs
- Regenerating `material_properties.json`

## The 4-Location Check

For each material, verify presence and consistency in:

### 1. `inventory.txt`
```
- Material Name (dilution%)  — μcat: <category>
```
- Check exact spelling (canonical name)
- Note the dilution percentage
- Check category placement
- Flag DEPLETED markers

### 2. `data/materials/<LETTER>.yaml`
- Verify `user_in_inventory: true`
- Check `mw_g_mol`, `logp`, `vp_25c_pa`, `odt_air_ppb`, `odt_eth_ppm`
- Check aliases array — must match inventory name variants
- Flag any missing `odt_*` fields

### 3. `engine/ingredient_intelligence.py` — `_PROFILES`
- Verify entry exists with `mw`, `vp`, `clogp`, `odt_air_ppb`, `odt_eth_ppm`
- Check `note`, `role`, `texture` are populated
- Verify `_TYPICAL_DOSE` entry exists
- Cross-check VP and ODT values match YAML (drift detection)

### 4. `engine/odor_thresholds.py` — `ODT_DATA`
- Verify entry exists
- Run duplicate scanner: `python -c "from engine.odor_thresholds import ODT_DATA; print(sum(1 for k,v in ODT_DATA.items() if k=='material_name'))"`
- The LAST entry wins — check for conflicting values

## Also Check
- `name_utils._ALIASES` — does the alias chain resolve correctly?
- `material_properties.json` — run `_generate_material_properties.py` after changes

## Common Drift Patterns
| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Pipeline OAV = 0 for a natural | Composite model missing this absolute | Add to `natural_absolute_decomposition.py` |
| OAV = 100M+ | Duplicate ODT entry | Remove duplicate, keep correct value |
| Profile VP ≠ YAML VP | Profile updated without YAML update | Fix profile to match data_spine |
| Material not found in pipeline | Alias mismatch | Add alias to `name_utils._ALIASES` |
