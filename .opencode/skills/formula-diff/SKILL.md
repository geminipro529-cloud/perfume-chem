---
name: formula-diff
description: Compare two formula versions — OAV deltas, material changes, pyramid shifts, cost impact. Use for reformulation review.
---

## What I do
- Compare two formula markdown files side-by-side
- Compute OAV deltas for materials present in both versions
- Show added/removed materials with functional impact
- Compare pyramid distribution (T/H/B) between versions
- Flag significant changes: OAV swings > 10x, pyramid shifts > 10%

## When to use me
Use when:
- Comparing a reformulated version against the original
- Reviewing optimization results
- Checking if a "sparkle/luxury" enhancement changed the family
- Verifying that a fixative adjustment didn't shift the pyramid
- Pre-commit: diff the formula before and after edits

## Diff procedure

### Phase 1: Material Inventory Diff
1. Parse both formula files — extract material names, dilutions, raw µL, active µL
2. Identify: ADDED (in new, not in old), REMOVED (in old, not in new), CHANGED (both, different doses)
3. For each CHANGED material, compute: Δ raw µL, Δ active µL, % change

### Phase 2: Functional Impact Assessment
For ADDED materials:
- What note tier (T/H/B)?
- What functional role (character, fixative, musk, structural)?
- Does it introduce a new odor family?

For REMOVED materials:
- What was its functional role?
- Is that role now uncovered?
- What replaced it (if anything)?

### Phase 3: OAV Delta (requires pipeline runs of both)
If both versions have been gated:
1. Extract OAV vectors from both pipeline outputs
2. Compute Δ OAV for each material
3. Flag materials with OAV change > 10x

### Phase 4: Pyramid Shift
1. Compare T/H/B percentages between versions
2. Flag shifts > 10% in any tier
3. Check if the family archetype boundaries are still respected

### Phase 5: Concentrate % Impact
1. Old concentrate % vs new concentrate %
2. Delta in total active µL
3. Performance projection impact (from OAV intelligence)

## Report format

```
═══════════════════════════════════════════════
FORMULA DIFF: v1 (original) → v2 (reformulated)
═══════════════════════════════════════════════

📊 MATERIAL CHANGES:
  + ADDED (2):  Paradisamide (120 µL neat), Zenolide (80 µL neat)
  - REMOVED (1): DBCA (100 µL neat)
  ~ CHANGED (5): See below

🔄 DOSE CHANGES:
| Material | Old µL | New µL | Δ µL | Δ % | Impact |
|----------|--------|--------|------|-----|--------|
| Hedione  | 300    | 250    | -50  | -17%| Reduced radiance |
| ISO E    | 400    | 420    | +20  | +5% | Minor structure |

🏛️ PYRAMID SHIFT:
  Top:  25% → 28%  (+3%)  ⚠️
  Heart: 35% → 30%  (-5%)
  Base:  40% → 42%  (+2%)

🧪 CONCENTRATE:
  Active µL:  1,110 → 1,080  (-30 µL, -2.7%)
  Concentrate: 11.1% → 10.8% (-0.3%)

⚡ FUNCTIONAL IMPACT:
  + Paradisamide: tropical-fruity modifier replaces DBCA's gardenia-rose
    → Family shift risk: LOW (fruity substitute for floral)
    → Note: Paradisamide has 150hr tenacity vs DBCA's 30hr — drier drydown

🚩 FLAGS:
  ⚠️  Top notes increased 3% — opening may feel more citrus-forward
  [✓] Base dominance maintained
  [✓] Musk chord unchanged
```
