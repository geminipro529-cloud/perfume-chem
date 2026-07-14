---
description: Diagnose failed pipeline output — pattern-match known bugs and suggest fixes
agent: build
---

Diagnose a pipeline gate failure by pattern-matching known bugs.

Format: `/pipeline-debug <pipeline_output.json>` or `/pipeline-debug` (uses output/pipeline_result.json)

1. Read the pipeline JSON output file
2. Extract all FAILED gates from `gate_results[]`
3. For each failed gate, match against known failure patterns:

   | Pattern | Symptom | Root Cause |
   |---------|---------|------------|
   | Pattern 1 | Pyramid T:0% H:100% B:0% | note_map key mismatch in gates.py:720 |
   | Pattern 2 | Material OAV > 100M | Duplicate ODT_DATA entry |
   | Pattern 3 | --brief has no effect | archetype not resolved in gates.py:953 |
   | Pattern 4 | Material missing physics data | Missing from YAML/profile/ODT_DATA |
   | Pattern 5 | Stale VP in profile | Profile VP ≠ data_spine VP |
   | Pattern 6 | ODT_VERIFICATION exists, ODT_DATA missing | Numeric values not in ODT_DATA |
   | Pattern 7 | Concentrate volume mismatch | --expected-concentrate-ul wrong |
   | Pattern 8 | Family drift fails unexpectedly | Forbidden materials or missing anchors |

4. For matched patterns: provide fix steps and verification commands
5. For unknown patterns: suggest full investigation with relevant files

Present results with:
- Confidence level (HIGH/MEDIUM/LOW) for each diagnosis
- Recommended fix ORDER (code bugs before data bugs)
- Specific file:line references for fixes
