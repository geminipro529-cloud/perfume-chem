# Dirty-worktree consolidation accounting — 2026-09-10

## Objective and authority

Consolidate useful changes from the 19 preserved source checkouts into this one
integration worktree. Preservation is complete for the documented capture scope;
consolidation is NOT complete. A passing focused integration suite does not prove
coverage of all source worktrees. Original checkouts remain untouched. No release,
publication, production activation, or bulk merge is authorized by this report.

Integration base: `45cd79cd01b6ac30c8acc5f2875bc272e1f3e488`.
Private capture and machine-readable accounting:
`D:/codex-preservation/perfume-chem-20260909/worktree-byte-accounting-20260910.json`.
Do not publish private archives or their contents. Byte classification is not
semantic acceptance. Unchanged tracked source files require Git-history comparison
in addition to the dirty-file manifests.

## Verified byte-accounting scope

All 19 source HEADs matched preserved HEADs during this review; dirty source bytes
are not frozen and must be checked again before import. There are 13 distinct heads.
The comparison covers 9,997 preserved file entries, including duplicates:

| Mechanical class | Entries |
|---|---:|
| Exact bytes present at the same integration path | 19 |
| Different bytes at the same path, requires disposition | 197 |
| Absent at the same path | 9,750 |
| Sensitive/tool-policy name excluded from content reading | 31 |

These are not counts of missing features. In particular, 7,085 entries are temporary
verifier/test evidence. Other categories are 2,691 evidence/domain-data entries,
181 code/test/config entries, 9 other entries, and the 31 protected entries.
Among absent code/test/config entries there are 67 distinct paths. That figure
does not include ordinary unchanged files recorded only in source Git history.
There are also 74 canonical deletion-status records and 410 unified-package
deletion-status records. Do not blindly apply or reverse those deletions.

## Source head accounting

`Codex/<id>` means `C:/Users/ASUS/.codex/worktrees/<id>/perfume-chem`.
Unique counts mean `base..source_head`, not independent missing functionality.

| Source | Head | Relation to base | Unique commits |
|---|---|---|---:|
| Canonical | e7002d4d | descendant | 1 |
| Codex/4046 | aeefeaa1 | diverged | 94 |
| Codex/52e4 | 974ff473 | ancestor | 0 |
| Codex/6155 | 974ff473 | ancestor | 0 |
| Codex/6992 | 398800c5 | diverged | 17 |
| Codex/72bc | 0af42cc6 | descendant | 3 |
| Codex/a48f | 0af42cc6 | descendant | 3 |
| Codex/a7e6 | 482022c7 | diverged | 84 |
| Codex/b577 | 9f4c9f0f | diverged | 2 |
| Codex/c4d5 | 0af42cc6 | descendant | 3 |
| Codex/edd7 | 4b550054 | diverged | 36 |
| Codex/perceptual-architecture-v1 | af0d126e | diverged | 92 |
| Codex/publish-perfume-chem | 6be61989 | diverged | 34 |
| Canonical .worktrees/cypress-harmonic-synthesis-v1 | aeefeaa1 | diverged | 94 |
| Canonical .worktrees/cypress-mineral-traverse-v1 | 2290fa3a | diverged | 1 |
| perfume-chem-dpp-push | b69cb097 | diverged | 1 |
| perfume-chem-fi-runtime | b69cb097 | diverged | 1 |
| perfume-chem-push-8c2a607 | c235e397 | diverged | 1 |
| perfume-chem-unified-package | 0af42cc6 | descendant | 3 |

## Known dispositions

- Inventory successor: reconciled in the inventory checkpoint; do not replace it
  with older worktree inventory snapshots.
- Receipt replacement b69cb097: rejected because it removes exact receipt/input
  bindings. Compatible API repairs are recorded separately. Similar-subject
  c235e397 is not accepted merely because it has a different commit hash.
- Deep Plane: original evidence runtime retained; alternate diagnostics integrated
  separately and disabled by default. See existing Deep Plane checkpoints.
- Registry: immutable V1 plus append-only integration overlay retained. Historical
  registry chains do not authorize runtime activation.
- Character-profile cleanup: unfinished experiment removed; wider cleanup parked
  so it does not replace the worktree-consolidation objective.
- Temporary generated evidence: preserved privately; not a source-code import queue.
- Sensitive/provider/tool configuration: not imported by bulk operations.
- Formula revisions, remaining source modules, and deletion intent: pending
  dependency-aware, source-specific disposition; not silently accepted or discarded.

## Candidate dependency review

Commit a2d9fae4 (SolForge cancellation cleanup) changes a service and its tests.
Parent inspection confirmed both files are absent from the integration worktree:
this cannot be treated as an isolated two-file patch. Native read-only dependency
review identifies an absent workbench API/UI and SolForge engine, with a historical
registry API incompatible with the retained integration overlay. Security review
also remains necessary for endpoint exposure, inherited subprocess environment,
and captured process output. Classification: PENDING_COHERENT_FEATURE_REVIEW;
not an accepted import and not a reason to replace the current registry wholesale.

Commit a0d47a95 (migration packaging) also depends on an absent CI workflow;
it is not an independent three-file overwrite candidate.

## Next acceptance work

Group the 67 absent code/test/config paths and differing source versions into
coherent feature bundles, include their committed-only dependencies, and record
accepted/reconciled/superseded/excluded/pending outcomes per source. Start from
existing parent-reviewed inventory, receipt, and registry contracts. Recheck live
source hashes and run focused tests for each accepted bundle. Keep pre-existing
repository failures separate unless a bundle depends on them. No new whole-repo
test run was performed for this accounting-only checkpoint.
