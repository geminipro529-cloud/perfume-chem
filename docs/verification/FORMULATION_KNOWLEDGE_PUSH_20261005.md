# Reviewed formulation knowledge — push verification, 5 October 2026

This is a development-code publication record, not merge, sensory, safety or
formula-release acceptance. The earlier knowledge-integration report retains
its original first-run failures; this record describes their scoped follow-up.

## Scope and preservation

The commit includes the reviewed knowledge pack and offline retrieval, required
Formula Studio/request/reference/UI/job dependencies, the already user-confirmed
AIMI identity correction and its stock records, focused tests and artifact review.
Local provider configuration, filesystem-tunnel work, runtime ledgers, databases,
scratch deletions and unrelated formula drafts are not staged.

The 128 indexed research files and two additional local source bindings were
checked against the staged Git blobs, not only the dirty working directory.
All 130 matched their SHA-256 references. Git attributes preserve exact research
bytes across platforms; archival Markdown formatting is retained, not rewritten.
All required implementation/reference paths for FORMULA_DESIGN, FORMULA_ANALYSIS
and REFERENCE_PANEL_EVALUATION exist in the candidate index.

## Artifact repair

The Prada Architecture Control input hash matches the six-field pre-G15 v1
algorithm in recorded commit `90d5895194ae66bf3c8b477624c8c9a7db852a20`.
The validator now includes the parent field only when that field exists in the
stored manifest. Current artifacts retain their parent binding. Tests reject
removed-parent/current-hash and present-parent/legacy-hash mismatches, and retain
content-tampering checks; no stored manifest or analysis hash was rewritten.

Thirty-seven stale analyses received an explicit historical quarantine notice.
Prada's existing quarantine remains. All 38 documents retain their original
analysis text. Removing only the new review metadata reproduces every original
formula-definition hash, proving the original quantities, stock declarations
and prose were preserved. No formula analysis was rerun or promoted.
Exact review hashes and statuses are in `FORMULA_ARTIFACT_REVIEW_20261005.json`.

## Verification

- Focused engine, knowledge, request, inventory and artifact suites: **176 passed**.
- Focused backend job, UI, reference and disposable migration suites: **42 passed**.
- Backend Ruff, changed job-service mypy and JavaScript syntax checks passed.
- Artifact-validator/test/knowledge-module Ruff passed.
- The quick project verifier passed all ten selected checks, including artifact
  validation and the unchanged golden lock. Overall completion remains
  `NOT_EVALUATED` because this is a partial, not full release-level run.
- Staged whitespace checks passed; archival research uses its declared
  byte-preserving formatting policy.

Whole-backend mypy's previously reported seven errors in the untouched llama.cpp
service remain outside this repair. A direct mypy run of the release CLI also
reported three errors in unchanged persistence/telemetry sites; the canonical
58-file truth-core type check passed. No full verifier, Docker release acceptance,
new empirical model training, physical compounding or safety approval is claimed.

Every scientific/action authority boundary and existing evidence hold remains
in effect. A successful Git push does not change those boundaries.
