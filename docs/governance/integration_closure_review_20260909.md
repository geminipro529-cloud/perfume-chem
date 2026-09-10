# Integration closure review — 2026-09-09

Status: full verification completed with FAIL; subsequent bounded repairs verified separately; release HOLD. This report does not supersede a failing verifier with a success claim.

## Latest addendum: registry checkpoint completed — 2026-09-10

Both remaining supplemental failures are now repaired. An append-only, exact-base
overlay classifies the three formulation-intelligence modules as non-runtime
unvalidated candidates without altering frozen V1. The missing collaboration
registry was recovered byte-for-byte as historical evidence. A further census
hash mismatch was resolved by restoring exact pinned mixed-line-ending bytes,
not by changing source logic or repinning evidence.

Fresh combined verification: **1134 passed, zero failures**. The CLI census also
passes with 56 findings and no missing, drifted, unclassified, or multiply
classified artifacts. Details, hashes, and unsuccessful intermediate attempts are
recorded in `registry_integration_20260910.md`.

This completes the supplemental registry checkpoint only. The previous full-run
scientific/data/artifact blockers remain open; no full release acceptance or
production activation is inferred.

## Latest addendum: native receipt API repaired

The receipt-API blocker described in the historical sections below is now repaired
and verified; see `receipt_api_integration_20260909.md` for contract details and
exact source/test hashes. Gate reports retain their actual dose receipt, explicit
OAV binding verifies current inventory and replays the entire state/simulation,
and the pre-mix status compatibility alias preserves existing decisions. Default
diagnostic activation and preflight semantics are unchanged; strict OAV remains
ABSTAINED and release authority remains false.

The latest deduplicated supplemental/repair run completed with **1120 passed,
2 failed**. The two failures are the existing three unclassified module findings
and missing collaboration registry. The earlier missing native receipt API
failure no longer occurs. This is fresh bounded evidence, not a replacement
for the last failing full repository verifier. All other unresolved scientific
data and historical artifact issues below remain open.

## Repairs completed after the previous full comparison

- Artifact validator includes the parent-lineage field when present, preserving the exact shape of older manifests without that field. Failed persistence restores original bytes, including LF/CRLF.
- Three obsolete preflight test hooks now target the actual current-inventory reader; original rejection assertions remain intact.
- Material resolution reuses an explicitly resolved registry identity after a stock-label profile lookup misses. ODT lookup follows the same bounded identity fallback, including verification metadata. No numeric physical data were invented or edited.
- Four stock-label cases (Anisaldehyde 10%, Ethyl Maltol 1%, Helional 10% v/v, Hexyl Acetate 1%) now reuse existing identity data. Requested labels, separate stock rows, raw amounts, dilutions and unavailable active-mass authority remain preserved.
- Dated live-stock assertions were updated to existing user-confirmed authority: Alpha Irone 10% w/w DEP, Orris 9% w/w DEP, Black Agarwood 10% w/w DPG, Castoreum 10% DEP with unspecified fraction basis, and the corrected Hydroxycitronellal bottle identity. Historical July catalogue fixture expectations remain explicitly separate.

## Isolated environment repair

- The canonical knowledge database passed SQLite integrity checking. It was absent in the integration checkout, so an exact local copy was staged there. Source/copy SHA256: `5A779F9D6850345D72DE3C8265D4330C50DAC529968B38BC9B08720B5DA63FE1`. The source database is unchanged; the copy remains Git-ignored and is not a scientific provenance upgrade.
- The backend now uses its own Poetry Python 3.11 environment, installed from the existing lockfile with the development group. Neither Poetry dependency manifest nor lockfile was edited. Backend lint and mypy passed; the previous 142 type errors disappeared after installation.
- The root has a separate Python 3.11 `.venv`, leaving the canonical shared Python 3.14 environment untouched. Exact installed versions are recorded in `integration_verification_environment_20260909.json`. This is a local verifier environment, not installation of optional model-serving dependencies from root requirements.txt.
- The documented pure-Python protobuf fallback was tried on the old environment but failed before backend selection. The new isolated environment passes the eight tracing/reconstruction tests. Reference: https://github.com/protocolbuffers/protobuf/blob/main/python/README.md.
- An exploratory backend coverage run was interrupted before completion. It overlapped the quick verifier's API test and exposed their shared test-database collision. The API test then passed alone (1 passed, 8 deselected). That quick API failure is not accepted as an integration regression. The full verifier runs backend checks serially.
- Coverage tooling deleted five tracked coverage shard files as a side effect; those exact previously unchanged files were restored from HEAD. No source changes were discarded.

## Focused verification

