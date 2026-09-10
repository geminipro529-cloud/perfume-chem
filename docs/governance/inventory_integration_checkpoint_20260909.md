# Inventory and receipt integration checkpoint — 2026-09-09

**Implemented; focused regression PASS. Not merged, committed, published, or release-approved.**

## Scope

- Imported the canonical September inventory successor chain, associated confirmation receipts, current inventory text, and the two unchanged historical bottle records referenced by the stock evidence.
- Preserved immutable predecessor data and existing authority pins. Added explicit LF checkout rules for hash-bound records; normalized the three existing historical JSON files to their already-pinned LF representation.
- Brought forward Neroli/Orris stock metadata and historical AHS formula fixtures required by the stock regressions. These are existing artifacts, not newly constructed or rebased formulas.
- Restored 13 identity aliases from the existing `IDENTITY_LABEL_ONLY` reconciliation manifest. No physical-property values were changed by the alias additions.
- Updated historical tests to distinguish the current stock head from inherited source authority, and to preserve the explicit Romandolide depletion and non-executable tincture basis holds.

## Receipt and state compatibility

Retained the baseline receipt builder and replay checks rather than replacing preflight with the alternate implementation that removes them. Added source-reference lineage for overlay-only stocks without workbook row numbers. Added replay checks for concentration basis, carrier, and declaration status.

Added receipt identifier/status fields to FormulaState and its serialized view. States rebuilt with changed doses remain unbound. Regressions cover identifier, raw-volume, active-volume, basis, carrier, and declaration tampering.

Carried the source-declared opaque-preblend classification for Lilyreal ND through MaterialProfile and formula-state evaluation. This prevents treating an opaque supplied product as a pure compound and preserves unknown OAV where decomposition is absent. No composition, density, assay, safety, or sensory-equivalence claim was introduced.

## Verification

- Final focused run: **168 passed, 0 failed**, 13.72 seconds reported by pytest.
- Scope: pipeline preflight; complexity/receipt design contracts; historical/current inventory synchronization and identity reconciliation; AHSEE, Neroli, Orris, Romandolide and tincture stock tests; formula-state and concentration-unit tests.
- Reused the existing canonical `.venv` interpreter with the isolated worktree as source-import root. Python bytecode and pytest cache were disabled; ignored test-output/temp artifacts may exist.
- 4,290 deprecation warnings originate from pytest-asyncio's use of a deprecated Python inspection API.
- Focused Ruff checks pass except one pre-existing E402 late import in `engine/ingredient_intelligence.py`. The same error was reproduced against the unmodified baseline; it was not suppressed or moved as part of this task.
- `git diff --check` passes.
- All 32 imported source-file fingerprints remained unchanged in the original canonical checkout at final comparison.

Exact imported-source and final candidate-file hashes are recorded in the adjacent JSON receipt. The receipt excludes itself and this explanatory note to avoid recursive hashing.

## Remaining boundaries

Full project verification and release acceptance are **NOT RUN**. The work remains uncommitted in `codex/integration-20260909`. Deep Plane variant reconciliation is the next checkpoint. Original worktrees and the sensitive local preservation snapshots remain in place; nothing was pushed or merged.
