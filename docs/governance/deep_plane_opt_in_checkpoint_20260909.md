# Deep Plane opt-in pipeline connection — 2026-09-09

**Implemented; 255 selected regression tests passed. Disabled by default. Not production-admitted or release-approved.**

## What is connected

The existing gate_formula caller now has an explicit ReleaseGateConfig.deep_plane_diagnostics_enabled switch, default false. When enabled it freezes the current stock/dose receipt, binds the child FormulaState, passes the receipt to preflight, and reuses the child simulation in the Deep Plane diagnostic adapter.

The parent is independently resolved and receipt-bound using its own formula and declared matrix metadata. The diagnostic rejects an absent or stale receipt, mismatched formula/state, missing or reordered time windows, foreign simulation origins, changed frame content, and incompatible parent/child calculation contexts.

Simulation provenance records the originating exact state and dose-receipt hashes plus each frame's content checksum. The checksum uses dataclass values rather than rounded display values. These checks detect inconsistent content under the supplied receipts; they are not digital signatures, independent physics reproduction, scientific admission, or proof against a party who can regenerate all hashes.

The physical model is unchanged. Regression tests compare the entire modeled state and display payload with provenance enabled and disabled. When disabled, no frame-provenance fields are added to the serialized output and the diagnostic adapter is not called.

## Fail-closed policy

- Diagnostic exceptions and malformed results are hard gate failures, not advisory warnings.
- Required thirteen-plane coverage, authority flags, receipt identity, finding/status consistency, and provenance assertions are checked at the adapter boundary.
- A diagnostic input-quality PASS is exposed as WARN by this candidate connection.
- Every enabled candidate run reports NOT_RELEASE_READY, including commercial-trial configurations.
- Existing missing-physics holds remain failures. The Hedione wiring fixture has a REQUIRED_PHYSICS_MISSING hold; the tests verify receipt/provenance success without pretending the physics hold was resolved.
- The separate recursive receipt runtime remains unchanged.
- No CLI activation flag or new pipeline script was created.

## Verification

- Before edits: existing caller tests **18 passed**.
- First corrected focused scope: **79 passed**.
- Final combined scope: **255 passed, 0 failures, 0 errors, 0 skips**, 38.31 seconds reported by pytest.
- Final scope: opt-in pipeline integration, existing pipeline gates, diagnostics, recursive receipt runtime, preflight, complexity/receipt contracts, inventory identity/synchronization and current-stock successor tests, formula state, concentration units.
- Ruff on all five scoped Python files: PASS.
- git diff --check: PASS. Existing line-ending warnings remain.
- All 42 file hashes from the inventory integration checkpoint still match. No staged changes.
- 6,898 pytest-asyncio deprecation warnings; no assertion failures.
- Full repository verifier, packaging, admission benchmark, external/scientific validation, and release acceptance: NOT RUN.

JUnit: D:/codex-preservation/perfume-chem-20260909/deep-plane-opt-in-final.xml.
Exact candidate hashes: deep_plane_opt_in_checkpoint_20260909.json.

## Scope and remaining boundaries

This completes the requested disabled-by-default local connection and selected cross-module verification. It does not enable the feature in saved production configuration, revise or compound a formula, admit the diagnostic to production, or integrate the remaining unrelated feature branches.

The earlier deep_plane_integration_checkpoint_20260909 report remains a historical checkpoint; this report supersedes its statement that caller wiring is unfinished. The opt-in connection is now present, while default activation and release admission remain withheld.

No commits, merges, pushes, permission changes, or credential actions were performed. Original checkouts and private snapshots remain in place.
