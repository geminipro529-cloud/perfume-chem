# Complex Perfumery V6 verifier reconciliation

Status: `VERIFIER_TIMEOUT_RESOLVED_DETERMINISTIC_QUARANTINED_ARTIFACT_HOLD`.

The prior recovered-scope receipt recorded a quick-verifier timeout. That timeout is no longer reproducible. With no pytest or Poetry owner process and no SQLite WAL/SHM sidecars, the previously named `golden_explicit_solvent` API case passed in isolation. The current quick project verifier then completed in 43.22 seconds with zero stderr and exactly one failed check: `formula-artifact-validation`.

## Exact blocker

Artifact verification reports 458 `NONE`, 13 `QUARANTINED`, 49 `UNBOUND_LEGACY`, and one `TAMPERED` artifact. The sole blocker is `formulas/Prada_LHomme_Architecture_Control_30mL_EdT.md`, whose persisted analysis has an `analysis_input_hash` integrity issue. The document is explicitly quarantined and has no release authority.

The reviewed canonical rebind command completed as a dry run and proposed a current v2 analysis binding. It was not applied. The D0 verifier binds the complete Markdown bytes at SHA-256 `151de70b2983a7902a67daf8ddd43e0692bfea4ee5f8c92e553c3174827e1d00`, and the governing D0 plan requires both Prada documents to remain byte-identical. Updating only the generated analysis would still change that full-file hash and invalidate D0.

## Acceptance boundary

- The timeout diagnosis is resolved; current formula logic did not cause the prior hang.
- The deterministic artifact hold remains and is not waived by quarantine.
- V6 remains the current collection state.
- Authorized recovered non-P6 native scopes remain applied and locally verified.
- Four optional exact identities and both P6 parent binaries remain unavailable.
- No formula, D0, inventory, stock, physical, package-code, migration, or authority state changed.
- Overall collection, implementation, package installation, and release remain incomplete.

Focused replay: 95 passed. Quick project verification: completed, one failed check. DeepLuna Chat used two bounded `DIRECT_PRO` lanes; Sol rejected the worker shortcut that did not match the current whole-file D0 hash contract.