- Final current-state repair/guard suite, including the expanded verifier tests and updated stock assertions: **198 passed** (`D:/codex-preservation/perfume-chem-20260909/closure-focused-final.xml`).
- Evidence, preflight, artifact and Deep Plane caller checkpoint: 82 passed before subsequent lookup repair.
- Lookup repair plus evidence, Deep Plane diagnostic/caller, preflight and Orris authority modules: **125 passed** (`D:/codex-preservation/perfume-chem-20260909/final-integration-focused.xml`).
- Complete updated material-additions module: **56 passed**.
- Tracing and reconstruction imports/tests in isolated root environment: **8 passed**.
- Database/property/Orris group: **105 passed, 1 failed**, exposing the missing Guaiacwood migration row (`environment-kb-stock-tests.xml` in the preservation directory).
- Data/knowledge shard recheck after adding its SQLAlchemy dependency: **244 passed, 4 failed, 4 errors** (`final-data-knowledge-recheck.xml` in the preservation directory).
- Scoped Ruff and `git diff --check` passed. Counts from overlapping runs are not added together.

## Evidence ceilings retained

The live OAV audit now reports **208 supported / 246 materials = 84.553%**, with **38 unknowns** and `release_authority: false`. The denominator is unchanged. The greater-than-85% assertion remains failing; it was not lowered. Remaining categories: 4 opaque preblends, 24 naturals missing composite evidence, 7 unresolved identities, and 3 other data gaps. An ODT-only alias for Aldehyde C-18 was deliberately not introduced: MW/VP gaps would remain and a zero modeled OAV could falsely improve coverage.

Historical formula artifacts, C0/D0 evidence bindings and inventory-panel pins remain unmodified. No historical record was repinned to label it current. Deep Plane remains disabled by default. No commit, merge, push, publication, production activation or physical compounding occurred.

The current August intake patch also contains 15 profiles whose `character` field is prose, although `MaterialProfile.character` requires numeric dimensions. This causes the expansion and chemical-life consumers to fail on mapping operations. The bounded review found no numeric replacements in their current profile/YAML/material-property records. Those values were not guessed or replaced by zeros. Any follow-on repair must preserve prose separately and explicitly represent unavailable character evidence; silently ignoring its contribution would distort aggregate scores.

The full run exposed 63 current test files omitted by the explicit engine shard manifest. A subsequent repair adds them to an explicit `integration-extensions` shard; all 17 verifier tests now pass, including exactly-once coverage of current root test files. That addition was checked locally and was not silently attributed to the earlier full run.

## Post-full transport and fixture repairs

- Recovered `incoming_review/Meaningful_Complexity_Audit_v2.md` from the canonical checkout only after its SHA256 matched the existing registry pin exactly (`07d84574365abb6a8e505fdcaf4e496ee1ac1d90f1397053d41f20b0a9394ff3`). It remains historical evidence, not runtime authority.
- Independently verified and normalized **27 files** using only CRLF-to-LF replacement, with each result matching an existing frozen receipt/sidecar pin. Added path-specific LF attributes. No pin values or semantic content changed. Exact allowlist and expected hashes: `frozen_transport_normalization_20260909.json`.
- Supplemental 63-file suite before normalization: **864 passed, 41 failed**. After normalization: **902 passed, 3 failed** (`supplemental-after-transport.xml` in the preservation directory). No collection errors remain in that supplemental run.
- Remaining supplemental failures: native complexity/OAV binding expects a dose receipt field on GateReport that the retained API does not expose; three formulation-intelligence modules lack census classification; an OpenAI cloud collaboration registry file is absent. The deeper OAV request/result contract also lacks the receipt-bound API expected by the newer consumer; a dummy field would not repair that integration.
- The backend's dated intervention test now excludes the user-corrected unowned alcohol instead of the owned aldehyde, including the unavailable-inventory request. Targeted API test: **1 passed**. Safety-authority rejection assertions were preserved. The other backend frozen-corpus failure remains: its mismatched theory/synergy files do not match expected pins after CRLF-to-LF replacement, so they were not normalized or repinned.

## Full result

The completed canonical full run is `output/verification/final-integration-full-20260909.json`: **11 groups passed, 8 failed, 2 optional Docker groups skipped**. Previous full comparison was 8 passed / 11 failed / 2 skipped. Group counts are not test counts.

Passing groups: engine compile/lint/types, backend lint/types, material-data validation, golden formula and API checks, package build, wheel smoke, and fixture lock.

Failed groups: historical formula artifacts, four engine shards, backend tests, scientific audit, and knowledge-rule validation. Backend completed **628 passed, 2 failed**, with no errors; one of those two dated-identity failures was subsequently corrected and passed on its targeted rerun. The full data/knowledge shard initially stopped on missing SQLAlchemy in the new root environment; its subsequent complete recheck is reported above and still fails on substantive assertions/type errors.

This full run precedes the final transport normalization, verifier-shard expansion, restored historical document, and targeted backend fixture correction. Those changes have their own fresh targeted evidence, not a claimed new all-green full run. The whole repository has not reached acceptance. Missing numerical character evidence, OAV/composite data, remaining receipt-API integration, and non-transport historical source mismatches remain unresolved. No scientific promotion or release approval is inferred from installation, checksum repair, or passing subsets.
