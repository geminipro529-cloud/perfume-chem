# Build B scientific-data authority report

Build B status: PASS

Scientific release authority: NOT GRANTED

This Build B report is read-only, non-promoting verification evidence. It does not authorize scientific release, legal compliance, safety certification, or real-world performance claims.

## Authority and checkpoints

The authoritative baseline is commit
`59637597706569360220e0354716ceeb4e4837ca`. The final runtime
implementation is
`428684fa987b673856fd533e2dba617cf0705e6e`, the final pre-B10 gate is
`a9c5e733c5ae74f78e37788afab82d63fe868416`, and the B10 report-input
commit is `d34af7289be2944d9c0a884089359dd62b53da4b`. The report commit
cannot contain its own commit ID without circular mutation; the handoff
records the final evidence-package commit.

Evidence remains separated as `MEASURED`, `LITERATURE_DERIVED`,
`SUPPLIER_PROVIDED`, `EMPIRICALLY_CALIBRATED`, `MODEL_ESTIMATED`,
`HEURISTIC`, `SPECULATIVE`, and `UNKNOWN`. No aggregate numeric
confidence is emitted.

## Source and observation inventory

The sealed B0 artifact contains 1,043 source digests, 1,262 material rows,
23,869 property observations, 300 code constants, 3,381 knowledge rules,
and 226 property conflict sets. Its compressed artifact is 1,506,865
bytes with SHA-256
`3f287b86c29e645d879e3b2af59ddcf53d059c11509ecf85576a7c126f9daebc`;
the 26,221,111-byte decompressed content has SHA-256
`1eb930343b33db9a60395567fa97748c428b416d46447beca9991448b4f7b779`.
The inventory contains no forbidden or generated path.

The current working tree has 1,263 material rows. The one-row delta is
`Magnolia EO`, recorded only as an observed inventory label. Species, plant
part, supplier, stock strength, amount, composition, and exact chemical
identity remain unknown. It is not promoted into the canonical knowledge DB
and remains in `naturals_missing_composite_evidence`. Current inventory
counts are 234 raw entries, 218 normalized identities, 213 fragrance
identities, and 210 available fragrance identities.

Legacy authority labels are: 20,949 `UNKNOWN`, 1,987
`UNATTRIBUTED_LEGACY`, 505 `LEGACY_HEURISTIC`, 311 `LEGACY_TRACEABLE`,
69 `LOCAL_RECORD`, 39 `LITERATURE_DERIVED`, and 9
`SUPPLIER_PROVIDED`. These are frozen legacy inventory counts, not
canonical migrated authority.

B1 defines 18 source types, 10 workflow states, four source/provenance
tables, immutable digests, exact locators, independence groups, and
derivation links. B2 defines typed observations, explicit identity scopes,
conflict sets, candidate selection, uncertainty, and fail-closed authority.

## Migration and production state

B1 through B8 created 40 append-only canonical table definitions across
migration heads `20260730_0005` through `20260731_0012`. B9 adds no
migration. Every phase migrated or backfilled zero real rows. The
no protected production database was migrated or backfilled. The existing
12,288-byte `perfume_chem.db` remained byte-identical through B10 and passes
immutable `PRAGMA quick_check`; its presence is not evidence that Build B
canonical tables were populated.

## Conflicts and selection

The frozen inventory has 226 property conflict sets. The legacy rule corpus
has 137 invalid exact records, 68 duplicates, one directed-cycle
diagnostic, zero blocking records, and zero numerical models. Unresolved
blocking property conflicts withhold authority; values are not averaged.
Selected assertions require an explicit candidate set, exact matching
scope, visible policy, uncertainty, and lineage.

## Contextual ODT and OAV authority

Legacy material data include 92 non-null air thresholds and 81 non-null
ethanol thresholds; the legacy code paths contain 301 ODT entries and 276
verification entries. Build B promoted zero of them. B3 requires exact
identity, grade, purity, stereochemistry, endpoint, route, medium, matrix,
basis, and conditions. Ten stable mismatch classes withhold OAV. A solution
threshold cannot become an air threshold through unit conversion alone,
strict mode has no heuristic fallback, and a compatible OAV is
screening-only.

## Knowledge rules

All 3,381 legacy rules remain quarantined unless explicitly compiled from
accepted sources and valid exact identities or explicit groups. Generic and
unresolved endpoints cannot block or become numerical. Numerical models
require controlled matching evidence. The 454-label identity-resolution
snapshot is a regression fixture, not canonical identity authority.

## Analytical validation matrix

