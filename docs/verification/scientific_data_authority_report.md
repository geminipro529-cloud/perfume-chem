# Build B scientific-data authority report

Build B status: PASS

Scientific release authority: NOT GRANTED

This Build B report is read-only, non-promoting verification evidence. It does not authorize scientific release, legal compliance, safety certification, or real-world performance claims.

## Authority and checkpoints

The authoritative baseline is commit
`9a8f11db77b40bb37a1f02bbc4cf440fae93e711`. The final runtime
implementation is
`596a90eaa4b7a6492137d15a77d7f006e16f6035`, the final pre-B10 gate is
`1a27b480b3946e94b984d26d689ac3ff22c25302`, and the B10 report-input
commit is `2ababd37aa0a6e9a38c0666cfc98066c9f6b6b12`. The report commit
cannot contain its own commit ID without circular mutation; the handoff
records the final evidence-package commit.

Evidence remains separated as `MEASURED`, `LITERATURE_DERIVED`,
`SUPPLIER_PROVIDED`, `EMPIRICALLY_CALIBRATED`, `MODEL_ESTIMATED`,
`HEURISTIC`, `SPECULATIVE`, and `UNKNOWN`. No aggregate numeric
confidence is emitted.

## Source and observation inventory

The frozen B0 artifact contains 997 source digests, 1,262 material rows,
23,869 property observations, 238 code constants, 3,381 knowledge rules,
and 226 property conflict sets. Its compressed artifact is 1,499,508
bytes with SHA-256
`fdfe1de2f51ecf2ae03014c27a3c13c594c2dbf1020dba9a31bffed487d08ca8`;
the 26,142,842-byte decompressed content has SHA-256
`955269451e42c9f8452624ae0c0fc4245591eba54fa0a00f7b805ad6e08707f2`.
The inventory contains no forbidden or generated path.

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
production `perfume_chem.db` remains an unchanged zero-byte file and no
production database was migrated or populated.

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

The exact 20-file B10 matrix passed 274 tests in 331.27 seconds with exit
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

The canonical non-Docker project verifier reports `PASS_WITH_SKIPS`: 19
mandatory checks passed, none failed, and only the optional Docker build
and smoke checks were skipped. The post-isolation seal run passed 189
truth-core tests, 235 data/knowledge tests, 580 gate/family tests, 69 legacy
tests, and 629 backend tests in a 787.08-second captured run. The knowledge
DB main file, WAL, and SHM remained byte-identical through that complete
run.

## Protected state and recovery

The restored `data/perfumery_kb.db` is 2,084,864 bytes with SHA-256
`5a779f9d6850345d72de3c8265d4330c50dac529968b38bc9b08720b5da63fe1`
and immutable `PRAGMA quick_check` result `ok`. Its original zero-byte WAL
and 32,768-byte SHM sidecars are also byte-identical. `perfume_chem.db`
remains zero bytes with the empty-file SHA-256.

The path-preserving workspace archive is
`D:\.backups\perfume-chem\build-b10-prewrite-20260731T103332+0700.tar`
with SHA-256
`8b52d5545bca4039dcbc1704a5e33d0cf593c2836e55db10aa90d8d272f81675`.
Its declared runtime exclusions are covered by the separately
extraction-verified protected-database archive
`D:\.backups\perfume-chem\build-b10-prewrite-protected-databases-supplement-20260731T113100+0700.tar`
with SHA-256
`42b2f1dc31ce6e5afec89bc395c94221bd5959abaff09186c21f1117dba233d6`.

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
shards preserve the main DB and both sidecars independently. Finally, an
inventory helper initially counted unique subjects rather than canonical
YAML rows; correcting the verifier semantics reconciled all B0 counts
without changing inventory data.

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
9. full non-Docker verification passes; and
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

DeepLuna Fast job `DS-547b23606efdb8742eefde8f5e19211a` returned `PASS`
after inspecting the 25-file B10 evidence allowlist. The exact-project
preflight was `READY`; the audit used one DeepInfra Priority
`DeepSeek-V4-Flash` provider call (53,196 prompt tokens and 693 completion
tokens), with zero Luna calls, zero Codex orchestration, and no scope
deviation. Its three concrete findings matched the inventory verifier,
protected-database state verifier, and canonical full-seal verifier. Sol
independently reconciled those findings against the captured local evidence;
the provider remains supplemental and has no final acceptance authority.
