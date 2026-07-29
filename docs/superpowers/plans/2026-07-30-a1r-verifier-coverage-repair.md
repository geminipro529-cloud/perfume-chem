# A1R Verifier Coverage Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` inline. Codex subagents are prohibited by the
> repository contract.

**Goal:** Make canonical verification lint and type-check every A1 production
module, remove the six live Ruff findings without behavior changes, and create
a verified A1R checkpoint before A2.

**Architecture:** Keep the existing verifier command structure and extend its
explicit target sets. Preserve the public mathematical `N` keyword while
renaming private/local variables. Use one regression test to bind verifier
coverage and existing behavioral tests to prove numerical compatibility.

**Tech Stack:** Python 3.11, pytest, Ruff, MyPy, Git, the repository's
`engine.project_verification` verifier.

---

### Task 1: Preserve the authoritative live tree

**Files:**
- Evidence:
  `C:\Users\ASUS\Documents\Codex\2026-07-29\the-perfume-chem-folder-is-the\outputs\a1r-preedit-recovery\perfume-chem-a0-20260729T185259Z`

- [x] **Step 1: Capture committed history and tracked overlays**

Use the established recovery script to create a Git bundle, binary patch, and
byte-exact tracked overlay ZIP.

- [x] **Step 2: Capture untracked and important ignored files**

Create path-preserving local-only ZIP archives. Do not print, commit, or
transmit secret-bearing bytes.

- [x] **Step 3: Verify restoration**

Clone the bundle, apply the patch and tracked overlay, extract the untracked
and ignored archives, and compare restored byte lengths and SHA-256 values.

Expected: `restoration_verified=true`,
`source_changed_during_archive_count=0`.

### Task 2: Bind A1 verifier coverage with a RED test

**Files:**
- Modify: `tests/test_project_verification.py`
- Test: `tests/test_project_verification.py`

- [ ] **Step 1: Add the failing coverage assertion**

Extend `test_verifier_commands_include_required_flags_and_targets` with:

```python
a1_targets = {
    "engine/domain_errors.py",
    "engine/units/concentration.py",
    "engine/target/formula.py",
    "engine/reconstruction/anti_compression.py",
    "engine/bottle/events.py",
    "engine/reconstruction/rank_prior.py",
    "engine/reconstruction/ensembles.py",
    "engine/reconstruction/chassis.py",
    "engine/reconstruction/recognizer.py",
    "engine/inventory/stock_model.py",
    "engine/identity/resolver.py",
}
assert a1_targets <= set(specs["engine-lint"].command)
assert a1_targets <= set(specs["engine-typecheck"].command)
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
$env:NO_COLOR='1'
$env:TERM='dumb'
& $supportedPython -m pytest `
  tests/test_project_verification.py::test_verifier_commands_include_required_flags_and_targets `
  -q --color=no -p no:cacheprovider
```

Expected: FAIL because the A1 target set is absent from one or both commands.

### Task 3: Extend canonical verifier targets

**Files:**
- Modify: `engine/project_verification.py:251`
- Test: `tests/test_project_verification.py`

- [ ] **Step 1: Add all A1 paths to `engine-lint`**

Append the exact `a1_targets` paths from Task 2 to the Ruff command tuple.
Do not broaden Ruff to the whole dirty repository.

- [ ] **Step 2: Add all A1 paths to `engine-typecheck`**

Append the same A1 paths to the MyPy command tuple. Preserve:

```text
--explicit-package-bases
--follow-imports=skip
--ignore-missing-imports
```

- [ ] **Step 3: Run the coverage test**

Run the Task 2 command.

Expected: PASS.

### Task 4: Remove six Ruff findings without changing behavior

**Files:**
- Modify: `engine/reconstruction/ensembles.py:44`
- Modify: `engine/reconstruction/ensembles.py:208`
- Modify: `engine/reconstruction/rank_prior.py:159`
- Modify: `engine/reconstruction/rank_prior.py:206`
- Modify: `engine/reconstruction/recognizer.py:50`
- Test: `tests/test_reconstruction_ensembles.py`
- Test: `tests/test_reconstruction_rank_prior.py`
- Test: `tests/test_a1_authoritative_contracts.py`

- [ ] **Step 1: Rename the private inline-prior parameter**

