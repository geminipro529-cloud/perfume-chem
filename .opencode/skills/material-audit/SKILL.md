---
name: material-audit
description: Verify a material exists in all 4 required data locations and has consistent properties
---

## What I do
- Audit a perfume material for completeness across the codebase
- Check all 4 required locations for material data
- Report inconsistencies in MW, VP, ODT, logP values
- Flag missing entries and data gaps

## When to use me
Use when:
- Adding a new material to inventory (4-place verification)
- Debugging a material with wrong OAV values
- Verifying data consistency after material updates
- Checking if a material is pipeline-ready

## Audit procedure

For a given material name, check these 4 locations:

### 1. inventory.txt
- Search for the material under any category header
- Confirm it exists and note its listed dilution percentage
- Check for DEPLETED markers

### 2. data/materials/<LETTER>.yaml
- Find the material by first letter of normalized name
- Verify these fields exist: `mw_g_mol`, `logp`, `vp_25c_pa`, `odt_air_ppb`, `odt_eth_ppm`, `user_stock_dilution`, `user_in_inventory: true`

### 3. engine/ingredient_intelligence.py
- Check `_PROFILES` dict for character, note, role, texture, mw, vp, clogp, synergies
- Check `_TYPICAL_DOSE` for dosing range
- Check `_ODOR_FAMILY_MAP` for family classification
- Check `_ACTIVITY_COEF_MAP` for activity coefficient
- Verify VP in profile matches data_spine YAML

### 4. engine/odor_thresholds.py
- Check `ODT_DATA` dict for `odt_air` and `odt_eth` values
- Run grep to count occurrences — duplicate keys mean "last entry wins"
- Flag if `ODT_VERIFICATION` exists but `ODT_DATA` entry is missing

### Also check
- Does `name_utils._ALIASES` need updating for this material?
- Does `_generate_material_properties.py` need the alias?

## MCP Cross-Reference (Tier 1 source)

When validating material data, the material_validator module can cross-check
local data against PubChem (via `engine/pubchem_client.py`). This catches:

- MW discrepancies (e.g., Alpha Irone VP=0.005 in profile vs 0.559 in YAML)
- logP calculation differences (local vs PubChem XLogP3)
- Missing CAS numbers
- Stale cache entries (TTL: 30 days)

### MCP freshness check

```python
from engine.pubchem_client import cache_stats
stats = cache_stats()
# stats = {"total_entries": 42, "fresh": 42, "stale": 0, "cache_file": "..."}
```

If `stale > 0`, consider running:
```bash
python engine/material_validator.py --materials <names> --report output/audit.md
```

This regenerates cache entries that are older than 30 days.

### Report format (extended)

| Check | Status | Detail |
|-------|--------|--------|
| inventory.txt | FOUND/MISSING | Category, dilution |
| data_spine YAML | FOUND/MISSING | Missing fields listed |
| Profiles | FOUND/MISSING | Missing sub-tables |
| ODT_DATA | FOUND/MISSING | Duplicates? |
| Aliases | OK/NEEDED | If normalized name differs |
| **PubChem MW** | MATCH/CONFLICT/MISS | local vs pubchem, pct_diff |
| **PubChem logP** | MATCH/CONFLICT/MISS | local vs pubchem, pct_diff |
| **MCP freshness** | FRESH/STALE | days since last PubChem fetch |

Recommend `python _generate_material_properties.py` if any YAML or profile data was updated.
