---
name: formula-validator
description: Pre-gate formula structural lint — format, naming, dilution consistency, concentrate math. Faster than full pipeline for quick iteration.
---

## What I do
- Validate formula markdown structure against the established format
- Check material naming consistency (normalized names vs aliases)
- Verify concentrate % math (total active µL / total batch µL × 100)
- Flag common dosing errors (trace overdoses, fixative under-dosing)
- Check pyramid balance sanity (top/heart/base distribution)
- Ensure all required sections exist in the formula file

## When to use me
Use BEFORE running the full pipeline gate when:
- Writing a new formula (fast iteration cycle)
- Making dosing adjustments to an existing formula
- Checking formula structure before committing
- The full pipeline takes too long — I'm the fast lint pass

## Validator procedure

### Phase 1: Structural Validation
1. Does the file have a table with columns: #, Ingredient, Dilution, Amount (µL), Amount (mL)?
2. Are there Top / Heart / Base section dividers?
3. Is the concentrate % calculated and stated?
4. Are all amounts in µL or mL (never grams)?
5. Is the batch size stated (typically 10.00 mL)?

### Phase 2: Material Name Validation
1. Normalize every material name using `engine/name_utils.py`
2. Check against known aliases in `_ALIASES` dict
3. Flag materials with ambiguous names (could refer to multiple inventory items)
4. Flag materials that don't match any known name (possible typo)

### Phase 3: Dilution Consistency
1. For each material, check: active µL = raw µL × (dilution% / 100)
2. Verify the dilution stated matches what's in inventory.txt
3. Flag dilutions that don't match any known inventory entry

### Phase 4: Math Validation
1. Sum all active µL → verify concentrate volume
2. Sum all raw µL → verify total raw volume
3. Calculate concentrate %: active µL / total batch µL × 100
4. Flag if stated concentrate % differs from calculated by > 0.5%

### Phase 5: Dosing Sanity
1. Trace materials (ODT < 1 ppb): should be ≤ 50 µL raw
2. Powerhouse materials (>500 µL neat): check for overuse
3. Fixative layer: total fixative active % should be 8-20% of concentrate
4. Musk axis: at least 2 musk materials covering different axes

### Report format

```
═══════════════════════════════════════════════
FORMULA VALIDATOR — <formula_name>
═══════════════════════════════════════════════

📐 STRUCTURE:
  [✓] Table format matches standard
  [✓] Top/Heart/Base sections present
  [✓] Concentrate % stated: 18.5%

🔤 NAMES:
  Found 1 ambiguous name: "Bergamot" → Bergamot FCF or Bergamot FCF Sicilian?
  0 material typos detected

🧪 DILUTIONS:
  12/12 materials match inventory dilutions ✓

🔢 MATH:
  Total active µL: 1,110 µL
  Total batch: 10,000 µL
  Concentrate: 11.1% (stated: 11.1%) ✓

💊 DOSING SANITY:
  ⚠️  Triplal at 80 µL neat — max recommended 50 µL (ODT 0.001 ppb)
  [✓] Fixative layer: 12.3% of concentrate (target 8-20%)
  [✓] Musk chord: 3 materials covering depth+projection+character-echo

🏁 OVERALL: PASS with 1 warning
```
