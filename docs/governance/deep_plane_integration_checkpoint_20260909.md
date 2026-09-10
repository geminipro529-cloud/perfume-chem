# Deep Plane compatibility checkpoint — 2026-09-09

Implemented and focused-regression verified in the isolated integration worktree. This is a diagnostic candidate, not production runtime admission or a release.

## Changes

- Preserved the existing recursive receipt API in engine/formulation_intelligence/deep_plane_runtime.py without edits.
- Imported the alternate checkout's diagnostic implementation into engine/formulation_intelligence/deep_plane_diagnostics.py, keeping the two distinct APIs separate.
- Imported its seven diagnostic tests under tests/test_deep_plane_diagnostics.py and added compatibility regressions.
- Diagnostic executability now requires the shared current inventory stock contract, a fresh expected dose receipt matching the supplied receipt, and exact formula-state replay. Undeclared fractions, non-executable tinctures, depleted stocks, extra state rows, changed doses, stale receipt metadata, and custom inventory paths cannot gain executable status through a name/dilution match.
- Standalone diagnostics do not automatically bind their modeled states: their executable-stock claim stays withheld. A caller may supply a valid receipt to the in-memory diagnostic evaluator.
- Preserved all false authority flags and HOLD status. A successful input check does not establish physical, sensory, safety, compounding, purchase, or release authority.
- Reconciled the actual pre-mix guard status vocabularies: FAIL/WARN/PASS and SCREEN_BLOCK/SCREEN_REVIEW/SCREEN_CLEAR. Unknown statuses block. This fixes an integration hazard where the alternate implementation would have missed the current guard's FAIL status.
- Updated the missing-natural-model regression to explicitly simulate missing coverage rather than assume Frankincense remains uncovered in the current registry. No chemical registry or physical model was changed.

## Verification

- Fresh combined run: **211 passed, 0 failed**, 29.12 seconds reported by pytest.
- Includes new diagnostic tests, the existing 12 recursive receipt tests, and the full previously selected inventory/preflight/formula-state/unit regression scope.
- Ruff on the two new Python files: PASS.
- git diff --check: PASS; existing checkout line-ending warnings remain.
- All 42 inventory-checkpoint candidate file hashes still match their recorded values.
- Both imported source files in the original alternate checkout retain their original hashes.
- No staged changes, commits, merges, pushes, new CLI scripts, or production gate wiring.
- 5,520 pytest-asyncio deprecation warnings; not assertion failures.
- Full project verifier, admission benchmark, transitive dependency closure, production integration, and release verification: NOT RUN.

## Remaining integration boundary

The alternate checkout's release-gate and CLI changes were deliberately not imported. The diagnostic module now coexists and connects to current inventory/receipt contracts through its callable API, but enabling it in the production pipeline still needs a separate bounded review of configuration, caller receipt propagation, parent-state binding, temporal-frame provenance, and admission requirements. Other retained diagnostic heuristics have not been scientifically revalidated by this checkpoint.

## Evidence

Exact source/candidate hashes are recorded in deep_plane_integration_checkpoint_20260909.json.
Test receipt: D:/codex-preservation/perfume-chem-20260909/deep-plane-integration-tests-final.xml.

The original checkouts and private preservation snapshots remain in place.
