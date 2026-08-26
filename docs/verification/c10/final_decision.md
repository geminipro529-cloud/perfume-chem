# Build C10 final decision

Decision: **PASS WITH HISTORICAL REGRESSION WITHHELD AND INHERITED CLEAN-BASELINE LIMITATION**

- Source commit: `19b993a11d96172faa2b338e0f2e5d74da5fa8f8`
- Evidence commit: `8882f9fd5e8f9040983cf36b8df2eee8343bc311`
- Canonical manifest commit: `90d5895194ae66bf3c8b477624c8c9a7db852a20`
- Detached replay: 64 C10 tests passed; canonical blob/archive/log validator PASS; empty stderr; clean worktree
- Authoritative preserved overlay: 1,753 tests passed in 109.27 seconds; empty stderr; worktree status unchanged
- Mutation gate: 7/7 mutations detected and all source bytes restored
- Historical regression: **BLOCKED / NONCANONICAL** because no complete replay bundle was found
- DeepLuna Fast evidence audit: PASS/POSITIVE; no Luna, GLM, or Codex-worker fallback

The C10 exit gate passes for constrained experiment selection and human-gated proposal authorization. It does not authorize a real experiment, production formulation, scientific or sensory outcome claim, database migration, or Build D.

C11 is authorized. Build D remains closed.
