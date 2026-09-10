# Artifact binding repair — 2026-09-09

Status: focused repair verified; repository release remains HOLD. No merge, commit, publication, production activation, dependency installation, or historical artifact regeneration.

## Boundary and evidence

The previous full-verifier comparison identified an inherited mismatch in `scripts/formula_release_gate.py`: the writer includes `g15_parent_formula_definitions` in the analysis-input digest, while the validator excluded it. Local writer, validator, persistence, and regression contracts were reviewed before editing. This is a serialization/integrity repair, not a scientific-model change.

The v1 validator now includes the parent field exactly when the persisted manifest contains it. Earlier v1 manifests that predate that field retain their original digest shape. The validator does not try multiple hashes until one passes. Parent additions, alterations, and removal fail the existing inner digest even if the outer manifest digest is recomputed. These hashes detect inconsistent content; they are not signatures or independent proof of ancestry.

Regression testing also exposed a rollback defect: failed persistence converted CRLF input to LF. Rollback now restores the captured original bytes using a binary temporary file and the existing atomic replacement path. Valid writes retain the existing renderer behavior.

## Verification

- Before repair, the nine new parent-binding cases produced 7 failures and 2 passes, exposing both digest mismatch and rollback byte drift.
- After repair, final focused artifact/rollback/CLI selection: **18 passed, 31 deselected**. Both LF and CRLF rollback cases are covered. XML: `D:/codex-preservation/perfume-chem-20260909/artifact-repair-final.xml`.
- Separate complete pre-mix guard and artifact-rebind modules: **11 passed**.
- Broader evidence-contract, artifact-rebind, and Deep Plane caller run: **61 passed, 3 failed**. All three failures are the previously recorded obsolete monkeypatch target `engine.pipeline.preflight.parse_inventory`, not artifact digest failures. XML: `D:/codex-preservation/perfume-chem-20260909/artifact-repair-focused.xml`. This run preceded expansion of the existing rollback test to explicit LF/CRLF parameters; the final focused run covers that expansion.
- Ruff on both changed Python files: passed. Scoped `git diff --check`: passed (Git emits line-ending conversion warnings).

No full verifier rerun was performed for this bounded checkpoint. The previous full result remains FAIL and is not upgraded by these focused passes. Earlier implementation manifests remain historical evidence; this repair changes the pipeline-source fingerprint, so prior generated analyses must not be presented as fresh evidence for the repaired code.

## Remaining work

Repair the obsolete preflight test fixtures at the authoritative stock-contract seam, preserving their intended rejection behavior. Resolve isolated test-environment prerequisites, review dated stock assertions and unresolved OAV coverage, then rerun affected checks and the full verifier before any release decision. Do not weaken scientific holds or repin old formula artifacts to force a pass.
