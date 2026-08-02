# Build C3 model-interface gate

Status: **PENDING**. The fresh local executable gate and final DeepLuna audit are
green, but the evidence commit, exact-commit replay, and postcommit decision have
not yet occurred. C4 remains closed.

## What C3 establishes

C3 publishes 22 typed `engine.physics` model-interface symbols, including six
closed operations, nine representable model families, five applicability states,
immutable release/request/result envelopes, one exact-selector router, and one
unranked model-comparison envelope. The complete `engine.physics` export surface
contains 62 unique names.

The four authoritative behaviors are locally proven:

- model selection is explicit by exact family and version;
- an unknown or duplicate selector cannot silently fall back;
- results bind the exact immutable release snapshot and reject release drift;
- `OUTSIDE_APPLICABILITY_DOMAIN`, `INSUFFICIENT_INPUT`, and
  `MODEL_NOT_VALIDATED` abstain before computation and cannot feed OAV screening.

## Fresh executable evidence

The non-PTY matrix ran with ANSI disabled, explicit timeouts, and separate UTF-8
stdout/stderr. All 22 jobs passed, none timed out, and every captured stderr file
was empty.

| Gate | Result |
| --- | ---: |
| C3 focused | 105 passed |
| C2 compatibility | 79 passed |
| C1 compatibility | 96 passed |
| C0 compatibility | 24 passed |
| Complete root suite | 1,402 passed |
| Dependency invariant | 1 passed |
| Ruff check / format | PASS / PASS |
| basedpyright | 0 errors, 0 warnings, 0 notes |
| mypy | no issues |

The duplicate-selector mutation produced the required four failures and returned
to four passes after restoration. Removing the outside-domain compute guard
produced the required one failure (with two unaffected cases passing) and
returned to three passes after restoration. The implementation source hash was
restored to
`d29ec7b6defba2f66160fbf707b17412e61220a216f2baa529ff55ad949797d5`.

The log manifest covers 61 files and reports valid UTF-8, zero ANSI escape bytes,
and zero credential-shaped matches. It records only match counts, never matched
values.

## Recovery, protected state, and scope

The path-preserving recovery archive is restorable and reverified at
118,286,848 bytes with SHA-256
`fd4e38ff22b9a611fe46b61454f8705eb4b989615c7780a526bf2b813ef3196e`.
All 429 preserved dirty/untracked paths still match; unsafe members, duplicates,
archive mismatches, and current-work mismatches are all zero.

Both protected databases match the C2 baseline before and after verification and
return read-only SQLite `quick_check=ok`. The C3 implementation diff contains
exactly seven approved paths. It contains no migration, database, scientific
artifact, production caller, compatibility-model, or legacy-implementation path.

## DeepLuna status

Three supplemental exact-project DeepLuna Fast reads and the mandatory final
audit are settled `PASS` with one DeepSeek V4 Flash call each, `NO_LUNA`, no
fallback, zero open or unknown reservations, zero Luna/GLM runs, and Codex
orchestration disabled. The final audit reported no negative finding. Its compact
packet truncated part of one positive finding, so Sol accepted nothing from the
packet alone and reproduced every gate claim from the canonical files and local
executable evidence. Provider output is never final authority.

## Explicit limitations

C3 implements contracts and router enforcement only. It does **not** implement
Raoult, Henry, UNIFAC, COSMO-RS, partition, dynamic release, calibration, or any
other scientific equation. It does not validate predictions, promote a model
family, change a production caller, add persistence, complete Build C, or
authorize scientific release.

The machine-readable source of this status is `model_interface_gate.json`. Until
the evidence commit, exact-commit replay, and Sol decision are green, `c4_open`
remains `false`.
