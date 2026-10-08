---
name: formula-variant-ladder
description: Build a dose ladder of perfume-chem formula variants (e.g. ±7.5% on named rows) that changes nothing else, gate each against the parent, and write a comparison.
---

# Formula variant ladder

> **Status: DRAFT (2026-10-08).** Not yet proven over many runs. If any step here
> is wrong or missing when you use it, fix this file in the same change and add a
> line under "Known issues / change log". Keep `.claude/skills/` and
> `.agents/skills/` copies identical (`tests/test_skill_mirrors.py` checks this).

Use when Kenny wants variants of an existing formula to compare or smell-test (for
example the Lavande R6 LavLow/LavHigh ladder).

## Design
1. Re-read the formula name and brief (Rule 3). A step is valid only if the variant
   still smells like its name; drop off-name moves (for example Iso E Super or
   Ambrox boosts on a lavender) and say why.
2. Pick the rows and the step from the reason for the test (literature or Kenny's
   ask). State rows by source row number and multiplier, e.g. rows 34, 36, 42
   × 0.925 / × 1.075.
3. Change only those rows. Keep stock dilutions identical; a stock-strength change
   must preserve active dose (`STOCK_REBASE_ACTIVE_EQUIVALENCE` is a hard fail).
4. Recompute the concentrate total for each variant. Name files
   `<Parent>_<Tag>_30mL_EDP.md`. Never edit Kenny's formula in place unless asked.

## Gate
Gate each file with the `perfume-gate-run` skill, using the parent as
`--parent-formula-file` for every variant, and the same brief and engine commit for
all runs. Record the engine branch and commit.

## Compare (write `GATE_COMPARISON_<date>.md`)
- Table: file, overall verdict, PASS/WARN/FAIL/SKIP counts, pre-mix guard result
  versus the parent.
- The changed rows' OAV lines for each variant side by side, plus any gate that
  differs between variants.
- Say plainly which FAILs are shared data gaps.
- Model differences are not sensory evidence. The decision comes from a blinded
  comparison (triangle test first when two bottles may be indistinguishable).

Leave earlier comparison files as they were; a re-gate on a newer engine gets a new
file that says what it supersedes.

## Known issues / change log
- 2026-10-08: first draft, from the Lavande R6 ±7.5% lavender ladder.
