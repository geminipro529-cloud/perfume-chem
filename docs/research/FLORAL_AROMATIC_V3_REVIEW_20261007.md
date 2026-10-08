# Floral/aromatic v3: implemented repairs, final corpus acceptance withheld

Date: 2026-10-07. This is a software/research increment, not project completion,
an empirical perfume model, a compounding instruction or a release certificate.

## What is now implemented

The active bridge has 44 source-bound mappings and 88 comparison options, up
from v2's 22 mappings and 44 options. V1/v2 manifests and ordered mappings are
preserved. The additions deepen rose, jasmine, orange blossom, muguet/cyclamen,
peony, lily, pollen, honeysuckle, lavender, fougere, sandalwood and patchouli.
All 13 planned floral packages have at least one mapping; that is not exhaustive
floral coverage. There remain 135 of 179 partial subtype cards without executable
mappings. Literature, source-review and subtype manifests were not promoted or
rewritten in this increment.

The initial frozen diagnostic completed 224 calls: 53 of 56 case contracts passed.
Its failed artifact is retained. Three defects were repaired:

- Explicit cyclamen intent now precedes the muguet token in the diagnostic's
  formula name. Qualified matching and stable tie order remain explicit v3-only
  rules, not a ranking of scent quality.
- Equal stock/dose compositions no longer appear as different source-bound
  alternatives merely because their role labels differ. The original control
  stays unchanged. Suppressed attempts retain bounded physical rows, a reference
  to the earlier retained formula, and diagnostic reasoning.
- The auditor recognizes the real CHIMIE L'HOMME campaign hold, but only after
  independently matching the current canonical hold and request. It cannot
  accept a self-asserted status or silently infer a campaign from nearby perfumes.

The auditor also checks every planned attempt, exact option/role correspondence,
failure-specific evidence, duplicate conservation, and recomputed stock-dose
identity. Nine mutation cases reproduced suppression-verification gaps before
repair, including an invented reference, missing attempt, status relabel and
swapped solved IDs.

Profiling identified two full capability-index builds per request. The runtime
now builds once and applies the same explicit-material matcher to that snapshot.
There is no new cross-request cache. Tests compare complete output against the
former rebuild path and check explicit flags without mutating the original index.

## Fresh verification, with its exact limits

- A broader architecture/Formula Studio run passed 242 tests before the final
  suppression-auditor refinements; the intervening architecture run passed 202.
- On the final repaired implementation, all 26 repair tests passed, followed by
  88 focused receipt-binding, successor and repair tests. These counts overlap;
  they must not be summed as independent tests.
- Scoped Ruff passed. Scoped mypy passed for four changed source modules with
  `--follow-imports skip --explicit-package-bases`.
- The earlier v3 backend fingerprint/UI slice passed 19 tests. The final golden
  explicit-solvent API regression separately passed in the existing backend
  Python 3.11 environment with a disposable database.
- The quick project verifier passed nine checks, but its API check selected an
  incomplete sandbox Python 3.14 environment and could not import pytest_asyncio.
  The failed report is retained; the separate successful API check is not
  misrepresented as a successful monolithic quick run.
- `git diff --check` passed with line-ending warnings. No full project verifier,
  Docker acceptance, browser interaction, sensory study or physical build was run.

See `output/floral_aromatic_v3_20261007/repair_verification.json` for commands,
timings and the verification sequence. All pre-drift test results apply to the
recorded prior inventory, not automatically to newly received stocks.

## Why the final 224-call rerun is not accepted

The repaired rerun completed 65 calls before the live inventory changed during
execution. The new text refers to a 53-line PerfumersWorld receipt, but the stock
loader still required its prior AIMI-bound inventory version. It raised:

`InventoryAuthorityError: AIMI identity successor is not bound to live inventory text`

The initial inventory hash was
`a07a862febe2e6da3b6301a1189b2cb330a55a801f5126b89ccd57751f0591bb`;
the observed new hash was
`116c39815c81d148f0a259332b8acf734b9f3eced484b5e390dc4bc7df38cc58`.
This work did not edit that inventory or its new receipt and did not bypass the
guard, reset user changes or combine old/new stock results into a claimed pass.
The partial timings are not performance acceptance or an accepted speedup.

The protected-input census had 587 files, including 578 formula files. At the
last pre-run check all were unchanged. After the interruption, only inventory.txt
had changed within that protected census; all 578 formula files remained equal.
This census starts at the recorded pre-validation point, not the start of the
entire long-running chat.

The machine-readable interrupted result is
`floral_aromatic_comparison_aborted_20261007.json`. No final passing v3 comparison
artifact exists. Do not describe this wave as fully corpus-accepted.

## Next safe checkpoint

1. Let the new received-stock reconciliation finish, with an exact versioned
   inventory binding. Do not weaken the historical AIMI guard or infer stock bases.
2. Freeze that reconciled inventory and check the affected inventory-dependent
   test fixtures. A previously duplicate pair may legitimately become distinct
   when new materials become available.
3. Rerun all 56 frozen prompts in both arms and reverse order on one unchanged
   inventory/source snapshot. Recheck duplicates, constraints, controls and speed.
4. Only then mark v3 corpus acceptance. Extend the remaining subtype mappings
   through new literature-first, bounded increments rather than claiming all
   botanical or perfume-structure research is complete.

CHIMIE L'HOMME still needs its exact accepted brief/formula; adjacent structures
do not clear that hold. Orris Liquid remains excluded. No scent-improvement,
pleasantness, consumer-liking, safety, compounding or release authority was added.
