# Build B Authoritative Reverification Design

## Goal

Seal Build B scientific-data authority from the final verified Build A checkpoint
`073ee8eaf66bd97a4894063c2f3ffc01c874e7b2`, using the current authoritative
working tree rather than historical reports or worker claims.

## Authority and scope

- `D:\chatbots\perfume-chem` is the only implementation authority.
- `D:\.prompts\perfume chem` remains read-only instruction material.
- Existing B0-B10 code, migrations, reports, and logs are historical leads until
  their current behavior is independently reproduced.
- Build C and Build D remain locked until the Build B completion gate passes and
  the Build B boundary report is presented.
- Sol is the sole head engineer and final approver. DeepLuna Fast may perform only
  bounded read audits after a fresh exact-project readiness check. No Codex
  subagents or fallback providers are permitted.

## Chosen approach

Reverify and repair the current tree in place, one phase at a time. Preserve the
dirty overlay and archive every affected path before edits. For each phase,
compare the master contract to current code, migrations, tests, databases, and
reports; reproduce the gate; write a failing regression for each confirmed
defect; apply the smallest root-cause fix; rerun focused and cumulative gates;
then commit only the phase-owned paths.

This approach is preferred over resetting to historical Build B commits because
resetting would discard or obscure the authoritative overlay. It is preferred
over a separate worktree because Build B must measure the actual current tree,
including preserved user work. It is preferred over accepting the historical
B10 seal because Build A subsequently changed canonical code, tests, verifier
counts, database observations, and report authority.

## Phase architecture

### B0: current scientific truth baseline

Repair deterministic inventory generation, exclude transient and secret-bearing
state, generate the current machine-readable inventory from the final Build A
boundary plus preserved overlay, and update the B0 report. B0 must report source
digests, consumers, authority classes, conflicts, compatibility behavior, and
claim impacts without promoting any scientific value.

### B1-B4: evidence and interpretation authority

Verify the linear source-to-observation path: immutable source documents and
extractions, typed property observations and selected assertions, contextual
threshold/OAV matching, and compiled knowledge rules. Legacy values remain
explicitly heuristic or advisory. Mismatched context, unresolved conflict,
generic identities, or unsupported rules must fail closed.

### B5-B9: analytical, regulatory, claim, backfill, and reporting authority

Verify method/run/raw-file/QC/identity/quantity chains, dated and jurisdictional
regulatory snapshots, claim-specific sufficiency policies, decision-value
backfill, and API/report projections. Current official regulatory facts are
rechecked from primary sources when B6 is reached. No result may be described as
certification, legal advice, scientific release, or real-world performance
validation.

### B10: cumulative seal

Run the required Build B matrix, migration-chain checks, protected-database
checks, artifact verification, and the repository-wide canonical verifier with
captured stdout/stderr, ANSI disabled, and explicit timeouts. Replace the final
Build B reports only from those live results, then obtain one bounded Fast-only
audit and reconcile it locally before final acceptance.

## State preservation

Before each first edit, create a path-preserving archive outside the edited path
set, list its members, extract it to a verification directory, and compare every
restored file hash to its source. Never clean or reset unrelated tracked or
untracked files. Protected databases are inspected read-only; migrations run
only against disposable databases unless a later contract explicitly requires
otherwise.

## Verification contract

- Python: repository-supported CPython 3.11 environments.
- Node: repository-supported Node runtime.
- Execution: non-PTY, `NO_COLOR=1`, `TERM=dumb`, separate stdout/stderr, explicit
  timeout, and terminal exit evidence.
- Tests: RED before implementation, then focused GREEN, cumulative phase GREEN,
  static checks, migration head/upgrade/downgrade/restore where required, and
  final full verification.
- DeepLuna: fresh exact-project `deepseek_check` immediately before each bounded
  Fast call; `FLASH`, one provider call, `NO_LUNA`, no writes, no secrets.
- Reports: machine-readable and human-readable evidence must state source SHA,
  current counts, skips, unknowns, protected-state hashes, and permitted claim
  wording.

## Failure handling

The earliest failed phase blocks all descendants. Local packing or range errors
are corrected before transmission and are not provider evidence. Provider
unavailability stops paid work but does not prevent deterministic local
diagnostics. A failed test is investigated to root cause before any fix; three
failed fix hypotheses trigger an architecture review rather than another patch.

## Completion condition

Build B completes only when B0-B10 are current and reproducible, every runtime
scientific value is traceable or visibly heuristic, contextual and authority
gates fail closed, the full verifier passes with only explicitly optional skips,
and the final reports make no scientific-release claim. Work then stops at the
Build B boundary before Build C.
