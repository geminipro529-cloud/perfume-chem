---
name: pipeline-debugger
description: Diagnose common pipeline failure patterns — pyramid T:0%, 100M+ OAV, stale VPs, brief not resolving, material data gaps.
---

## What I do
- Diagnose pipeline gate failures by pattern-matching known bugs
- Cross-reference output JSON against known failure signatures
- Suggest targeted fixes for each failure class
- Check for data quality issues that silently corrupt results

## When to use me
Use when:
- A pipeline gate run produces unexpected PASS/FAIL results
- OAV values seem unreasonably high (100M+) or zero
- Pyramid shows T:0% H:100% B:0% for all formulas
- The `--brief` flag seems to have no effect
- Materials are missing physics data in the output
- Gate results contradict manual calculations

## Known failure patterns

### Pattern 1: Pyramid T:0% H:100% B:0%
**Root cause**: `engine/pipeline/gates.py` ~line 720 — note_map built with mixed-case keys, `.lower()` lookup returns "heart" default.
**Fix**: Check `gates.py` for `.lower()` call on note_map keys. This is a known code bug, not a formula issue.
**Verify**: Run `rg "note_map" engine/pipeline/gates.py` and confirm `.lower()` usage.

### Pattern 2: Material has OAV > 100M
**Root cause**: Duplicate ODT_DATA entries in `engine/odor_thresholds.py` — later wrong value overwrites correct one. Common with Hedione, Benzoin, and recently edited materials.
**Fix**: Run `/duplicate-odt-scanner` to find conflicts. Check which entry "wins" (last in file).
**Verify**: `rg "material_name" engine/odor_thresholds.py` — if count > 1, there's a duplicate.

### Pattern 3: `--brief` has no effect on gate results
**Root cause**: `perfume_knowledge` gate reads `family_archetype` raw; brief parameter never resolved to archetype.
**Fix**: Check `engine/pipeline/gates.py` ~line 953 — need `infer_archetype()` fallback.
**Verify**: Check `config_summary.archetype` in pipeline JSON output.

### Pattern 4: Material missing physics data (MW, VP, ODT all zero/null)
**Root cause**: Material added to inventory but missing from data_spine YAML, ingredient_intelligence profile, ODT_DATA, or all three.
**Fix**: Run `/material-audit <material_name>` and follow the 4-location verification.
**Verify**: Check that all 4 locations have the material.

### Pattern 5: Stale note/VPs in profiles (profile VP differs from data_spine)
**Root cause**: ingredient_intelligence profile was updated but data_spine YAML wasn't, or vice versa.
**Fix**: Compare `_PROFILES[mat]['vp']` vs `data/materials/<LETTER>.yaml` `vp_25c_pa`. Sync to data_spine value.
**Verify**: Run `python _generate_material_properties.py` to resync.

### Pattern 6: ODT_VERIFICATION entry exists but ODT_DATA missing
**Root cause**: Material has verification metadata but no numeric ODT values. `_lookup_odt()` only reads ODT_DATA.
**Fix**: Copy numeric ODT values from verification dict to ODT_DATA, or add to ODT_DATA directly.
**Verify**: `rg "material_name" engine/odor_thresholds.py` — check both dicts.

### Pattern 7: Concentrate volume mismatch (gate expects different µL)
**Root cause**: `--expected-concentrate-ul` doesn't match formula's actual active µL.
**Fix**: Check formula math: sum all (raw µL × dilution%) = active µL. Pass that number.
**Verify**: Manually calculate active µL from formula table.

### Pattern 8: Family drift detection fails unexpectedly
**Root cause**: Formula contains materials forbidden by the family archetype, or anchor materials are missing.
**Fix**: Check `engine/families/registry.py` for the archetype's forbidden/anchor lists.
**Verify**: Compare formula materials against `ArchetypeSpec.forbidden_materials`.

## Diagnostic procedure

1. Read the pipeline JSON output
2. Check `gate_results[]` — which gates FAILED?
3. For each failed gate, extract `data` and `reason` fields
4. Match against the known patterns above
5. If no pattern matches, check:
   - Did all materials have ODT data? (check `formula_state.materials[].odt_ppm`)
   - Were dilutions correctly parsed? (check `formula_state.materials[].dilution`)
   - Did the brief/archetype resolve correctly? (check `config_summary`)
6. Report: pattern matched → fix + verify steps. No match → escalate to full investigation.

## Report format

```
═══════════════════════════════════════════════
PIPELINE DEBUGGER
═══════════════════════════════════════════════

🔴 FAILED GATES (3 of 12):

1. perfume_knowledge → PATTERN 1: Pyramid T:0% H:100% B:0%
   Fix: Check gates.py line 720 for .lower() on note_map
   Confidence: HIGH

2. oav_intelligence → PATTERN 2: Hedione OAV = 150,000,000
   Fix: Run /duplicate-odt-scanner for Hedione
   Confidence: HIGH

3. family_drift_detector → UNKNOWN PATTERN
   Needs investigation: formula has 2 forbidden materials
   See: engine/families/registry.py → vetiver_woody.forbidden_materials

🟡 WARNINGS:
- 3 materials use default γ=1.0 (no activity coefficient data)

📋 RECOMMENDED FIX ORDER:
  1. Fix Pattern 1 (code bug, blocks all passes)
  2. Fix Pattern 2 (data bug, inflates OAV)
  3. Investigate Pattern 3 separately
```
