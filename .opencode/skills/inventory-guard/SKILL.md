---
name: inventory-guard
description: Verify every material in a formula against live inventory — stock, dilution, data completeness. MUST USE before any formula creation or pipeline run.
---

## What I do
- Cross-check all materials in a formula against `inventory.txt`
- Flag depleted materials, wrong dilutions, and missing inventory entries
- Verify every material has complete data in all 4 required locations
- Validate that materials can be physically dosed (dilution compatibility)
- Produce a go/no-go report before any gate run

## When to use me
Use BEFORE:
- Creating any new formula
- Running `scripts/formula_release_gate.py`
- Modifying an existing formula (verify new materials)
- Running `/gate` command (pre-flight check)

## Guard procedure

### Phase 1: Inventory Cross-Check
For every material in the formula:
1. Parse `inventory.txt` — locate the material under any category
2. Verify the dilution percentage matches what's listed in inventory
3. Check for DEPLETED markers — if depleted, recommend alternatives
4. If material NOT FOUND in inventory → HARD STOP, suggest alternatives

### Phase 2: Data Completeness (4-location check)
For every material in the formula:
1. **`engine/odor_thresholds.py`** — exists in ODT_DATA? Check for duplicate entries (last wins)
2. **`data/materials/<LETTER>.yaml`** — has MW, logP, VP, ODT fields populated?
3. **`engine/ingredient_intelligence.py`** — has profile with note, role, texture, mw, vp?
4. **`engine/ingredient_intelligence.py`** — has _TYPICAL_DOSE entry?

### Phase 3: Dosing Feasibility
- Can the required active µL be achieved with the available dilution?
- Are trace materials (≤1%) dosed within their working range?
- Are neat powerhouses (Iso E Super, Hedione, etc.) not overdosed?

### Report format

```
═══════════════════════════════════════════════
INVENTORY GUARD — Formula: <name>
═══════════════════════════════════════════════

📦 STOCK CHECK:
| # | Material | Formula Dilution | Inventory Dilution | Match? | Stock |
|---|----------|-------------------|---------------------|--------|-------|
| 1 | X        | 10%              | 10%                 | ✓      | OK    |
| 2 | Y        | neat             | 10%                 | ✗ MISMATCH | OK |

🔬 DATA COMPLETENESS:
| Material | ODT_DATA | YAML | Profile | Typical Dose | Status |
|----------|----------|------|---------|--------------|--------|

⚠️  FLAGS:
- [CRITICAL] Material not in inventory: Z
- [WARNING] Depleted: A
- [WARNING] ODT_DATA duplicate: B (entries: 2, last wins)
- [INFO] No typical dose: C

🏁 VERDICT: GO / NO-GO
```

## Critical rules
- NEVER skip inventory verification — inventory changes between sessions
- ALWAYS flag depleted materials and suggest alternatives from inventory
- ALWAYS warn about ODT_DATA duplicates (last entry wins, may be wrong)
- If dilution mismatch exceeds 2x, require formula correction
- Materials not in inventory → HARD STOP, do not proceed
