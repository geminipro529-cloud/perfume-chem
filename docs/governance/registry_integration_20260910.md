# Registry integration checkpoint — 2026-09-10

Status: bounded registry/integration verification PASS. Whole-repository release
remains HOLD; this checkpoint does not supersede the earlier full verifier.

## Changes and authority boundary

The frozen V1 registry is unchanged at SHA256
`7567f3ca00ccbf3e1b2b41f50645ed21f4d163612872b8449db6cc022818c639`.

An explicit append-only overlay,
`configs/complexity/complexity_module_registry_integration_20260910.json`, binds
that exact base and classifies three already-existing modules:

- `engine/formulation_intelligence/admission.py`
- `engine/formulation_intelligence/hedonic_platform.py`
- `engine/formulation_intelligence/temporal_architecture.py`

All three remain `FUTURE_CANDIDATE_NOT_VALIDATED`, with null import paths and no
runtime eligibility. The overlay cannot override existing rows, discovery,
dismissal rules, hashes, or runtime states. It accepts only non-runtime additions
and reuses the original closed-schema, duplicate-ID/path, and filesystem
containment validation. Drift in the base or candidate bytes remains blocking.

The current census uses this overlay. Historical benchmark candidate evaluation
continues to reference frozen V1; no benchmark results or admission receipts were
rewritten. Overlay SHA256:
`08ecf52c3cb35330fd287f8a84407b49e1d9577850b9ca8a5dd1f08948eb17b0`.

## Exact historical recovery

Restored `data/governance/openai_cloud_compute_collaboration_registry_20260901.json`
from canonical committed revision `e7002d4dacde0ae4c6b92db454fa4034c830e8f4`.
The canonical file's raw Git object matched the committed blob
`a18333ad1bb343fe8a593ce3fa72aec8f10917f0` before recovery, and the integration copy
matches SHA256 `9c9b12e123bf70f9b40b2ca95d2e869756119233a742284cc09236a09311b78d`.
Its test now explicitly describes a byte-bound September 1 historical registration,
not live workers. No task was contacted, activated, or granted authority. Existing
no-push/no-merge and evidence/physical/release ceilings remain unchanged.

The census additionally exposed a frozen optimizer transport mismatch. Neither
uniform LF nor uniform CRLF matched the frozen pin, but the canonical checkout's
mixed-line-ending bytes did. Before repair, normalizing both source and destination
to LF produced exactly identical text. Restored only the exact transport bytes in
`future_modules/family_hedonic_optimizer.py`, preserving SHA256
`8c3de4caedd2dc184d1c2c4573e8721647579aa317b93b074fd2fdad41c6547f`.
No code, numerical values, or evidence pins changed. A path-specific `-text`
attribute prevents future Git normalization of this frozen legacy file.

## Fresh verification

- Focused registry/routing suite: **35 passed**.
- Final deduplicated supplemental plus integration repair suite: **1134 passed**,
  74.87 seconds. JUnit:
  `D:/codex-preservation/perfume-chem-20260909/registry-integration-final-20260910.xml`.
- Current CLI census: **PASS**, 56 findings, zero provider calls, no blockers,
  hash drift, missing files, unclassified entries, or multiple classifications.
  Command: `.venv/Scripts/python.exe scripts/pipeline_audit.py complexity-benchmark --operation census --run-dir output/complexity_xhigh_benchmark/integration-20260910 --json`.
- Scoped Ruff and registry mypy passed. Scoped source/test diff checks passed.
  The exact mixed-EOL legacy file triggers ordinary Git whitespace warnings;
  its `git diff --ignore-space-at-eol --exit-code` check passed and its frozen
  checksum takes precedence over cosmetic normalization.
- An earlier overlapping run reported 1132 passes and two failures: the then-open
  optimizer hash mismatch and an artifact freshness assertion while transport
  bytes were being repaired. That run is retained as an unsuccessful intermediate
  attempt, not acceptance evidence. The final 1134-test run had no concurrent edits.

No new pipeline scripts, external-provider calls, original-checkout writes,
commits, merges, pushes, publications, or production activation occurred.
Diagnostics remain disabled by default. Scientific data gaps and other historical
artifact issues from the last full verifier remain unresolved; the full verifier
was not rerun for this bounded checkpoint.