| Control | Result | Authority boundary |
| --- | --- | --- |
| Method authority | PASS | Versioned, source-bound, digest-bound, exact scope |
| Method validation | PASS | Claim-specific criteria, uncertainty, review, matrix, analyte, and method |
| Calibration | PASS | Exact analyte, matrix, method, applicability, and validation |
| Sequence and run | PASS | Atomic order and exact primary subject |
| Raw-file attachment | PASS | Content digest and exact run binding |
| Peak identity | PASS | Six closed states; library match alone cannot promote |
| GC-O | PASS | Alignment and training preserved; no exact chemical identity |
| Quality control | PASS | Blocking QC withholds; qualifying QC caps at advisory |
| Claim assessment | PASS | Exact applicability and canonical evidence required |

## Regulatory snapshots

The B6 record is dated 2026-07-31 and preserves
`PASS_FOR_DECLARED_SCOPE`, `FAIL`, `UNKNOWN`, and `NOT_EVALUATED`. It
records the IFRA 52nd Amendment as consultation material rather than an
enforced standard and applies dated EU allergen transition logic for the
recorded evaluation date. Natural composition must be complete and
lot-specific or an explicit documented proxy; partial or unknown
composition cannot pass. Future evaluation dates require source refresh.
This is scoped screening, not legal certification.

## Runtime call graph

Before Build B:

```text
legacy constants/YAML/JSON/SQLite
  -> direct engine consumers
  -> calculations/recommendations/safety helpers
  -> output claims
```

After Build B:

```text
B1 source document/extraction/workflow
  -> B2 typed observation/conflict/selected assertion
  -> B3 contextual threshold/screening OAV
  -> B4 compiled rule
  -> B5 validated method/run/QC/uncertainty/claim assessment
  -> B6 dated regulatory snapshot/finding
  -> B7 claim-specific authority decision
  -> B8 non-promoting gap priority
  -> B9 read-only strict/exploratory JSON, Markdown, and UI
```

Legacy data enter the new path only through an explicit adapter and retain
a heuristic, speculative, unknown, or otherwise non-promoting label until
their named authority gates pass.

## Current verifier evidence

The exact 20-file B10 matrix passed 274 tests in 425.11 seconds with exit
zero and no timeout. It covers:

1. source ingestion and digest verification;
2. exact locator preservation;
3. duplicate and independence grouping;
4. observation round trips;
5. selected-assertion conflict handling;
6. unit conversion and incompatibility;
7. contextual ODT matching;
8. strict science mode;
9. OAV claim boundaries;
10. rule compilation and invalid-reference prevention;
11. analytical method validation;
12. calibration/QC/uncertainty;
13. GC-O alignment;
14. raw-file attachment and digest;
15. regulatory dates and snapshot versioning;
16. natural contribution aggregation;
17. negative authority promotion cases;
18. API and report provenance; and
19. export/import/backup/restore.

The current canonical non-Docker project verifier reports
`PASS_WITH_SKIPS`: 19 mandatory checks passed, none failed, and only the
optional Docker build and smoke checks were skipped. The final run passed
191 truth-core tests, 236 data/knowledge tests, 602 gate/family tests, 69
legacy tests, and 630 backend tests in an 840.593-second captured run. Two
earlier complete attempts are retained as RED evidence: one exposed stale
inventory/knowledge expectations; the next exposed the Magnolia quarantine
snapshot plus a 900-second backend-wrapper timeout after all backend tests
had passed. The final run used the tested 1,200-second backend contract. All
four protected files remained byte-identical.

The post-full package verifier passed 22 checks across 153 files, parsed 63
JSON documents, verified all four recovery archives, and found zero JSON
parse failures, ANSI files, or sensitive-value shapes.

## Protected state and recovery

The restored `data/perfumery_kb.db` is 2,084,864 bytes with SHA-256
`5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`
and immutable `PRAGMA quick_check` result `ok`. Its zero-byte WAL and
32,768-byte SHM sidecars are byte-identical. `perfume_chem.db` is 12,288
bytes with SHA-256
`02b64be88e4a8881c968ec9ef7f0185ed7b1bcedc6ed33885f07d7de70a0da5e`
and immutable `quick_check` result `ok`.

Four path-preserving ZIP archives were extraction-verified with zero unsafe
members:

- `b10-evidence-before-refresh.zip`, 59,811 bytes, SHA-256
  `2dcfeed4be62846fcfbba8440f76b57820bb8da5b511cec008faf810e4c23920`;
- `b10-verifier-outputs-before-run.zip`, 17,489,486 bytes, SHA-256
  `cbb2df5a08450dbdb1216863e751a683ddeafdd8debad5132249ecfce01d43bc`;
- `b10-inventory-kb-before-repair.zip`, 331,178 bytes, SHA-256
  `c9a7294dd5507afbc9a5f90f4ec17e1ca020c622e5da7bc18e4701b5fc7a56d6`;