In `_inline_rank_prior`, rename `N` to `material_count` and update validation,
range, and break conditions. Preserve the error's mathematical `N` wording.

```python
def _inline_rank_prior(
    ordered_materials: list[str],
    total_budget: float,
    p: float,
    material_count: int,
) -> dict[str, float]:
```

- [ ] **Step 2: Preserve the public `generate_ensemble` keyword**

Keep `N` because existing tests call `generate_ensemble(..., N=10)`. Add only
the narrow inline Ruff suppression:

```python
    N: int = 70,  # noqa: N803 - public mathematical compatibility
```

- [ ] **Step 3: Rename rank-prior locals**

Use:

```python
material_count = config.N
total_budget = config.B
```

and:

```python
material_count = len(material_names)
adapted = RankPriorConfig(
    N=material_count,
    B=config.B,
    p=config.p,
    label=config.label,
)
```

Update only references to those local variables.

- [ ] **Step 4: Rename the recognizer local mapping**

Change `_ROLE_WEIGHTS` to `role_weights` and update the local lookup. Correct
the docstring reference to say “role-weight mapping.”

- [ ] **Step 5: Run focused behavioral tests**

Run:

```powershell
& $supportedPython -m pytest `
  tests/test_project_verification.py `
  tests/test_reconstruction_ensembles.py `
  tests/test_reconstruction_rank_prior.py `
  tests/test_a1_authoritative_contracts.py `
  -q --color=no -p no:cacheprovider
```

Expected: all selected tests PASS.

- [ ] **Step 6: Run expanded Ruff and MyPy**

Run canonical `engine-lint` and `engine-typecheck` through:

```powershell
& $supportedPython scripts/pipeline_audit.py project-verify `
  --only engine-lint --json
& $supportedPython scripts/pipeline_audit.py project-verify `
  --only engine-typecheck --json
```

Expected: both selected checks PASS and include every A1 target.

### Task 5: Run the A1R exit gate

**Files:**
- Create outside repository:
  `outputs/perfume-chem-a1r-20260730/A1R_IMPLEMENTATION_REPORT.md`
- Create outside repository:
  `outputs/perfume-chem-a1r-20260730/A1R_MACHINE_REPORT.json`
- Create outside repository:
  `outputs/perfume-chem-a1r-20260730/A1R_DELIVERABLES_MANIFEST.json`

- [ ] **Step 1: Run the complete root suite**

```powershell
& $supportedPython -m pytest tests -q --color=no `
  --disable-warnings -p no:cacheprovider
```

Expected: 999 or more passed, zero failed.

- [ ] **Step 2: Run the complete backend suite**

From `backend`:

```powershell
& $supportedPoetry run pytest -q --color=no `
  --disable-warnings -p no:cacheprovider
```

Expected: 190 or more passed, zero failed.

- [ ] **Step 3: Run artifact verification**

```powershell
& $supportedPython scripts/pipeline_audit.py artifact-verify --json
```

Expected: exit zero; no blocking `STALE` or `TAMPERED` status. Quarantined and
unbound legacy artifacts remain non-current and non-promoting.

- [ ] **Step 4: Run the canonical verifier**

```powershell
& $supportedPython scripts/pipeline_audit.py project-verify --json
```

Expected: every required check PASS. Docker may be SKIPPED only when unavailable
and must remain explicitly optional.

- [ ] **Step 5: Verify preservation and scope**

Confirm:

```text
HEAD starts at f55d4b3b2e4ccf23105045b25ab1628fa4b67a54
no migration file changed
no database file changed
user-owned API/schema/test changes remain present
only A1R files and approved docs are staged
```

- [ ] **Step 6: Create the bounded A1R checkpoint**

Stage only:

```text
docs/superpowers/specs/2026-07-30-a1r-a2-staged-convergence-design.md
docs/superpowers/plans/2026-07-30-a1r-verifier-coverage-repair.md
engine/project_verification.py
engine/reconstruction/ensembles.py
engine/reconstruction/rank_prior.py
engine/reconstruction/recognizer.py
tests/test_project_verification.py
```

Commit:

```text
build(a1r): close verifier coverage gap
```

- [ ] **Step 7: Validate reports and stop**

Hash every A1R deliverable, validate JSON, record the checkpoint SHA, and stop
before A2.
