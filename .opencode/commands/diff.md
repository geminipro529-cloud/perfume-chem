---
description: Compare two formula versions — material changes, dose deltas, pyramid shifts
agent: build
---

Compare two formula files and show differences.

Format: `/diff <old_formula.md> <new_formula.md>`

1. Parse both formula files — extract materials, dilutions, raw µL
2. Show:
   - **Added** materials (in new, not in old) with functional roles
   - **Removed** materials (in old, not in new) — what role is now uncovered?
   - **Changed** materials (both files, different doses) with Δ µL and % change
3. Compute pyramid (T/H/B) shift between versions
4. Compute concentrate % delta
5. If both formulas have pipeline JSON available (output/ directory), include OAV deltas

Flag significant changes:
- OAV swings > 10x for any material
- Pyramid shift > 10% in any tier
- Concentrate % change > 2%
- Family-shifting materials added (Benzoin, Labdanum, Coumarin, Vanillin, etc.)

Present as a structured diff table with functional impact assessment.
