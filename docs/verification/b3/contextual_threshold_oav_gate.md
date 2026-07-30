# Build B3 Contextual Threshold and OAV Gate

Decision: **PASS**

Implementation authority: `3a61de2acd9a658ebba4600c29ffe22cff02b7cc`.

This gate covers Build B Phase B3 only. It does not compile rule packs (B4),
expand analytical or regulatory authority (B5-B6), implement claim
sufficiency (B7), backfill decision-value data (B8), connect API/UI consumers
(B9), or run the Build B release audit (B10).

## Implemented canonical contract

- Three append-only tables store a one-to-one contextual specialization of a
  B2 threshold observation, deterministic OAV assessments, and quarantined
  legacy threshold records.
- Threshold context preserves identity, grade, purity, stereochemistry,
  endpoint, route, medium, matrix and composition, basis, apparatus,
  temperature, humidity, population, training, sample size, psychophysical
  procedure and statistic, typed value, unit, uncertainty, source, locator,
  evidence class, and quality flags.
- Conversion is allowed only within an explicitly supported compatible unit
  convention. A solution threshold never becomes an air threshold by
  conversion alone.
- OAV is computed only when concentration and threshold are compatible across
  identity, basis, medium and matrix, endpoint, route, conditions, model
  applicability, authority, and unit convention.
- Every incompatible path is fail-closed with a stable ordered subset of:
  `MISSING_THRESHOLD`, `IDENTITY_SCOPE_MISMATCH`,
  `THRESHOLD_MEDIUM_MISMATCH`, `THRESHOLD_ENDPOINT_MISMATCH`,
  `THRESHOLD_ROUTE_MISMATCH`, `THRESHOLD_UNIT_INCOMPARABLE`,
  `THRESHOLD_MATRIX_UNSPECIFIED`, `THRESHOLD_AUTHORITY_TOO_LOW`,
  `CONCENTRATION_NOT_COMPARABLE`, and
  `MODEL_OUTSIDE_APPLICABILITY_DOMAIN`.
- A supplied threshold assertion must exist, and both its requested and
  applicability context IDs must equal the unique context attached to the
  selected threshold observation.
- Computed OAV is screening evidence only. It cannot authorize exact
  intensity, percentage contribution, pleasantness, similarity, family,
  longevity, sillage, skin performance, release, or deletion below OAV 1.
- The migration creates no observations, assertions, assessments, or legacy
  imports. The explicit adapter preserves the original legacy verification
  status and produces quarantine commands without promotion.

## Fresh verification

All commands ran non-interactively under supported Python 3.11.15 with ANSI
disabled, explicit timeouts, and separate stdout/stderr logs under
`docs/verification/b3/logs/`.

| Gate | Result | Stdout SHA-256 | Stderr SHA-256 |
|---|---:|---|---|
| B1+B2+B3+compatibility pytest | 100 passed in 92.39 s | `E9292AD4...B06E48` | empty-file SHA |
| Ruff, exact B3 paths | all checks passed | `AF352A86...D2D9AF` | empty-file SHA |
| Mypy, four B3 modules | no issues | `9A7B872E...C9400` | empty-file SHA |
| DeepLuna Fast assertion-context delta | PASS | `4C7EFB1E...AC8535` | empty-file SHA |

The exact commands, complete hashes, environment boundary, and path hashes are
in `contextual_threshold_oav_gate.json`.

The protected root `perfume_chem.db` remains zero bytes with SHA-256
`E3B0C442...B855`. `data/perfumery_kb.db` remains 2,084,864 bytes with
SHA-256 `5A779F9D...3FE1`; an immutable read-only SQLite connection reports
integrity `ok`.

## Independent review and DeepLuna boundary

The first bounded Fast-only audit
(`DS-46ee2ccab1c3fbd3829728c78360841f`) returned PASS. Sol did not accept that
packet as authority and independently found three defects: assertion context
IDs could disagree with the selected observation context, a supplied missing
assertion ID could silently degrade to a missing-threshold result, and model
metadata omitted four indexes created by the migration.

RED tests reproduced each defect. The implementation now rejects a missing
assertion, withholds authority for either context mismatch, and declares all
four indexes in both model metadata and the migration. The authoritative
100-test slice then passed. A second bounded Fast-only delta audit
(`DS-d21fe93a9d16d6b9fc523043cfac45c9`) passed the assertion-context fix;
Sol independently verified the index parity with executable schema tests.

DeepLuna remained Fast-only and advisory. No Luna fallback or Codex subagent
was used.

## B3 exit decision

The master gate requires that any context mismatch withhold OAV and that OAV
never unlock a stronger claim.

All ten mismatch codes are executable, deterministically ordered, and produce
no OAV. Full compatibility is required before computation. The persisted
assessment exposes a screening-only permitted-use surface and explicit
prohibited claims. Strict-science mode has no heuristic fallback, legacy
status is never upgraded, and the migration promotes zero legacy values.
Therefore B3 passes without claiming that any threshold value is scientifically
true or that any formula is release-ready.

## Protected state and recovery

- The A0 full recovery package remains preserved.
- The scratch preimplementation archive is
  `outputs/b3-preimplementation-recovery/b3-scratch-targets-20260730_230738.zip`
  in the Codex evidence workspace, SHA-256 `03D3992B...E5BE`.
- The canonical prepromotion archive is
  `outputs/b3-prepromotion-recovery/canonical-b3-targets-prepromotion-20260730_232612.zip`,
  SHA-256 `A06B61FB...29DC`.
- Both archives were extracted separately. Every present path matched its
  source hash, and the absent-path manifest matched.
- After the implementation commit, the pre-existing worktree still had 105
  tracked dirty paths, 585 untracked files, and zero staged entries. Only the
  exact 16 B3 implementation/spec paths were committed.
- Dirty legacy `engine/odor_thresholds.py`,
  `engine/pipeline/oav_intelligence.py`, `tests/test_oav_authority.py`, and
  `tests/test_oav_intelligence.py` were not modified by B3.

## Limitations and claim boundary

- B3 promotes no real literature threshold observation.
- The legacy adapter is explicit quarantine machinery, not an automatic
  Alembic backfill. Decision-value ingestion remains B8.
- No production API, UI, or legacy-engine consumer is connected until B9.
- The first DeepLuna PASS missed defects later found by Sol; provider evidence
  remains supplemental to canonical source, tests, database constraints, and
  reproducible artifacts.
- Scientific release remains **BLOCKED**.

B4 may begin under its own RED tests and exit gate.
