# Build C10 experiment-selection gate

Decision: **PENDING EXACT EVIDENCE-COMMIT REPLAY**

- Source commit: `19b993a11d96172faa2b338e0f2e5d74da5fa8f8`
- C10 focused tests: 64 passed
- C10 plus project-verifier tests: 81 passed
- Legacy optimizer/planner compatibility: 47 passed
- Authoritative preserved-overlay root suite: 1753 passed
- Mutation evidence: 7/7 authority mutations detected; all source bytes restored
- Matrix: 41/41 jobs passed; 0 timeouts; 0 stderr bytes
- Archive: PASS, restorable and path-preserving; 429 inherited dirty/untracked paths preserved
- Databases: immutable quick checks `ok`; before/after hashes identical
- DeepLuna Fast audit: PASS/POSITIVE; Sol independently reproduced the findings

## Authority decision

C10 supports constrained candidate generation, hard-gate filtering, explicit uncertainty-aware Pareto/acquisition selection, mandatory controls and exact replicates, preregistered stop conditions, and exact-hash human authorization. It does not authorize an experiment by itself and does not permit legacy or unsupported numeric authority.

## Withheld historical claim

The reported La Nuit search numbers (about 30,000 candidates, 35 guardrails, DNA threshold 97.5, reported winner about 97.76) remain **noncanonical**. The bounded search inspected 6430 repository/handoff files and found no complete replay implementation/input/result bundle. C11 cannot claim an independent historical replay unless that exact bundle is supplied.

## Exact replay limitation

The detached source commit passes all 64 C10 tests. Its root checkout reproduces the same nine collection errors and four baseline assertion failures at the pre-C10 parent because tracked tests depend on a pre-existing user overlay absent from the clean tree. Therefore, no standalone clean-tree full-green claim is made; the authoritative state is the exact commit plus the verified, archive-preserved overlay, where all 1753 tests pass.

The next action is to commit this evidence and replay that exact evidence commit. C11 remains closed until that replay succeeds.