- `b10-verifier-defects-before-repair.zip`, 15,775 bytes, SHA-256
  `64efb1452c2e73a0363730dc70643aebbd26965c7614bf6b6458d75bdb4ae90f`.

## Defects closed during B10

The verifier shard manifest omitted two new top-level tests; both are now
assigned and the manifest regression passes. Two verifier runs also exposed
that interaction-graph tests wrote six synthetic rows into the protected
knowledge DB and removed its sidecars. The mutated state was archived, the
exact prior files were restored, import-time seeding was removed, reads use
immutable connections, and all mutation tests now use isolated copies with
a live-database hash invariant. Additional live query paths in the material,
rule, property-validation, and science-KB APIs were converted to explicit
immutable read-only connections; science-KB population stays explicitly
writable and its tests now target a temporary database. All four engine
shards preserve the main DB and both sidecars independently.

The historical B10 report and helper were rejected as current authority
because they described an obsolete B0 artifact and obsolete gate schemas.
The current helper separates the sealed 1,262-row B0 baseline from the
1,263-row live source tree.

The live inventory added Bergamot FCF oil Sicilian and Magnolia EO after
fixed-count snapshots were written. Bergamot resolves through an existing
exact alias. Magnolia was not aliased to the unrelated synthetic Magnolan;
it was added as an identity-unknown source observation and the explicit
quarantine snapshots were refreshed.

Two complete disposable KB builds were byte-identical at SHA-256
`13c9ab5a3e696ce19d5a2474d7bec2f0a81a4173c9185fbbdefec938a86696a3`
and preserved Magnolia's unknown fields. Their logical diff against the
protected KB changed 86 common material rows and multiple whole-table
populations, so canonical replacement was withheld. The backend timeout was
then raised from 900 to 1,200 seconds under a RED/GREEN verifier-contract
test; the selected backend check and final full verifier both passed.

## Build B completion

All ten completion criteria are satisfied:

1. runtime values are traceable or explicitly labeled;
2. selected values expose policy and uncertainty;
3. ODTs are contextual;
4. OAV mismatches fail closed;
5. advisory rules cannot become hidden numerical truth;
6. analytical claims require method validation and QC;
7. regulatory screens are dated, scoped, current for their recorded date, and preserve unknowns;
8. heuristic data remain visibly separate;
9. full non-Docker verification passes (1,098 engine and 630 backend tests); and
10. no scientific-release claim is made.

## Exact claim wording

- `ALLOW_EXACT`: The claim may be stated exactly for the recorded identity and condition scope only.
- `ALLOW_SCOPED`: The claim may be stated only with the recorded scope and qualifications.
- `ADVISORY_ONLY`: The observation may be described as preliminary advisory evidence.
- `WITHHOLD_UNKNOWN`: No affirmative scientific claim is permitted while critical requirements remain unknown.
- `BLOCK`: No affirmative scientific claim is permitted because a blocking condition is present.

Forbidden wording: `release-grade`, `certified`, `universally safe`, and
`unscoped equivalence`.

## Remaining unknowns

- No Build B migration promoted a real literature observation, threshold,
  analytical record, regulatory record, or knowledge rule.
- Magnolia EO remains an observed label with unknown botanical, supplier,
  strength, amount, composition, and exact-identity dimensions.
- The protected knowledge DB was not rebuilt from current sources because
  the disposable candidate contained broad unrelated logical drift.
- Most frozen legacy observations remain unknown, unattributed, or
  heuristic.
- Legacy ODT values remain non-contextual until explicitly adapted through
  B1-B3.
- Quarantined invalid, duplicate, and cyclic legacy rules remain.
- Regulatory sources require refresh for later evaluation dates.
- Held-out sensory validation, real-world performance validation, legal
  approval, safety certification, and scientific release evidence do not
  exist.
- Optional Docker checks were not executed by this non-Docker gate.

## Independent read-only audit

DeepLuna Fast job `DS-204c549decc18c3c19787a9bc69b4592` returned `PASS`
after inspecting the current B10 report and bounded evidence allowlist. The
exact-project preflight was `READY`; the audit used one DeepInfra Priority
`DeepSeek-V4-Flash` provider call (87,754 prompt tokens and 923 completion
tokens), with zero Luna calls, zero Codex orchestration, no fallback, and no
scope deviation. It reported no negative findings. Sol independently
reconciled every material claim against the local receipts; the provider
remains supplemental and has no final acceptance authority.

Post-seal Fast job `DS-b5b28b7a2921c6132dda946a78a84f1d` independently
matched the stable 191/236/602/69 engine counts, 630 backend tests,
840.593-second wrapper duration, final report digest, protected hashes, and
post-full package result. It used one FLASH call, zero Luna calls, no
fallback, and reported no negative findings. Sol retained final authority.
