# Build B10 scientific-data authority verification plan

> **Execution authority:** The controlling master prompt and the user's
> standing instruction authorize Sol to execute without conversational
> approval pauses. Sol remains final authority. DeepLuna Fast is read-only,
> Fast-only, one-call bounded, and has no Luna or Codex fallback.

**Goal:** Produce current executable evidence for all B10 requirements, write
the two required Build B authority reports, and stop before Build C.

**Runtime:** Python
`D:\chatbots\perfume-chem\output\verification-envs\a2-slice2-py311\Scripts\python.exe`
and Node `v26.3.0`.

**Recovery checkpoint:**
`D:\.backups\perfume-chem\build-b10-prewrite-20260731T103332+0700.tar`

## Task 1: Freeze design and report inputs

Files:

- `docs/superpowers/specs/2026-07-31-build-b10-scientific-authority-verification-design.md`
- `docs/superpowers/plans/2026-07-31-build-b10-scientific-authority-verification.md`

Checks:

- B10 and Build B completion requirements are transcribed exactly;
- no production or migration change is planned;
- baseline and final SHA meanings are explicit;
- report authority is non-promoting; and
- every report input has a canonical local source.

Commit:

```text
docs: freeze Build B10 verification design
docs: plan Build B10 verification
```

## Task 2: Reproduce the required scientific test matrix

Run the twenty current source, observation, threshold, rule, analytical,
regulatory, claim-authority, API, export, and backup/restore test files
identified by the B10 coverage audit.

Capture:

- exact command and test files;
- pytest count and duration;
- stdout/stderr separately;
- timeout and exit code; and
- test-node inventory used by each of the nineteen report categories.

Gate:

- exit `0`;
- no timeout;
- no uncategorized B10 requirement; and
- no historical PASS used as current proof.

## Task 3: Verify the frozen B0 inventory and Build B gates

Read and hash:

- `docs/verification/b0/scientific_truth_inventory.json.gz`;
- `docs/verification/b0/scientific_truth_baseline.json`;
- B1 through B9 gate JSON; and
- the B8 current-inventory projection.

Recompute:

- compressed/decompressed digests;
- source/material/observation/constant/rule/conflict counts;
- authority-label counts;
- each phase decision and migration head;
- migrated/backfilled canonical row count; and
- protected-database hashes.

Gate:

- every recomputed value matches the committed gate evidence;
- legacy inventory is never described as canonical migrated authority; and
- the current Alembic graph has one head at `20260731_0012`.

## Task 4: Run the repository verifier

Run:

```powershell
python scripts/pipeline_audit.py project-verify --json --output <B10 log path>
```

Use:

- no PTY;
- `NO_COLOR=1`, `TERM=dumb`, and equivalent tool-specific controls;
- explicit process timeout; and
- captured stdout/stderr.

Gate:

- completion gate `PASS`;
- all mandatory non-Docker checks are current;
- any optional skip is named and justified; and
- Docker is not silently assumed.

If this gate fails, use systematic debugging to identify whether the failure
is a Build B defect, a preserved unrelated-work defect, or verifier
infrastructure. Do not suppress a real failure.

## Task 5: Write the report artifact contract RED

File:

- `tests/test_scientific_data_authority_report.py`

Tests:

- both required report files exist;
- machine schema and status are closed;
- four Git checkpoint roles are explicit;
- all required inventories and call graphs exist;
- exactly nineteen required-test rows exist;
- exactly ten Build B completion rows exist;
- evidence labels remain separate;
- exact B7 permitted/forbidden wording matches;
- remaining unknowns are nonempty and visible;
- no scientific-release authority is asserted; and
- Markdown and JSON agree.

Run the focused test and record the intended missing-artifact failure.

Commit:

```text
test: define Build B10 authority report contract
```

## Task 6: Assemble the required reports

Files:

- `docs/verification/scientific_data_authority_report.json`
- `docs/verification/scientific_data_authority_report.md`

Required content:

- baseline/final SHA;
- source and observation inventory;
- migrated data;
- conflicts and selected-assertion policies;
- contextual ODT authority;
- knowledge-rule status;
- analytical validation matrix;
- regulatory snapshots;
- before/after runtime call graph;
- current verifier output;
- remaining unknowns;
- exact permitted and forbidden wording;
- all nineteen current test categories; and
- all ten Build B completion decisions.

Run the focused report test until GREEN.

Commit:

```text
docs: assemble Build B scientific authority report
```

## Task 7: Run final compatibility and static gates

Run:

- the complete A2 through B9 canonical compatibility list plus the B10
  artifact test;
- Ruff on B10 test and any verifier helper;
- mypy on any new Python source;
- Node syntax where applicable;
- `alembic heads`;
- immutable read-only `PRAGMA quick_check`;
- B10 recovery-archive SHA/tar verification;
- protected database before/after hashes;
- all report JSON parses and digest reconciliation;
- ANSI byte scan; and
- credential-shaped value scan that returns only counts/path names.

No full-suite success is inferred from a subset.

## Task 8: Run final bounded DeepLuna Fast review

After a fresh exact-project `deepseek_check` returns `READY`, submit one
read-only Flash task over:

- the B10 design/plan;
- both final reports;
- the artifact contract test;
- required-test and compatibility logs;
- full verifier result;
- inventory and database checks; and
- recovery evidence.

Constraints:

- `FLASH`;
- `NO_LUNA`;
- one attempt and one provider call;
- explicit read allowlist/ranges;
- no commands, writes, environment access, or final acceptance authority.

Sol must reproduce or reject every finding.

## Task 9: Seal Build B and stop

Update reports only for verified final facts, run the focused report test and
package validation again, then commit exact B10 evidence paths.

Confirm:

- B10 paths are clean after commit;
- unrelated work is unchanged;
- Build B status is PASS or candidly BLOCKED;
- no release claim is made; and
- Build C files have not been read or changed beyond the already-read mission
  boundary required to identify the stop point.

Stop and present the Build B evidence report. Do not begin Build C.
